package ai.helixor.runtime.regulatorypiiguard.playbook;

import ai.helixor.runtime.DecisionResult;
import ai.helixor.runtime.HelixorPlaybook;
import ai.helixor.runtime.NecessaryCause;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Bytecode-executable decision playbook for compliance.regulatory_pii_guard.v1.
 * Evaluates decisions directly in-process with zero C-FFI or JNI overhead.
 */
public class RegulatoryPiiGuardPlaybook implements HelixorPlaybook {

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
        List<NecessaryCause> causes = new ArrayList<>();
        boolean passed = true;

        Object val_has_ssn = state.get("has_ssn");
        if (!(val_has_ssn instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_ssn' (boolean) is required by rule 'RULE-GLBA-SSN-BLOCK'");
        }
        if (Boolean.TRUE.equals(val_has_ssn)) {
            passed = false;
            causes.add(new NecessaryCause("has_ssn", 1.0, 0.0, "RULE-GLBA-SSN-BLOCK"));
        }
        Object val_has_credit_card = state.get("has_credit_card");
        if (!(val_has_credit_card instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_credit_card' (boolean) is required by rule 'RULE-PCI-DSS-PAN-BLOCK'");
        }
        if (Boolean.TRUE.equals(val_has_credit_card)) {
            passed = false;
            causes.add(new NecessaryCause("has_credit_card", 1.0, 0.0, "RULE-PCI-DSS-PAN-BLOCK"));
        }
        Object val_has_health_record = state.get("has_health_record");
        if (!(val_has_health_record instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_health_record' (boolean) is required by rule 'RULE-HIPAA-PHI-BLOCK'");
        }
        if (Boolean.TRUE.equals(val_has_health_record)) {
            passed = false;
            causes.add(new NecessaryCause("has_health_record", 1.0, 0.0, "RULE-HIPAA-PHI-BLOCK"));
        }
        Object val_has_email = state.get("has_email");
        if (!(val_has_email instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_email' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (Boolean.TRUE.equals(val_has_email)) {
            passed = false;
            causes.add(new NecessaryCause("has_email", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
        }
        Object val_has_phone = state.get("has_phone");
        if (!(val_has_phone instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_phone' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (Boolean.TRUE.equals(val_has_phone)) {
            passed = false;
            causes.add(new NecessaryCause("has_phone", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
        }
        Object val_has_ip = state.get("has_ip");
        if (!(val_has_ip instanceof Boolean)) {
            throw new IllegalArgumentException("State attribute 'has_ip' (boolean) is required by rule 'RULE-GDPR-CONTACT-REDACT'");
        }
        if (Boolean.TRUE.equals(val_has_ip)) {
            passed = false;
            causes.add(new NecessaryCause("has_ip", 1.0, 0.0, "RULE-GDPR-CONTACT-REDACT"));
        }

        String action = passed ? "permit_clean_payload" : "block_glba_ssn_leakage";
        String verdict = passed ? "compliant" : "refuse";

        return new DecisionResult(
            action,
            verdict,
            passed,
            1.0,
            merkleRoot(),
            packId(),
            causes,
            null
        );
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

    @Override
    public String merkleRoot() {
        return "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08";
    }
}
