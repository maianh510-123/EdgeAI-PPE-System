"""Week 6: run unified PPE inference on MP4 videos and save JSONL/summary.

Run from ce_project root, e.g.:
  python scripts/week6/test_videos.py --video-dir datasets/test_videos --max-frames 150

Reports end-to-end predict() time per sampled frame (including Ultralytics
pre/postprocessing), excluding video decode, model loading and disk writes.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from inference.inference_wrapper import UnifiedInferenceWrapper

MODEL_PATHS = {
    "yolo11n_pt": ROOT / "models/yolo11n/yolo11n_best.pt",
    "yolo11n_onnx": ROOT / "models/yolo11n/yolo11n_best.onnx",
    "yolo26n_pt": ROOT / "models/yolo26n/yolo26n_best.pt",
    "yolo26n_onnx": ROOT / "models/yolo26n/yolo26n_best.onnx",
}
EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def process_video(wrapper, path, output_dir, max_frames, stride):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    source_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    out_path = output_dir / f"{path.stem}_frames.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    count, examined, detections, durations_ms = 0, 0, 0, []
    try:
        with out_path.open("w", encoding="utf-8") as out:
            while count < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_index = examined
                examined += 1
                if frame_index % stride:
                    continue
                start = time.perf_counter()
                prediction = wrapper.predict(frame)
                elapsed_ms = (time.perf_counter() - start) * 1000
                durations_ms.append(elapsed_ms)
                count += 1
                detections += len(prediction["detections"])
                entry = {
                    "video": path.name,
                    "source_frame_index": frame_index,
                    "timestamp_seconds": frame_index / fps if fps > 0 else None,
                    "latency_ms": elapsed_ms,
                    **prediction,
                }
                out.write(json.dumps(entry) + "\n")
    finally:
        cap.release()
    if not count:
        raise RuntimeError(f"No sampled frames decoded from {path}")
    total_s = sum(durations_ms) / 1000
    sorted_times = sorted(durations_ms)
    p95 = sorted_times[min(len(sorted_times) - 1, int(0.95 * (len(sorted_times) - 1)))]
    return {
        "video": path.name,
        "source_fps": fps if fps > 0 else None,
        "source_frame_count_reported": source_frames,
        "sampled_frames": count,
        "sample_stride": stride,
        "detections_total": detections,
        "mean_predict_latency_ms": sum(durations_ms) / count,
        "p95_predict_latency_ms": p95,
        "predict_only_fps": count / total_s,
        "per_frame_output": str(out_path.relative_to(ROOT)) if out_path.is_relative_to(ROOT) else str(out_path),
        "timing_note": "predict() only: includes preprocessing, model execution and postprocessing; excludes video decode, model load and output file writing",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", default="datasets/test_videos")
    parser.add_argument("--out", default="experiments/week6/video_results")
    parser.add_argument("--max-frames", type=int, default=150, help="Maximum sampled frames per video")
    parser.add_argument("--stride", type=int, default=1, help="Sample every Nth source frame")
    parser.add_argument("--models", nargs="+", choices=list(MODEL_PATHS), default=list(MODEL_PATHS))
    args = parser.parse_args()
    if args.max_frames < 1 or args.stride < 1:
        parser.error("--max-frames and --stride must be >= 1")
    video_dir = Path(args.video_dir).resolve()
    if not video_dir.is_dir():
        parser.error(f"Video directory not found: {video_dir}")
    videos = sorted(p for p in video_dir.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not videos:
        parser.error(f"No supported video files in {video_dir}")
    missing = [str(MODEL_PATHS[key]) for key in args.models if not MODEL_PATHS[key].is_file()]
    if missing:
        parser.error("Missing model files: " + ", ".join(missing))
    out_dir = Path(args.out).resolve()
    results = []
    for model_key in args.models:
        print(f"\nLoading {model_key}...", flush=True)
        wrapper = UnifiedInferenceWrapper(MODEL_PATHS[model_key], device="cpu", imgsz=640, conf=0.25, iou=0.7)
        for video in videos:
            print(f"  Processing {video.name}...", flush=True)
            try:
                item = process_video(wrapper, video, out_dir / model_key, args.max_frames, args.stride)
                item["model"] = model_key
                item["status"] = "ok"
                print(f"    {item['sampled_frames']} frames; {item['mean_predict_latency_ms']:.1f} ms/frame", flush=True)
            except Exception as error:
                item = {"model": model_key, "video": video.name, "status": "error", "error": str(error)}
                print(f"    ERROR: {error}", flush=True)
            results.append(item)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "results": results}
    destination = out_dir / "video_summary.json"
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved summary: {destination}")
    if any(item["status"] == "error" for item in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
