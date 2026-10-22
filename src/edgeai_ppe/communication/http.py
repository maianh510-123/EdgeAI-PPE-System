"""HTTP experiment adapter; one new connection per event, no proxy lookup."""
import http.client
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from edgeai_ppe.communication.ack import MAX_PAYLOAD_BYTES, make_ack, read_ack


class HTTPClient:
    def __init__(self, host="127.0.0.1", port=8080, timeout=5.0):
        self.host, self.port, self.timeout = host, port, timeout

    def exchange(self, event):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request("POST", "/ppe", event.to_json().encode("utf-8"),
                               {"Content-Type": "application/json"})
            response = connection.getresponse()
            payload = response.read(MAX_PAYLOAD_BYTES + 1)
            if response.status != 200:
                raise OSError(f"HTTP status {response.status}")
            return read_ack(payload, event.message_id)
        except (http.client.HTTPException, ValueError) as exc:
            raise OSError(str(exc)) from exc
        finally:
            connection.close()

    def send(self, event):
        self.exchange(event)

    def close(self):
        pass


class PPEHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ppe":
            self.send_error(404)
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Chunked requests are unsupported")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_PAYLOAD_BYTES:
                raise ValueError("Invalid Content-Length")
            self.connection.settimeout(5)
            payload = self.rfile.read(length)
            received_ns = time.perf_counter_ns()
            if len(payload) != length:
                raise ValueError("Incomplete body")
            ack = make_ack(payload, received_ns)
        except (ValueError, TypeError, KeyError, OSError):
            self.send_error(400, "Invalid PPE event")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(ack)))
        self.end_headers()
        self.wfile.write(ack)

    def log_message(self, format, *args):
        pass


def create_http_server(host="127.0.0.1", port=8080):
    return ThreadingHTTPServer((host, port), PPEHandler)
