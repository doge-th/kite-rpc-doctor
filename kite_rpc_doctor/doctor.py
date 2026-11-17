import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .rpc import JsonRpcClient, parse_hex_quantity


@dataclass(frozen=True)
class DoctorReport:
    chain_id: int
    expected_chain_id: int
    latest_block: int
    chain_latency_ms: float
    block_latency_ms: float
    observed_at: str

    @property
    def ok(self) -> bool:
        return self.chain_id == self.expected_chain_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": "pass" if self.ok else "fail",
            "chainId": self.chain_id,
            "expectedChainId": self.expected_chain_id,
            "latestBlock": self.latest_block,
            "latestBlockHex": hex(self.latest_block),
            "observedAt": self.observed_at,
            "latencyMs": {
                "chainId": self.chain_latency_ms,
                "blockNumber": self.block_latency_ms,
            },
        }


def run_doctor(client: JsonRpcClient, expected_chain_id: int) -> DoctorReport:
    started = time.monotonic()
    chain_result = client.call("eth_chainId")
    chain_latency = (time.monotonic() - started) * 1000
    chain_id = parse_hex_quantity(chain_result, "eth_chainId result")

    started = time.monotonic()
    block_result = client.call("eth_blockNumber")
    block_latency = (time.monotonic() - started) * 1000
    latest_block = parse_hex_quantity(block_result, "eth_blockNumber result")

    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return DoctorReport(
        chain_id=chain_id,
        expected_chain_id=expected_chain_id,
        latest_block=latest_block,
        chain_latency_ms=round(chain_latency, 3),
        block_latency_ms=round(block_latency, 3),
        observed_at=observed_at,
    )
