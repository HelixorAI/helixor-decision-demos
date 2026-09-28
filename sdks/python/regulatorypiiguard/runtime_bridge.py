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


def _require(state: Dict[str, Any], factor: str, rule_id: str) -> Any:
    val = state.get(factor)
    if val is None:
        raise DecisionStateError(
            f"State attribute '{factor}' is required by rule '{rule_id}' but is missing"
        )
    return val


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
        action: str,
        state_dict: Dict[str, Any],
    ) -> Tuple[str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
        """Execute decision via native C FFI, GraalVM native image, or pure-Python fallback.

        Returns: (verdict, confidence, proof_sha256, causes, counterfactual, latency_us)
        """
        start = time.perf_counter_ns()
        if self.has_native_engine and getattr(HelixorNativeBridge, "_is_graal_native", False):
            state_json = json.dumps(state_dict)
            out_buf = ctypes.create_string_buffer(4096)
            thread = HelixorNativeBridge._graal_thread
            pack_id_str = "compliance.regulatory_pii_guard.v1"
            rc = HelixorNativeBridge._graal_exec_fn(
                thread,
                pack_id_str.encode("utf-8"),
                state_json.encode("utf-8"),
                out_buf,
                4096,
            )
            elapsed_us = (time.perf_counter_ns() - start) / 1000.0
            if rc != 0:
                raise RuntimeError(f"Native GraalVM decision execution failed with code {rc}")
            data = json.loads(out_buf.value.decode("utf-8"))
            verdict = _map_verdict(data.get("verdict"))
            causes = [_map_cause(c) for c in data.get("necessary_causes", [])]
            return verdict, 1.0, data["proof_sha256"], causes, data.get("counterfactual"), elapsed_us

        if self.has_native_engine:
            if pack_handle < 0:
                raise NativeRuntimeError(f"Pack '{PACK_ID}' is not loaded into the native runtime; pass pack_path.")
            raw = self._call_with_output(
                HelixorNativeBridge._lib.helixor_decision_execute,
                PACK_ID.encode("utf-8"),
                json.dumps(state_dict).encode("utf-8"),
            )
            elapsed_us = (time.perf_counter_ns() - start) / 1000.0
            data = json.loads(raw)
            verdict = _map_verdict(data.get("verdict"))
            causes = [_map_cause(c) for c in data.get("necessary_causes", [])]
            cf = None
            raw_cf = data.get("counterfactual")
            if raw_cf and causes:
                target = causes[0]["factor"]
                cf = {
                    "remedy": raw_cf.get("remedy", ""),
                    "target_factor": target,
                    "required_value": (raw_cf.get("target_state") or {}).get(target),
                    "delta": causes[0]["distance_to_boundary"],
                }
            return verdict, 1.0, data["proof_sha256"], causes, cf, elapsed_us

        if not self.allow_python_fallback:
            raise NativeRuntimeUnavailableError("No native pack handle is loaded and the Python evaluator was not requested.")
        return self._fallback_evaluate(action, state_dict, start)

    def _fallback_evaluate(
        self, action: str, state: Dict[str, Any], start_ns: int
    ) -> Tuple[str, float, str, List[Dict[str, Any]], Optional[Dict[str, Any]], float]:
        causes = []
        cf = None
        verdict = "approve"

        # AST invariant evaluations
        val = _require(state, "has_ssn", "RULE-GLBA-SSN-BLOCK")
        if bool(val) is True:
            causes.append({
                "factor": "has_ssn",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_ssn (rule RULE-GLBA-SSN-BLOCK)",
                "target_factor": "has_ssn",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }
        val = _require(state, "has_credit_card", "RULE-PCI-DSS-PAN-BLOCK")
        if bool(val) is True:
            causes.append({
                "factor": "has_credit_card",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_credit_card (rule RULE-PCI-DSS-PAN-BLOCK)",
                "target_factor": "has_credit_card",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }
        val = _require(state, "has_health_record", "RULE-HIPAA-PHI-BLOCK")
        if bool(val) is True:
            causes.append({
                "factor": "has_health_record",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_health_record (rule RULE-HIPAA-PHI-BLOCK)",
                "target_factor": "has_health_record",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }
        val = _require(state, "has_email", "RULE-GDPR-CONTACT-REDACT")
        if bool(val) is True:
            causes.append({
                "factor": "has_email",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_email (rule RULE-GDPR-CONTACT-REDACT)",
                "target_factor": "has_email",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }
        val = _require(state, "has_phone", "RULE-GDPR-CONTACT-REDACT")
        if bool(val) is True:
            causes.append({
                "factor": "has_phone",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_phone (rule RULE-GDPR-CONTACT-REDACT)",
                "target_factor": "has_phone",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }
        val = _require(state, "has_ip", "RULE-GDPR-CONTACT-REDACT")
        if bool(val) is True:
            causes.append({
                "factor": "has_ip",
                "observed_value": val,
                "threshold": 0.0,
                "direction": "is_true",
                "distance_to_boundary": 1.0,
            })
            if cf is None:  # rules run in priority order; the first to fire owns the counterfactual
              cf = {
                "remedy": "Resolve has_ip (rule RULE-GDPR-CONTACT-REDACT)",
                "target_factor": "has_ip",
                "required_value": False,
                "delta": 1.0,
                "feasibility": 0.50,
              }

        if causes:
            verdict = "refuse"

        elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
        # Deterministic DecisionProof hash
        preimage = f"compliance.regulatory_pii_guard.v1:{action}:{verdict}:{json.dumps(state, sort_keys=True)}"
        proof_sha = hashlib.sha256(preimage.encode("utf-8")).hexdigest()

        return verdict, 1.0, proof_sha, causes, cf, elapsed_us

    def get_audit_report(self) -> Dict[str, Any]:
        if not self.has_native_engine or getattr(HelixorNativeBridge, "_is_graal_native", False):
            raise NativeRuntimeUnavailableError(
                "The audit ledger is kept by the native C runtime; this bridge has none loaded."
            )
        return json.loads(self._call_with_output(HelixorNativeBridge._lib.helixor_get_audit_report))
