
# event_generator.py

from datetime import datetime, timezone
from uuid import uuid4

from ppe_compliance import evaluate_detection


def generate_events(
    frame,
    device_id="edge_01",
    camera_id="cam_01"
):
    events = []

    width = frame["image_width"]
    height = frame["image_height"]

    for detection in frame["detections"]:

        checked = evaluate_detection(
            detection, width, height
        )

        event = {
            "message_id": str(uuid4()),
            "device_id": device_id,
            "camera_id": camera_id,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "detection_class": checked["class_name"],
            "status": checked["status"],
            "confidence": checked["confidence"],

            "bbox": checked["bbox"],
            "video": frame.get("video"),
            "source_frame_index": frame.get(
                "source_frame_index"
            ),
            "timestamp_seconds": frame.get(
                "timestamp_seconds"
            )
        }

        events.append(event)

    return events
