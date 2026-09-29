package ai.helixor.runtime.regulatorypiiguard.playbook;

import ai.helixor.runtime.DecisionResult;
import ai.helixor.runtime.HelixorPlaybook;
import ai.helixor.runtime.NecessaryCause;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Bytecode-executable decision playbook for compliance.regulatory_pii_guard.v1.
 *
 * <p>Hard rules run in priority order. The first rule that fires sets the action
 * (the pack's default action when none fires); every firing rule term is a
 * necessary cause. Verdicts use the runtime vocabulary: "compliant" or
 * "invariant_breach".
 */
public class RegulatoryPiiGuardPlaybook implements HelixorPlaybook {

    static final String DEFAULT_ACTION = "permit_clean_payload";

    static {
        try {
            ai.helixor.runtime.entrypoint.HelixorNativeEntryPoints.registerPlaybook(new RegulatoryPiiGuardPlaybook());
        } catch (Throwable ignored) {
            // In standard OpenJDK runtimes where GraalVM C-ABI entrypoints are unused, ignore gracefully
        }
    }

    @Override
    public String packId() {
        return "compliance.regulatory_pii_guard.v1";
    }

    @Override
    public DecisionResult decide(Map<String, Object> state) {
        long startNs = System.nanoTime();
        List<NecessaryCause> causes = new ArrayList<>();
        String firedAction = null;

        Object v0 = state.get("has_ssn");
        if (!(v0 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_ssn' (boolean) is required by rule 'RULE-GLBA-SSN-BLOCK'");
        }
        if (((Boolean) v0) == true) {
            causes.add(new NecessaryCause("has_ssn", 1.0, 0.0, "RULE-GLBA-SSN-BLOCK"));
            if (firedAction == null) {
                firedAction = "block_glba_ssn_leakage";
            }
        }
        Object v1 = state.get("has_credit_card");
        if (!(v1 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_credit_card' (boolean) is required by rule 'RULE-PCI-DSS-PAN-BLOCK'");
        }
        if (((Boolean) v1) == true) {
            causes.add(new NecessaryCause("has_credit_card", 1.0, 0.0, "RULE-PCI-DSS-PAN-BLOCK"));
            if (firedAction == null) {
                firedAction = "block_pci_dss_pan_leakage";
            }
        }
        Object v2 = state.get("has_health_record");
        if (!(v2 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_health_record' (boolean) is required by rule 'RULE-HIPAA-PHI-BLOCK'");
        }
        if (((Boolean) v2) == true) {
            causes.add(new NecessaryCause("has_health_record", 1.0, 0.0, "RULE-HIPAA-PHI-BLOCK"));
            if (firedAction == null) {
                firedAction = "block_hipaa_phi_leakage";
            }
        }
        Object v3 = state.get("has_email");
        if (!(v3 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_email' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (((Boolean) v3) == true) {
            causes.add(new NecessaryCause("has_email", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
            if (firedAction == null) {
                firedAction = "redact_and_permit_contact_pii";
            }
        }
        Object v4 = state.get("has_phone");
        if (!(v4 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_phone' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (((Boolean) v4) == true) {
            causes.add(new NecessaryCause("has_phone", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
            if (firedAction == null) {
                firedAction = "redact_and_permit_contact_pii";
            }
        }
        Object v5 = state.get("has_ip");
        if (!(v5 instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_ip' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (((Boolean) v5) == true) {
            causes.add(new NecessaryCause("has_ip", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
            if (firedAction == null) {
                firedAction = "redact_and_permit_contact_pii";
            }
        }

        boolean passed = firedAction == null;
        String action = passed ? DEFAULT_ACTION : firedAction;
        String verdict = passed ? "compliant" : "invariant_breach";
        double latencyUs = (System.nanoTime() - startNs) / 1000.0;

        return new DecisionResult(
            action,
            verdict,
            passed,
            latencyUs,
            decisionProof(action, verdict, state),
            packId(),
            causes,
            null
        );
    }

    /** SHA-256 over pack id, action, verdict and the state with sorted keys. */
    private String decisionProof(String action, String verdict, Map<String, Object> state) {
        StringBuilder canonical = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : new TreeMap<>(state).entrySet()) {
            if (!first) {
                canonical.append(',');
            }
            first = false;
            canonical.append('"').append(escape(entry.getKey())).append("\":");
            Object value = entry.getValue();
            if (value == null || value instanceof Boolean || value instanceof Number) {
                canonical.append(value);
            } else {
                canonical.append('"').append(escape(String.valueOf(value))).append('"');
            }
        }
        canonical.append('}');
        String preimage = packId() + ":" + action + ":" + verdict + ":" + canonical;
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(preimage.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : digest) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is unavailable", e);
        }
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    @org.graalvm.nativeimage.c.function.CEntryPoint(name = "helixor_playbook_execute")
    public static int executeNativeDecision(
        org.graalvm.nativeimage.IsolateThread thread,
        org.graalvm.nativeimage.c.type.CCharPointer packIdPtr,
        org.graalvm.nativeimage.c.type.CCharPointer stateJsonPtr,
        org.graalvm.nativeimage.c.type.CCharPointer outputBufPtr,
        int bufLen
    ) {
        return ai.helixor.runtime.entrypoint.HelixorNativeEntryPoints.executeDecision(thread, packIdPtr, stateJsonPtr, outputBufPtr, bufLen);
    }

    /** SHA-256 Merkle root of the canonical pack payload (from the pack manifest). */
    @Override
    public String merkleRoot() {
        return "d924f870db0232502ca7cdaee40f1403d99c7348cf25b40e5a90dd2b3d2555ee";
    }
}
