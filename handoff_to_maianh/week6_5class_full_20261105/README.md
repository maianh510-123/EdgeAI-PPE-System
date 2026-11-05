# Five-class PPE integration handoff

These are the uploaded trained checkpoints, exported and tested locally.
Training was not repeated: the original curated five-class dataset is missing.
The imported accuracy reports are separate from these local rerun results.

## Use

```python
from inference_wrapper import UnifiedInferenceWrapper
from compliance_adapter import normalize_prediction

detector = UnifiedInferenceWrapper("yolo11n_best.onnx", conf=0.25, device="cpu")
# frame: OpenCV BGR uint8 image
prediction = normalize_prediction(detector.predict(frame))
```

`yolo11n_compliance_detections.jsonl` and
`yolo26n_compliance_detections.jsonl` contain all sampled frames from the four
videos, using ONNX CPU inference. Each line includes video, frame index,
video-relative timestamp, image dimensions and detections. Empty detection
arrays are retained. Boxes are `[x1, y1, x2, y2]` in original-image pixels.
Confidence and boxes are unchanged by the adapter.

## Class mapping

| Checkpoint class_id | Raw name | Compliance name |
|---|---|---|
| 0 | helmet | helmet |
| 1 | no_helmet | no_helmet |
| 2 | person | person |
| 3 | vest | safety_vest |
| 4 | no_vest | no_safety_vest |

`source_class_name` retains the detector name. Class IDs belong to this
checkpoint and differ from the old 11-class models. Integrate using class names.
The adapter does not associate objects with people, infer violations from
missing detections, or generate compliance events.

## Validation and configuration

- Input: 640, confidence: 0.25, NMS IoU: 0.7, CPU.
- Both models tested against their own ONNX exports on 141 local images.
- One-to-one same-class matching at IoU >= 0.99; see dataset_comparison/.
- Four videos x two models x two backends: 16 runs, up to 150 frames each.
- All raw PT/ONNX frame outputs are in raw_video_results/.
- Video timings include the first prediction and are not warmed-up benchmarks.
- selection.json records the friend's selected YOLO11n threshold; this local
  rerun uses 0.25 for both models to match the existing comparison setup.
- Local dependency versions are recorded in requirements.txt.

The existing 11-class test labels cannot measure these five-class models'
accuracy directly. Backend agreement does not establish detection accuracy.
