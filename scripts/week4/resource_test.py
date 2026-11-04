from ultralytics import YOLO
from pathlib import Path
import torch
import psutil
import os
import time
import sys
import threading
import numpy as np

MODEL_PATH = sys.argv[1]
MODEL_NAME = sys.argv[2]

TEST_DIR = Path("./ppe-research/datasets/construction-ppe/images/test")
IMAGE_SIZE = 640
WARMUP_RUNS = 20
MAX_IMAGES = 141

if torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

def sync():
    if DEVICE == "mps":
        torch.mps.synchronize()

images = sorted(
    [p for p in TEST_DIR.iterdir()
     if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]
)[:MAX_IMAGES]

process = psutil.Process(os.getpid())

ram_samples = []
cpu_samples = []
mps_samples = []
running = True

def monitor():
    process.cpu_percent(None)

    while running:
        ram_samples.append(
            process.memory_info().rss / (1024 ** 2)
        )
        cpu_samples.append(
            process.cpu_percent(None)
        )

        if DEVICE == "mps":
            try:
                mps_samples.append(
                    torch.mps.current_allocated_memory() / (1024 ** 2)
                )
            except:
                pass

        time.sleep(0.05)

model = YOLO(MODEL_PATH)
model.model.float()

for _ in range(WARMUP_RUNS):
    model.predict(
        source=str(images[0]),
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False
    )

sync()

thread = threading.Thread(target=monitor, daemon=True)
thread.start()

for img in images:
    model.predict(
        source=str(img),
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False
    )

sync()

running = False
thread.join()

print("=" * 50)
print(MODEL_NAME)
print("=" * 50)

print(f"Mean RAM: {np.mean(ram_samples):.2f} MB")
print(f"Peak RAM: {np.max(ram_samples):.2f} MB")
print(f"Mean CPU: {np.mean(cpu_samples):.2f} %")

if mps_samples:
    print(f"Mean MPS memory: {np.mean(mps_samples):.2f} MB")
    print(f"Peak MPS memory: {np.max(mps_samples):.2f} MB")
