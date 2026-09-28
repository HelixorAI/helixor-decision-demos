# Reasoning backend contract snapshot

`reasoning-backend.openapi.json` holds only the operations the integration
scripts (`integrations/01`–`04`) call, and the component schemas those
operations reference. It is cut from the reasoning backend's OpenAPI document
(version 0.1.4) by `prune_openapi.py`. `tests/test_integration_payloads.py`
validates every request body those scripts build against it, and
`tests/test_contract_snapshot.py` fails if the snapshot ever carries an
operation outside that allow list.

This repository is public: never commit the backend's full OpenAPI document.

Regenerate it when the backend API changes (from a checkout that has the
backend installed), writing the full document outside this repository:

```bash
python -c "import json; from helixor_reasoning_backend.app import app; \
  json.dump(app.openapi(), open('/tmp/reasoning-backend.full.json', 'w'))"
python tests/contracts/prune_openapi.py /tmp/reasoning-backend.full.json \
  tests/contracts/reasoning-backend.openapi.json
```

When an integration script starts calling a new endpoint, add it to
`OPERATIONS` in `prune_openapi.py` and regenerate.
