# Architecture

## Modules

- `kite_rpc_doctor/rpc.py` validates endpoint settings, sends bounded JSON-RPC 2.0 requests, reads at most 1 MiB of each response, validates response IDs and envelopes, surfaces transport/RPC errors, and parses canonical EVM hex quantities.
- `kite_rpc_doctor/doctor.py` performs chain, block, and freshness checks, optionally requests contract bytecode, and creates an immutable report.
- `kite_rpc_doctor/compare.py` runs the doctor flow against two clients and compares their chain IDs and block heights with a configured maximum delta.
- `kite_rpc_doctor/cli.py` provides the `check` and `compare` commands, parses arguments and environment defaults, renders text or versioned JSON, emits structured JSON runtime errors, and maps results to documented exit statuses.
- `kite_rpc_doctor/__main__.py` supports `python3 -m kite_rpc_doctor`.
- `tests/` uses local HTTP JSON-RPC servers, fixed observation times, and mocked client failures; the standard suite does not require public network access.

## Check flow

1. Parse the RPC URL, expected chain ID, request timeout, maximum block age, and optional contract address.
2. Validate the contract address before making any RPC call when it is supplied.
3. Send `eth_chainId` and require a matching JSON-RPC response ID and canonical hex result.
4. Repeat for `eth_blockNumber`.
5. Request the corresponding block with `eth_getBlockByNumber(height, false)`.
6. Require the returned block number to match and its timestamp to be a canonical hex quantity.
7. If requested, call `eth_getCode(address, height)`, require whole-byte hex data, and treat `0x` as missing code.
8. Compare the chain ID, block age, and contract presence with expectations. Ages outside `0..maxBlockAgeSeconds`, including future timestamps, fail the report.

## Comparison flow

1. Run the complete check flow against the primary endpoint.
2. Run it against the secondary endpoint with the same expected chain ID and freshness limit.
3. Require both reports to pass, their chain IDs to match, and the absolute block-height difference to be at most `maxBlockDelta`.
4. Emit both reports and the comparison result. Endpoint URLs are not included in the output.

## Local development

Use Python 3.9 or later. Runtime code uses only the Python standard library. Keep the CLI read-only, preserve existing JSON output field names for automation, and add regression tests for malformed responses and boundary conditions when changing RPC behavior. Inject a fixed observation time in block-age tests to keep them deterministic.
