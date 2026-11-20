"""Detector wrapper

This module exposes a lazy loader for the detector to avoid heavy imports at import-time.
It offers `load_model()` and `detect_people(frame)` which returns a list of detections:
    [(x1,y1,x2,y2,conf), ...]

Current implementation uses Ultralytics YOLO (v8). If not installed, the loader will raise
an informative error. Keeping the wrapper makes it easy to swap to OpenCV DNN later.
"""

from typing import List, Tuple
from ocr import config

_model = None

def load_model(path: str):
    """Lazy-load the YOLO model (ultralytics). Respects config.USE_GPU."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
        except Exception as e:
            raise RuntimeError("Ultralytics YOLO not installed. Install with: pip install ultralytics") from e
        _model = YOLO(path)
        # Move model to GPU if configured
        if config.USE_GPU:
            try:
                _model.to("cuda")
            except Exception:
                print("⚠️  USE_GPU=True but CUDA not available — falling back to CPU.")
    return _model


def detect_people(frame, model=None, conf_thresh=0.5) -> List[Tuple[int, int, int, int, float]]:
    """Return list of person detections as (x1,y1,x2,y2,conf).

    frame: BGR image (numpy array)
    model: optionally pass preloaded model
    """
    if model is None:
        raise RuntimeError("Model not loaded. Call load_model(path) first and pass it here.")
    results = model(frame, classes=[0], verbose=False)
    detections = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            if conf >= conf_thresh:
                detections.append((x1, y1, x2, y2, conf))
    return detections
