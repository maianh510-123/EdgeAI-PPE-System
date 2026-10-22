"""CoAP runs when installed; MQTT needs an isolated local broker test port."""
import asyncio
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from edgeai_ppe.communication.payload import create_event
from edgeai_ppe.detection.result import Detection
from edgeai_ppe.benchmark.runner import run_benchmark


@unittest.skipUnless(importlib.util.find_spec("aiocoap"), "Optional aiocoap not installed")
class CoAPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_udp_ack(self):
        from edgeai_ppe.communication.coap import CoAPClient, create_coap_server
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        context = await create_coap_server("127.0.0.1", port)
        event = create_event(Detection("no_helmet", 1), "test", "synthetic", is_demo=True)

        def send():
            client = CoAPClient(port=port, timeout=3)
            try:
                receipt = client.exchange(event)
                with tempfile.TemporaryDirectory(dir=ROOT) as temp:
                    for mode in ("rtt", "local-e2e"):
                        _, summary = run_benchmark(client, protocol="coap", host="127.0.0.1",
                                                   port=port, output=temp, messages=3,
                                                   interval=0, measurement=mode)
                        self.assertEqual(summary["acknowledged"], 3)
                return receipt
            finally:
                client.close()
        try:
            receipt = await asyncio.to_thread(send)
            self.assertEqual(receipt.message_id, event.message_id)
            self.assertGreater(receipt.receiver_perf_ns, 0)
        finally:
            await context.shutdown()


@unittest.skipUnless(os.environ.get("EDGEAI_MQTT_TEST_PORT"), "No local MQTT test broker configured")
class MQTTIntegrationTests(unittest.TestCase):
    def test_real_broker_application_ack(self):
        from edgeai_ppe.communication.mqtt import MQTTClient, create_mqtt_receiver
        port = int(os.environ["EDGEAI_MQTT_TEST_PORT"])
        prefix = "ppe/test/" + uuid4().hex
        receiver = create_mqtt_receiver(port=port, topic_prefix=prefix, timeout=3)
        try:
            client = MQTTClient(port=port, topic_prefix=prefix, timeout=3)
            try:
                for _ in range(3):
                    event = create_event(Detection("no_helmet", 1), "test", "synthetic", is_demo=True)
                    self.assertEqual(client.exchange(event).message_id, event.message_id)
                with tempfile.TemporaryDirectory(dir=ROOT) as temp:
                    for mode in ("rtt", "local-e2e"):
                        _, summary = run_benchmark(client, protocol="mqtt", host="127.0.0.1",
                                                   port=port, output=temp, messages=3,
                                                   interval=0, measurement=mode)
                        self.assertEqual(summary["acknowledged"], 3)
            finally:
                client.close()
        finally:
            receiver.close()

    def test_absent_subscriber_times_out(self):
        from edgeai_ppe.communication.mqtt import MQTTClient
        client = MQTTClient(port=int(os.environ["EDGEAI_MQTT_TEST_PORT"]),
                            topic_prefix="ppe/test/" + uuid4().hex, timeout=.5)
        try:
            event = create_event(Detection("no_helmet", 1), "test", "synthetic", is_demo=True)
            with self.assertRaises(TimeoutError):
                client.exchange(event)
        finally:
            client.close()
