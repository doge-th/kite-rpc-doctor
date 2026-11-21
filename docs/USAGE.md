# CLI usage

```text
kite-rpc-doctor check [--rpc-url URL] [--expected-chain-id ID]
                      [--timeout SECONDS] [--max-block-age-seconds SECONDS]
                      [--contract-address ADDRESS] [--json]

kite-rpc-doctor compare --rpc-url URL --secondary-rpc-url URL
                        [--expected-chain-id ID] [--timeout SECONDS]
                        [--max-block-age-seconds SECONDS]
                        [--max-block-delta BLOCKS] [--json]
```

`python3 -m kite_rpc_doctor` is equivalent to the installed command.

## Health-check examples

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

## Endpoint comparison

Replace the placeholder with an independent Kite RPC provider:

```bash
python3 -m kite_rpc_doctor compare \
  --rpc-url https://rpc-testnet.gokite.ai \
  --secondary-rpc-url https://your-secondary-kite-rpc.example \
  --max-block-delta 5 \
  --json
```

Both endpoint reports must pass, chain IDs must match, and the absolute block-height difference must not exceed the configured limit. A result can fail because either endpoint is unhealthy or because their observations diverge. Reusing one URL for both sides checks the CLI flow only and is not independent evidence.

Use either command in shell automation:

```bash
if python3 -m kite_rpc_doctor compare \
  --secondary-rpc-url https://your-secondary-kite-rpc.example \
  --json > comparison.json; then
  echo "Both endpoints are consistent"
else
  status=$?
  echo "Comparison failed with status $status"
fi
```

A chain mismatch, stale block, future-dated block, requested contract with empty code, or endpoint divergence returns `1`; connectivity, configuration, and response errors return `2`. Treat all of them as a failed readiness gate. With `--json`, runtime errors are emitted as JSON with `reportVersion`, `status:"error"`, and an `error` object containing `type` and `message`; successful reports also carry `reportVersion:1`.

The base health report contains `ok`, `status`, `chainId`, `expectedChainId`, `latestBlock`, `latestBlockHex`, `latestBlockTimestamp`, `latestBlockAgeSeconds`, `maxBlockAgeSeconds`, `blockFresh`, `observedAt`, and per-call `latencyMs` fields. Contract checks add `contractAddress`, `contractDeployed`, and a `contractCode` latency field. Comparisons add `blockDelta`, `maxBlockDelta`, `chainIdsMatch`, `blocksInSync`, `primary`, and `secondary`.

## Authentication and errors

There is no wallet authentication. RPC providers that require query tokens can be used through environment variables; URL userinfo is deliberately rejected. Error output is written to standard error. Reports do not include either RPC URL.

This CLI does not expose an HTTP service or an authentication API. It is a local process that makes outbound read-only JSON-RPC requests.
