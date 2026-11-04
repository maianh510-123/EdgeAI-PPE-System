from ultralytics import YOLO
import torch
from pathlib import Path

YOLO11 = "./code/yolo11n_best.pt"
YOLO26 = "./code/yolo26n_best.pt"

TEST_DIR = Path(
    "./ppe-research/datasets/construction-ppe/images/test"
)

images = sorted(
    list(TEST_DIR.glob("*.jpg")) +
    list(TEST_DIR.glob("*.jpeg")) +
    list(TEST_DIR.glob("*.png"))
)

if not images:
    raise RuntimeError("No test images found.")

test_image = str(images[0])

device = "mps" if torch.backends.mps.is_available() else "cpu"

print("Device:", device)
print("Test image:", test_image)

models = {
    "YOLO11n": YOLO11,
    "YOLO26n": YOLO26,
}

for name, path in models.items():
    print("\n" + "=" * 60)
    print(name)
    print("Checkpoint:", path)

    model = YOLO(path)

    dtype = next(model.model.parameters()).dtype
    print("Model dtype:", dtype)

    results = model.predict(
        source=test_image,
        imgsz=640,
        device=device,
        half=False,
        verbose=False
    )

    result = results[0]

    print("Inference successful")
    print("Detected boxes:", len(result.boxes))
    print("Timing:", result.speed)

print("\nBoth models executed successfully.")
