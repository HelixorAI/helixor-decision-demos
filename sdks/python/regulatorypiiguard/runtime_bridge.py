"""In-process bridge to libhelixor_runtime.

The native runtime is required. The generated pure-Python evaluator runs only
when the caller opts in with ``allow_python_fallback=True``.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class NativeRuntimeUnavailableError(RuntimeError):
    """The native runtime is not available and the Python evaluator was not requested."""


class NativeRuntimeLoadError(RuntimeError):
    """A native runtime library exists but could not be loaded."""


class DecisionStateError(ValueError):
    """The decision state is missing an attribute a hard rule evaluates."""


class LicenseRequiredError(RuntimeError):
    """The native runtime needs a license that was not provided or was rejected."""


class NativeRuntimeUnsupportedPackError(RuntimeError):
    """The loaded libhelixor_runtime cannot evaluate this pack's declared rules."""


class NativeRuntimeError(RuntimeError):
    """A native runtime call failed or returned a result the bridge cannot interpret."""


PACK_ID = "compliance.regulatory_pii_guard.v1"

# libhelixor_runtime before 1.1.0 ignored pack-declared rules (it applied fixed
# mortgage rules to every pack) and accepted unsigned licenses; never use it.
MIN_C_RUNTIME_VERSION = (1, 1, 0)


def _parse_version(text: str) -> Tuple[int, ...]:
    parts = []
    for piece in text.split("-", 1)[0].split("+", 1)[0].split("."):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts)

# HELIXOR_* status codes (helixor_runtime.h).
_HELIXOR_OK = 0
_HELIXOR_ERR_BUFFER_TOO_SMALL = 8

_VERDICTS = {"compliant": "approve", "refuse": "refuse", "invariant_breach": "refuse"}


def _map_verdict(raw: Any) -> str:
    if raw not in _VERDICTS:
        raise NativeRuntimeError(f"Native runtime returned an unknown verdict {raw!r}")
    return _VERDICTS[raw]


def _map_cause(raw: Dict[str, Any]) -> Dict[str, Any]:
    observed = raw.get("observed", raw.get("observed_value"))
    threshold = raw.get("threshold")
    distance = None
    if isinstance(observed, (int, float)) and isinstance(threshold, (int, float)) and not isinstance(observed, bool):
        distance = abs(float(observed) - float(threshold))
    return {
        "factor": raw["factor"],
        "observed_value": observed,
        "threshold": threshold,
        "direction": raw.get("direction") or raw.get("rule"),
        "distance_to_boundary": distance,
    }


def _load_license_json(license_json: Optional[str], license_file: Optional[str | Path]) -> Optional[str]:
    if license_json:
        return license_json
    path = license_file or os.getenv("HELIXOR_LICENSE_FILE")
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_file():
        raise LicenseRequiredError(f"License file not found: {p}")
    return p.read_text(encoding="utf-8")


# Hard-rule terms in priority order, from the pack IR:
# (rule_id, rule_verdict, action, factor, operator, threshold)
RULE_TERMS: List[Tuple[str, str, str, str, str, Optional[float]]] = [
    ('RULE-GLBA-SSN-BLOCK', 'refuse', 'block_glba_ssn_leakage', 'has_ssn', 'is_true', None),
    ('RULE-PCI-DSS-PAN-BLOCK', 'refuse', 'block_pci_dss_pan_leakage', 'has_credit_card', 'is_true', None),
    ('RULE-HIPAA-PHI-BLOCK', 'refuse', 'block_hipaa_phi_leakage', 'has_health_record', 'is_true', None),
    ('RULE-GDPR-CONTACT-REDACT', 'refuse', 'redact_and_permit_contact_pii', 'has_email', 'is_true', None),
    ('RULE-GDPR-CONTACT-REDACT', 'refuse', 'redact_and_permit_contact_pii', 'has_phone', 'is_true', None),
    ('RULE-GDPR-CONTACT-REDACT', 'refuse', 'redact_and_permit_contact_pii', 'has_ip', 'is_true', None),
]
DEFAULT_ACTION = 'permit_clean_payload'


class AuditReportUnavailableError(NativeRuntimeUnavailableError):
    """The audit ledger exists only in the native C runtime, which this client is not using."""


