# Changelog

Notable changes are documented here. The project follows semantic versioning.

## 0.5.0 - 2026-11-22

### Added

- `failureReasons` in comparison JSON reports: machine-readable breakdown of comparison failures (`primary_chain_id_mismatch`, `secondary_block_stale`, `chain_id_divergence`, `block_delta_exceeded`, and related codes).
- Text `compare` output now prints `Failure reasons:` whenever the comparison fails.
- Regression tests for reason breakdown, empty list on pass, JSON field, and text output.

## 0.4.1 - 2026-11-21

### Added

- Versioned JSON reports and structured JSON runtime errors for transport, RPC-response, and configuration failures.
- Standard-output error reports under `--json`, preserving text behavior for non-JSON callers.
- Regression tests for structured error type, message, version, and exit status.

## 0.4.0 - 2026-11-20

### Added

- New `compare` command for independent Kite RPC health and divergence checks.
- Configurable maximum block-height delta with chain ID and endpoint health requirements.
- Full primary/secondary comparison reports without endpoint URLs.
- Environment configuration for secondary RPC URL and block delta, with CLI and boundary tests.

## 0.3.1 - 2026-11-19

### Fixed

- Limit JSON-RPC response bodies to 1 MiB so malformed or hostile endpoints cannot cause unbounded memory consumption.
- Add a loopback regression covering responses that exceed the limit.

## 0.3.0 - 2026-11-19

### Added

- Optional `eth_getCode` check for deployed contract bytecode at the observed latest block.
- `--contract-address` and `KITE_CONTRACT_ADDRESS` configuration.
- Contract presence and latency fields in JSON reports, plus CLI output and exit-status handling.
- Validation for contract addresses and malformed bytecode responses, with loopback and CLI regressions.

## 0.2.0 - 2026-11-18

### Added

- Read the latest block with `eth_getBlockByNumber` and verify that it matches the reported height.
- Report the block timestamp, age, freshness decision, and configurable maximum age.
- Fail closed for stale or future-dated blocks while keeping read-only behavior.
- Deterministic block-age tests and loopback coverage for block detail retrieval.

## 0.1.0 - 2026-11-17

### Added

- Read-only Kite JSON-RPC checks for chain identity and latest block height.
- Text and JSON reports with per-call latency and UTC observation time.
- CLI flags and environment configuration for endpoint, expected chain ID, and timeout.
- Validation for JSON-RPC envelopes, response IDs, errors, and canonical hex quantities.
- Standard-library unit and loopback integration tests, usage documentation, and testnet smoke-check instructions.
