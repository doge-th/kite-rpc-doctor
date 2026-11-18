# CLI usage

```text
kite-rpc-doctor check [--rpc-url URL] [--expected-chain-id ID]
                      [--timeout SECONDS] [--max-block-age-seconds SECONDS]
                      [--contract-address ADDRESS] [--json]
```

`python3 -m kite_rpc_doctor` is equivalent to the installed command.

## Examples

Check Kite Testnet with defaults:

```bash
python3 -m kite_rpc_doctor check
```

Check Kite Mainnet by chain ID:

```bash
python3 -m kite_rpc_doctor check \
  --rpc-url https://rpc.gokite.ai \
  --expected-chain-id 2366
```

Allow a ten-minute block age for a slower network:

```bash
python3 -m kite_rpc_doctor check --max-block-age-seconds 600
```

Check for contract bytecode at the observed block:

```bash
python3 -m kite_rpc_doctor check \
  --contract-address 0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A \
  --json
```

Use the check in shell automation:

```bash
if python3 -m kite_rpc_doctor check --json > report.json; then
  echo "RPC, chain ID, and block freshness are ready"
else
  status=$?
  echo "Check failed with status $status"
fi
```

A chain mismatch, stale block, future-dated block, or requested contract with empty code returns `1`; connectivity, configuration, and response errors return `2`. Treat all of them as a failed readiness gate.

The base JSON report contains `ok`, `status`, `chainId`, `expectedChainId`, `latestBlock`, `latestBlockHex`, `latestBlockTimestamp`, `latestBlockAgeSeconds`, `maxBlockAgeSeconds`, `blockFresh`, `observedAt`, and per-call `latencyMs` fields. Contract checks add `contractAddress`, `contractDeployed`, and a `contractCode` latency field.

## Authentication and errors

There is no wallet authentication. RPC providers that require query tokens can be used through `KITE_RPC_URL`; URL userinfo is deliberately rejected. Error output is written to standard error. Reports do not include the RPC URL.

This CLI does not expose an HTTP service or an authentication API. It is a local process that makes outbound read-only JSON-RPC requests.
