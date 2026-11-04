"""One-to-one greedy IoU-based comparison of same-checkpoint PT vs ONNX outputs."""
import argparse
import json
import sys
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from inference.inference_wrapper import UnifiedInferenceWrapper


def box_iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0., x2-x1)*max(0., y2-y1)
    aa = max(0., a[2]-a[0])*max(0., a[3]-a[1])
    bb = max(0., b[2]-b[0])*max(0., b[3]-b[1])
    return intersection/(aa+bb-intersection) if aa+bb-intersection > 0 else 0.


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pt',required=True)
    p.add_argument('--onnx',required=True)
    p.add_argument('--image',required=True)
    p.add_argument('--save',default='experiments/week6/backend_comparison.json')
    args=p.parse_args()
    image=cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(args.image)
    pt=UnifiedInferenceWrapper(args.pt).predict(image)['detections']
    ox=UnifiedInferenceWrapper(args.onnx).predict(image)['detections']
    available=set(range(len(ox)))
    matches=[]
    for det in pt:
        candidates=[(box_iou(det['bbox'],ox[j]['bbox']),j) for j in available
                    if det['class_id']==ox[j]['class_id']]
        if candidates:
            iou,j=max(candidates)
            if iou>=0.99:
                available.remove(j)
                matches.append({'iou':iou,'confidence_delta':abs(det['confidence']-ox[j]['confidence'])})
    summary={
        'pytorch_count':len(pt), 'onnx_count':len(ox), 'matches_iou_ge_0_99':len(matches),
        'unmatched_pytorch':len(pt)-len(matches),'unmatched_onnx':len(ox)-len(matches),
        'mean_matched_iou': sum(m['iou'] for m in matches)/len(matches) if matches else None,
        'max_confidence_difference':max((m['confidence_delta'] for m in matches),default=None),
        'match_note':'Greedy matching on one image; not full validation or mAP equivalence',
    }
    dest=Path(args.save); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2)); print(f'Saved: {dest}')

if __name__=='__main__':
    main()
