# PPE Detection — Integration Handoff

## Contents

- inference_wrapper.py: Unified PyTorch/ONNX inference wrapper
- yolo11n_best.onnx: Trained YOLO11n ONNX model
- yolo11n_sample_detections.jsonl: 150 ONNX frames from workers_walking.mp4
- yolo26n_sample_detections.jsonl: 150 ONNX frames from workers_walking.mp4
- yolo26n_best.onnx: Trained YOLO26n ONNX model
- video_summary.json: Week 6 video performance results

## Detection configuration

- Input size: 640 x 640
- Confidence threshold: 0.25
- NMS IoU threshold: 0.70
- Backend: ONNX Runtime, CPUExecutionProvider

## Class mapping

0: helmet
1: no_helmet
2: person
3: vest
4: no_vest

## Integration notes

The inference wrapper produces object detections.
Person-to-PPE association and compliance event generation
must be handled by the integration module.

Check the sample JSONL structure before implementing
the event-processing interface.

Python dependencies include ultralytics, torch,
onnxruntime, opencv-python, and numpy.

## Available detection models

### YOLO11n
- File: yolo11n_best.onnx
- Sample predictions: yolo11n_sample_detections.jsonl
- Supported backend: ONNX Runtime CPU

### YOLO26n
- File: yolo26n_best.onnx
- Sample predictions: yolo26n_sample_detections.jsonl
- Supported backend: ONNX Runtime CPU

Both models were tested on 141 test images.
All PyTorch detections matched ONNX detections
at IoU >= 0.99 under the tested configuration.

The models use the same five-class PPE mapping.
For the compliance module, map `vest` to `safety_vest` and `no_vest` to
`no_safety_vest`. Keep the checkpoint class IDs separate from older 11-class IDs.

The integration module can switch between the
models without changing the detection schema.

## Result versions

The files at this folder root contain the latest five-class handoff update.
`video_summary.json` records all 16 runs (four videos, two models, two backends),
with 150 sampled frames per run. The root JSONL files are samples from one video.
The dated `week6_5class_full_20261105/` folder retains the earlier
complete five-class package, including the class-name adapter and raw outputs.
These tests check inference and backend agreement; they do not measure labeled mAP.
