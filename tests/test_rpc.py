import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kite_rpc_doctor.rpc import (
    JsonRpcClient,
    RpcResponseError,
    RpcTransportError,
    parse_hex_quantity,
)


class RpcHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))

        if self.path == "/http-error":
            self.send_error(503)
            return
        if self.path == "/malformed":
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

    def test_surfaces_rpc_errors(self):
        with self.assertRaisesRegex(RpcResponseError, "method not found"):
            JsonRpcClient(self.base_url + "/rpc-error").call("eth_chainId")

    def test_rejects_malformed_json(self):
        with self.assertRaisesRegex(RpcResponseError, "malformed JSON"):
            JsonRpcClient(self.base_url + "/malformed").call("eth_chainId")

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

    def test_parses_canonical_hex_quantities(self):
        self.assertEqual(parse_hex_quantity("0x940", "chain ID"), 2368)
        self.assertEqual(parse_hex_quantity("0x0", "block"), 0)
        for value in ("940", "0x", "0x0940", "", None, 2368):
            with self.subTest(value=value), self.assertRaises(RpcResponseError):
                parse_hex_quantity(value, "chain ID")


if __name__ == "__main__":
    unittest.main()
