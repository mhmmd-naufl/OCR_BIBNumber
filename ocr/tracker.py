"""Tracker module — ByteTrack (primary) with SimpleTracker fallback.

Public API (unchanged from before — run.py needs no edits):
    tracker = SimpleTracker(max_age, iou_threshold)   <- now a ByteTrack wrapper
    tracks  = tracker.update(detections)

Input:
    detections: List of (x1, y1, x2, y2, conf)  — from detector.detect_people()

Output:
    tracks: List of {'id': int, 'bbox': (x1,y1,x2,y2), 'conf': float}

ByteTrack advantages over the previous greedy-IOU tracker:
  - Kalman filter predicts position between frames -> fewer dropped tracks on fast movement
  - Hungarian algorithm (via lap) for optimal detection-to-track assignment
  - Two-stage matching: high-conf detections first, then low-conf re-association
  - Lost tracks kept alive briefly for re-identification after occlusion

If ultralytics BYTETracker is unavailable, falls back to the original SimpleTracker
so the pipeline still works without crashing.
"""
from __future__ import annotations

from typing import List, Tuple
import numpy as np

# ---------------------------------------------------------------------------
# Try to import BYTETracker from ultralytics
# ---------------------------------------------------------------------------
try:
    from ultralytics.trackers import BYTETracker as _BYTETracker
    _BYTETRACK_AVAILABLE = True
except Exception:
    _BYTETracker = None
    _BYTETRACK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Thin numpy wrapper so BYTETracker receives objects with .conf / .cls / .xywh
# ---------------------------------------------------------------------------
class _DetectionResults:
    """Wraps a plain numpy array as a Results-like object for BYTETracker.

    BYTETracker._split_detections() accesses:
        results.conf   -> 1-D array of confidences
        results.cls    -> 1-D array of class ids
        results.xywh   -> (N, 4) array [cx, cy, w, h]

    It also boolean-indexes the object (results[mask]), so __getitem__ is needed.
    """

    def __init__(self, data: np.ndarray):
        # data shape: (N, 6) -> [x1, y1, x2, y2, conf, cls]
        self._data = data

    @property
    def conf(self) -> np.ndarray:
        return self._data[:, 4]

    @property
    def cls(self) -> np.ndarray:
        return self._data[:, 5]

    @property
    def xywh(self) -> np.ndarray:
        x1, y1, x2, y2 = (self._data[:, i] for i in range(4))
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        w  = x2 - x1
        h  = y2 - y1
        return np.stack([cx, cy, w, h], axis=1)

    @property
    def xyxy(self) -> np.ndarray:
        return self._data[:, :4]

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, mask):
        return _DetectionResults(self._data[mask])


# ---------------------------------------------------------------------------
# ByteTrack args namespace
# ---------------------------------------------------------------------------
class _ByteTrackArgs:
    """Minimal args namespace expected by BYTETracker.__init__()."""

    def __init__(self, track_buffer: int = 30, match_thresh: float = 0.8):
        self.track_high_thresh: float = 0.25   # detections above this get first-stage match
        self.track_low_thresh:  float = 0.1    # detections above this enter second-stage match
        self.new_track_thresh:  float = 0.25   # min score to spawn a new track
        self.track_buffer:      int   = track_buffer
        self.match_thresh:      float = match_thresh
        self.fuse_score:        bool  = True   # fuse detection score into track score


