"""Small application ACK shared by the standalone communication experiments."""
import json
import time
from dataclasses import dataclass
from uuid import UUID

from edgeai_ppe.communication.payload import PPEEvent

MAX_PAYLOAD_BYTES = 16384


@dataclass(frozen=True)
class Receipt:
    message_id: str
    receiver_perf_ns: int


def make_ack(payload: bytes, received_ns: int) -> bytes:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("Payload is too large")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Expected a PPE event object")
    event = PPEEvent(**value)
    UUID(event.message_id)
    return json.dumps({"message_id": event.message_id, "accepted": True,
                       "receiver_perf_ns": received_ns}).encode("utf-8")


def read_ack(payload: bytes, expected_id: str) -> Receipt:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("ACK is too large")
    value = json.loads(payload)
    if not isinstance(value, dict) or value.get("message_id") != expected_id:
        raise ValueError("ACK message_id mismatch")
    if value.get("accepted") is not True:
        raise ValueError("Receiver did not accept the event")
    received = value.get("receiver_perf_ns")
    if type(received) is not int or received < 0:
        raise ValueError("Invalid receiver clock value")
    return Receipt(expected_id, received)


def receive_now(payload: bytes) -> bytes:
    return make_ack(payload, time.perf_counter_ns())
