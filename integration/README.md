# Week 6: PPE compliance and event integration

Standalone integration modules contributed by Mai Anh. These consume normalized
five-class detections from the Week 6 handoff. Existing inference, communication,
and teammate modules are unchanged; this is an offline integration experiment.

## Files and requirements

- `ppe_compliance.py`: validates detections and assigns detection-level status.
- `event_generator.py`: creates one UUID event per validated detection, with UTC
  generation time, source video/frame/time metadata, confidence, and bounding box.
- `event_queue.py`: non-blocking FIFO queue with full/empty handling.
- `test_compliance.py`, `test_event_queue.py`: functional checks.
- `test_integration.py`: processes stored detections and saves events and counts.
- `validate_events.py`: checks generated events for required fields, UUIDs,
  duplicate IDs, timestamps, class/status mapping, confidence, and box shape.
- `results_yolo11n/summary.json`, `results_yolo26n/summary.json`: supplied result
  summaries, independently reproduced from the local handoff on 2026-11-06.

Python 3.10+; integration uses only the standard library. Verification used
Python 3.12.10. Model weights, video files, and large JSONL files are excluded.

## Input contract

Each JSONL line is a frame containing `image_width`, `image_height`, and
`detections`; optional metadata includes `video`, `source_frame_index`, and
`timestamp_seconds`. Each detection has `class_id`, `class_name`, `confidence`
in [0, 1], and pixel coordinates `bbox = [x1, y1, x2, y2]` within the image.
Empty detection arrays produce no events. Invalid detections raise `ValueError`
and stop the current run; they are not silently skipped.

| Class ID in this handoff | Normalized class | Status |
|---|---|---|
| 0 | helmet | compliant |
| 1 | no_helmet | violation |
| 2 | person | detected |
| 3 | safety_vest | compliant |
| 4 | no_safety_vest | violation |

The input must already normalize `vest` and `no_vest` to `safety_vest` and
`no_safety_vest`. These IDs belong to the five-class handoff, not older models.

## Run from the repository root

```powershell
python integration/test_compliance.py
python integration/test_event_queue.py
```

For the full offline experiment, obtain these two files from the local handoff
and place them in the repository root (beside `integration/`):

```text
yolo11n_compliance_detections.jsonl
yolo26n_compliance_detections.jsonl
```

These normalized compliance files are required; the existing
`handoff_to_maianh/*_sample_detections.jsonl` files are not interchangeable.

```powershell
python integration/test_integration.py
python integration/validate_events.py
```

The integration runner writes `ppe_events.jsonl` and overwrites `summary.json`
in each `integration/results_<model>/` directory. Generated event files are
ignored by Git. The validator prints `FINAL RESULT: PASS` or `FAIL`; its current
command-line script does not set a failing exit code, so inspect the output.

## Verified results

Both complete input files were rerun in temporary output folders; resulting
summaries matched the supplied summaries exactly. All 10,431 generated events
passed the implemented validator (zero reported errors). Compliance checks
passed for all five classes and unknown-class rejection. Queue checks passed
for FIFO order, full queue, and empty queue.

| Model input | Frames | Detections/events | Queue rejections | Detected | Compliant | Violation |
|---|---:|---:|---:|---:|---:|---:|
| YOLO11n | 600 | 4,926 | 0 | 1,722 | 3,180 | 24 |
| YOLO26n | 600 | 5,505 | 0 | 1,864 | 3,639 | 2 |

`events_rejected` counts failed queue insertions, not invalid detections.
The queue is drained immediately after each insertion in this experiment.

## Discussion and limitations

The experiment verifies conversion of stored normalized detections into events
and basic FIFO behavior. Status is assigned per detection: a compliant PPE item
does not establish full worker compliance. Person-to-PPE association and temporal
deduplication are absent, so consecutive frames may repeat the same situation.
Live camera-to-event latency, sustained asynchronous queue performance, and
network transmission were not measured. Counts are not ground-truth accuracy
measurements and do not establish which model detects violations more accurately.
