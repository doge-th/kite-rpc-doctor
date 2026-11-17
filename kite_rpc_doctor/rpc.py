import json
import math
import re
import urllib.error
import urllib.request
from itertools import count
from typing import Any, List, Optional
from urllib.parse import urlparse


class RpcError(Exception):
    pass


class RpcTransportError(RpcError):
    pass


class RpcResponseError(RpcError):
    pass


class JsonRpcClient:
    def __init__(self, url: str, timeout: float = 10.0) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RPC URL must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("RPC URL must not contain user credentials")
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("RPC timeout must be a positive finite number")

        self.url = url
        self.timeout = float(timeout)
        self._ids = count(1)

    def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        if not method:
            raise ValueError("RPC method must not be empty")

        request_id = next(self._ids)
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or [],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise RpcTransportError("RPC endpoint returned HTTP {}".format(exc.code)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RpcTransportError("RPC request failed: {}".format(reason)) from exc

        try:
            message = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RpcResponseError("RPC endpoint returned malformed JSON") from exc

        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            raise RpcResponseError("RPC response is not a JSON-RPC 2.0 object")
        if message.get("id") != request_id:
            raise RpcResponseError("RPC response ID does not match the request")
        if "error" in message:
            error = message["error"]
            if isinstance(error, dict):
                raise RpcResponseError("RPC error {}: {}".format(
                    error.get("code", "unknown"), error.get("message", "unknown")
                ))
            raise RpcResponseError("RPC endpoint returned an invalid error object")
        if "result" not in message:
            raise RpcResponseError("RPC response contains neither result nor error")
        return message["result"]


def parse_hex_quantity(value: Any, field: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(
        r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value
    ):
        raise RpcResponseError("{} must be a canonical JSON-RPC hex quantity".format(field))
    return int(value, 16)
