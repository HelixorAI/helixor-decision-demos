package ai.helixor.runtime.regulatorypiiguard.model;

public record Counterfactual(
    String remedy,
    String targetFactor,
    Object requiredValue,
    Double delta,
    double feasibility
) {}
