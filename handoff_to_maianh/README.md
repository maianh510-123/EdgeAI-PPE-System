# PPE Detection — Integration Handoff

## Contents

- inference_wrapper.py: Unified PyTorch/ONNX inference wrapper
- yolo11n_best.onnx: Trained YOLO11n ONNX model
- sample_detections.jsonl: Frame-by-frame detection samples
- video_summary.json: Week 6 video performance results

## Detection configuration

- Input size: 640 x 640
- Confidence threshold: 0.25
- NMS IoU threshold: 0.70
- Backend: ONNX Runtime, CPUExecutionProvider

## Class mapping

0: helmet
1: gloves
2: vest
3: boots
4: goggles
5: none
6: Person
7: no_helmet
8: no_goggle
9: no_gloves
10: no_boots

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

The models use the same 11-class PPE mapping.

The integration module can switch between the
models without changing the detection schema.
