package ai.helixor.runtime.regulatorypiiguard.model;

import java.util.List;

/**
 * The state changes that together clear every necessary cause: one change per
 * cause, all of which must hold. targetFactor, requiredValue and delta repeat the
 * first change.
 */
public record Counterfactual(
    String remedy,
    String targetFactor,
    Object requiredValue,
    Double delta,
    List<CounterfactualChange> changes
) {}
