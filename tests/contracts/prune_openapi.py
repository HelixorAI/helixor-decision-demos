#!/usr/bin/env python3
"""Reduce the reasoning-backend OpenAPI document to the operations the demos call.

The demo repository is public. It must carry only the request/response shapes
of the endpoints its integration scripts use, never the backend's full API
surface. This script keeps the allow-listed operations and the component
schemas they reference (transitively), and drops everything else.

    python tests/contracts/prune_openapi.py FULL_OPENAPI.json tests/contracts/reasoning-backend.openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# (path, method) pairs the integration scripts call. Keep in sync with integrations/0[1-4].
OPERATIONS: dict[str, tuple[str, ...]] = {
    "/api/v1/health": ("get",),
    "/api/v1/decide": ("post",),
    "/api/v1/reasoning/chat/stream": ("post",),
    "/api/v1/reasoning/playbooks/list": ("get",),
    "/api/v1/reasoning/playbooks/validate": ("post",),
    "/api/v1/reasoning/playbooks/compile": ("post",),
    "/api/v1/reasoning/playbooks/admit": ("post",),
    "/api/v1/reasoning/playbooks/turn": ("post",),
    "/api/v1/reasoning/ontology/config": ("get", "put"),
}
SCHEMA_PREFIX = "#/components/schemas/"


def _refs(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(SCHEMA_PREFIX):
            found.add(ref[len(SCHEMA_PREFIX):])
        for value in node.values():
            found |= _refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= _refs(value)
    return found


def prune(spec: dict[str, Any]) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for path, methods in OPERATIONS.items():
        if path not in spec["paths"]:
            raise KeyError(f"{path} is not in the backend OpenAPI; update OPERATIONS")
        for method in methods:
            if method not in spec["paths"][path]:
                raise KeyError(f"{method.upper()} {path} is not in the backend OpenAPI; update OPERATIONS")
        paths[path] = {m: spec["paths"][path][m] for m in methods}

    all_schemas = spec.get("components", {}).get("schemas", {})
    keep: set[str] = set()
    todo = list(_refs(paths))
    while todo:
        name = todo.pop()
        if name in keep:
            continue
        keep.add(name)
        todo.extend(_refs(all_schemas[name]) - keep)

    return {
        "openapi": spec["openapi"],
        "info": {"title": spec["info"]["title"], "version": spec["info"]["version"]},
        "paths": paths,
        "components": {"schemas": {n: all_schemas[n] for n in sorted(keep)}},
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    Path(argv[2]).write_text(json.dumps(prune(spec), indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
