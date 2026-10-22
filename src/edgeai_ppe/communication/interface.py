from typing import Protocol
from edgeai_ppe.communication.payload import PPEEvent

class CommunicationClient(Protocol):
    def send(self, event: PPEEvent) -> None:
        """Send once; raise OSError on transport failure. No delivery guarantee."""
        ...

class ConsoleClient:
    """Local JSON output only; no network calls."""
    def send(self, event: PPEEvent) -> None:
        print(event.to_json())

# Experiment adapters live in http.py, mqtt.py and coap.py; not selected by core CLI.
# TODO: production lifecycle, authentication and bounded retry queue.
