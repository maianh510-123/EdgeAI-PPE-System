"""Compare sample detections from Week 4 .pt (MPS) and Week 5 .onnx (CPU).
Only a sanity check: visually inspect saved images; this does NOT establish mAP parity.
"""
from pathlib import Path
import json
import cv2
import torch
from ultralytics import YOLO

MODELS = {
    "YOLO11n": ("./code/yolo11n_best.pt", "./code/yolo11n_best.onnx"),
    "YOLO26n": ("./code/yolo26n_best.pt", "./code/yolo26n_best.onnx"),
}
TEST_DIR = Path("./ppe-research/datasets/construction-ppe/images/test")
OUT = Path("week5_results/detection_samples")
OUT.mkdir(parents=True, exist_ok=True)
images = sorted(p for p in TEST_DIR.iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})
if len(images) != 141:
    raise RuntimeError(f"Expected 141 images, got {len(images)}")
selected = [images[0], images[len(images) // 2], images[-1]]
pt_device = "mps" if torch.backends.mps.is_available() else "cpu"
records = []
for name, (pt, onnx) in MODELS.items():
    pytorch = YOLO(pt)
    onnx_model = YOLO(onnx)
    for k, path in enumerate(selected, 1):
        opts = dict(source=str(path), imgsz=640, verbose=False)
        original = pytorch.predict(device=pt_device, **opts)[0]
        exported = onnx_model.predict(device="cpu", **opts)[0]
        pt_img = original.plot()
        onnx_img = exported.plot()
        cv2.imwrite(str(OUT / f"{name}_sample{k}_pytorch.jpg"), pt_img)
        cv2.imwrite(str(OUT / f"{name}_sample{k}_onnx.jpg"), onnx_img)
        info = {
            "model": name, "file": path.name,
            "pt_box_count": len(original.boxes),
            "onnx_box_count": len(exported.boxes),
            "pt_classes": original.boxes.cls.int().tolist(),
            "onnx_classes": exported.boxes.cls.int().tolist(),
        }
        records.append(info)
        print(info)
(OUT / "comparison.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print("Visual samples saved to:", OUT)
print("NOTE: Minor FP32 numerical differences can exist. Check boxes/classes visually.")
