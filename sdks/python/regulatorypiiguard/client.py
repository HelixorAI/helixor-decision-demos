"""Strongly-typed client for RegulatoryPiiGuard decision evaluation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Counterfactual,
    DecisionResult,
    DecisionVerdict,
    RegulatoryPiiGuardState,
    NecessaryCause,
    TrueUpReport,
)
from .runtime_bridge import HelixorNativeBridge


class RegulatoryPiiGuardClient:
    """Enterprise client for compliance.regulatory_pii_guard.v1.

    Provides sub-millisecond in-process decisioning, zero-GC memory allocation,
    and automatic tamper-evident Merkle ledger audit tracking.
    """

    def __init__(
        self,
        pack_path: Optional[str | Path] = None,
        license_json: Optional[str] = None,
        license_file: Optional[str | Path] = None,
        native_lib_path: Optional[str | Path] = None,
        allow_python_fallback: bool = False,
    ):
        """Create a client.

        Raises NativeRuntimeUnavailableError when the native runtime is absent,
        unless ``allow_python_fallback=True`` selects the generated Python evaluator.
        """
        self.bridge = HelixorNativeBridge(
            lib_path=native_lib_path,
            license_json=license_json,
            license_file=license_file,
            allow_python_fallback=allow_python_fallback,
        )
        self.pack_handle = -1
        if pack_path:
            p = Path(pack_path)
            if not p.is_file():
                raise FileNotFoundError(f"Sealed pack not found: {p}")
            self.pack_handle = self.bridge.load_sealed_pack(p.read_bytes())

    @property
    def is_native(self) -> bool:
        """Return True if executing on zero-overhead native C engine."""
        return self.bridge.has_native_engine and self.pack_handle >= 0

    def decide(
        self,
        state: RegulatoryPiiGuardState | Dict[str, Any],
        action: str = "permit_clean_payload",
    ) -> DecisionResult:
        """Evaluate a single decision request in-process (<0.005 ms latency)."""
        state_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state)
        verdict_str, conf, proof, causes_raw, cf_raw, lat_us = self.bridge.execute_decision(
            self.pack_handle,
            action,
            state_dict,
        )

        causes = [
            NecessaryCause(
                factor=c.get("factor", ""),
                observed_value=c.get("observed_value"),
                threshold=c.get("threshold"),
                direction=c.get("direction"),
                distance_to_boundary=c.get("distance_to_boundary"),
            )
            for c in causes_raw
        ]

        cf = None
        if cf_raw:
            cf = Counterfactual(
                remedy=cf_raw.get("remedy", ""),
                target_factor=cf_raw.get("target_factor", ""),
                required_value=cf_raw.get("required_value"),
                delta=cf_raw.get("delta"),
                feasibility=cf_raw.get("feasibility", 1.0),
            )

        return DecisionResult(
            pack_id="compliance.regulatory_pii_guard.v1",
            action=action,
            verdict=DecisionVerdict(verdict_str),
            confidence=conf,
            proof_sha256=proof,
            latency_us=lat_us,
            execution_mode=self.bridge.execution_mode,
            necessary_causes=causes,
            counterfactual=cf,
            raw_payload=state_dict,
        )

    def decide_batch(
        self,
        states: List[RegulatoryPiiGuardState | Dict[str, Any]],
        action: str = "permit_clean_payload",
    ) -> List[DecisionResult]:
        """Evaluate a batch of decision requests in-process."""
        return [self.decide(s, action=action) for s in states]

    def get_audit_report(self) -> TrueUpReport:
        """Retrieve usage counts and the Merkle ledger root; a malformed report raises ValidationError."""
        return TrueUpReport.model_validate(self.bridge.get_audit_report())
