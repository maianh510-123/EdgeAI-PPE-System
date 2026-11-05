
import json
import uuid
from pathlib import Path
from datetime import datetime
from collections import Counter

REQUIRED_FIELDS = {
    "message_id", "device_id", "camera_id",
    "timestamp", "detection_class",
    "status", "confidence"
}

STATUS_MAPPING = {
    "person": "detected",
    "helmet": "compliant",
    "safety_vest": "compliant",
    "no_helmet": "violation",
    "no_safety_vest": "violation",
}


def validate_file(path):
    errors = []
    total = 0
    counts = Counter()
    seen_ids = set()

    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"Line {line_number}: invalid JSON")
                continue

            total += 1

            missing = REQUIRED_FIELDS - event.keys()
            if missing:
                errors.append(
                    f"Line {line_number}: missing {missing}"
                )
                continue

            try:
                uuid.UUID(event["message_id"])
            except (ValueError, TypeError, AttributeError):
                errors.append(
                    f"Line {line_number}: invalid message_id"
                )

            if event["message_id"] in seen_ids:
                errors.append(
                    f"Line {line_number}: duplicate message_id"
                )
            seen_ids.add(event["message_id"])

            for field in ("device_id", "camera_id"):
                if (
                    not isinstance(event[field], str)
                    or not event[field].strip()
                ):
                    errors.append(
                        f"Line {line_number}: invalid {field}"
                    )

            try:
                datetime.fromisoformat(event["timestamp"])
            except (ValueError, TypeError):
                errors.append(
                    f"Line {line_number}: invalid timestamp"
                )

            name = event["detection_class"]
            expected = STATUS_MAPPING.get(name)

            if expected is None:
                errors.append(
                    f"Line {line_number}: unknown class {name}"
                )
            elif event["status"] != expected:
                errors.append(
                    f"Line {line_number}: wrong status"
                )

            conf = event["confidence"]
            if (
                type(conf) not in (int, float)
                or not 0 <= conf <= 1
            ):
                errors.append(
                    f"Line {line_number}: invalid confidence"
                )

            bbox = event.get("bbox")
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or not all(
                    type(v) in (int, float) for v in bbox
                )
                or not (
                    bbox[0] < bbox[2]
                    and bbox[1] < bbox[3]
                )
            ):
                errors.append(
                    f"Line {line_number}: invalid bbox"
                )

            counts[event["status"]] += 1

    print(f"\nFILE: {path}")
    print(f"Total events: {total}")
    print(f"Status counts: {dict(counts)}")
    print(f"Errors: {len(errors)}")

    for error in errors[:10]:
        print("ERROR:", error)

    return len(errors) == 0


if __name__ == "__main__":
    base = Path(__file__).resolve().parent

    all_passed = True

    for folder in ("results_yolo11n", "results_yolo26n"):
        path = base / folder / "ppe_events.jsonl"

        if not path.exists():
            print(f"MISSING FILE: {path}")
            all_passed = False
            continue

        if not validate_file(path):
            all_passed = False

    print("\nFINAL RESULT:", "PASS" if all_passed else "FAIL")
