package ai.helixor.runtime.regulatorypiiguard.model;

public record NecessaryCause(
    String factor,
    Object observedValue,
    Double threshold,
    String direction,
    Double distanceToBoundary
) {}
