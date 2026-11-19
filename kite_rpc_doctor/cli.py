import argparse
import json
import math
import os
import sys
from typing import List, Optional

from .compare import run_comparison
from .doctor import run_doctor
from .rpc import JsonRpcClient, RpcError


def positive_chain_id(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("chain ID must be a decimal or 0x-prefixed integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("chain ID must be positive")
    return parsed


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a decimal or 0x-prefixed integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return parsed


def positive_seconds(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive and finite")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kite-rpc-doctor",
        description="Run read-only health checks against Kite EVM JSON-RPC endpoints.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check chain ID, block freshness, and optional contract code")
    check.add_argument("--rpc-url", default=os.environ.get("KITE_RPC_URL", "https://rpc-testnet.gokite.ai"))
    check.add_argument("--expected-chain-id", type=positive_chain_id, default=os.environ.get("KITE_EXPECTED_CHAIN_ID", "2368"))
    check.add_argument("--timeout", type=positive_seconds, default=os.environ.get("KITE_RPC_TIMEOUT_SECONDS", "10"))
    check.add_argument("--max-block-age-seconds", type=positive_seconds, default=os.environ.get("KITE_MAX_BLOCK_AGE_SECONDS", "300"))
    check.add_argument("--contract-address", default=os.environ.get("KITE_CONTRACT_ADDRESS"))
    check.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    compare = commands.add_parser("compare", help="compare two independent Kite RPC endpoints")
    compare.add_argument("--rpc-url", default=os.environ.get("KITE_RPC_URL", "https://rpc-testnet.gokite.ai"))
    compare.add_argument(
        "--secondary-rpc-url",
        required=os.environ.get("KITE_SECONDARY_RPC_URL") is None,
        default=os.environ.get("KITE_SECONDARY_RPC_URL"),
        help="second RPC URL (default: KITE_SECONDARY_RPC_URL)",
    )
    compare.add_argument("--expected-chain-id", type=positive_chain_id, default=os.environ.get("KITE_EXPECTED_CHAIN_ID", "2368"))
    compare.add_argument("--timeout", type=positive_seconds, default=os.environ.get("KITE_RPC_TIMEOUT_SECONDS", "10"))
    compare.add_argument("--max-block-age-seconds", type=positive_seconds, default=os.environ.get("KITE_MAX_BLOCK_AGE_SECONDS", "300"))
    compare.add_argument("--max-block-delta", type=non_negative_int, default=os.environ.get("KITE_MAX_BLOCK_DELTA", "5"))
    compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compare":
            report = run_comparison(
                JsonRpcClient(args.rpc_url, args.timeout),
                JsonRpcClient(args.secondary_rpc_url, args.timeout),
                args.expected_chain_id,
                args.max_block_age_seconds,
                args.max_block_delta,
            )
        else:
            report = run_doctor(
                JsonRpcClient(args.rpc_url, args.timeout),
                args.expected_chain_id,
                args.max_block_age_seconds,
                contract_address=args.contract_address,
            )
    except (RpcError, ValueError) as exc:
        print("kite-rpc-doctor: {}".format(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    elif args.command == "compare":
        print("Kite RPC comparison: {}".format("PASS" if report.ok else "FAIL"))
        print("Primary: chain {}, block {}".format(report.primary.chain_id, report.primary.latest_block))
        print("Secondary: chain {}, block {}".format(report.secondary.chain_id, report.secondary.latest_block))
        print("Block delta: {} (limit {})".format(report.block_delta, report.max_block_delta))
    else:
        print("Kite RPC check: {}".format("PASS" if report.ok else "FAIL"))
        print("Chain ID: {} (expected {})".format(report.chain_id, report.expected_chain_id))
        print("Latest block: {} ({})".format(report.latest_block, hex(report.latest_block)))
        print("Block age: {} seconds (limit {})".format(
            report.latest_block_age_seconds, report.max_block_age_seconds
        ))
        if report.contract_address is not None:
            print("Contract code: {}".format("DEPLOYED" if report.contract_deployed else "MISSING"))
        print("Observed at: {}".format(report.observed_at))
    return 0 if report.ok else 1
