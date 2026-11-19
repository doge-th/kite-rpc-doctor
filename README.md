# kite-rpc-doctor

A small, read-only command-line health check for Kite EVM JSON-RPC endpoints. It helps agent and x402 developers detect a wrong network, an unreachable RPC, malformed responses, stale block data, or missing contract code before starting an agent or payment service.

## KiteAI integration

The tool sends real `eth_chainId`, `eth_blockNumber`, and `eth_getBlockByNumber` JSON-RPC requests to a Kite endpoint. When a contract address is supplied, it also calls `eth_getCode` at that block. The default endpoint is Kite Testnet (`https://rpc-testnet.gokite.ai`, chain ID `2368` / `0x940`). The integration is implemented in `kite_rpc_doctor/rpc.py` and `kite_rpc_doctor/doctor.py`; the name is not merely a label or an unused dependency.

The tool never submits transactions, signs payloads, requests wallet keys, verifies x402 payments, or claims settlement. It performs only read-only JSON-RPC calls.

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
Block age: <seconds> seconds (limit 300.0)
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
  --max-block-age-seconds 300 \
  --json
```

- `KITE_RPC_URL`: endpoint URL; credentials in URL userinfo are rejected.
- `KITE_EXPECTED_CHAIN_ID`: decimal or `0x`-prefixed expected chain ID.
- `KITE_RPC_TIMEOUT_SECONDS`: positive, finite request timeout.
- `KITE_MAX_BLOCK_AGE_SECONDS`: positive, finite maximum accepted block age. The default is 300 seconds.
- `KITE_CONTRACT_ADDRESS`: optional 20-byte EVM address checked for deployed bytecode.

The block detail must match the reported height. A stale block or a timestamp later than the local observation time fails the check. Tune the age limit for the target network and expected block production pattern.

`.env.example` is a configuration template, not an auto-loaded file. Export values in your shell or use your process manager's environment support. Do not commit real credentials.

## Contract deployment check

Pass `--contract-address` or set `KITE_CONTRACT_ADDRESS` to call `eth_getCode` at the observed latest block:

```bash
python3 -m kite_rpc_doctor check \
  --contract-address 0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A \
  --json
```

The JSON report then includes `contractAddress`, `contractDeployed`, and contract-call latency. Empty code (`0x`) fails the check. Code presence proves only that bytecode exists at that address and block, not that it is the intended, secure, or verified contract.

## Exit status

- `0`: RPC responses are valid, the chain ID matches, the latest block is fresh, and requested contract code exists.
- `1`: RPC responses are valid but the chain ID differs, the block is stale/future-dated, or requested contract code is missing.
- `2`: invalid local configuration, transport failure, RPC error, or malformed response.

See [usage](docs/USAGE.md), [architecture](docs/ARCHITECTURE.md), and [testing and deployment](docs/TESTING.md) for details.

## Known limitations

- A successful check proves RPC responsiveness, chain identity, timely block data, and requested code presence only; it does not prove that a facilitator, wallet, or paid service is ready.
- The latest block is not compared with an independent RPC or explorer, so the tool cannot detect every stalled, censored, or manipulated RPC.
- Block freshness depends on the local system clock and the configured age limit.
- Contract code presence does not establish contract identity, ownership, source verification, or safety.
- HTTP endpoints are supported for local development. Use HTTPS for remote endpoints.
- JSON-RPC response bodies are limited to 1 MiB to prevent unbounded memory consumption.
- Each JSON-RPC call has its own timeout; calls are sequential.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Released under the [MIT License](LICENSE).
