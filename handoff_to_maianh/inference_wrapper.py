"""Shared Ultralytics-backed PyTorch/ONNX inference interface for PPE detection.

Preprocessing (letterbox, RGB conversion, scaling), model execution and NMS
are handled by Ultralytics. This wrapper validates input and standardizes output.
"""
from pathlib import Path
from typing import Any
import numpy as np
from ultralytics import YOLO

class UnifiedInferenceWrapper:
    def __init__(self, model_path: str | Path, *, imgsz: int = 640,
                 conf: float = 0.25, iou: float = 0.7, device: str = 'cpu'):
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise FileNotFoundError(f'Model not found: {self.model_path}')
        if self.model_path.suffix.lower() not in {'.pt', '.onnx'}:
            raise ValueError('Expected .pt or .onnx checkpoint')
        self.backend = 'pytorch' if self.model_path.suffix.lower() == '.pt' else 'onnx'
        self.imgsz, self.conf, self.iou, self.device = imgsz, conf, iou, device
        self.model = YOLO(str(self.model_path))

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Validate OpenCV BGR uint8 input; Ultralytics handles transformations."""
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError('Input must be HxWx3 NumPy BGR image')
        if frame.dtype != np.uint8 or frame.shape[0] == 0 or frame.shape[1] == 0:
            raise ValueError('Input must be nonempty uint8 image')
        return np.ascontiguousarray(frame)

    def inference(self, frame: np.ndarray) -> Any:
        return self.model.predict(source=frame, imgsz=self.imgsz,
                                  conf=self.conf, iou=self.iou,
                                  device=self.device, rect=False,
                                  verbose=False)[0]

    @staticmethod
    def postprocess(result: Any) -> list[dict]:
        names = result.names
        detections = []
        for box in result.boxes:
            class_id = int(box.cls.item())
            detections.append({
                'class_id': class_id,
                'class_name': str(names[class_id]),
                'confidence': float(box.conf.item()),
                'bbox': [float(v) for v in box.xyxy[0].tolist()],
            })
        return detections

    def predict(self, frame: np.ndarray) -> dict:
        frame = self.preprocess(frame)
        result = self.inference(frame)
        return {
            'backend': self.backend,
            'image_width': int(frame.shape[1]),
            'image_height': int(frame.shape[0]),
            'detections': self.postprocess(result),
        }
