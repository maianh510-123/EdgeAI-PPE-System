from ultralytics import YOLO
from pathlib import Path
import torch
import numpy as np
import psutil
import os
import time
import threading
import csv
import gc

# ============================================================
# Experimental configuration
# ============================================================

MODELS = {
    "YOLO11n": "./code/yolo11n_best.pt",
    "YOLO26n": "./code/yolo26n_best.pt",
}

TEST_DIR = Path(
    "./ppe-research/datasets/construction-ppe/images/test"
)

IMAGE_SIZE = 640
BATCH_SIZE = 1

# Remove initialization effects
WARMUP_RUNS = 20

# Repeat the complete test set three times
REPEATS = 3

# Set to None to use every test image.
# Change to 100 if the dataset is very large.
MAX_IMAGES = None


# ============================================================
# Device selection
# ============================================================

if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"


def synchronize():
    """Synchronize accelerator before recording timestamps."""
    if DEVICE == "mps":
        torch.mps.synchronize()
    elif DEVICE == "cuda":
        torch.cuda.synchronize()


# ============================================================
# Load identical image list for both models
# ============================================================

extensions = {".jpg", ".jpeg", ".png", ".bmp"}

images = sorted(
    p for p in TEST_DIR.iterdir()
    if p.is_file() and p.suffix.lower() in extensions
)

if not images:
    raise RuntimeError(f"No test images found in {TEST_DIR}")

if MAX_IMAGES is not None:
    images = images[:MAX_IMAGES]

print("=" * 70)
print("PYTORCH FP32 SOFTWARE BASELINE")
print("=" * 70)
print("Execution device:", DEVICE)
print("Input resolution:", f"{IMAGE_SIZE} x {IMAGE_SIZE}")
print("Batch size:", BATCH_SIZE)
print("Warm-up runs:", WARMUP_RUNS)
print("Test images:", len(images))
print("Repeats:", REPEATS)
print("Total measured inferences per model:", len(images) * REPEATS)
print()


# ============================================================
# Resource monitoring
# ============================================================

class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid())

        self.running = False
        self.thread = None

        self.process_cpu = []
        self.system_cpu = []
        self.ram = []
        self.mps_memory = []

    def _monitor(self):

        # Initialize CPU measurement
        self.process.cpu_percent(None)
        psutil.cpu_percent(None)

        while self.running:

            self.process_cpu.append(
                self.process.cpu_percent(None)
            )

            self.system_cpu.append(
                psutil.cpu_percent(None)
            )

            self.ram.append(
                self.process.memory_info().rss / (1024 ** 2)
            )

            if DEVICE == "mps":
                try:
                    self.mps_memory.append(
                        torch.mps.current_allocated_memory()
                        / (1024 ** 2)
                    )
                except Exception:
                    pass

            time.sleep(0.05)

    def start(self):
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor,
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def mean(self, data):
        return float(np.mean(data)) if data else float("nan")

    def maximum(self, data):
        return float(np.max(data)) if data else float("nan")


# ============================================================
# Benchmark
# ============================================================