_BOOLEAN_OPERATORS = ("is_true", "is_false")
_NUMERIC_TESTS = {
    ">": lambda value, threshold: value > threshold,
    "<": lambda value, threshold: value < threshold,
    ">=": lambda value, threshold: value >= threshold,
    "<=": lambda value, threshold: value <= threshold,
    "==": lambda value, threshold: value == threshold,
}
# Relation the factor must satisfy for the term to stop firing.
_COMPLIANT_RELATION = {
    ">": "<=", "<": ">=", ">=": "<", "<=": ">", "==": "!=", "is_true": "==", "is_false": "==",
}
_RULE_ACTIONS = {term[0]: term[2] for term in RULE_TERMS}
_TERM_INDEX = {(term[0], term[3]): index for index, term in enumerate(RULE_TERMS)}


def _term_value(state: Dict[str, Any], factor: str, rule_id: str, operator: str) -> Any:
    val = state.get(factor)
    if val is None:
        raise DecisionStateError(
            f"State attribute '{factor}' is required by rule '{rule_id}' but is missing"
        )
    if operator in _BOOLEAN_OPERATORS:
        if not isinstance(val, bool):
            raise DecisionStateError(
                f"State attribute '{factor}' must be a boolean for rule '{rule_id}', got {type(val).__name__}"
            )
    elif isinstance(val, bool) or not isinstance(val, (int, float)):
        raise DecisionStateError(
            f"State attribute '{factor}' must be a number for rule '{rule_id}', got {type(val).__name__}"
        )
    return val


def _cause(index: int, observed: Any) -> Dict[str, Any]:
    rule_id, rule_verdict, _action, factor, operator, threshold = RULE_TERMS[index]
    numeric = operator not in _BOOLEAN_OPERATORS
    return {
        "factor": factor,
        "observed_value": float(observed) if numeric else bool(observed),
        "threshold": threshold if numeric else None,
        "direction": operator,
        "distance_to_boundary": abs(float(observed) - float(threshold)) if numeric and threshold is not None else None,
        "rule": rule_id,
        "rule_verdict": rule_verdict,
    }


def _action_for(causes: List[Dict[str, Any]]) -> str:
    """The first rule that fires sets the action; none firing means DEFAULT_ACTION."""
    return _RULE_ACTIONS[causes[0]["rule"]] if causes else DEFAULT_ACTION


