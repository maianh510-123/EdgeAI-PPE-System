
# test_integration.py

import json
import csv
from pathlib import Path
from collections import Counter

from event_generator import generate_events
from event_queue import PPEEventQueue


def run_test(input_path, output_dir):

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    event_queue = PPEEventQueue(maxsize=1000)

    frames_processed = 0
    detections_processed = 0
    events_generated = 0
    events_rejected = 0

    status_counts = Counter()

    output_file = output_dir / "ppe_events.jsonl"

    with (
        open(input_path, "r", encoding="utf-8") as source,
        open(output_file, "w", encoding="utf-8") as output
    ):

        for line in source:

            frame = json.loads(line)
            frames_processed += 1

            detections_processed += len(
                frame["detections"]
            )

            events = generate_events(frame)

            for event in events:

                events_generated += 1
                status_counts[event["status"]] += 1

                if not event_queue.enqueue(event):
                    events_rejected += 1

                # Drain the queue to simulate a consumer.
                while not event_queue.is_empty():
                    queued_event = event_queue.dequeue()

                    if queued_event is not None:
                        output.write(
                            json.dumps(queued_event)
                            + "\n"
                        )
                        event_queue.task_done()

    summary = {
        "frames_processed": frames_processed,
        "detections_processed": detections_processed,
        "events_generated": events_generated,
        "events_rejected": events_rejected,
        "status_counts": dict(status_counts)
    }

    with open(
        output_dir / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    integration_dir = Path(__file__).resolve().parent

    print("=== Testing YOLO11n ===")
    run_test(
        base / "yolo11n_compliance_detections.jsonl",
        integration_dir / "results_yolo11n"
    )

    print("\n=== Testing YOLO26n ===")
    run_test(
        base / "yolo26n_compliance_detections.jsonl",
        integration_dir / "results_yolo26n"
    )