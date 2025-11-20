"""Simple IOU-based tracker (CPU friendly)

Provides a SimpleTracker class with API:
- tracker = SimpleTracker(max_age, iou_threshold)
- tracks = tracker.update(detections)

Where `detections` is list of (x1,y1,x2,y2,conf) and `tracks` is list of dicts
with keys: 'id', 'bbox', 'conf'.
"""
from typing import List, Tuple
import numpy as np


def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    inter = interW * interH
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = float(boxAArea + boxBArea - inter)
    if denom <= 0:
        return 0.0
    return inter / denom


class SimpleTracker:
    def __init__(self, max_age=30, iou_threshold=0.3):
        self.next_id = 1
        self.tracks = {}  # id -> {bbox, age, hits, conf}
        self.max_age = max_age
        self.iou_threshold = iou_threshold

    def update(self, detections: List[Tuple[int, int, int, int, float]]):
        matched_tracks = set()
        det_bboxes = [d[:4] for d in detections]
        det_confs = [d[4] for d in detections]

        iou_matrix = []
        track_ids = list(self.tracks.keys())
        for tid in track_ids:
            tb = self.tracks[tid]['bbox']
            row = [iou(tb, db) for db in det_bboxes]
            iou_matrix.append(row)

        used_dets = set()
        matches = []
        for t_idx, tid in enumerate(track_ids):
            if len(iou_matrix[t_idx]) == 0:
                continue
            best_det = int(np.argmax(iou_matrix[t_idx]))
            best_iou = iou_matrix[t_idx][best_det]
            if best_iou >= self.iou_threshold and best_det not in used_dets:
                matches.append((tid, best_det))
                used_dets.add(best_det)

        for tid, didx in matches:
            x1, y1, x2, y2 = det_bboxes[didx]
            conf = det_confs[didx]
            self.tracks[tid]['bbox'] = (x1, y1, x2, y2)
            self.tracks[tid]['age'] = 0
            self.tracks[tid]['hits'] += 1
            self.tracks[tid]['conf'] = conf
            matched_tracks.add(tid)

        for idx, det in enumerate(detections):
            if idx in used_dets:
                continue
            x1, y1, x2, y2, conf = det
            tid = self.next_id
            self.next_id += 1
            self.tracks[tid] = {'bbox': (x1, y1, x2, y2), 'age': 0, 'hits': 1, 'conf': conf}
            matched_tracks.add(tid)

        remove_ids = []
        for tid in list(self.tracks.keys()):
            if tid not in matched_tracks:
                self.tracks[tid]['age'] += 1
            if self.tracks[tid]['age'] > self.max_age:
                remove_ids.append(tid)
        for rid in remove_ids:
            del self.tracks[rid]

        out = []
        for tid, v in self.tracks.items():
            out.append({'id': tid, 'bbox': v['bbox'], 'conf': v.get('conf', 0.0)})
        return out
