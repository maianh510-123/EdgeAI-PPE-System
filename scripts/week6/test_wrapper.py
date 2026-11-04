"""Run from project root: python scripts/week6/test_wrapper.py --model ... --image ..."""
import argparse
import json
import sys
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from inference.inference_wrapper import UnifiedInferenceWrapper


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--image', required=True)
    p.add_argument('--save', default='experiments/week6/detection_output.json')
    args = p.parse_args()
    image = cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(f'Unable to open image: {args.image}')
    output = UnifiedInferenceWrapper(args.model).predict(image)
    dest = Path(args.save)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))
    print(f'Saved: {dest}')

if __name__ == '__main__':
    main()
