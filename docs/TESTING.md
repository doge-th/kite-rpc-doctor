# Testing and deployment

## Automated tests

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q kite_rpc_doctor tests
```

The suite covers successful RPC calls, block detail retrieval, HTTP and JSON-RPC errors, malformed JSON, oversized responses, response ID mismatches, missing results, URL and timeout validation, hex quantity boundaries, chain mismatches, stale and future blocks, mismatched block details, deployed and missing contract code, malformed code responses, contract address validation, JSON output, and CLI exit statuses. Tests use a loopback HTTP server, fixed observation times, and mocks; they do not need testnet tokens or a wallet.

## Real Kite Testnet smoke check

```bash
python3 -m kite_rpc_doctor check \
  --rpc-url https://rpc-testnet.gokite.ai \
  --expected-chain-id 2368 \
  --timeout 15 \
  --max-block-age-seconds 300 \
  --json
```

Confirm `ok` is `true`, `chainId` is `2368`, `latestBlock` is a non-negative integer, and `blockFresh` is `true`. If the network produces blocks less frequently, select a justified larger age limit instead of hiding a failure. A fresh block alone is not proof of payment readiness or settlement.

To include a contract code check, add `--contract-address <0x address>`. A passing result means bytecode exists at that address and block; it does not verify source code or contract safety.

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
- **Stale or future block**: check the local clock, RPC synchronization status, and the configured age limit.
- **Contract code missing**: verify the address, network, and whether the contract was deployed before the observed block.
- **Malformed response**: confirm the URL is a JSON-RPC endpoint rather than a website or REST endpoint.
- **No module named `kite_rpc_doctor`**: run from the repository root or install the package in the active virtual environment.
