# Contributing

Use focused branches and keep each change tied to a real diagnostic need. Do not add wallet private keys, paid transaction submission, fabricated chain data, or simulated success output.

Before submitting a change:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q kite_rpc_doctor tests
python3 -m kite_rpc_doctor check --json
```

The final command uses the public Kite Testnet and may be omitted only when network access is unavailable; state that explicitly in the change description. Add or update tests for behavior changes, update user-facing documentation, and record notable changes in `CHANGELOG.md`.

Commit under your own GitHub-linked identity. AI assistance is allowed, but the contributor must understand, review, and test the final code. Do not commit `.env`, credentials, build artifacts, or virtual environments.
