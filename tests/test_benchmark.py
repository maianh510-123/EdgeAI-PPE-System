import csv
import http.client
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from edgeai_ppe.benchmark.cli import main
from edgeai_ppe.benchmark.metrics import latency_metrics
from edgeai_ppe.benchmark.runner import run_benchmark
from edgeai_ppe.communication.ack import Receipt, make_ack, read_ack
from edgeai_ppe.communication.http import HTTPClient, create_http_server
from edgeai_ppe.communication.payload import create_event
from edgeai_ppe.detection.result import Detection


def sample_event():
    return create_event(Detection("no_helmet", 1.0), "test", "synthetic", is_demo=True)


class MetricTests(unittest.TestCase):
    def test_known_statistics(self):
        result = latency_metrics([1, 2, 3, 4, 5])
        self.assertEqual(result["mean_ms"], 3)
        self.assertEqual(result["median_ms"], 3)
        self.assertAlmostEqual(result["p95_ms"], 4.8)
        self.assertEqual(result["jitter_ms"], 1)

    def test_empty_single_invalid(self):
        self.assertTrue(all(value is None for value in latency_metrics([]).values()))
        self.assertIsNone(latency_metrics([2])["jitter_ms"])
        for bad in ([-1], [float("nan")], [float("inf")]):
            with self.assertRaises(ValueError):
                latency_metrics(bad)

    def test_ack_validation(self):
        event = sample_event()
        ack = make_ack(event.to_json().encode(), 1234)
        self.assertEqual(read_ack(ack, event.message_id), Receipt(event.message_id, 1234))
        with self.assertRaises(ValueError):
            read_ack(ack, "wrong-id")
        with self.assertRaises(ValueError):
            make_ack(b"[]", 1234)
        value = event.to_dict()
        value["status"] = "compliant"
        with self.assertRaises(ValueError):
            make_ack(json.dumps(value).encode(), 1234)

    def test_all_dropped_does_not_send_and_writes_evidence(self):
        class NeverSend:
            def exchange(self, event):
                raise AssertionError("Dropped events must not be sent")
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            directory, result = run_benchmark(NeverSend(), protocol="http", host="localhost",
                                              port=8080, output=temp, messages=5,
                                              loss_rate=1.0, interval=0)
            self.assertEqual(result["simulated_drops"], 5)
            self.assertEqual(result["attempted_sends"], 0)
            self.assertEqual(result["application_ack_rate_planned_pct"], 0)
            self.assertIsNone(result["application_ack_rate_sent_pct"])
            self.assertIsNone(result["mean_ms"])
            with (directory / "raw.csv").open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row["status"] == "simulated_drop" for row in rows))
            self.assertEqual(json.loads((directory / "summary.json").read_text())["planned_messages"], 5)

    def test_failure_and_seed_reproducibility(self):
        class RejectingClient:
            def exchange(self, event):
                raise TimeoutError("No application ACK")
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            results = []
            for _ in range(2):
                directory, summary = run_benchmark(RejectingClient(), protocol="http", host="localhost",
                                                   port=8080, output=temp, messages=20,
                                                   loss_rate=.5, seed=42, interval=0)
                with (directory / "raw.csv").open(newline="") as file:
                    results.append([row["status"] for row in csv.DictReader(file)])
                self.assertEqual(summary["acknowledged"], 0)
                self.assertEqual(summary["failed"], summary["attempted_sends"])
                self.assertIsNone(summary["mean_ms"])
            self.assertEqual(results[0], results[1])

    def test_remote_one_way_rejected_before_sending(self):
        with self.assertRaises(ValueError):
            run_benchmark(None, protocol="http", host="192.168.1.183", port=8080,
                          measurement="local-e2e")


class HTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_http_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)

    def test_http_rtt_and_local_e2e(self):
        client = HTTPClient(port=self.port, timeout=2)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            for mode in ("rtt", "local-e2e"):
                _, summary = run_benchmark(client, protocol="http", host="127.0.0.1", port=self.port,
                                           output=temp, messages=3, interval=0, measurement=mode)
                self.assertEqual(summary["acknowledged"], 3)
                self.assertEqual(summary["failed"], 0)
                self.assertGreaterEqual(summary["mean_ms"], 0)

    def test_receiver_rejects_bad_payload(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request("POST", "/ppe", b"{}", {"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            response.read()
        finally:
            connection.close()

    def test_cli_writes_actual_results(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            with redirect_stdout(io.StringIO()):
                code = main(["send", "--protocol", "http", "--port", str(self.port),
                             "--messages", "2", "--output", temp, "--interval", "0"])
            self.assertEqual(code, 0)
            self.assertEqual(len(list(Path(temp).glob("*/summary.json"))), 1)

    def test_connection_failure_is_recorded(self):
        # Reserve an unused port without listening to avoid accidentally targeting another service.
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
            client = HTTPClient(port=port, timeout=.2)
            with tempfile.TemporaryDirectory(dir=ROOT) as temp:
                _, summary = run_benchmark(client, protocol="http", host="127.0.0.1", port=port,
                                           output=temp, messages=1, interval=0)
            self.assertEqual(summary["failed"], 1)
            self.assertIsNone(summary["mean_ms"])
