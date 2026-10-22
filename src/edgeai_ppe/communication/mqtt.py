"""Optional MQTT 3.1.1 experiment: application ACK, not broker PUBACK."""
import json
import logging
import threading
import time
from uuid import uuid4

from edgeai_ppe.communication.ack import make_ack, read_ack


class MQTTSession:
    def __init__(self, host, port, topic, callback, timeout=5.0, qos=1):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("Install communication_testbed/requirements.txt for MQTT") from exc
        self.host, self.port, self.topic = host, port, topic
        self.timeout, self.qos, self.callback = timeout, qos, callback
        self.ready = threading.Event()
        self.error = None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id="ppe-" + uuid4().hex, reconnect_on_failure=False)
        self.client.connect_timeout = timeout
        self.client.max_queued_messages_set(100)
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.error = f"MQTT connection rejected: {reason_code}"
            self.ready.set()
            return
        rc, _ = client.subscribe(self.topic, qos=self.qos)
        if rc != 0:
            self.error = f"MQTT subscribe failed: {rc}"
            self.ready.set()

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            self.error = "MQTT subscription rejected"
        self.ready.set()

    def _on_message(self, client, userdata, message):
        if message.retain:
            return
        self.callback(message.payload, time.perf_counter_ns())

    def start(self):
        try:
            self.client.connect(self.host, self.port, keepalive=30)
            self.client.loop_start()
            if not self.ready.wait(self.timeout):
                raise TimeoutError("MQTT subscription timed out")
            if self.error:
                raise OSError(self.error)
        except BaseException:
            self.close()
            raise
        return self

    def publish(self, topic, payload):
        result = self.client.publish(topic, payload, qos=self.qos, retain=False)
        if result.rc != 0:
            raise OSError(f"MQTT publish failed: {result.rc}")

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()


class MQTTClient:
    def __init__(self, host="127.0.0.1", port=1883, timeout=5.0,
                 topic_prefix="ppe/benchmark", qos=1):
        self.prefix, self.timeout = topic_prefix.rstrip("/"), timeout
        self.pending = None
        self.ack = None
        self.lock = threading.Lock()
        self.arrived = threading.Event()
        self.session = MQTTSession(host, port, self.prefix + "/ack/+", self._receive,
                                   timeout, qos).start()

    def _receive(self, payload, received_ns):
        try:
            with self.lock:
                if self.pending is not None:
                    receipt = read_ack(payload, self.pending)
                    self.ack = receipt
                    self.arrived.set()
        except (ValueError, TypeError, KeyError):
            pass  # Ignore unrelated, duplicate, malformed or late ACKs.

    def exchange(self, event):
        with self.lock:
            if self.pending is not None:
                raise OSError("MQTTClient supports sequential requests only")
            self.pending, self.ack = event.message_id, None
            self.arrived.clear()
        try:
            self.session.publish(self.prefix + "/events", event.to_json().encode("utf-8"))
            if not self.arrived.wait(self.timeout):
                raise TimeoutError("MQTT application ACK timed out")
            return self.ack
        finally:
            with self.lock:
                self.pending = None

    def send(self, event):
        self.exchange(event)

    def close(self):
        self.session.close()


def create_mqtt_receiver(host="127.0.0.1", port=1883, timeout=5.0,
                         topic_prefix="ppe/benchmark", qos=1):
    prefix = topic_prefix.rstrip("/")

    def receive(payload, received_ns):
        try:
            ack = make_ack(payload, received_ns)
            message_id = json.loads(ack)["message_id"]
            session.publish(prefix + "/ack/" + message_id, ack)
        except (ValueError, TypeError, KeyError, OSError):
            logging.getLogger(__name__).warning("Rejected event or failed ACK", exc_info=True)

    session = MQTTSession(host, port, prefix + "/events", receive, timeout, qos)
    return session.start()