# ---------------------------------------------------------------------------
# Public SimpleTracker class (now a ByteTrack wrapper)
# ---------------------------------------------------------------------------
class SimpleTracker:
    """ByteTrack-backed tracker with the same API as the original SimpleTracker.

    Parameters mirror the old ones so config.py values still work:
        max_age       -> track_buffer  (frames a lost track is kept alive)
        iou_threshold -> match_thresh  (IoU threshold for assignment)

    Falls back to the original greedy-IOU implementation if BYTETracker is
    not importable (e.g. missing lap dependency).
    """

    def __init__(self, max_age: int = 30, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.iou_threshold = iou_threshold

        if _BYTETRACK_AVAILABLE:
            args = _ByteTrackArgs(track_buffer=max_age, match_thresh=iou_threshold)
            self._byte = _BYTETracker(args)
            self._use_byte = True
            print("Tracker: ByteTrack (Kalman + Hungarian)")
        else:
            self._use_byte = False
            self._next_id = 1
            self._tracks: dict = {}
            print("Tracker: SimpleTracker (greedy IOU) -- install ultralytics>=8 and lap for ByteTrack")

    # ------------------------------------------------------------------
    # Public update() -- same signature and return type as before
    # ------------------------------------------------------------------
    def update(self, detections: List[Tuple[int, int, int, int, float]]) -> List[dict]:
        """Update tracker with new detections.

        Args:
            detections: list of (x1, y1, x2, y2, conf)

        Returns:
            list of {'id': int, 'bbox': (x1,y1,x2,y2), 'conf': float}
        """
        if self._use_byte:
            return self._update_bytetrack(detections)
        return self._update_simple(detections)

    # ------------------------------------------------------------------
    # ByteTrack path
    # ------------------------------------------------------------------
    def _update_bytetrack(self, detections: List[Tuple]) -> List[dict]:
        # Build (N, 6) array: [x1, y1, x2, y2, conf, cls=0]
        if detections:
            arr = np.array(
                [[x1, y1, x2, y2, conf, 0.0] for x1, y1, x2, y2, conf in detections],
                dtype=np.float32,
            )
        else:
            arr = np.zeros((0, 6), dtype=np.float32)

        results_obj = _DetectionResults(arr)
        tracks_arr = self._byte.update(results_obj)
        return self._parse_byte_output(tracks_arr)

    @staticmethod
    def _parse_byte_output(tracks_arr: np.ndarray) -> List[dict]:
        """Convert BYTETracker output (N, 8) -> list of dicts.

        BYTETracker.update() returns shape (N, 8):
            [x1, y1, x2, y2, track_id, score, cls, det_idx]
        """
        out = []
        if tracks_arr is None or len(tracks_arr) == 0:
            return out
        for row in tracks_arr:
            x1, y1, x2, y2 = row[0], row[1], row[2], row[3]
            tid, score      = row[4], row[5]
            out.append({
                'id':   int(tid),
                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                'conf': float(score),
            })
        return out

    # ------------------------------------------------------------------
    # Original greedy-IOU fallback
    # ------------------------------------------------------------------
    def _update_simple(self, detections: List[Tuple]) -> List[dict]:
        matched_tracks: set = set()
        det_bboxes = [d[:4] for d in detections]
        det_confs  = [d[4]  for d in detections]

        track_ids = list(self._tracks.keys())
        iou_matrix = []
        for tid in track_ids:
            tb  = self._tracks[tid]['bbox']
            row = [_iou(tb, db) for db in det_bboxes]
            iou_matrix.append(row)

        used_dets: set = set()
        for t_idx, tid in enumerate(track_ids):
            if not iou_matrix[t_idx]:
                continue
            best_det = int(np.argmax(iou_matrix[t_idx]))
            if iou_matrix[t_idx][best_det] >= self.iou_threshold and best_det not in used_dets:
                x1, y1, x2, y2 = det_bboxes[best_det]
                self._tracks[tid].update({
                    'bbox': (x1, y1, x2, y2),
                    'age':  0,
                    'conf': det_confs[best_det],
                })
                self._tracks[tid]['hits'] += 1
                matched_tracks.add(tid)
                used_dets.add(best_det)

        for idx, det in enumerate(detections):
            if idx in used_dets:
                continue
            x1, y1, x2, y2, conf = det
            tid = self._next_id
            self._next_id += 1
            self._tracks[tid] = {'bbox': (x1, y1, x2, y2), 'age': 0, 'hits': 1, 'conf': conf}
            matched_tracks.add(tid)

        for tid in list(self._tracks.keys()):
            if tid not in matched_tracks:
                self._tracks[tid]['age'] += 1
            if self._tracks[tid]['age'] > self.max_age:
                del self._tracks[tid]

        return [
            {'id': tid, 'bbox': v['bbox'], 'conf': v.get('conf', 0.0)}
            for tid, v in self._tracks.items()
        ]


# ---------------------------------------------------------------------------
# Standalone IOU helper (used by fallback only)
# ---------------------------------------------------------------------------
def _iou(boxA, boxB) -> float:
    xA = max(boxA[0], boxB[0]); yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]); yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    aA = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    aB = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = float(aA + aB - inter)
    return inter / denom if denom > 0 else 0.0
