# Testing and deployment

## Automated tests

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q kite_rpc_doctor tests
```

The suite covers successful RPC calls, HTTP and JSON-RPC errors, malformed JSON, response ID mismatches, missing results, URL and timeout validation, hex quantity boundaries, chain mismatches, JSON output, and CLI exit statuses. Tests use a loopback HTTP server and mocks; they do not need testnet tokens or a wallet.

## Real Kite Testnet smoke check

```bash
python3 -m kite_rpc_doctor check \
  --rpc-url https://rpc-testnet.gokite.ai \
  --expected-chain-id 2368 \
  --timeout 15 \
  --json
```

Confirm `ok` is `true`, `chainId` is `2368`, and `latestBlock` is a non-negative integer. A block height alone is not proof of payment readiness or settlement.

## Deployment

This is a CLI, not a long-running service. Run it as an initialization gate, scheduled diagnostic, or manual developer tool. For an editable installation:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
kite-rpc-doctor check --json
```

## Troubleshooting

- **HTTP 401/403**: check the provider's authentication requirements without committing tokens.
- **Timeout or connection error**: check DNS, outbound network policy, endpoint availability, and the configured timeout.
- **Chain mismatch**: stop the dependent agent or service and verify its network configuration before continuing.
- **Malformed response**: confirm the URL is a JSON-RPC endpoint rather than a website or REST endpoint.
- **No module named `kite_rpc_doctor`**: run from the repository root or install the package in the active virtual environment.
