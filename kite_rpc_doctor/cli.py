import argparse
import json
import math
import os
import sys
from typing import List, Optional

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


def positive_timeout(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be positive and finite")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kite-rpc-doctor",
        description="Run read-only health checks against a Kite EVM JSON-RPC endpoint.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check chain ID and latest block")
    check.add_argument(
        "--rpc-url",
        default=os.environ.get("KITE_RPC_URL", "https://rpc-testnet.gokite.ai"),
        help="RPC URL (default: KITE_RPC_URL or Kite testnet)",
    )
    check.add_argument(
        "--expected-chain-id",
        type=positive_chain_id,
        default=os.environ.get("KITE_EXPECTED_CHAIN_ID", "2368"),
        help="expected chain ID (default: KITE_EXPECTED_CHAIN_ID or 2368)",
    )
    check.add_argument(
        "--timeout",
        type=positive_timeout,
        default=os.environ.get("KITE_RPC_TIMEOUT_SECONDS", "10"),
        help="request timeout in seconds (default: KITE_RPC_TIMEOUT_SECONDS or 10)",
    )
    check.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = JsonRpcClient(args.rpc_url, args.timeout)
        report = run_doctor(client, args.expected_chain_id)
    except (RpcError, ValueError) as exc:
        print("kite-rpc-doctor: {}".format(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print("Kite RPC check: {}".format("PASS" if report.ok else "FAIL"))
        print("Chain ID: {} (expected {})".format(report.chain_id, report.expected_chain_id))
        print("Latest block: {} ({})".format(report.latest_block, hex(report.latest_block)))
        print("Observed at: {}".format(report.observed_at))
    return 0 if report.ok else 1