def evaluate_rules(state: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """Evaluate every hard-rule term; return (action, causes) in priority order."""
    causes: List[Dict[str, Any]] = []
    for index, (rule_id, _verdict, _action, factor, operator, threshold) in enumerate(RULE_TERMS):
        val = _term_value(state, factor, rule_id, operator)
        if operator in _BOOLEAN_OPERATORS:
            fired = val is (operator == "is_true")
        else:
            fired = _NUMERIC_TESTS[operator](float(val), threshold)
        if fired:
            causes.append(_cause(index, val))
    return _action_for(causes), causes


def _normalize_native_causes(raw_causes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map causes reported by a native engine onto this pack's rule terms, in priority order."""
    indexed = []
    for raw in raw_causes:
        rule_id = raw.get("rule", raw.get("rule_id"))
        index = _TERM_INDEX.get((str(rule_id), str(raw.get("factor"))))
        if index is None:
            raise NativeRuntimeError(
                f"Native runtime reported cause {raw!r} (rule {rule_id!r}), which is not a hard-rule term of "
                f"pack '{PACK_ID}'"
            )
        operator = RULE_TERMS[index][4]
        if operator in _BOOLEAN_OPERATORS:
            observed: Any = operator == "is_true"  # a boolean term fires only on its breach value
        else:
            observed = raw.get("observed", raw.get("observed_value"))
            if isinstance(observed, bool) or not isinstance(observed, (int, float)):
                raise NativeRuntimeError(f"Native runtime reported a non-numeric observation in cause {raw!r}")
        indexed.append((index, _cause(index, observed)))
    return [cause for _, cause in sorted(indexed, key=lambda item: item[0])]


def _checked_native_action(raw_action: Any, causes: List[Dict[str, Any]]) -> str:
    """The native engine's action must be the one this pack's rules select."""
    expected = _action_for(causes)
    if raw_action != expected:
        raise NativeRuntimeError(
            f"Native runtime returned action {raw_action!r}; pack '{PACK_ID}' selects {expected!r} for these causes"
        )
    return expected


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return repr(float(value))


def build_counterfactual(causes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """One change per cause; together they stop every hard rule from firing."""
    if not causes:
        return None
    changes = []
    for cause in causes:
        operator = cause["direction"]
        if operator in _BOOLEAN_OPERATORS:
            required: Any = operator == "is_false"
            delta = None
        else:
            required = cause["threshold"]
            delta = cause["threshold"] - float(cause["observed_value"])
        changes.append({
            "rule": cause["rule"],
            "factor": cause["factor"],
            "relation": _COMPLIANT_RELATION[operator],
            "required_value": required,
            "observed_value": cause["observed_value"],
            "delta": delta,
        })
    remedy = "; ".join(
        f"{c['factor']} {c['relation']} {_format_value(c['required_value'])} (rule {c['rule']})" for c in changes
    )
    first = changes[0]
    return {
        "remedy": remedy,
        "target_factor": first["factor"],
        "required_value": first["required_value"],
        "delta": first["delta"],
        "changes": changes,
    }


def evaluate_python(state: Dict[str, Any], start_ns: int) -> Tuple[str, str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
    """The generated Python evaluator: (verdict, action, confidence, proof, causes, counterfactual, latency_us)."""
    action, causes = evaluate_rules(state)
    verdict = "refuse" if causes else "approve"
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
    preimage = f"{PACK_ID}:{action}:{verdict}:{json.dumps(state, sort_keys=True)}"
    proof_sha = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
    return verdict, action, 1.0, proof_sha, causes, build_counterfactual(causes), elapsed_us


class HelixorNativeBridge:
    """Manages the in-process native C enclave and atomic Merkle ledger."""

    _lib: Optional[ctypes.CDLL] = None
    _is_initialized: bool = False
    _shared_pack_handle: int = -1

    def __init__(
        self,
        lib_path: Optional[str | Path] = None,
        license_json: Optional[str] = None,
        license_file: Optional[str | Path] = None,
        allow_python_fallback: bool = False,
    ):
        self.allow_python_fallback = allow_python_fallback
        self.searched_paths: List[Path] = []
        # The C runtime is initialized from the signed .hxlic the Helixor
        # Licensing service issued (license_json, license_file, or
        # $HELIXOR_LICENSE_FILE); there is no default. The Python evaluator
        # needs no license.
        self.license_json = _load_license_json(license_json, license_file)
        self._load_library(lib_path)
        if HelixorNativeBridge._lib is None and not allow_python_fallback:
            raise NativeRuntimeUnavailableError(
                "Native Helixor runtime not found (searched: "
                + ", ".join(str(p) for p in self.searched_paths)
                + "). Set HELIXOR_RUNTIME_LIB or pass lib_path; pass "
                "allow_python_fallback=True to run the generated Python evaluator instead."
            )
        self._init_runtime()

    def _load_library(self, custom_path: Optional[str | Path]) -> None:
        if HelixorNativeBridge._lib is not None:
            return

        candidates = []
        if custom_path:
            candidates.append(Path(custom_path))
        if os.getenv("HELIXOR_RUNTIME_LIB"):
            candidates.append(Path(os.environ["HELIXOR_RUNTIME_LIB"]))

        system = platform.system()
        lib_name = "libhelixor_runtime.dylib" if system == "Darwin" else ("helixor_runtime.dll" if system == "Windows" else "libhelixor_runtime.so")
        candidates.extend([
            Path(__file__).parent / "native" / lib_name,
            Path("/usr/local/lib") / lib_name,
            Path("/opt/helixor/lib") / lib_name,
        ])

        self.searched_paths = list(candidates)
        for path in candidates:
            if path.is_file():
                try:
                    lib = ctypes.CDLL(str(path))
                    exec_sym = getattr(lib, "helixor_playbook_execute", None) or getattr(lib, "helixor_java_decision_execute", None)
                    if exec_sym is not None:
                        lib.graal_create_isolate.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
                        lib.graal_create_isolate.restype = ctypes.c_int
                        exec_sym.argtypes = [
                            ctypes.c_void_p,
                            ctypes.c_char_p,
                            ctypes.c_char_p,
                            ctypes.c_char_p,
                            ctypes.c_int,
                        ]
                        exec_sym.restype = ctypes.c_int
                        HelixorNativeBridge._graal_exec_fn = exec_sym
                        HelixorNativeBridge._is_graal_native = True
                        HelixorNativeBridge._lib = lib
                        return

                    # Function signatures from helixor_runtime.h
                    lib.helixor_version.argtypes = []
                    lib.helixor_version.restype = ctypes.c_char_p
                    lib.helixor_license_init.argtypes = [ctypes.c_char_p]
                    lib.helixor_license_init.restype = ctypes.c_int

                    lib.helixor_pack_load_sealed.argtypes = [
                        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_char_p,
                    ]
                    lib.helixor_pack_load_sealed.restype = ctypes.c_int

                    lib.helixor_decision_execute.argtypes = [
                        ctypes.c_char_p,
                        ctypes.c_char_p,
                        ctypes.c_char_p,
                        ctypes.c_size_t,
                        ctypes.POINTER(ctypes.c_size_t),
                    ]
                    lib.helixor_decision_execute.restype = ctypes.c_int

                    lib.helixor_get_audit_report.argtypes = [
                        ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
                    ]
                    lib.helixor_get_audit_report.restype = ctypes.c_int

                    lib.helixor_last_error.argtypes = []
                    lib.helixor_last_error.restype = ctypes.c_char_p

                    lib.helixor_runtime_shutdown.argtypes = []
                    lib.helixor_runtime_shutdown.restype = None

                    HelixorNativeBridge._is_graal_native = False
                    HelixorNativeBridge._lib = lib
                    return
                except Exception as exc:
                    raise NativeRuntimeLoadError(
                        f"Native runtime at {path} could not be loaded: {type(exc).__name__}: {exc}"
                    ) from exc

    def _init_runtime(self) -> None:
        if HelixorNativeBridge._lib is not None and not HelixorNativeBridge._is_initialized:
            if getattr(HelixorNativeBridge, "_is_graal_native", False):
                isolate = ctypes.c_void_p()
                thread = ctypes.c_void_p()
                rc = HelixorNativeBridge._lib.graal_create_isolate(None, ctypes.byref(isolate), ctypes.byref(thread))
                if rc != 0:
                    raise RuntimeError(f"Failed to initialize GraalVM isolate: {rc}")
                HelixorNativeBridge._graal_isolate = isolate
                HelixorNativeBridge._graal_thread = thread
            else:
                raw_version = HelixorNativeBridge._lib.helixor_version()
                version = raw_version.decode("utf-8") if raw_version else ""
                if _parse_version(version) < MIN_C_RUNTIME_VERSION:
                    raise NativeRuntimeUnsupportedPackError(
                        f"libhelixor_runtime {version or '(unknown version)'} does not evaluate pack-declared "
                        "rules or verify license signatures; version 1.1.0 or later is required."
                    )
                if not self.license_json:
                    raise LicenseRequiredError(
                        "The native Helixor runtime requires a license: pass license_json or "
                        "license_file, or set HELIXOR_LICENSE_FILE."
                    )
                rc = HelixorNativeBridge._lib.helixor_license_init(self.license_json.encode("utf-8"))
                if rc != _HELIXOR_OK:
                    raise LicenseRequiredError(f"Native runtime rejected the license ({rc}): {self._last_error()}")
            HelixorNativeBridge._is_initialized = True

    @property
    def has_native_engine(self) -> bool:
        return HelixorNativeBridge._lib is not None

    @staticmethod
    def _last_error() -> str:
        raw = HelixorNativeBridge._lib.helixor_last_error()
        return raw.decode("utf-8") if raw else ""

    @staticmethod
    def _call_with_output(fn: Any, *args: Any) -> str:
        """Call a C function that writes JSON to (buf, buf_len, out_written), growing the buffer."""
        size = 4096
        while True:
            buf = ctypes.create_string_buffer(size)
            written = ctypes.c_size_t(0)
            rc = fn(*args, buf, size, ctypes.byref(written))
            if rc == _HELIXOR_ERR_BUFFER_TOO_SMALL and size < (1 << 20):
                size *= 4
                continue
            if rc != _HELIXOR_OK:
                raise NativeRuntimeError(f"Native call failed ({rc}): {HelixorNativeBridge._last_error()}")
            return buf.raw[: written.value].decode("utf-8")

    @property
    def execution_mode(self) -> str:
        return "embedded_native" if self.has_native_engine else "embedded_python"

    def load_sealed_pack(self, sealed_bytes: bytes) -> int:
        if not self.has_native_engine:
            return 1  # Python evaluator (explicitly requested) runs the generated rules
        if getattr(HelixorNativeBridge, "_is_graal_native", False):
            return 1  # Native GraalVM image has playbook compiled into binary
        # The runtime derives the pack key from the license; packs are then
        # addressed by pack id.
        buf = (ctypes.c_uint8 * len(sealed_bytes)).from_buffer_copy(sealed_bytes)
        rc = HelixorNativeBridge._lib.helixor_pack_load_sealed(buf, len(sealed_bytes), PACK_ID.encode("utf-8"))
        if rc != _HELIXOR_OK:
            raise NativeRuntimeError(f"Native pack loading failed ({rc}): {self._last_error()}")
        return 0

    def execute_decision(
        self,
        pack_handle: int,
        state_dict: Dict[str, Any],
    ) -> Tuple[str, str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
        """Execute a decision via the native C runtime, a GraalVM playbook image, or the Python evaluator.

        Native results are checked against this pack's rules: causes must be rule terms,
        the action must be the one the first firing rule declares, and the verdict must
        agree with the causes. Returns:
        (verdict, action, confidence, proof_sha256, causes, counterfactual, latency_us)
        """
        start = time.perf_counter_ns()
        if self.has_native_engine and getattr(HelixorNativeBridge, "_is_graal_native", False):
            state_json = json.dumps(state_dict)
            out_buf = ctypes.create_string_buffer(4096)
            thread = HelixorNativeBridge._graal_thread
            rc = HelixorNativeBridge._graal_exec_fn(
                thread,
                PACK_ID.encode("utf-8"),
                state_json.encode("utf-8"),
                out_buf,
                4096,
            )
            elapsed_us = (time.perf_counter_ns() - start) / 1000.0
            if rc != 0:
                raise NativeRuntimeError(f"Native GraalVM decision execution failed with code {rc}")
            return self._checked_native_result(json.loads(out_buf.value.decode("utf-8")), elapsed_us)

        if self.has_native_engine:
            if pack_handle < 0:
                raise NativeRuntimeError(f"Pack '{PACK_ID}' is not loaded into the native runtime; pass pack_path.")
            raw = self._call_with_output(
                HelixorNativeBridge._lib.helixor_decision_execute,
                PACK_ID.encode("utf-8"),
                json.dumps(state_dict).encode("utf-8"),
            )
            elapsed_us = (time.perf_counter_ns() - start) / 1000.0
            return self._checked_native_result(json.loads(raw), elapsed_us)

        if not self.allow_python_fallback:
            raise NativeRuntimeUnavailableError("No native pack handle is loaded and the Python evaluator was not requested.")
        return self._fallback_evaluate(state_dict, start)

    @staticmethod
    def _checked_native_result(
        data: Dict[str, Any], elapsed_us: float
    ) -> Tuple[str, str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
        verdict = _map_verdict(data.get("verdict"))
        causes = _normalize_native_causes(data.get("necessary_causes") or [])
        if (verdict == "approve") != (not causes):
            raise NativeRuntimeError(
                f"Native runtime returned verdict {data.get('verdict')!r} with {len(causes)} necessary cause(s)"
            )
        action = _checked_native_action(data.get("action"), causes)
        proof = data.get("proof_sha256")
        if not isinstance(proof, str) or len(proof) != 64:
            raise NativeRuntimeError(f"Native runtime returned no decision proof: {proof!r}")
        return verdict, action, 1.0, proof, causes, build_counterfactual(causes), elapsed_us

    def _fallback_evaluate(
        self, state: Dict[str, Any], start_ns: int
    ) -> Tuple[str, str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
        """The generated Python evaluator (execution_mode native_or_python without a native library)."""
        # Evaluates the 6 rule term(s) in RULE_TERMS, in priority order.
        return evaluate_python(state, start_ns)

    @property
    def audit_available(self) -> bool:
        """True when the native C runtime, which keeps the audit ledger, is loaded."""
        return self.has_native_engine and not getattr(HelixorNativeBridge, "_is_graal_native", False)

    def get_audit_report(self) -> Dict[str, Any]:
        if not self.audit_available:
            raise AuditReportUnavailableError(
                "The audit ledger is kept by the native C runtime (libhelixor_runtime); this client "
                f"runs {self.execution_mode} and has no ledger."
            )
        return json.loads(self._call_with_output(HelixorNativeBridge._lib.helixor_get_audit_report))
