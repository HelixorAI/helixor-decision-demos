# Helixor Decision Demos — Developer Examples

Consumer-facing examples for the Helixor Decision Runtime (`helixor-runtime`).
This repository is public and Apache-2.0; the runtime is proprietary (see
`NOTICE`) and is a pure-Python reference implementation in 0.3.x — see
`docs/ARCHITECTURE.md` for what it does and does not protect.

## Conventions

- Examples import from `helixor_runtime`, never from internal modules.
- No engine source, extractors, remedy logic, decision logic, or cryptographic
  implementations belong here. `tests/test_repo_hygiene.py` fails if runtime
  source is vendored or internal modules are imported.
- `tests/contracts/` carries only the pruned OpenAPI operations the
  integrations call (`prune_openapi.py`), never the backend's full API.
- `playbooks/` holds declarative YAML; a Developer license compiles a playbook
  into a `.hxpack` with `helixor-pack compile`.

## Docs stay in sync with real output

The README's "Get started" section and https://helixor.dev/guide/quickstart.html
are the same seven steps with the same names. Change them together, and only
with output from a run on a clean checkout. `python scripts/check_docs.py`
must pass before a change lands; after a deliberate output change, run it with
`--update` and review the diff of `tests/expected/`.
