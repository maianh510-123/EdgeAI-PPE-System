from ultralytics import YOLO
import torch

models = {
    "YOLO11n": "yolo11n_best.pt",
    "YOLO26n": "yolo26n_best.pt"
}

IMAGE_PATH = "test.jpg"

if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print("Using device:", device)

for model_name, model_path in models.items():
    print(f"\n===== {model_name} =====")

    model = YOLO(model_path)

    results = model.predict(
        source=IMAGE_PATH,
        imgsz=640,
        device=device,
        half=False,
        verbose=False
    )

    result = results[0]

    print("Inference successful")
    print("Detected boxes:", len(result.boxes))
    print("Speed:", result.speed)
