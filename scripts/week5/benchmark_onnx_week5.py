"""Week 5: mirror last week's benchmark_pytorch.py using ONNX Runtime CPU.
Run separately for fresh-process measurements:
    python benchmark_onnx_week5.py YOLO11n
    python benchmark_onnx_week5.py YOLO26n
"""
from pathlib import Path
import csv
import json
import os
import platform
import sys
import threading
import time
import hashlib

import numpy as np
import onnxruntime as ort
import psutil
from ultralytics import YOLO
import ultralytics

MODELS = {
    "YOLO11n": Path("./code/yolo11n_best.onnx"),
    "YOLO26n": Path("./code/yolo26n_best.onnx"),
}
TEST_DIR = Path("./ppe-research/datasets/construction-ppe/images/test")
IMAGE_SIZE = 640
BATCH_SIZE = 1
WARMUP_RUNS = 20
REPEATS = 3
EXPECTED_IMAGES = 141
DEVICE = "cpu"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}  # matches Week 4
RESULT_DIR = Path("week5_results")


def image_manifest_hash(files):
    """Fingerprint exact image names AND bytes, for experimental reproducibility."""
    h = hashlib.sha256()
    for path in files:
        h.update(path.name.encode("utf-8"))
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


class ResourceMonitor:
    """Matching Week 4's 0.05s psutil background sampling."""
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.cpu = []
        self.system_cpu = []
        self.ram = []
        self.running = False
        self.thread = None

    def _run(self):
        self.process.cpu_percent(None)
        psutil.cpu_percent(None)
        while self.running:
            self.cpu.append(self.process.cpu_percent(None))
            self.system_cpu.append(psutil.cpu_percent(None))
            self.ram.append(self.process.memory_info().rss / (1024 ** 2))
            time.sleep(0.05)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    @staticmethod
    def mean(values):
        return float(np.mean(values)) if values else float("nan")

    @staticmethod
    def max(values):
        return float(np.max(values)) if values else float("nan")


def check_actual_provider(model):
    """Make sure Ultralytics used ONNX Runtime and NOT OpenCV or CoreML."""
    backend = model.predictor.model
    session = getattr(backend, "session", None)
    if session is None:
        session = getattr(getattr(backend, "backend", None), "session", None)
    if session is None or not hasattr(session, "get_providers"):
        raise RuntimeError("Unable to verify underlying ONNX Runtime session; do not label results as ORT.")
    providers = session.get_providers()
    if providers != ["CPUExecutionProvider"]:
        raise RuntimeError(f"Unexpected execution provider(s): {providers}")
    return providers


