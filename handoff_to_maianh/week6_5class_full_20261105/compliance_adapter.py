"""Normalize detector class names for the compliance module without adding rules."""
from copy import deepcopy

CLASS_NAMES = {
    "helmet": "helmet", "no_helmet": "no_helmet", "person": "person",
    "vest": "safety_vest", "no_vest": "no_safety_vest",
}


def normalize_prediction(prediction: dict) -> dict:
    """Keep boxes/confidences and raw class metadata; map only class names."""
    output = deepcopy(prediction)
    for detection in output["detections"]:
        raw_name = detection["class_name"]
        detection["class_name"] = CLASS_NAMES[raw_name]
        detection["source_class_name"] = raw_name
    return output
