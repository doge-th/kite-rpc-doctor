# kite-rpc-doctor

A small, read-only command-line health check for Kite EVM JSON-RPC endpoints. It helps agent and x402 developers detect a wrong network, an unreachable RPC, or a malformed endpoint response before starting an agent or payment service.

## KiteAI integration

The tool sends real `eth_chainId` and `eth_blockNumber` JSON-RPC requests to a Kite endpoint. The default endpoint is Kite Testnet (`https://rpc-testnet.gokite.ai`, chain ID `2368` / `0x940`). The integration is implemented in `kite_rpc_doctor/rpc.py` and `kite_rpc_doctor/doctor.py`; the name is not merely a label or an unused dependency.

The tool never submits transactions, signs payloads, requests wallet keys, verifies x402 payments, or claims settlement. It performs only the two read-only calls above.

## Requirements

- Python 3.9 or later
- No third-party runtime dependencies

## Quick start

Run directly from a source checkout:

```bash
python3 -m kite_rpc_doctor check
```

Expected text output:

```text
Kite RPC check: PASS
Chain ID: 2368 (expected 2368)
Latest block: <current height> (<current hex height>)
Observed at: <UTC timestamp>
```

Machine-readable output:

```bash
python3 -m kite_rpc_doctor check --json
```

Optional editable installation provides the `kite-rpc-doctor` command:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
kite-rpc-doctor check --json
```

## Configuration

Flags override environment defaults:

```bash
python3 -m kite_rpc_doctor check \
  --rpc-url https://rpc-testnet.gokite.ai \
  --expected-chain-id 2368 \
  --timeout 10 \
  --json
```

- `KITE_RPC_URL`: endpoint URL; credentials in URL userinfo are rejected.
- `KITE_EXPECTED_CHAIN_ID`: decimal or `0x`-prefixed expected chain ID.
- `KITE_RPC_TIMEOUT_SECONDS`: positive, finite request timeout.

`.env.example` is a configuration template, not an auto-loaded file. Export values in your shell or use your process manager's environment support. Do not commit real credentials.

## Exit status

- `0`: RPC responses are valid and the chain ID matches.
- `1`: RPC responses are valid but the chain ID differs from the expected value.
- `2`: invalid local configuration, transport failure, RPC error, or malformed response.

See [usage](docs/USAGE.md), [architecture](docs/ARCHITECTURE.md), and [testing and deployment](docs/TESTING.md) for details.

## Known limitations

- A successful check proves RPC responsiveness and chain identity only; it does not prove that a facilitator, wallet, contract, or paid service is ready.
- The latest block height is reported but not compared with another source, so this version does not detect every stalled or censored RPC.
- HTTP endpoints are supported for local development. Use HTTPS for remote endpoints.
- Each JSON-RPC call has its own timeout; the two-call check is sequential.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Released under the [MIT License](LICENSE).
