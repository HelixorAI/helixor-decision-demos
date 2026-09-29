#!/usr/bin/env bash
# Run every example that runs on this machine with the Helixor runtime wheel
# alone, and report PASS / FAIL / SKIP / KNOWN per example with the reason.
#
#   ./run_all.sh            # summary only
#   ./run_all.sh -v         # also print each failing example's last lines
#
# Exit status: 0 when nothing FAILs, 1 when any example FAILs, 2 when the
# runtime is not installed. SKIP means the example needs something the wheel
# does not provide (named on the line); KNOWN means a documented defect in the
# released runtime and the error it raises. Neither is counted as a pass.

set -u

cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1

if ! "$PY" -c "import helixor_runtime" 2>/dev/null; then
    echo "helixor_runtime is not importable with $PY."
    echo "Install the runtime wheel first (see README.md, step 3):"
    echo "  pip install ./helixor_runtime-<version>-py3-none-any.whl"
    exit 2
fi
RUNTIME_VERSION="$("$PY" -c 'import helixor_runtime; print(helixor_runtime.__version__)')"
HAS_SOLVERS=0
"$PY" -c "import helixor_solvers" 2>/dev/null && HAS_SOLVERS=1

PASS=0; FAIL=0; SKIP=0; KNOWN=0
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

pass() { PASS=$((PASS + 1)); printf "  PASS   %-40s %5.1fs\n" "$1" "$2"; }
fail() {
    FAIL=$((FAIL + 1)); printf "  FAIL   %-40s exit %s\n" "$1" "$2"
    if [ "$VERBOSE" = 1 ]; then tail -5 "$LOG" | sed 's/^/           /'; fi
}
skip() { SKIP=$((SKIP + 1)); printf "  SKIP   %-40s %s\n" "$1" "$2"; }

# run FILE [ARGS...]: run one example, PASS on exit 0, FAIL otherwise.
run() {
    local file="$1"; shift
    local start end rc
    start="$("$PY" -c 'import time; print(time.time())')"
    "$PY" "$file" "$@" >"$LOG" 2>&1
    rc=$?
    end="$("$PY" -c 'import time; print(time.time())')"
    if [ $rc -eq 0 ]; then
        pass "$file" "$("$PY" -c "print($end - $start)")"
    else
        fail "$file" "$rc"
    fi
}

# known FILE PATTERN REASON: a documented runtime defect. The example must fail
# with PATTERN in its output; if it passes, or fails differently, that is
# reported so the note gets removed or corrected.
known() {
    local file="$1" pattern="$2" reason="$3"
    if "$PY" "$file" >"$LOG" 2>&1; then
        pass "$file (known issue fixed: update run_all.sh)" 0
    elif grep -q "$pattern" "$LOG"; then
        KNOWN=$((KNOWN + 1)); printf "  KNOWN  %-40s %s\n" "$file" "$reason"
    else
        fail "$file" "unexpected error"
    fi
}

# unavailable FILE REASON: an example for a Planned capability. It must fail
# closed with exit 3 and say UNAVAILABLE; it is reported as SKIP. If it exits 0
# it produced a result for something that does not exist, which is a FAIL.
unavailable() {
    local file="$1" reason="$2" rc
    "$PY" "$file" >"$LOG" 2>&1
    rc=$?
    if [ $rc -eq 3 ] && grep -q "^UNAVAILABLE:" "$LOG"; then
        skip "$file" "$reason (fails closed)"
    else
        fail "$file" "$rc (expected to fail closed with exit 3)"
    fi
}

echo "Helixor decision demos: helixor_runtime $RUNTIME_VERSION, $("$PY" --version 2>&1)"

echo ""
echo "Examples (PII Guard tutorial)"
for f in examples/01_quickstart.py \
         examples/02_batch_benchmark.py \
         examples/03_prompt_interceptor.py \
         examples/04_streaming_interceptor.py \
         examples/05_http_service.py \
         examples/06_decision_protocols.py \
         examples/07_custom_rules.py \
         examples/08_generated_sdk_client.py; do
    run "$f"
done

echo ""
echo "Use cases"
for f in use_cases/loan_recourse.py \
         use_cases/demand_forecasting.py \
         use_cases/belief_tracking.py; do
    run "$f"
done
for f in use_cases/fleet_routing.py use_cases/shift_rostering.py; do
    if [ "$HAS_SOLVERS" = 1 ]; then
        run "$f"
    else
        skip "$f" "needs the helixor-solvers package (not in the runtime wheel)"
    fi
done
known use_cases/sales_arbitration.py "sales binding not found" \
    "runtime 0.3.0 does not package the sales playbook"

echo ""
echo "Integrations"
for f in integrations/06_output_guardrail.py \
         integrations/07_batch_csv_pipeline.py; do
    run "$f"
done
unavailable integrations/05_governed_query.py "governed data access is Planned"
for f in integrations/01_server_evaluate.py \
         integrations/02_server_decision.py \
         integrations/03_playbook_studio.py \
         integrations/04_ontology_binding.py; do
    skip "$f" "needs a Helixor server (HELIXOR_API_URL)"
done

echo ""
echo "Result: $PASS passed, $FAIL failed, $SKIP skipped, $KNOWN known issues"
[ "$FAIL" -eq 0 ]
