from dataclasses import dataclass
from edgeai_ppe.constants import PPE_CLASSES

@dataclass(frozen=True)
class Detection:
    class_name: str
    confidence: float

    def __post_init__(self):
        if self.class_name not in PPE_CLASSES:
            raise ValueError(f"Unknown PPE class: {self.class_name}")
        if type(self.confidence) not in (int, float) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

# TODO: agree on bounding box coordinates and person association before adding them.