def main(name):
    if name not in MODELS:
        raise SystemExit("Usage: python benchmark_onnx_week5.py YOLO11n|YOLO26n")
    checkpoint = MODELS[name]
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Missing {checkpoint}. Run export_onnx_week5.py first.")
    if not TEST_DIR.is_dir():
        raise FileNotFoundError(f"Missing test images: {TEST_DIR}")
    images = sorted(p for p in TEST_DIR.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if len(images) != EXPECTED_IMAGES:
        raise RuntimeError(f"Expected {EXPECTED_IMAGES} images, found {len(images)} in {TEST_DIR}")
    if "CPUExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("ONNX Runtime CPUExecutionProvider is unavailable")

    print("=" * 65)
    print("WEEK 5 — ONNX RUNTIME FP32")
    print("Model:", name)
    print("ONNX:", checkpoint)
    print("Input resolution:", IMAGE_SIZE, "x", IMAGE_SIZE)
    print("Batch size:", BATCH_SIZE)
    print("Warm-up runs:", WARMUP_RUNS)
    print("Test images:", len(images))
    print("Repeats:", REPEATS)
    print("Total measured inferences:", len(images) * REPEATS)

    model = YOLO(str(checkpoint))
    settings = dict(imgsz=IMAGE_SIZE, batch=BATCH_SIZE, device=DEVICE,
                    verbose=False)  # same Week 4 default detection settings

    print("Warming up...")
    for _ in range(WARMUP_RUNS):
        model.predict(source=str(images[0]), **settings)
    providers = check_actual_provider(model)
    print("Actual ONNX Runtime provider:", providers)

    model_latencies = []
    preprocess_latencies = []
    postprocess_latencies = []
    e2e_latencies = []
    per_image = []
    monitor = ResourceMonitor()
    monitor.start()
    try:
        for repeat in range(REPEATS):
            print(f"Measured pass {repeat + 1}/{REPEATS}...")
            for index, image_path in enumerate(images):
                # Use a FILE PATH like the original Week 4 script, so the end-to-end
                # timer includes the same type of image reading as Week 4.
                start = time.perf_counter()
                result = model.predict(source=str(image_path), **settings)[0]
                end = time.perf_counter()
                inf = float(result.speed["inference"])
                prep = float(result.speed["preprocess"])
                post = float(result.speed["postprocess"])
                e2e = (end - start) * 1000.0
                model_latencies.append(inf)
                preprocess_latencies.append(prep)
                postprocess_latencies.append(post)
                e2e_latencies.append(e2e)
                per_image.append({
                    "model": name, "repeat": repeat + 1,
                    "image": image_path.name, "inference_ms": inf,
                    "preprocess_ms": prep, "postprocess_ms": post,
                    "end_to_end_ms": e2e,
                    "detections": len(result.boxes) if result.boxes is not None else 0,
                })
    finally:
        monitor.stop()

    mean_inference = float(np.mean(model_latencies))
    mean_e2e = float(np.mean(e2e_latencies))
    summary = {
        "model": name,
        "runtime": "ONNX Runtime FP32",
        "device": DEVICE,
        "provider": providers[0],
        "model_size_mib": checkpoint.stat().st_size / (1024 ** 2),
        "mean_inference_ms": mean_inference,
        "median_inference_ms": float(np.median(model_latencies)),
        "p95_inference_ms": float(np.percentile(model_latencies, 95)),
        "model_fps": 1000.0 / mean_inference,
        "mean_preprocess_ms": float(np.mean(preprocess_latencies)),
        "mean_postprocess_ms": float(np.mean(postprocess_latencies)),
        "mean_end_to_end_ms": mean_e2e,
        "median_end_to_end_ms": float(np.median(e2e_latencies)),
        "p95_end_to_end_ms": float(np.percentile(e2e_latencies, 95)),
        "pipeline_fps": 1000.0 / mean_e2e,
        "mean_ram_mb": monitor.mean(monitor.ram),
        "peak_ram_mb": monitor.max(monitor.ram),
        "mean_process_cpu_percent": monitor.mean(monitor.cpu),
        "mean_system_cpu_percent": monitor.mean(monitor.system_cpu),
        "input_size": IMAGE_SIZE,
        "batch_size": BATCH_SIZE,
        "test_images": len(images),
        "repeats": REPEATS,
        "warmup_runs": WARMUP_RUNS,
        "measured_inferences": len(model_latencies),
        "test_image_sha256": image_manifest_hash(images),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ultralytics": ultralytics.__version__,
        "onnxruntime": ort.__version__,
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = RESULT_DIR / f"{name.lower()}_onnx_per_image.csv"
    summary_path = RESULT_DIR / f"{name.lower()}_onnx_summary.json"
    with detail_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=per_image[0].keys())
        writer.writeheader()
        writer.writerows(per_image)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nRESULTS (no fabricated values):")
    for key, value in summary.items():
        if key in {"mean_inference_ms", "median_inference_ms", "p95_inference_ms",
                   "model_fps", "mean_end_to_end_ms", "pipeline_fps",
                   "mean_ram_mb", "peak_ram_mb", "mean_process_cpu_percent", "model_size_mib"}:
            print(f"  {key:28s} {value:.2f}")
    print("Saved:", detail_path, summary_path, sep="\n  ")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python benchmark_onnx_week5.py YOLO11n|YOLO26n")
    main(sys.argv[1])
