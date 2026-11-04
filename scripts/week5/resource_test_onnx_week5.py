"""Week 5 isolated resource test mirroring Week 4 resource_test.py.
Usage (run EACH command in a fresh process):
    python resource_test_onnx_week5.py YOLO11n
    python resource_test_onnx_week5.py YOLO26n
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import psutil
from ultralytics import YOLO

MODELS = {
    "YOLO11n": Path("./code/yolo11n_best.onnx"),
    "YOLO26n": Path("./code/yolo26n_best.onnx"),
}
TEST_DIR = Path("./ppe-research/datasets/construction-ppe/images/test")
IMAGE_SIZE = 640
WARMUP_RUNS = 20
EXPECTED_IMAGES = 141


def main(name):
    if name not in MODELS:
        raise SystemExit("Usage: python resource_test_onnx_week5.py YOLO11n|YOLO26n")
    path = MODELS[name]
    if not path.is_file():
        raise FileNotFoundError(path)
    if not TEST_DIR.is_dir():
        raise FileNotFoundError(TEST_DIR)
    images = sorted(p for p in TEST_DIR.iterdir()
                    if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})
    if len(images) != EXPECTED_IMAGES:
        raise RuntimeError(f"Expected {EXPECTED_IMAGES} images, found {len(images)}")
    if "CPUExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("ONNX Runtime CPU provider unavailable")

    model = YOLO(str(path))
    opts = dict(imgsz=IMAGE_SIZE, device="cpu", verbose=False)
    for _ in range(WARMUP_RUNS):
        model.predict(source=str(images[0]), **opts)
    backend = model.predictor.model
    session = getattr(backend, "session", None)
    if session is None:
        session = getattr(getattr(backend, "backend", None), "session", None)
    if session is None or session.get_providers() != ["CPUExecutionProvider"]:
        raise RuntimeError("Could not verify ONNX Runtime CPUExecutionProvider")

    process = psutil.Process(os.getpid())
    ram_samples, cpu_samples = [], []
    running = threading.Event()
    running.set()

    def monitor():
        process.cpu_percent(None)
        while running.is_set():
            ram_samples.append(process.memory_info().rss / (1024 ** 2))
            cpu_samples.append(process.cpu_percent(None))
            time.sleep(0.05)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        # Exactly ONE traversal of 141 images, as in your Week 4 resource_test.py
        for img in images:
            model.predict(source=str(img), **opts)
    finally:
        running.clear()
        thread.join()

    if not ram_samples or not cpu_samples:
        raise RuntimeError("No resource-monitoring samples collected")
    summary = {
        "model": name,
        "runtime": "ONNX Runtime FP32 CPU",
        "provider": session.get_providers(),
        "warmup_runs": WARMUP_RUNS,
        "measured_images": len(images),
        "mean_ram_mb": float(np.mean(ram_samples)),
        "peak_ram_mb": float(np.max(ram_samples)),
        "mean_cpu_percent": float(np.mean(cpu_samples)),
        "ram_unit": "MiB (2^20 bytes); same calculation as Week 4 script",
    }
    out = Path("week5_results")
    out.mkdir(exist_ok=True)
    output = out / f"{name.lower()}_onnx_isolated_resources.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("=" * 55)
    print(name, "— isolated ONNX CPU resource test")
    print("Mean RAM: %.2f MiB" % summary["mean_ram_mb"])
    print("Peak RAM: %.2f MiB" % summary["peak_ram_mb"])
    print("Mean process CPU: %.2f %%" % summary["mean_cpu_percent"])
    print("Saved:", output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python resource_test_onnx_week5.py YOLO11n|YOLO26n")
    main(sys.argv[1])
