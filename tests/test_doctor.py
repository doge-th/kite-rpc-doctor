import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from kite_rpc_doctor.cli import main
from kite_rpc_doctor.doctor import run_doctor
from kite_rpc_doctor.rpc import RpcResponseError, RpcTransportError


class DoctorTests(unittest.TestCase):
    def test_reports_matching_chain_and_block(self):
        client = Mock()
        client.call.side_effect = ["0x940", "0x1506163"]
        report = run_doctor(client, 2368)

        self.assertTrue(report.ok)
        self.assertEqual(report.chain_id, 2368)
        self.assertEqual(report.latest_block, 22045027)
        self.assertEqual(report.to_dict()["status"], "pass")

    def test_marks_chain_mismatch_as_failed(self):
        client = Mock()
        client.call.side_effect = ["0x1", "0x10"]
        report = run_doctor(client, 2368)
        self.assertFalse(report.ok)
        self.assertEqual(report.to_dict()["status"], "fail")

    def test_rejects_non_quantity_results(self):
        client = Mock()
        client.call.return_value = "2368"
        with self.assertRaises(RpcResponseError):
            run_doctor(client, 2368)

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_json_cli_returns_success(self, client_type):
        client_type.return_value.call.side_effect = ["0x940", "0x10"]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["check", "--json"])

        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["chainId"], 2368)
        self.assertEqual(report["latestBlock"], 16)

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_chain_mismatch_has_exit_status_one(self, client_type):
        client_type.return_value.call.side_effect = ["0x1", "0x10"]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["check"])
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


if __name__ == "__main__":
    unittest.main()
