# Architecture

## Modules

- `kite_rpc_doctor/rpc.py` validates endpoint settings, sends bounded JSON-RPC 2.0 requests, validates response IDs and envelopes, surfaces transport/RPC errors, and parses canonical EVM hex quantities.
- `kite_rpc_doctor/doctor.py` performs `eth_chainId` followed by `eth_blockNumber`, records per-call latency, and creates an immutable report.
- `kite_rpc_doctor/cli.py` parses arguments and environment defaults, renders text or JSON, and maps results to documented exit statuses.
- `kite_rpc_doctor/__main__.py` supports `python3 -m kite_rpc_doctor`.
- `tests/` uses a local HTTP JSON-RPC server and mocked client failures; the standard suite does not require public network access.

## Check flow

1. Parse the RPC URL, expected chain ID, and timeout.
2. Send `eth_chainId` with an incrementing request ID and no parameters.
3. Require a matching JSON-RPC 2.0 response ID and a canonical hex result.
4. Repeat the process for `eth_blockNumber`.
5. Compare the observed chain ID with the expected value and emit a report.

No credentials, transaction data, signatures, or payment headers are accepted or emitted. URL userinfo is rejected to reduce accidental credential exposure. Query-based provider tokens are not printed in reports, but callers should still protect their environment and process listings.

## Local development

Use Python 3.9 or later. Runtime code uses only the Python standard library. Keep the CLI read-only, preserve JSON output field names for automation, and add regression tests for malformed responses and boundary conditions when changing RPC behavior.
