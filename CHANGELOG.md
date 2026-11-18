# Changelog

Notable changes are documented here. The project follows semantic versioning.

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
