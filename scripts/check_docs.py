#!/usr/bin/env python3
"""Re-run the examples and the README's commands, and compare with what is written down.

Two checks, so that neither the README nor an example's output can drift from
what the runtime actually does:

1. Example outputs. Every example that runs with the runtime wheel alone is
   run, its output normalized (timings, ports and clock values replaced by
   placeholders) and compared line for line with tests/expected/<name>.txt.

2. README commands. Every ```bash block in README.md preceded by a
   `<!-- verify -->` line is run, in order, in a scratch copy of this
   repository, and the ```text block that follows it must appear in the
   output: each of its lines in order, with `...` lines matching anything
   (outputs in the README are trimmed) and timings normalized as above.

    python scripts/check_docs.py            # check; exit 1 on any difference
    python scripts/check_docs.py --update   # rewrite tests/expected/ from this run

Run it with the interpreter that has the runtime installed (README step 3).
Exit status: 0 everything matches, 1 a difference, 2 the runtime is missing.
--update never touches the README: change the README by hand, from a run.
"""

from __future__ import annotations

import argparse
import atexit
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = ROOT / "tests" / "expected"
README = ROOT / "README.md"

# Examples whose whole output is pinned. Others are left out on purpose:
# 11 needs a Developer license, the solver use cases need helixor-solvers,
# and integrations 01 to 05 need a server or a Planned capability.
PINNED = (
    "examples/01_quickstart.py",
    "examples/02_batch_benchmark.py",
    "examples/03_prompt_interceptor.py",
    "examples/04_streaming_interceptor.py",
    "examples/05_http_service.py",
    "examples/06_decision_protocols.py",
    "examples/07_custom_rules.py",
    "examples/08_generated_sdk_client.py",
    "examples/09_receipts.py",
    "examples/10_outcome_memory.py",
    "use_cases/loan_recourse.py",
    "use_cases/demand_forecasting.py",
    "use_cases/belief_tracking.py",
    "integrations/06_output_guardrail.py",
    "integrations/07_batch_csv_pipeline.py",
)

# What varies between runs and machines. Everything else must match exactly.
_VOLATILE = (
    (re.compile(r"\d[\d,]*(?:\.\d+)?(?=\s?(?:µs|ms|ops/sec)\b)"), "<n>"),
    (re.compile(r"(127\.0\.0\.1|localhost):\d+"), r"\1:<port>"),
    (re.compile(r"'time': [\d.]+"), "'time': <t>"),
    (re.compile(r"(?<=\s)\d+\.\ds$"), "<t>s"),                      # run_all.sh durations
    (re.compile(r"Python 3\.\d+\.\d+"), "Python 3.<x>"),            # run_all.sh header
)


def normalize(line: str) -> str:
    line = line.rstrip()
    for pattern, repl in _VOLATILE:
        line = pattern.sub(repl, line)
    return line


_COMMUNITY_HOME = tempfile.mkdtemp(prefix="helixor-demos-home-")
atexit.register(shutil.rmtree, _COMMUNITY_HOME, ignore_errors=True)


def _env() -> dict[str, str]:
    """The Community tier, as in the README: no license file anywhere the runtime looks.

    HOME points at an empty directory and HELIXOR_LICENSE_FILE is unset, so a
    license on this machine cannot change the outputs. This interpreter comes
    first on PATH, so `python` in a README block is this one.
    """
    env = dict(os.environ)
    env.pop("HELIXOR_LICENSE_FILE", None)
    env["HOME"] = _COMMUNITY_HOME
    env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_example(relative: str, cwd: Path = ROOT) -> tuple[int, list[str]]:
    proc = subprocess.run([sys.executable, relative], cwd=cwd, env=_env(),
                          capture_output=True, text=True, timeout=300)
    return proc.returncode, (proc.stdout + proc.stderr).splitlines()


def expected_path(relative: str) -> Path:
    return EXPECTED / (relative.replace("/", "__").removesuffix(".py") + ".txt")


def check_examples(update: bool) -> list[str]:
    problems = []
    for relative in PINNED:
        rc, lines = run_example(relative)
        got = [normalize(line) for line in lines]
        if rc != 0:
            problems.append(f"{relative}: exit {rc}\n    " + "\n    ".join(lines[-5:]))
            continue
        path = expected_path(relative)
        if update:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(got) + "\n", encoding="utf-8")
            print(f"  wrote  {path.relative_to(ROOT)}")
            continue
        if not path.exists():
            problems.append(f"{relative}: no {path.relative_to(ROOT)}; run with --update and review it")
            continue
        want = path.read_text(encoding="utf-8").splitlines()
        if got != want:
            diff = "\n    ".join(list(difflib.unified_diff(want, got, "expected", "actual", lineterm="", n=1))[:30])
            problems.append(f"{relative}: output differs from {path.relative_to(ROOT)}\n    {diff}")
        else:
            print(f"  same   {relative}")
    return problems


_BLOCK = re.compile(r"<!-- verify -->\s*\n```bash\n(.*?)```\s*\n+```text\n(.*?)```", re.DOTALL)


def readme_blocks(text: str) -> list[tuple[str, list[str]]]:
    return [(cmd, out.splitlines()) for cmd, out in _BLOCK.findall(text)]


def contains_in_order(expected: list[str], actual: list[str]) -> str | None:
    """None when every expected line (other than '...') appears in actual, in order."""
    wanted = [normalize(line) for line in expected if line.strip() != "..."]
    got = [normalize(line) for line in actual]
    i = 0
    for line in wanted:
        while i < len(got) and got[i] != line:
            i += 1
        if i == len(got):
            return line
        i += 1
    return None


def check_readme() -> list[str]:
    blocks = readme_blocks(README.read_text(encoding="utf-8"))
    if not blocks:
        return ["README.md: no `<!-- verify -->` blocks found"]
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "helixor-decision-demos"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "*.egg-info"))
        for command, expected in blocks:
            proc = subprocess.run(["bash", "-e", "-c", command], cwd=copy, env=_env(),
                                  capture_output=True, text=True, timeout=600)
            actual = (proc.stdout + proc.stderr).splitlines()
            first = command.strip().splitlines()[-1]
            missing = contains_in_order(expected, actual)
            if proc.returncode != 0:
                problems.append(f"README `{first}`: exit {proc.returncode}\n    " + "\n    ".join(actual[-5:]))
            elif missing is not None:
                problems.append(f"README `{first}`: output does not contain, in order:\n    {missing!r}")
            else:
                print(f"  same   README `{first}`")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--update", action="store_true", help="rewrite tests/expected/ from this run")
    args = parser.parse_args(argv)
    try:
        import helixor_runtime  # noqa: F401
    except ImportError:
        print(f"helixor_runtime is not importable with {sys.executable}; install the wheels (README step 3).")
        return 2
    print("Example outputs (tests/expected/)")
    problems = check_examples(args.update)
    if not args.update:
        print("README commands (<!-- verify --> blocks)")
        problems += check_readme()
    for problem in problems:
        print(f"  DIFF   {problem}")
    print(f"\n{'OK' if not problems else f'{len(problems)} difference(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
