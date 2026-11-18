import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .rpc import JsonRpcClient, RpcResponseError, parse_hex_quantity


@dataclass(frozen=True)
class DoctorReport:
    chain_id: int
    expected_chain_id: int
    latest_block: int
    latest_block_timestamp: int
    latest_block_age_seconds: float
    max_block_age_seconds: float
    chain_latency_ms: float
    block_latency_ms: float
    block_detail_latency_ms: float
    observed_at: str

    @property
    def block_fresh(self) -> bool:
        return 0 <= self.latest_block_age_seconds <= self.max_block_age_seconds

    @property
    def ok(self) -> bool:
        return self.chain_id == self.expected_chain_id and self.block_fresh

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": "pass" if self.ok else "fail",
            "chainId": self.chain_id,
            "expectedChainId": self.expected_chain_id,
            "latestBlock": self.latest_block,
            "latestBlockHex": hex(self.latest_block),
            "latestBlockTimestamp": self.latest_block_timestamp,
            "latestBlockAgeSeconds": self.latest_block_age_seconds,
            "maxBlockAgeSeconds": self.max_block_age_seconds,
            "blockFresh": self.block_fresh,
            "observedAt": self.observed_at,
            "latencyMs": {
                "chainId": self.chain_latency_ms,
                "blockNumber": self.block_latency_ms,
                "blockByNumber": self.block_detail_latency_ms,
            },
        }


def run_doctor(
    client: JsonRpcClient,
    expected_chain_id: int,
    max_block_age_seconds: float = 300.0,
    now: Optional[datetime] = None,
) -> DoctorReport:
    if not math.isfinite(max_block_age_seconds) or max_block_age_seconds <= 0:
        raise ValueError("maximum block age must be a positive finite number")
    current_time = now if now is not None else datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("observation time must be timezone-aware")

    started = time.monotonic()
    chain_result = client.call("eth_chainId")
    chain_latency = (time.monotonic() - started) * 1000
    chain_id = parse_hex_quantity(chain_result, "eth_chainId result")

    started = time.monotonic()
    block_result = client.call("eth_blockNumber")
    block_latency = (time.monotonic() - started) * 1000
    latest_block = parse_hex_quantity(block_result, "eth_blockNumber result")

    started = time.monotonic()
    block = client.call("eth_getBlockByNumber", [hex(latest_block), False])
    block_detail_latency = (time.monotonic() - started) * 1000
    if not isinstance(block, dict):
        raise RpcResponseError("eth_getBlockByNumber result must be an object")
    block_number = parse_hex_quantity(block.get("number"), "block number")
    if block_number != latest_block:
        raise RpcResponseError("block detail number does not match eth_blockNumber")
    block_timestamp = parse_hex_quantity(block.get("timestamp"), "block timestamp")
    try:
        block_time = datetime.fromtimestamp(block_timestamp, timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise RpcResponseError("block timestamp is outside the supported range") from exc

    block_age = (current_time - block_time).total_seconds()
    observed_at = current_time.isoformat(timespec="seconds").replace("+00:00", "Z")
    return DoctorReport(
        chain_id=chain_id,
        expected_chain_id=expected_chain_id,
        latest_block=latest_block,
        latest_block_timestamp=block_timestamp,
        latest_block_age_seconds=block_age,
        max_block_age_seconds=float(max_block_age_seconds),
        chain_latency_ms=round(chain_latency, 3),
        block_latency_ms=round(block_latency, 3),
        block_detail_latency_ms=round(block_detail_latency, 3),
        observed_at=observed_at,
    )
