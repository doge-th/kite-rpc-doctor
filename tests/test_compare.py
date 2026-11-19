import io
import json
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from kite_rpc_doctor.cli import main
from kite_rpc_doctor.compare import run_comparison

NOW = int(time.time())


def block_result(number, age=30):
    return {"number": hex(number), "timestamp": hex(NOW - age)}


class ComparisonTests(unittest.TestCase):
    def test_matching_endpoints_pass(self):
        primary = Mock()
        secondary = Mock()
        primary.call.side_effect = ["0x940", "0x64", block_result(100)]
        secondary.call.side_effect = ["0x940", "0x64", block_result(100)]
        report = run_comparison(primary, secondary, 2368)

        self.assertTrue(report.ok)
        self.assertEqual(report.block_delta, 0)
        self.assertTrue(report.blocks_in_sync)

    def test_block_delta_within_limit_passes(self):
        primary = Mock()
        secondary = Mock()
        primary.call.side_effect = ["0x940", "0x64", block_result(100)]
        secondary.call.side_effect = ["0x940", "0x62", block_result(98)]
        report = run_comparison(primary, secondary, 2368, max_block_delta=2)
        self.assertTrue(report.ok)
        self.assertEqual(report.block_delta, 2)

    def test_block_delta_above_limit_fails(self):
        primary = Mock()
        secondary = Mock()
        primary.call.side_effect = ["0x940", "0x64", block_result(100)]
        secondary.call.side_effect = ["0x940", "0x62", block_result(98)]
        report = run_comparison(primary, secondary, 2368, max_block_delta=1)
        self.assertFalse(report.blocks_in_sync)
        self.assertFalse(report.ok)

    def test_chain_mismatch_fails(self):
        primary = Mock()
        secondary = Mock()
        primary.call.side_effect = ["0x940", "0x64", block_result(100)]
        secondary.call.side_effect = ["0x1", "0x64", block_result(100)]
        report = run_comparison(primary, secondary, 2368)
        self.assertFalse(report.chain_ids_match)
        self.assertFalse(report.ok)

    def test_unhealthy_secondary_fails_even_when_blocks_match(self):
        primary = Mock()
        secondary = Mock()
        primary.call.side_effect = ["0x940", "0x64", block_result(100)]
        secondary.call.side_effect = ["0x940", "0x64", block_result(100, age=3600)]
        report = run_comparison(primary, secondary, 2368)
        self.assertFalse(report.secondary.ok)
        self.assertFalse(report.ok)

    def test_rejects_negative_delta_before_rpc_calls(self):
        primary = Mock()
        secondary = Mock()
        with self.assertRaises(ValueError):
            run_comparison(primary, secondary, 2368, max_block_delta=-1)
        primary.call.assert_not_called()
        secondary.call.assert_not_called()

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_compare_json_cli_returns_success(self, client_type):
        client_type.return_value.call.side_effect = [
            "0x940", "0x64", block_result(100),
            "0x940", "0x64", block_result(100),
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["compare", "--secondary-rpc-url", "https://rpc-testnet.gokite.ai", "--json"])
        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["blockDelta"], 0)

    @patch("kite_rpc_doctor.cli.JsonRpcClient")
    def test_compare_divergence_has_exit_status_one(self, client_type):
        client_type.return_value.call.side_effect = [
            "0x940", "0x64", block_result(100),
            "0x940", "0x50", block_result(80),
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["compare", "--secondary-rpc-url", "https://rpc-testnet.gokite.ai"])
        self.assertEqual(status, 1)
        self.assertIn("FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
