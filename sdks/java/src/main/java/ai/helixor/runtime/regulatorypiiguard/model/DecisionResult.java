package ai.helixor.runtime.regulatorypiiguard.model;

import java.util.List;

/**
 * Decision for compliance.regulatory_pii_guard.v1. {@code action} is the action the first firing
 * hard rule declares (the pack's default action when none fires); {@code verdict}
 * is "approve" or "refuse".
 */
public record DecisionResult(
    String packId,
    String action,
    String verdict,
    double confidence,
    String proofSha256,
    double latencyUs,
    String executionMode,
    List<NecessaryCause> necessaryCauses,
    Counterfactual counterfactual
) {
    public boolean isApproved() {
        return "approve".equals(verdict);
    }
}
