"""Domain models for RegulatoryPiiGuard decision evaluation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DecisionVerdict(str, Enum):
    APPROVE = "approve"
    REFUSE = "refuse"
    ESCALATE = "escalate"
    DEFER = "defer"


class NecessaryCause(BaseModel):
    """Causal factor driving a refusal or constraint violation."""
    factor: str
    observed_value: Any
    threshold: Optional[float] = None
    direction: Optional[str] = None
    distance_to_boundary: Optional[float] = None


class Counterfactual(BaseModel):
    """Judea Pearl Level 3 prescriptive remedy identifying minimal state perturbation."""
    remedy: str
    target_factor: str
    required_value: Any
    delta: Optional[float] = None
    feasibility: float = 1.0


class TrueUpReport(BaseModel):
    """Usage counts and Merkle ledger root from libhelixor_runtime; pricing belongs to billing."""
    license_id: str
    tenant_id: str
    tier: str
    enforcement_mode: str
    total_decisions_executed: int
    decisions_over_quota: int
    decisions_over_rate_limit: int
    ledger_merkle_root: str


class RegulatoryPiiGuardState(BaseModel):
    """Strongly-typed entity state for compliance.regulatory_pii_guard.v1."""
    has_ssn: bool = Field(description="SSN detected (GLBA/FCRA)")
    has_credit_card: bool = Field(description="Credit card PAN detected (PCI-DSS)")
    has_health_record: bool = Field(description="Health record ID detected (HIPAA)")
    has_email: bool = Field(description="Email address detected (GDPR/CCPA)")
    has_phone: bool = Field(description="Phone number detected (TCPA/CCPA)")
    has_ip: bool = Field(description="IPv4 address detected (GDPR)")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DecisionResult(BaseModel):
    """Cryptographically attested decision result."""
    pack_id: str = "compliance.regulatory_pii_guard.v1"
    action: str
    verdict: DecisionVerdict
    confidence: float = 1.0
    proof_sha256: str = ""
    latency_us: float = 0.0
    execution_mode: str = "embedded_native"
    necessary_causes: List[NecessaryCause] = Field(default_factory=list)
    counterfactual: Optional[Counterfactual] = None
    raw_payload: Optional[Dict[str, Any]] = None

    @property
    def is_approved(self) -> bool:
        return self.verdict == DecisionVerdict.APPROVE
