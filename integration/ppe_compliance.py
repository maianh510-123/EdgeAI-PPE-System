
# ppe_compliance.py

CLASS_STATUS = {
    "person": "detected",
    "helmet": "compliant",
    "safety_vest": "compliant",
    "no_helmet": "violation",
    "no_safety_vest": "violation",
}

CLASS_IDS = {
    "helmet": 0,
    "no_helmet": 1,
    "person": 2,
    "safety_vest": 3,
    "no_safety_vest": 4,
}


def validate_detection(detection, width, height):
    """Validate a five-class detection."""

    if not isinstance(detection, dict):
        raise ValueError("Detection must be a dictionary")

    name = detection.get("class_name")
    class_id = detection.get("class_id")
    confidence = detection.get("confidence")
    bbox = detection.get("bbox")

    if name not in CLASS_STATUS:
        raise ValueError(f"Unknown class: {name}")

    if type(class_id) is not int:
        raise ValueError("class_id must be an integer")

    if class_id != CLASS_IDS[name]:
        raise ValueError("Class ID/name mismatch")

    if (
        type(confidence) not in (int, float)
        or not 0 <= confidence <= 1
    ):
        raise ValueError("Invalid confidence")

    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("Invalid bounding box")

    if not all(
        type(v) in (int, float) for v in bbox
    ):
        raise ValueError("BBox coordinates must be numeric")

    x1, y1, x2, y2 = bbox

    if not (0 <= x1 < x2 <= width):
        raise ValueError("Invalid bbox x coordinates")

    if not (0 <= y1 < y2 <= height):
        raise ValueError("Invalid bbox y coordinates")

    return True


def evaluate_detection(detection, width, height):
    validate_detection(detection, width, height)

    result = detection.copy()
    result["status"] = CLASS_STATUS[
        detection["class_name"]
    ]

    return result
