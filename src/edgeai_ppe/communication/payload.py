import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4
from edgeai_ppe.compliance.evaluator import evaluate_status
from edgeai_ppe.detection.result import Detection

@dataclass(frozen=True)
class PPEEvent:
    message_id: str
    device_id: str
    camera_id: str
    timestamp: str
    detection_class: str
    status: str
    confidence: float
    is_demo: bool
    schema_version: str = "1.0"

    def __post_init__(self):
        Detection(self.detection_class, self.confidence)
        if self.status != evaluate_status(self.detection_class):
            raise ValueError("Status does not match detection class")
        for name in ("message_id", "device_id", "camera_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if datetime.fromisoformat(self.timestamp).utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        if type(self.is_demo) is not bool:
            raise ValueError("is_demo must be boolean")
        if self.schema_version != "1.0":
            raise ValueError("Unsupported schema version")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False)

def create_event(detection: Detection, device_id: str, camera_id: str, *, is_demo: bool) -> PPEEvent:
    return PPEEvent(
        message_id=str(uuid4()), device_id=device_id, camera_id=camera_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        detection_class=detection.class_name, status=evaluate_status(detection.class_name),
        confidence=detection.confidence, is_demo=is_demo,
    )
