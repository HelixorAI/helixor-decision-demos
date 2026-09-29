package ai.helixor.runtime.regulatorypiiguard.model;

public record TrueUpReport(
    String licenseId,
    String tenantId,
    String tier,
    String enforcementMode,
    long totalDecisionsExecuted,
    long decisionsOverQuota,
    long decisionsOverRateLimit,
    String ledgerMerkleRoot
) {}
