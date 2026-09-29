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


class ExecutionMode(str, Enum):
    """How the client evaluates decisions. There is no implicit fallback.

    NATIVE: libhelixor_runtime is required; construction fails without it.
    PYTHON: the generated Python evaluator; the native library is never loaded.
    NATIVE_OR_PYTHON: native when the library is found, else the Python evaluator.
    DecisionResult.execution_mode reports which one ran.
    """
    NATIVE = "native"
    PYTHON = "python"
    NATIVE_OR_PYTHON = "native_or_python"


class NecessaryCause(BaseModel):
    """One hard-rule term that fired. Numeric terms carry threshold and distance; boolean terms do not."""
    factor: str
    observed_value: Any
    threshold: Optional[float] = None
    direction: Optional[str] = None
    distance_to_boundary: Optional[float] = None
    rule: Optional[str] = None
    rule_verdict: Optional[str] = None


class CounterfactualChange(BaseModel):
    """A state change that stops one cause from firing: ``factor relation required_value``."""
    rule: str
    factor: str
    relation: str
    required_value: Any
    observed_value: Any
    delta: Optional[float] = None


class Counterfactual(BaseModel):
    """The state changes that together clear every necessary cause.

    ``changes`` has one entry per cause; all must hold for the decision to pass.
    ``target_factor``, ``required_value`` and ``delta`` repeat the first change.
    """
    remedy: str
    target_factor: str
    required_value: Any
    delta: Optional[float] = None
    changes: List[CounterfactualChange] = Field(default_factory=list)


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
    has_ssn: bool = Field(description="Evaluated by invariant RULE-GLBA-SSN-BLOCK")
    has_credit_card: bool = Field(description="Evaluated by invariant RULE-PCI-DSS-PAN-BLOCK")
    has_health_record: bool = Field(description="Evaluated by invariant RULE-HIPAA-PHI-BLOCK")
    has_phone: bool = Field(description="Evaluated by invariant RULE-GDPR-CONTACT-REDACT")
    has_ip: bool = Field(description="Evaluated by invariant RULE-GDPR-CONTACT-REDACT")
    has_email: bool = Field(description="Evaluated by invariant RULE-GDPR-CONTACT-REDACT")

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