def benchmark(name, checkpoint):

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    file_size_mb = os.path.getsize(checkpoint) / (1024 ** 2)

    print("Checkpoint:", checkpoint)
    print(f"Checkpoint size: {file_size_mb:.2f} MB")

    model = YOLO(checkpoint)

    # Explicitly keep model in FP32
    model.model.float()

    dtype = next(model.model.parameters()).dtype

    print("Model dtype:", dtype)
    print("Device:", DEVICE)

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    print(f"\nRunning {WARMUP_RUNS} warm-up inferences...")

    warmup_image = str(images[0])

    for _ in range(WARMUP_RUNS):
        model.predict(
            source=warmup_image,
            imgsz=IMAGE_SIZE,
            device=DEVICE,
            verbose=False
        )

    synchronize()

    print("Warm-up complete.")

    # --------------------------------------------------------
    # Measured inference
    # --------------------------------------------------------

    inference_ms = []
    preprocess_ms = []
    postprocess_ms = []
    end_to_end_ms = []

    monitor = ResourceMonitor()
    monitor.start()

    total = len(images) * REPEATS
    counter = 0

    for repeat in range(REPEATS):

        print(
            f"Measured pass {repeat + 1}/{REPEATS}..."
        )

        for image_path in images:

            synchronize()

            start = time.perf_counter()

            result = model.predict(
                source=str(image_path),
                imgsz=IMAGE_SIZE,
                device=DEVICE,
                verbose=False
            )[0]

            synchronize()

            end = time.perf_counter()

            wall_time = (end - start) * 1000.0

            preprocess_ms.append(
                result.speed["preprocess"]
            )

            inference_ms.append(
                result.speed["inference"]
            )

            postprocess_ms.append(
                result.speed["postprocess"]
            )

            end_to_end_ms.append(
                wall_time
            )

            counter += 1

            if counter % 50 == 0:
                print(
                    f"  {counter}/{total} completed"
                )

    monitor.stop()

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    inference_ms = np.array(inference_ms)
    preprocess_ms = np.array(preprocess_ms)
    postprocess_ms = np.array(postprocess_ms)
    end_to_end_ms = np.array(end_to_end_ms)

    mean_inf = float(np.mean(inference_ms))
    median_inf = float(np.median(inference_ms))
    p95_inf = float(np.percentile(inference_ms, 95))

    mean_e2e = float(np.mean(end_to_end_ms))
    median_e2e = float(np.median(end_to_end_ms))
    p95_e2e = float(np.percentile(end_to_end_ms, 95))

    model_fps = 1000.0 / mean_inf
    pipeline_fps = 1000.0 / mean_e2e

    summary = {
        "model": name,
        "checkpoint_size_mb": file_size_mb,
        "precision": str(dtype),
        "device": DEVICE,
        "input_size": IMAGE_SIZE,
        "batch_size": BATCH_SIZE,
        "test_images": len(images),
        "repeats": REPEATS,
        "measured_inferences": len(inference_ms),

        "mean_preprocess_ms":
            float(np.mean(preprocess_ms)),

        "mean_inference_ms":
            mean_inf,

        "median_inference_ms":
            median_inf,

        "p95_inference_ms":
            p95_inf,

        "model_fps":
            model_fps,

        "mean_postprocess_ms":
            float(np.mean(postprocess_ms)),

        "mean_end_to_end_ms":
            mean_e2e,

        "median_end_to_end_ms":
            median_e2e,

        "p95_end_to_end_ms":
            p95_e2e,

        "pipeline_fps":
            pipeline_fps,

        "mean_ram_mb":
            monitor.mean(monitor.ram),

        "peak_ram_mb":
            monitor.maximum(monitor.ram),

        "mean_process_cpu_percent":
            monitor.mean(monitor.process_cpu),

        "mean_system_cpu_percent":
            monitor.mean(monitor.system_cpu),

        "mean_mps_memory_mb":
            monitor.mean(monitor.mps_memory),

        "peak_mps_memory_mb":
            monitor.maximum(monitor.mps_memory),
    }

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    print("\nRESULTS")
    print("-" * 50)

    print(f"Model size:             {file_size_mb:.2f} MB")

    print(
        f"Mean inference:         {mean_inf:.2f} ms"
    )
    print(
        f"Median inference:       {median_inf:.2f} ms"
    )
    print(
        f"P95 inference:          {p95_inf:.2f} ms"
    )
    print(
        f"Model FPS:              {model_fps:.2f}"
    )

    print(
        f"Mean preprocessing:     "
        f"{np.mean(preprocess_ms):.2f} ms"
    )

    print(
        f"Mean postprocessing:    "
        f"{np.mean(postprocess_ms):.2f} ms"
    )

    print(
        f"Mean end-to-end:        {mean_e2e:.2f} ms"
    )
    print(
        f"Median end-to-end:      {median_e2e:.2f} ms"
    )
    print(
        f"P95 end-to-end:         {p95_e2e:.2f} ms"
    )
    print(
        f"Pipeline FPS:           {pipeline_fps:.2f}"
    )

    print(
        f"Mean process RAM:       "
        f"{summary['mean_ram_mb']:.2f} MB"
    )

    print(
        f"Peak process RAM:       "
        f"{summary['peak_ram_mb']:.2f} MB"
    )

    print(
        f"Mean process CPU:       "
        f"{summary['mean_process_cpu_percent']:.2f} %"
    )

    print(
        f"Mean system CPU:        "
        f"{summary['mean_system_cpu_percent']:.2f} %"
    )

    if DEVICE == "mps":
        print(
            f"Mean MPS memory:        "
            f"{summary['mean_mps_memory_mb']:.2f} MB"
        )

        print(
            f"Peak MPS memory:        "
            f"{summary['peak_mps_memory_mb']:.2f} MB"
        )

    # --------------------------------------------------------
    # Clean up before next model
    # --------------------------------------------------------

    del model
    gc.collect()

    if DEVICE == "mps":
        torch.mps.empty_cache()

    elif DEVICE == "cuda":
        torch.cuda.empty_cache()

    return summary


# ============================================================
# Execute both models
# ============================================================

summaries = []

for name, checkpoint in MODELS.items():

    summaries.append(
        benchmark(name, checkpoint)
    )


# ============================================================
# Save summary CSV
# ============================================================

output_file = "pytorch_fp32_benchmark.csv"

with open(output_file, "w", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=summaries[0].keys()
    )

    writer.writeheader()
    writer.writerows(summaries)


print("\n" + "=" * 70)
print("BENCHMARK COMPLETE")
print("=" * 70)

print(f"Results saved to: {output_file}")
