import json
import threading
import time
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional
from unittest.mock import patch

from kite_rpc_doctor.rpc import (
    MAX_RESPONSE_BYTES,
    JsonRpcClient,
    RpcResponseError,
    RpcTransportError,
    parse_hex_quantity,
)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, _limit: int = -1) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class RpcHandler(BaseHTTPRequestHandler):
    received_headers: List[Dict[str, Optional[str]]] = []

    def do_POST(self):
        self.received_headers.append({
            "content-type": self.headers.get("Content-Type"),
            "accept": self.headers.get("Accept"),
            "x-api-key": self.headers.get("X-Api-Key"),
        })
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))

        if self.path == "/http-error":
            self.send_error(503)
            return
        if self.path == "/large-response":
            body = b"{" + b" " * MAX_RESPONSE_BYTES
        elif self.path == "/malformed":
            body = b"{"
        else:
            message = {"jsonrpc": "2.0", "id": request["id"]}
            if self.path == "/wrong-id":
                message["id"] = request["id"] + 1
                message["result"] = "0x940"
            elif self.path == "/missing-result":
                pass
            elif self.path == "/rpc-error":
                message["error"] = {"code": -32601, "message": "method not found"}
            elif request["method"] == "eth_getCode":
                message["result"] = "0x6000"
            elif request["method"] == "eth_getBlockByNumber":
                message["result"] = {
                    "number": request["params"][0],
                    "timestamp": hex(int(time.time()) - 30),
                }
            else:
                message["result"] = "0x940" if request["method"] == "eth_chainId" else "0x1506163"
            body = json.dumps(message).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class JsonRpcClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), RpcHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:{}".format(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_calls_json_rpc_methods(self):
        client = JsonRpcClient(self.base_url)
        self.assertEqual(client.call("eth_chainId"), "0x940")
        self.assertEqual(client.call("eth_blockNumber"), "0x1506163")
        block = client.call("eth_getBlockByNumber", ["0x1506163", False])
        self.assertEqual(block["number"], "0x1506163")
        self.assertGreater(int(block["timestamp"], 16), 0)
        self.assertEqual(client.call("eth_getCode", ["0x38129cf4CE5E183eFF248F42A7D345Bb1B47621A", "0x1506163"]), "0x6000")

    def test_surfaces_rpc_errors(self):
        with self.assertRaisesRegex(RpcResponseError, "method not found"):
            JsonRpcClient(self.base_url + "/rpc-error").call("eth_chainId")

    def test_rejects_malformed_json(self):
        with self.assertRaisesRegex(RpcResponseError, "malformed JSON"):
            JsonRpcClient(self.base_url + "/malformed").call("eth_chainId")

    def test_rejects_oversized_responses(self):
        with self.assertRaisesRegex(RpcResponseError, "1 MiB limit"):
            JsonRpcClient(self.base_url + "/large-response").call("eth_chainId")

    def test_rejects_mismatched_response_ids(self):
        with self.assertRaisesRegex(RpcResponseError, "ID does not match"):
            JsonRpcClient(self.base_url + "/wrong-id").call("eth_chainId")

    def test_rejects_missing_results(self):
        with self.assertRaisesRegex(RpcResponseError, "neither result nor error"):
            JsonRpcClient(self.base_url + "/missing-result").call("eth_chainId")

    def test_surfaces_http_errors(self):
        with self.assertRaisesRegex(RpcTransportError, "HTTP 503"):
            JsonRpcClient(self.base_url + "/http-error").call("eth_chainId")

    def test_validates_url_and_timeout(self):
        for url in ("", "file:///tmp/rpc", "https://user:secret@example.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                JsonRpcClient(url)
        for timeout in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                JsonRpcClient(self.base_url, timeout)

    def test_accepts_and_sends_custom_headers(self):
        RpcHandler.received_headers.clear()
        client = JsonRpcClient(self.base_url, headers={"X-Api-Key": "secret"})
        self.assertEqual(client.call("eth_chainId"), "0x940")
        self.assertEqual(RpcHandler.received_headers[-1]["content-type"], "application/json")
        self.assertEqual(RpcHandler.received_headers[-1]["accept"], "application/json")
        self.assertEqual(RpcHandler.received_headers[-1]["x-api-key"], "secret")

    def test_rejects_invalid_custom_headers(self):
        for headers in ("not-a-dict", {1: "value"}, {"key": 123}):
            with self.subTest(headers=headers), self.assertRaises(ValueError):
                JsonRpcClient(self.base_url, headers=headers)

    def test_validates_max_retries(self):
        for max_retries in (-1, True, 1.5, None):
            with self.subTest(max_retries=max_retries), self.assertRaises(ValueError):
                JsonRpcClient(self.base_url, max_retries=max_retries)
        self.assertEqual(JsonRpcClient(self.base_url, max_retries=0).call("eth_chainId"), "0x940")

    def test_retries_connection_failures_then_succeeds(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x940"}).encode("utf-8")
        failures = [urllib.error.URLError("boom"), urllib.error.URLError("boom")]
        with patch("kite_rpc_doctor.rpc.urllib.request.urlopen") as urlopen, \
                patch("kite_rpc_doctor.rpc.time.sleep") as sleep:
            urlopen.side_effect = failures + [_FakeResponse(body)]
            client = JsonRpcClient(self.base_url, max_retries=3)
            self.assertEqual(client.call("eth_chainId"), "0x940")
        self.assertEqual(urlopen.call_count, 3)
        self.assertGreaterEqual(sleep.call_count, 2)

    def test_gives_up_after_exhausting_retries(self):
        with patch("kite_rpc_doctor.rpc.urllib.request.urlopen") as urlopen, \
                patch("kite_rpc_doctor.rpc.time.sleep"):
            urlopen.side_effect = urllib.error.URLError("offline")
            client = JsonRpcClient(self.base_url, max_retries=2)
            with self.assertRaisesRegex(RpcTransportError, "offline"):
                client.call("eth_chainId")
        self.assertEqual(urlopen.call_count, 3)

    def test_does_not_retry_http_errors(self):
        with patch("kite_rpc_doctor.rpc.urllib.request.urlopen") as urlopen, \
                patch("kite_rpc_doctor.rpc.time.sleep") as sleep:
            urlopen.side_effect = urllib.error.HTTPError(
                self.base_url, 503, "Service Unavailable", {}, None)
            client = JsonRpcClient(self.base_url, max_retries=3)
            with self.assertRaisesRegex(RpcTransportError, "HTTP 503"):
                client.call("eth_chainId")
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    def test_rejects_invalid_method_and_params_without_sending_a_request(self):
        client = JsonRpcClient(self.base_url)
        for method in ("", None, 123, True):
            with self.subTest(method=method), self.assertRaises(ValueError) as ctx:
                client.call(method)
            self.assertIn("RPC method", str(ctx.exception))
        for params in ("0x940", 5, 1.5, True):
            with self.subTest(params=params), self.assertRaises(ValueError) as ctx:
                client.call("eth_chainId", params)
            self.assertIn("RPC params", str(ctx.exception))

    def test_accepts_list_and_dict_params(self):
        client = JsonRpcClient(self.base_url)
        self.assertEqual(client.call("eth_chainId", []), "0x940")
        self.assertEqual(client.call("eth_chainId", {"block": "latest"}), "0x940")

    def test_parses_canonical_hex_quantities(self):
        self.assertEqual(parse_hex_quantity("0x940", "chain ID"), 2368)
        self.assertEqual(parse_hex_quantity("0x0", "block"), 0)
        for value in ("940", "0x", "0x0940", "", None, 2368):
            with self.subTest(value=value), self.assertRaises(RpcResponseError):
                parse_hex_quantity(value, "chain ID")


if __name__ == "__main__":
    unittest.main()
