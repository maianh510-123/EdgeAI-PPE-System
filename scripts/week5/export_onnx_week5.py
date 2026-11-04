"""Week 5: export the EXACT Week 4 .pt checkpoints to ONNX FP32.
Run from the SAME project root used for Week 4: python export_onnx_week5.py
"""
from pathlib import Path
import hashlib
import json

import onnx
import onnxruntime as ort
from ultralytics import YOLO

MODELS = {
    "YOLO11n": Path("./code/yolo11n_best.pt"),
    "YOLO26n": Path("./code/yolo26n_best.pt"),
}
IMAGE_SIZE = 640
BATCH_SIZE = 1


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


for name, pt_path in MODELS.items():
    if not pt_path.is_file():
        raise FileNotFoundError(f"Missing original checkpoint: {pt_path}")

    print(f"\n=== Exporting {name}: {pt_path} ===", flush=True)
    # nms=None preserves default one-to-many predictions (external NMS), matching
    # the original Week 4 model.predict() behavior for YOLO26n.
    onnx_path = Path(YOLO(str(pt_path)).export(
        format="onnx", imgsz=IMAGE_SIZE, batch=BATCH_SIZE,
        dynamic=False, simplify=False,
        device="cpu", nms=None,
    ))

    graph = onnx.load(str(onnx_path))
    onnx.checker.check_model(graph)
    if not graph.graph.input:
        raise RuntimeError("ONNX graph has no input")
    tensor_dtype = graph.graph.input[0].type.tensor_type.elem_type
    if tensor_dtype != onnx.TensorProto.FLOAT:
        raise RuntimeError(f"Expected FP32 input, got ONNX tensor type {tensor_dtype}")
    half_weights = [
        w.name for w in graph.graph.initializer
        if w.data_type in (onnx.TensorProto.FLOAT16, onnx.TensorProto.BFLOAT16)
    ]
    if half_weights:
        raise RuntimeError(f"Found {len(half_weights)} FP16/BF16 weights")

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    if session.get_providers() != ["CPUExecutionProvider"]:
        raise RuntimeError(f"Unexpected ONNX provider: {session.get_providers()}")

    summary = {
        "model": name,
        "source_pt": str(pt_path),
        "onnx_file": str(onnx_path),
        "input_shape": session.get_inputs()[0].shape,
        "input_type": session.get_inputs()[0].type,
        "output_shapes": [o.shape for o in session.get_outputs()],
        "provider": session.get_providers(),
        "onnx_size_mib": onnx_path.stat().st_size / (1024 ** 2),
        "pt_size_mib": pt_path.stat().st_size / (1024 ** 2),
        "pt_sha256": sha256(pt_path),
        "onnx_sha256": sha256(onnx_path),
        "precision": "FP32",
        "nms_export_setting": None,
        "input_size": IMAGE_SIZE,
        "batch": BATCH_SIZE,
    }
    metadata_path = onnx_path.with_suffix(".export_info.json")
    metadata_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("ONNX validated:", onnx_path)
    print("Input:", summary["input_shape"], summary["input_type"])
    print("Output shapes:", summary["output_shapes"])
    print("Execution provider:", summary["provider"])
    print(f"Model size: {summary['onnx_size_mib']:.2f} MiB")
    print("Export metadata:", metadata_path)

print("\nBoth FP32 ONNX exports were verified successfully.")
