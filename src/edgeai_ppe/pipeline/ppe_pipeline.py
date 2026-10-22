import logging
from dataclasses import dataclass
from edgeai_ppe.config import AppConfig
from edgeai_ppe.detection.detector import Detector
from edgeai_ppe.communication.interface import CommunicationClient
from edgeai_ppe.communication.payload import create_event

@dataclass(frozen=True)
class RunSummary:
    accepted: int
    sent: int
    failed: int

class PPEPipeline:
    def __init__(self, config: AppConfig, detector: Detector,
                 client: CommunicationClient, *, is_demo: bool):
        self.config, self.detector, self.client = config, detector, client
        self.is_demo = is_demo

    def run_once(self, frame: object = None) -> RunSummary:
        accepted = sent = failed = 0
        for detection in self.detector.detect(frame):
            if detection.confidence < self.config.confidence_threshold:
                continue
            event = create_event(detection, self.config.device_id,
                                 self.config.camera_id, is_demo=self.is_demo)
            accepted += 1
            try:
                self.client.send(event)
                sent += 1
            except OSError:
                failed += 1
                logging.getLogger(__name__).exception("Event send failed: %s", event.message_id)
        return RunSummary(accepted, sent, failed)

# TODO: frame source, continuous loop, shutdown, nonblocking bounded queue.
# Current sends are synchronous; failed events are counted, not retained/retried.
