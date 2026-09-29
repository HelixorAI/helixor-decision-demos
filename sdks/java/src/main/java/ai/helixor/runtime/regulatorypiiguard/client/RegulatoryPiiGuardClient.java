package ai.helixor.runtime.regulatorypiiguard.client;

import ai.helixor.runtime.regulatorypiiguard.model.*;
import ai.helixor.runtime.HelixorNativeRuntime;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * In-process decision client for compliance.regulatory_pii_guard.v1.
 *
 * <p>The first hard rule that fires sets the action ({@value #DEFAULT_ACTION} when
 * none fires). Every firing rule term is a necessary cause, and the counterfactual
 * lists one change per cause. Results from the runtime are checked against the
 * pack's rules; a mismatch throws IllegalStateException.
 *
 * <p>The audit ledger exists only in the native C runtime: {@link #auditAvailable()}
 * says whether it is loaded, and {@link #getAuditReport()} throws
 * {@link AuditReportUnavailableException} when it is not.
 */
public class RegulatoryPiiGuardClient implements AutoCloseable {

    /** Hard-rule term, in priority order, generated from the pack IR. */
    private record Term(String rule, String ruleVerdict, String action, String factor, String operator, Double threshold) {
        boolean isBoolean() {
            return "is_true".equals(operator) || "is_false".equals(operator);
        }
    }

    private static final List<Term> TERMS = List.of(
        new Term("RULE-GLBA-SSN-BLOCK", "refuse", "block_glba_ssn_leakage", "has_ssn", "is_true", null),
        new Term("RULE-PCI-DSS-PAN-BLOCK", "refuse", "block_pci_dss_pan_leakage", "has_credit_card", "is_true", null),
        new Term("RULE-HIPAA-PHI-BLOCK", "refuse", "block_hipaa_phi_leakage", "has_health_record", "is_true", null),
        new Term("RULE-GDPR-CONTACT-REDACT", "refuse", "redact_and_permit_contact_pii", "has_email", "is_true", null),
        new Term("RULE-GDPR-CONTACT-REDACT", "refuse", "redact_and_permit_contact_pii", "has_phone", "is_true", null),
        new Term("RULE-GDPR-CONTACT-REDACT", "refuse", "redact_and_permit_contact_pii", "has_ip", "is_true", null)
    );

    public static final String DEFAULT_ACTION = "permit_clean_payload";

    private static final Map<String, String> COMPLIANT_RELATION = Map.of(
        ">", "<=", "<", ">=", ">=", "<", "<=", ">", "==", "!=", "is_true", "==", "is_false", "=="
    );

    private final HelixorNativeRuntime runtime;
    private final String packId;

    public RegulatoryPiiGuardClient(Path bundlePath) throws IOException {
        this.runtime = new HelixorNativeRuntime();
        if (bundlePath != null) {
            this.runtime.loadBundle(bundlePath);
        }
        this.packId = "compliance.regulatory_pii_guard.v1";
    }

    public RegulatoryPiiGuardClient(HelixorNativeRuntime sharedRuntime, String packId) {
        this.runtime = sharedRuntime;
        this.packId = packId != null ? packId : "compliance.regulatory_pii_guard.v1";
    }

    public DecisionResult decide(RegulatoryPiiGuardState state) {
        long startNs = System.nanoTime();
        ai.helixor.runtime.DecisionResult raw = runtime.decide(packId, state.toJson());
        double latencyUs = (System.nanoTime() - startNs) / 1000.0;

        List<NecessaryCause> causes = normalizeCauses(raw.necessaryCauses());
        String verdict = mapVerdict(raw.verdict());
        if ("approve".equals(verdict) != causes.isEmpty()) {
            throw new IllegalStateException("Runtime returned verdict '" + raw.verdict() + "' with "
                + causes.size() + " necessary cause(s) for pack " + packId);
        }
        String action = causes.isEmpty() ? DEFAULT_ACTION : actionOf(causes.get(0).rule());
        if (!action.equals(raw.action())) {
            throw new IllegalStateException("Runtime returned action '" + raw.action() + "'; pack " + packId
                + " selects '" + action + "' for these causes");
        }

        return new DecisionResult(
            "compliance.regulatory_pii_guard.v1",
            action,
            verdict,
            1.0,
            raw.proofSha256(),
            latencyUs,
            executionMode(),
            causes,
            counterfactual(causes)
        );
    }

    /** True when the native C runtime, which keeps the audit ledger, is loaded. */
    public boolean auditAvailable() {
        return runtime.isNativeLoaded();
    }

    public TrueUpReport getAuditReport() {
        if (!auditAvailable()) {
            throw new AuditReportUnavailableException(
                "The audit ledger is kept by the native C runtime (libhelixor_runtime), which is not loaded");
        }
        var r = runtime.getAuditReport();
        return new TrueUpReport(
            r.licenseId(),
            r.tenantId(),
            r.tier(),
            r.enforcementMode(),
            r.totalDecisionsExecuted(),
            r.decisionsOverQuota(),
            r.decisionsOverRateLimit(),
            r.ledgerMerkleRoot()
        );
    }

    private String executionMode() {
        if (runtime.hasBytecodePack(packId)) {
            return "embedded_bytecode";
        }
        return runtime.isPanamaActive() ? "graalvm_panama_native" : "embedded_native";
    }

    private static String mapVerdict(String raw) {
        if ("compliant".equals(raw)) {
            return "approve";
        }
        if ("invariant_breach".equals(raw) || "refuse".equals(raw)) {
            return "refuse";
        }
        throw new IllegalStateException("Runtime returned an unknown verdict: " + raw);
    }

    private static String actionOf(String rule) {
        for (Term t : TERMS) {
            if (t.rule().equals(rule)) {
                return t.action();
            }
        }
        throw new IllegalStateException("Unknown rule " + rule);
    }

    private static List<NecessaryCause> normalizeCauses(List<ai.helixor.runtime.NecessaryCause> raw) {
        List<int[]> order = new ArrayList<>();
        List<NecessaryCause> byOrder = new ArrayList<>();
        if (raw != null) {
            for (var c : raw) {
                int index = -1;
                for (int i = 0; i < TERMS.size(); i++) {
                    if (TERMS.get(i).rule().equals(c.rule()) && TERMS.get(i).factor().equals(c.factor())) {
                        index = i;
                        break;
                    }
                }
                if (index < 0) {
                    throw new IllegalStateException("Runtime reported cause " + c.factor() + " (rule " + c.rule()
                        + "), which is not a hard-rule term of the pack");
                }
                Term t = TERMS.get(index);
                NecessaryCause cause = t.isBoolean()
                    // A boolean term fires only on its breach value.
                    ? new NecessaryCause(t.factor(), "is_true".equals(t.operator()), null, t.operator(), null,
                        t.rule(), t.ruleVerdict())
                    : new NecessaryCause(t.factor(), c.observed(), t.threshold(), t.operator(),
                        Math.abs(c.observed() - t.threshold()), t.rule(), t.ruleVerdict());
                order.add(new int[] {index, byOrder.size()});
                byOrder.add(cause);
            }
        }
        order.sort(Comparator.comparingInt(pair -> pair[0]));
        List<NecessaryCause> causes = new ArrayList<>();
        for (int[] pair : order) {
            causes.add(byOrder.get(pair[1]));
        }
        return causes;
    }

    private static Counterfactual counterfactual(List<NecessaryCause> causes) {
        if (causes.isEmpty()) {
            return null;
        }
        List<CounterfactualChange> changes = new ArrayList<>();
        StringBuilder remedy = new StringBuilder();
        for (NecessaryCause c : causes) {
            boolean isBoolean = "is_true".equals(c.direction()) || "is_false".equals(c.direction());
            Object required = isBoolean ? (Object) "is_false".equals(c.direction()) : (Object) c.threshold();
            Double delta = isBoolean ? null : c.threshold() - ((Number) c.observedValue()).doubleValue();
            String relation = COMPLIANT_RELATION.get(c.direction());
            changes.add(new CounterfactualChange(c.rule(), c.factor(), relation, required, c.observedValue(), delta));
            if (remedy.length() > 0) {
                remedy.append("; ");
            }
            remedy.append(c.factor()).append(' ').append(relation).append(' ').append(required)
                .append(" (rule ").append(c.rule()).append(')');
        }
        CounterfactualChange first = changes.get(0);
        return new Counterfactual(remedy.toString(), first.factor(), first.requiredValue(), first.delta(), changes);
    }

    @Override
    public void close() {
        // Resource cleanup managed by runtime lifecycle
    }
}
