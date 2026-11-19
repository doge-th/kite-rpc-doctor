import math
from dataclasses import dataclass
from typing import Any, Dict

from .doctor import DoctorReport, run_doctor
from .rpc import JsonRpcClient


@dataclass(frozen=True)
class ComparisonReport:
    primary: DoctorReport
    secondary: DoctorReport
    max_block_delta: int

    @property
    def block_delta(self) -> int:
        return abs(self.primary.latest_block - self.secondary.latest_block)

    @property
    def chain_ids_match(self) -> bool:
        return self.primary.chain_id == self.secondary.chain_id

    @property
    def blocks_in_sync(self) -> bool:
        return self.chain_ids_match and self.block_delta <= self.max_block_delta

    @property
    def ok(self) -> bool:
        return self.primary.ok and self.secondary.ok and self.blocks_in_sync

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": "pass" if self.ok else "fail",
            "blockDelta": self.block_delta,
            "maxBlockDelta": self.max_block_delta,
            "chainIdsMatch": self.chain_ids_match,
            "blocksInSync": self.blocks_in_sync,
            "primary": self.primary.to_dict(),
            "secondary": self.secondary.to_dict(),
        }


def run_comparison(
    primary: JsonRpcClient,
    secondary: JsonRpcClient,
    expected_chain_id: int,
    max_block_age_seconds: float = 300.0,
    max_block_delta: int = 5,
) -> ComparisonReport:
    if isinstance(max_block_delta, bool) or not isinstance(max_block_delta, int) or max_block_delta < 0:
        raise ValueError("maximum block delta must be a non-negative integer")
    if not math.isfinite(max_block_age_seconds) or max_block_age_seconds <= 0:
        raise ValueError("maximum block age must be a positive finite number")

    primary_report = run_doctor(primary, expected_chain_id, max_block_age_seconds)
    secondary_report = run_doctor(secondary, expected_chain_id, max_block_age_seconds)
    return ComparisonReport(primary_report, secondary_report, max_block_delta)
