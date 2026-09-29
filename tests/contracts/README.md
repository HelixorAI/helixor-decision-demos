# Reasoning backend contract snapshot

`reasoning-backend.openapi.json` holds only the operations the integration
scripts (`integrations/01`–`04`) call, and the component schemas those
operations reference. It is cut from the reasoning backend's OpenAPI document
(version 0.1.4) by `prune_openapi.py`. `tests/test_integration_payloads.py`
validates every request body those scripts build against it, and
`tests/test_contract_snapshot.py` fails if the snapshot ever carries an
operation outside that allow list.

This repository is public: never commit the backend's full OpenAPI document.

Regenerate it when the backend API changes. Save the server's full OpenAPI
document **outside** this repository (for example from its `/openapi.json`),
then prune it into place:

```bash
python tests/contracts/prune_openapi.py /path/outside/repo/reasoning-backend.full.json \
  tests/contracts/reasoning-backend.openapi.json
```

When an integration script starts calling a new endpoint, add it to
`OPERATIONS` in `prune_openapi.py` and regenerate.
