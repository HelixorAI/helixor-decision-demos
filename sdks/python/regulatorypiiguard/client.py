"""Strongly-typed client for RegulatoryPiiGuard decision evaluation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Counterfactual,
    CounterfactualChange,
    DecisionResult,
    DecisionVerdict,
    ExecutionMode,
    RegulatoryPiiGuardState,
    NecessaryCause,
    TrueUpReport,
)
from .runtime_bridge import AuditReportUnavailableError, HelixorNativeBridge, evaluate_python


def _resolve_execution_mode(execution_mode: Optional[ExecutionMode | str], allow_python_fallback: bool) -> ExecutionMode:
    if execution_mode is None:
        return ExecutionMode.NATIVE_OR_PYTHON if allow_python_fallback else ExecutionMode.NATIVE
    if allow_python_fallback:
        raise ValueError("Pass execution_mode or allow_python_fallback, not both.")
    try:
        return ExecutionMode(execution_mode)
    except ValueError:
        raise ValueError(
            f"execution_mode must be one of {[m.value for m in ExecutionMode]}, got {execution_mode!r}"
        ) from None


class RegulatoryPiiGuardClient:
    """In-process decision client for compliance.regulatory_pii_guard.v1.

    Execution modes (see ExecutionMode; there is no implicit fallback):

    - ``native`` (default): libhelixor_runtime evaluates the sealed pack. Construction
      raises NativeRuntimeUnavailableError when the library is absent.
    - ``python``: the generated Python evaluator. The native library, license and
      sealed pack are not used, and passing them is an error.
    - ``native_or_python`` (also ``allow_python_fallback=True``): native when the
      library is found, else the Python evaluator.

    Every mode returns the same action, verdict, causes and counterfactual for a
    state: the first hard rule that fires sets the action, every firing rule term is
    a necessary cause, and the counterfactual lists one change per cause.

    The audit ledger exists only in the native C runtime. ``audit_available`` says
    whether this client has it; ``get_audit_report`` raises AuditReportUnavailableError
    when it does not.
    """

    def __init__(
        self,
        pack_path: Optional[str | Path] = None,
        license_json: Optional[str] = None,
        license_file: Optional[str | Path] = None,
        native_lib_path: Optional[str | Path] = None,
        allow_python_fallback: bool = False,
        execution_mode: Optional[ExecutionMode | str] = None,
    ):
        self.execution_mode = _resolve_execution_mode(execution_mode, allow_python_fallback)
        self.pack_handle = -1
        self.bridge: Optional[HelixorNativeBridge] = None
        if self.execution_mode is ExecutionMode.PYTHON:
            native_only = {
                "pack_path": pack_path,
                "license_json": license_json,
                "license_file": license_file,
                "native_lib_path": native_lib_path,
            }
            passed = [name for name, value in native_only.items() if value is not None]
            if passed:
                raise ValueError(
                    f"execution_mode='python' does not use {', '.join(passed)}; "
                    "use execution_mode='native' to run the sealed pack on libhelixor_runtime."
                )
            return
        self.bridge = HelixorNativeBridge(
            lib_path=native_lib_path,
            license_json=license_json,
            license_file=license_file,
            allow_python_fallback=self.execution_mode is ExecutionMode.NATIVE_OR_PYTHON,
        )
        if pack_path:
            p = Path(pack_path)
            if not p.is_file():
                raise FileNotFoundError(f"Sealed pack not found: {p}")
            self.pack_handle = self.bridge.load_sealed_pack(p.read_bytes())

    @property
    def is_native(self) -> bool:
        """Return True if decisions run on the native engine."""
        return self.bridge is not None and self.bridge.has_native_engine and self.pack_handle >= 0

    @property
    def audit_available(self) -> bool:
        """True when the native C runtime, which keeps the audit ledger, is loaded."""
        return self.bridge is not None and self.bridge.audit_available

    def decide(self, state: RegulatoryPiiGuardState | Dict[str, Any]) -> DecisionResult:
        """Evaluate one decision in-process. The pack's rules choose the action."""
        state_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state)
        if self.bridge is None:
            outcome = evaluate_python(state_dict, time.perf_counter_ns())
            mode = "embedded_python"
        else:
            outcome = self.bridge.execute_decision(self.pack_handle, state_dict)
            mode = self.bridge.execution_mode
        verdict_str, action, conf, proof, causes_raw, cf_raw, lat_us = outcome

        causes = [NecessaryCause(**c) for c in causes_raw]
        cf = None
        if cf_raw:
            cf = Counterfactual(
                remedy=cf_raw["remedy"],
                target_factor=cf_raw["target_factor"],
                required_value=cf_raw["required_value"],
                delta=cf_raw["delta"],
                changes=[CounterfactualChange(**change) for change in cf_raw["changes"]],
            )

        return DecisionResult(
            pack_id="compliance.regulatory_pii_guard.v1",
            action=action,
            verdict=DecisionVerdict(verdict_str),
            confidence=conf,
            proof_sha256=proof,
            latency_us=lat_us,
            execution_mode=mode,
            necessary_causes=causes,
            counterfactual=cf,
            raw_payload=state_dict,
        )

    def decide_batch(self, states: List[RegulatoryPiiGuardState | Dict[str, Any]]) -> List[DecisionResult]:
        """Evaluate a batch of decisions in-process."""
        return [self.decide(s) for s in states]

    def get_audit_report(self) -> TrueUpReport:
        """Return usage counts and the Merkle ledger root from the native runtime.

        Raises AuditReportUnavailableError unless ``audit_available``; a malformed
        report raises ValidationError.
        """
        if self.bridge is None:
            raise AuditReportUnavailableError(
                "The audit ledger is kept by the native C runtime (libhelixor_runtime); "
                "execution_mode='python' has no ledger."
            )
        return TrueUpReport.model_validate(self.bridge.get_audit_report())
