import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional

from .compare import run_comparison
from .doctor import run_doctor
from .rpc import JsonRpcClient, RpcError, RpcTransportError


def parse_header(value: str) -> "tuple[str, str]":
    if ":" not in value:
        raise argparse.ArgumentTypeError("header must be in 'Name: value' form")
    name, header_value = value.split(":", 1)
    name = name.strip()
    header_value = header_value.strip()
    if not name:
        raise argparse.ArgumentTypeError("header name must not be empty")
    return name, header_value


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


def error_report(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, ValueError):
        error_type = "configuration"
    elif isinstance(exc, RpcTransportError):
        error_type = "transport"
    else:
        error_type = "rpc_response"
    return {
        "reportVersion": 1,
        "ok": False,
        "status": "error",
        "error": {"type": error_type, "message": str(exc)},
    }


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
    check.add_argument(
        "--header",
        action="append",
        type=parse_header,
        default=[],
        metavar="NAME: VALUE",
        help="custom HTTP header for RPC requests (repeatable)",
    )
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
    compare.add_argument(
        "--header",
        action="append",
        type=parse_header,
        default=[],
        metavar="NAME: VALUE",
        help="custom HTTP header for RPC requests (repeatable)",
    )
    compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def build_headers(pairs: List["tuple[str, str]"]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    seen: set = set()
    for name, value in pairs:
        key = name.lower()
        if key in seen:
            raise ValueError("duplicate HTTP header: {}".format(name))
        seen.add(key)
        headers[name] = value
    return headers


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        headers = build_headers(args.header)
        if args.command == "compare":
            report = run_comparison(
                JsonRpcClient(args.rpc_url, args.timeout, headers),
                JsonRpcClient(args.secondary_rpc_url, args.timeout, headers),
                args.expected_chain_id,
                args.max_block_age_seconds,
                args.max_block_delta,
            )
        else:
            report = run_doctor(
                JsonRpcClient(args.rpc_url, args.timeout, headers),
                args.expected_chain_id,
                args.max_block_age_seconds,
                contract_address=args.contract_address,
            )
    except (RpcError, ValueError) as exc:
        if args.json:
            print(json.dumps(error_report(exc), indent=2, sort_keys=True))
        else:
            print("kite-rpc-doctor: {}".format(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    elif args.command == "compare":
        print("Kite RPC comparison: {}".format("PASS" if report.ok else "FAIL"))
        print("Primary: chain {}, block {}".format(report.primary.chain_id, report.primary.latest_block))
        print("Secondary: chain {}, block {}".format(report.secondary.chain_id, report.secondary.latest_block))
        print("Block delta: {} (limit {})".format(report.block_delta, report.max_block_delta))
        if not report.ok:
            print("Failure reasons: {}".format(", ".join(report.failure_reasons) or "none"))
    else:
        print("Kite RPC check: {}".format("PASS" if report.ok else "FAIL"))
        print("Chain ID: {} (expected {})".format(report.chain_id, report.expected_chain_id))
        print("Latest block: {} ({})".format(report.latest_block, hex(report.latest_block)))
        if report.latest_block_hash is not None:
            print("Block hash: {}".format(report.latest_block_hash))
        print("Block age: {} seconds (limit {})".format(
            report.latest_block_age_seconds, report.max_block_age_seconds
        ))
        if report.contract_address is not None:
            print("Contract code: {}".format("DEPLOYED" if report.contract_deployed else "MISSING"))
        print("Observed at: {}".format(report.observed_at))
    return 0 if report.ok else 1
