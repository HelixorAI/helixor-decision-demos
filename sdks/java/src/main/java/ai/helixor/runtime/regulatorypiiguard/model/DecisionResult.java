package ai.helixor.runtime.regulatorypiiguard.model;

import java.util.List;

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
        return "approve".equalsIgnoreCase(verdict);
    }
}
