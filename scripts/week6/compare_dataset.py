"""Week 6: compare PyTorch and ONNX detections across a directory of images.

Run from the project root:
python scripts/week6/compare_dataset.py

This tests backend agreement at a fixed operating threshold, not mAP vs labels.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from inference.inference_wrapper import UnifiedInferenceWrapper

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
DEFAULT_MODELS = {
    "yolo11n": (
        "models/yolo11n/yolo11n_best.pt",
        "models/yolo11n/yolo11n_best.onnx",
    ),
    "yolo26n": (
        "models/yolo26n/yolo26n_best.pt",
        "models/yolo26n/yolo26n_best.onnx",
    ),
}


def box_iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union > 0.0 else 0.0


def match_detections(pt: list[dict], onnx: list[dict], threshold: float):
    # Highest-IoU-first, one-to-one same-class greedy matching.
    candidates = []
    for i, left in enumerate(pt):
        for j, right in enumerate(onnx):
            if left["class_id"] != right["class_id"]:
                continue
            overlap = box_iou(left["bbox"], right["bbox"])
            if overlap >= threshold:
                candidates.append((overlap, i, j))
    candidates.sort(reverse=True)

    used_pt, used_onnx, matches = set(), set(), []
    for overlap, i, j in candidates:
        if i in used_pt or j in used_onnx:
            continue
        used_pt.add(i)
        used_onnx.add(j)
        matches.append({
            "iou": overlap,
            "confidence_difference": abs(pt[i]["confidence"] - onnx[j]["confidence"]),
        })
    return matches


def run_model(name: str, pt_path: Path, onnx_path: Path, images: list[Path], args, output_dir: Path):
    print(f"\n=== {name}: loading PyTorch and ONNX (CPU) ===", flush=True)
    pt_wrapper = UnifiedInferenceWrapper(
        pt_path, imgsz=args.imgsz, conf=args.conf, iou=args.nms_iou, device="cpu"
    )
    onnx_wrapper = UnifiedInferenceWrapper(
        onnx_path, imgsz=args.imgsz, conf=args.conf, iou=args.nms_iou, device="cpu"
    )

    rows = []
    all_iou, all_conf_delta = [], []
    for k, image_path in enumerate(images, start=1):
        image = cv2.imread(str(image_path))
        if image is None:
            raise RuntimeError(f"Cannot read image: {image_path}")

        pt = pt_wrapper.predict(image)["detections"]
        onnx = onnx_wrapper.predict(image)["detections"]
        matches = match_detections(pt, onnx, args.match_iou)
        ious = [m["iou"] for m in matches]
        conf_deltas = [m["confidence_difference"] for m in matches]
        all_iou.extend(ious)
        all_conf_delta.extend(conf_deltas)

        rows.append({
            "image": image_path.name,
            "pt_detections": len(pt),
            "onnx_detections": len(onnx),
            "matched": len(matches),
            "unmatched_pt": len(pt) - len(matches),
            "unmatched_onnx": len(onnx) - len(matches),
            "mean_matched_iou": sum(ious) / len(ious) if ious else "",
            "max_confidence_difference": max(conf_deltas) if conf_deltas else "",
        })
        if k % 20 == 0 or k == len(images):
            print(f"{name}: {k}/{len(images)} images processed", flush=True)

    pt_count = sum(r["pt_detections"] for r in rows)
    onnx_count = sum(r["onnx_detections"] for r in rows)
    matched = sum(r["matched"] for r in rows)
    summary = {
        "model": name,
        "images_processed": len(rows),
        "pytorch_detections": pt_count,
        "onnx_detections": onnx_count,
        "matched_detections": matched,
        "unmatched_pytorch": pt_count - matched,
        "unmatched_onnx": onnx_count - matched,
        "images_with_unmatched_detections": sum(
            r["unmatched_pt"] > 0 or r["unmatched_onnx"] > 0 for r in rows
        ),
        "mean_matched_iou": sum(all_iou) / len(all_iou) if all_iou else None,
        "min_matched_iou": min(all_iou) if all_iou else None,
        "max_confidence_difference": max(all_conf_delta) if all_conf_delta else None,
        "config": {
            "image_size": args.imgsz,
            "confidence_threshold": args.conf,
            "nms_iou_threshold": args.nms_iou,
            "matching_iou_threshold": args.match_iou,
            "device": "cpu",
        },
        "pt_checkpoint": str(pt_path),
        "onnx_checkpoint": str(onnx_path),
        "note": (
            "Same-class, one-to-one greedy box matching on test images. "
            "Evaluates output consistency only; not ground-truth accuracy, "
            "mAP equivalence, or runtime speed."
        ),
    }
    csv_path = output_dir / f"{name}_per_image.csv"
    json_path = output_dir / f"{name}_summary.json"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved: {csv_path}\nSaved: {json_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images", type=Path,
        default=Path("datasets/construction-ppe/images/test"),
        help="Test-image directory, relative to project root",
    )
    parser.add_argument("--models", nargs="+", choices=list(DEFAULT_MODELS), default=list(DEFAULT_MODELS))
    parser.add_argument("--out", type=Path, default=Path("experiments/week6/dataset_comparison"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--nms-iou", type=float, default=0.7)
    parser.add_argument("--match-iou", type=float, default=0.99)
    parser.add_argument("--expected-images", type=int, default=141)
    args = parser.parse_args()

    images_dir = (ROOT / args.images).resolve() if not args.images.is_absolute() else args.images
    if not images_dir.is_dir():
        parser.error(f"Missing image folder: {images_dir}")
    images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file())
    if len(images) != args.expected_images:
        parser.error(f"Expected {args.expected_images} images, found {len(images)} in {images_dir}. "
                     "Use --expected-images N if you intentionally test a different set.")

    output_dir = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for name in args.models:
        relative_pt, relative_onnx = DEFAULT_MODELS[name]
        pt, onnx = ROOT / relative_pt, ROOT / relative_onnx
        for model_path in (pt, onnx):
            if not model_path.is_file():
                parser.error(f"Missing model: {model_path}")
        summaries.append(run_model(name, pt, onnx, images, args, output_dir))

    combined = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "image_directory": str(images_dir),
        "model_summaries": summaries,
    }
    combined_path = output_dir / "combined_summary.json"
    combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"\nSaved combined report: {combined_path}")


if __name__ == "__main__":
    main()
