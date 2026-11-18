import io
import json
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from kite_rpc_doctor.cli import main
from kite_rpc_doctor.doctor import run_doctor
from kite_rpc_doctor.rpc import RpcResponseError, RpcTransportError

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def block_result(number=16, timestamp=None):
    if timestamp is None:
        timestamp = int(time.time()) - 30
    return {"number": hex(number), "timestamp": hex(timestamp)}


class DoctorTests(unittest.TestCase):
    def test_reports_matching_chain_block_and_freshness(self):
        client = Mock()
        client.call.side_effect = [
            "0x940",
            "0x1506163",
            block_result(22045027, int(NOW.timestamp()) - 30),
        ]
        report = run_doctor(client, 2368, 300, now=NOW)

        self.assertTrue(report.ok)
        self.assertTrue(report.block_fresh)
        self.assertEqual(report.chain_id, 2368)
        self.assertEqual(report.latest_block, 22045027)
        self.assertEqual(report.latest_block_age_seconds, 30)
        self.assertEqual(report.to_dict()["status"], "pass")
        client.call.assert_called_with("eth_getBlockByNumber", ["0x1506163", False])

    def test_marks_chain_mismatch_as_failed(self):
        client = Mock()
        client.call.side_effect = ["0x1", "0x10", block_result()]
        report = run_doctor(client, 2368, 300, now=NOW)
        self.assertFalse(report.ok)
        self.assertEqual(report.to_dict()["status"], "fail")

    def test_marks_stale_block_as_failed(self):
        client = Mock()
        client.call.side_effect = [
            "0x940",
            "0x10",
            block_result(16, int(NOW.timestamp()) - 301),
        ]
        report = run_doctor(client, 2368, 300, now=NOW)
        self.assertFalse(report.block_fresh)
        self.assertFalse(report.ok)

    def test_marks_future_block_as_failed(self):
        client = Mock()
        client.call.side_effect = [
            "0x940",
            "0x10",
            block_result(16, int(NOW.timestamp()) + 1),
        ]
        report = run_doctor(client, 2368, 300, now=NOW)
        self.assertEqual(report.latest_block_age_seconds, -1)
        self.assertFalse(report.ok)

    def test_rejects_non_quantity_results(self):
        client = Mock()
        client.call.return_value = "2368"
        with self.assertRaises(RpcResponseError):
            run_doctor(client, 2368)

    def test_rejects_mismatched_block_details(self):
        client = Mock()
        client.call.side_effect = ["0x940", "0x10", block_result(17)]
        with self.assertRaisesRegex(RpcResponseError, "does not match"):
            run_doctor(client, 2368)

    def test_rejects_missing_block_timestamp(self):
        client = Mock()
        client.call.side_effect = ["0x940", "0x10", {"number": "0x10"}]
        with self.assertRaisesRegex(RpcResponseError, "block timestamp"):
            run_doctor(client, 2368)

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_json_cli_returns_success(self, client_type):
        client_type.return_value.call.side_effect = ["0x940", "0x10", block_result()]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["check", "--json"])

        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["ok"])
        self.assertTrue(report["blockFresh"])
        self.assertEqual(report["chainId"], 2368)
        self.assertEqual(report["latestBlock"], 16)
        self.assertEqual(report["maxBlockAgeSeconds"], 300.0)

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_chain_mismatch_has_exit_status_one(self, client_type):
        client_type.return_value.call.side_effect = ["0x1", "0x10", block_result()]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["check"])
        self.assertEqual(status, 1)
        self.assertIn("FAIL", output.getvalue())

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_stale_block_has_exit_status_one(self, client_type):
        client_type.return_value.call.side_effect = [
            "0x940",
            "0x10",
            block_result(timestamp=int(time.time()) - 3600),
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["check", "--max-block-age-seconds", "300"])
        self.assertEqual(status, 1)
        self.assertIn("FAIL", output.getvalue())

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_rpc_failure_has_exit_status_two(self, client_type):
        client_type.return_value.call.side_effect = RpcTransportError("offline")
        errors = io.StringIO()
        with redirect_stderr(errors):
            status = main(["check"])
        self.assertEqual(status, 2)
        self.assertIn("offline", errors.getvalue())

    def test_reports_deployed_contract_code(self):
        client = Mock()
        address = "0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A"
        client.call.side_effect = [
            "0x940",
            "0x10",
            block_result(16, int(NOW.timestamp()) - 30),
            "0x6000",
        ]
        report = run_doctor(client, 2368, 300, now=NOW, contract_address=address)
        self.assertTrue(report.contract_deployed)
        self.assertTrue(report.ok)
        self.assertTrue(report.to_dict()["contractDeployed"])
        client.call.assert_called_with("eth_getCode", [address, "0x10"])

    def test_missing_contract_code_fails_the_check(self):
        client = Mock()
        client.call.side_effect = ["0x940", "0x10", block_result(), "0x0"]
        with self.assertRaises(RpcResponseError):
            run_doctor(client, 2368, contract_address="0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A")

    def test_rejects_invalid_contract_address_before_rpc_calls(self):
        client = Mock()
        with self.assertRaises(ValueError):
            run_doctor(client, 2368, contract_address="0x1234")
        client.call.assert_not_called()

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_missing_contract_code_has_exit_status_one(self, client_type):
        client_type.return_value.call.side_effect = ["0x940", "0x10", block_result(), "0x"]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main([
                "check",
                "--contract-address",
                "0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A",
            ])
        self.assertEqual(status, 1)
        self.assertIn("Contract code: MISSING", output.getvalue())


if __name__ == "__main__":
    unittest.main()
