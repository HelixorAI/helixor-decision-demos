package ai.helixor.runtime.regulatorypiiguard.model;

/**
 * A state change that stops one cause from firing: {@code factor relation requiredValue}.
 */
public record CounterfactualChange(
    String rule,
    String factor,
    String relation,
    Object requiredValue,
    Object observedValue,
    Double delta
) {}
