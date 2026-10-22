from typing import Iterable, Protocol
from edgeai_ppe.detection.result import Detection

class Detector(Protocol):
    def detect(self, frame: object) -> Iterable[Detection]:
        """Return normalized detections. Adapter owns model-specific class mapping."""
        ...

class DemoDetector:
    """Synthetic records only. No image analysis or model inference occurs."""
    def detect(self, frame: object) -> Iterable[Detection]:
        return (Detection("person", 0.99), Detection("no_helmet", 0.90))

# TODO: implement a real detector adapter after model/runtime selection.
