package ai.helixor.runtime.regulatorypiiguard.model;

/**
 * One hard-rule term that fired. Numeric terms carry threshold and distance;
 * boolean terms do not.
 */
public record NecessaryCause(
    String factor,
    Object observedValue,
    Double threshold,
    String direction,
    Double distanceToBoundary,
    String rule,
    String ruleVerdict
) {}
