"""
prelabel.py
- Input: folder frames (default: ./frames)
- Output:
  - ./prelabels/labels  (YOLO .txt per image, class 0 = bib)
  - ./prelabels/crops   (cropped images of estimated bib region)
Usage:
  python prelabel.py --frames ./frames --model /path/to/bib_model.pt
If --model not provided, fallback to HOG-person -> chest-crop heuristic.
"""
import os
import argparse
from glob import glob
import cv2
import numpy as np

def ensure(d): 
    os.makedirs(d, exist_ok=True)

def yolo_prelabel(frames_dir, labels_out, crops_out, model_path, imgsz=640, conf_thres=0.3):
    # Requires: pip install ultralytics
    from ultralytics import YOLO
    model = YOLO(model_path)
    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    for fp in frames:
        img = cv2.imread(fp)
        h0, w0 = img.shape[:2]
        results = model.predict(source=fp, imgsz=imgsz, conf=conf_thres, save=False, verbose=False)
        # results is a list; take first
        if len(results)==0: continue
        r = results[0]
        boxes = r.boxes.cpu().numpy() if hasattr(r, 'boxes') else []
        # ultralytics objects differ by version; handle robustly
        label_lines = []
        for box in getattr(r, 'boxes', []):
            # box.xyxy, box.conf, box.cls
            xyxy = box.xyxy.cpu().numpy().flatten()
            conf = float(box.conf.cpu().numpy())
            cls = int(box.cls.cpu().numpy())
            # we assume model was trained for bib class (cls==0) or provide mapping
            x1, y1, x2, y2 = map(int, xyxy.tolist())
            # clamp
            x1, y1 = max(0,x1), max(0,y1)
            x2, y2 = min(w0-1,x2), min(h0-1,y2)
            if x2<=x1 or y2<=y1: 
                continue
            crop = img[y1:y2, x1:x2]
            base = os.path.splitext(os.path.basename(fp))[0]
            cropname = f"{base}_auto.jpg"
            cv2.imwrite(os.path.join(crops_out, cropname), crop)
            # YOLO label normalized
            cx = (x1 + x2) / 2.0 / w0
            cy = (y1 + y2) / 2.0 / h0
            bw = (x2 - x1) / w0
            bh = (y2 - y1) / h0
            label_lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        if label_lines:
            with open(os.path.join(labels_out, base + ".txt"), "w") as f:
                f.write("\n".join(label_lines))

def hog_person_prelabel(frames_dir, labels_out, crops_out, max_w=640):
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    frames = sorted(glob(os.path.join(frames_dir, "*.jpg")))
    for fp in frames:
        img = cv2.imread(fp)
        if img is None: 
            continue
        h0, w0 = img.shape[:2]
        scale = 1.0
        if w0 > max_w:
            scale = max_w / float(w0)
            img_small = cv2.resize(img, (int(w0*scale), int(h0*scale)))
        else:
            img_small = img.copy()
        gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
        # faster params
        rects, weights = hog.detectMultiScale(gray, winStride=(8,8), padding=(8,8), scale=1.2)
        base = os.path.splitext(os.path.basename(fp))[0]
        lines = []
        pcount = 0
        for (x, y, pw, ph), conf in zip(rects, weights):
            # map back
            x0 = int(x / scale); y0 = int(y / scale)
            pw0 = int(pw / scale); ph0 = int(ph / scale)
            if pw0*ph0 < 7000: 
                continue
            pcount += 1
            # chest region heuristic
            bx1 = int(x0 + 0.1*pw0)
            bx2 = int(x0 + 0.9*pw0)
            by1 = int(y0 + 0.25*ph0)
            by2 = int(y0 + 0.55*ph0)
            bx1, by1 = max(0,bx1), max(0,by1)
            bx2, by2 = min(w0-1,bx2), min(h0-1,by2)
            if bx2-bx1 < 8 or by2-by1 < 8: 
                continue
            crop = img[by1:by2, bx1:bx2]
            cv2.imwrite(os.path.join(crops_out, f"{base}_p{pcount}.jpg"), crop)
            cx = (bx1 + bx2) / 2.0 / w0
            cy = (by1 + by2) / 2.0 / h0
            bw = (bx2 - bx1) / w0
            bh = (by2 - by1) / h0
            lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        if lines:
            with open(os.path.join(labels_out, base + ".txt"), "w") as f:
                f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", default="./frames", help="frames folder")
    parser.add_argument("--out", default="./prelabels", help="output base folder")
    parser.add_argument("--model", default=None, help="optional: path to YOLO bib model (.pt)")
    args = parser.parse_args()
    frames_dir = args.frames
    out = args.out
    labels_out = os.path.join(out, "labels")
    crops_out = os.path.join(out, "crops")
    ensure(labels_out); ensure(crops_out)
    if args.model:
        print("Using YOLO model for prelabel:", args.model)
        yolo_prelabel(frames_dir, labels_out, crops_out, args.model)
    else:
        print("No model provided: using HOG-person fallback heuristic")
        hog_person_prelabel(frames_dir, labels_out, crops_out)
    print("Done. Labels at:", labels_out, "Crops at:", crops_out)

if __name__ == "__main__":
    main()
