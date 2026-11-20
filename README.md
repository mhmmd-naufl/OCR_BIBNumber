# OCR BIB Number Detection & Tracking

A real-time pipeline that detects people in race footage, locates their bib (race number), reads the number via OCR, and logs every result to CSV.

## How it works

```
Video frame
  → YOLOv8 person detection
  → ByteTrack (Kalman filter + Hungarian algorithm)
  → Chest-region crop → Canny + contour bib localization
  → Preprocessing (4× upscale · denoise · CLAHE · sharpen · adaptive threshold)
  → Ensemble OCR  (EasyOCR + Tesseract)
  → Weighted temporal voting per track
  → CSV log  (12 columns including real OCR confidence)
```

## Features

- **ByteTrack** — Kalman-filter prediction and optimal Hungarian assignment keep IDs stable across occlusions and fast movement
- **Ensemble OCR** — EasyOCR (primary) and Tesseract (fallback) with confidence-weighted voting; real per-read confidence propagated to CSV
- **Weighted temporal aggregation** — reads with higher OCR confidence carry more weight in the per-track vote buffer
- **Structured CSV logging** — 12 columns: frame index, timestamp, track ID, bib number, bounding box, bbox confidence, OCR confidence, occlusion flag, capture flag
- **Post-run analysis** — `analyze_csv.py` produces per-track breakdowns, capture summaries, and filtered exports
- **Performance controls** — independent skip-frame settings for YOLO detection, OCR, and NlMeans denoising; display scaling; lazy model loading

## Stack

| Component | Library |
|---|---|
| Person detection | YOLOv8n (`ultralytics`) |
| Tracking | ByteTrack via `ultralytics.trackers` |
| Image processing | OpenCV (`opencv-contrib-python`) |
| OCR — primary | EasyOCR |
| OCR — fallback | Tesseract / pytesseract |
| Deep learning | PyTorch ≥ 2.0 |
| Assignment solver | `lap` (Hungarian algorithm) |

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/mhmmd-naufl/OCR_BIBNumber.git
cd OCR_BIBNumber

python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 2. Install PyTorch

Install PyTorch first from [pytorch.org](https://pytorch.org) — choose CPU or the CUDA version that matches your GPU.

```bash
# CPU example
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3. Install remaining dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract (optional but recommended)

Tesseract is used as the OCR fallback and improves ensemble accuracy.

| OS | Command |
|---|---|
| Windows | Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), install to default path |
| Linux | `sudo apt install tesseract-ocr` |
| macOS | `brew install tesseract` |

EasyOCR downloads its model (~100 MB) automatically on first run.

### 5. Add your video

Place your video at `videos/video_input.mp4`, or change `VIDEO_RELATIVE` in `ocr/config.py`.

## Usage

```bash
python run.py
```

Press **`q`** to stop. `ocr_bib.py` is an alias that calls the same entry point.

### Analyzing results

```bash
# Full summary
python analyze_csv.py --all

# Per-track breakdown
python analyze_csv.py --per-track

# High-confidence captures only
python analyze_csv.py --captures

# Export filtered rows
python analyze_csv.py --captures --export captures.csv
```

## Output

`tracking_results.csv` is written during the run (append mode — safe to interrupt).

| Column | Description |
|---|---|
| `frame_index` | Frame number in the video |
| `timestamp` | Seconds since video start |
| `track_id` | Unique ID assigned by ByteTrack |
| `bib_number` | Aggregated bib read (empty if none yet) |
| `bbox_x1/y1/x2/y2` | Person bounding box pixels |
| `bbox_confidence` | YOLO detection confidence (0–1) |
| `ocr_confidence` | Real OCR confidence from EasyOCR (0–1) |
| `occlusion_flag` | `1` if `bbox_confidence ≤ 0.6` |
| `capture_flag` | `1` if `ocr_confidence ≥ 0.7` |

## Configuration

All parameters live in `ocr/config.py`. Nothing else needs editing for most use cases.

```python
# Paths
VIDEO_RELATIVE = "videos/video_input.mp4"
YOLO_MODEL     = "yolov8n.pt"      # swap to yolov8s/m for more accuracy

# Performance
SKIP_FRAMES       = 1              # run YOLO every N frames
SKIP_OCR_FRAMES   = 3              # run OCR every N frames
DISPLAY_SCALE     = 0.75           # resize display window
USE_GPU           = False          # True if CUDA is available
PREPROCESS_USE_NLMEANS = True      # False = faster, slightly less clean

# Tracking
TRACKER_MAX_AGE    = 30            # frames to keep a lost track alive
TRACKER_IOU_THRESH = 0.3

# OCR
OCR_BUFFER_SIZE                   = 10
OCR_MIN_DIGITS                    = 2
OCR_USE_ENSEMBLE                  = True
OCR_EASYOCR_CONFIDENCE_THRESHOLD  = 0.3

# Logging thresholds
BBOX_CONF_THRESHOLD_OCCLUSION = 0.6
OCR_CONF_THRESHOLD_CAPTURE    = 0.7
```

### Common tuning scenarios

**Low-end CPU / high-FPS video**
```python
SKIP_FRAMES            = 2
SKIP_OCR_FRAMES        = 5
DISPLAY_SCALE          = 0.5
PREPROCESS_USE_NLMEANS = False
```

**Maximum OCR accuracy**
```python
SKIP_OCR_FRAMES                  = 1
OCR_BUFFER_SIZE                  = 20
OCR_EASYOCR_CONFIDENCE_THRESHOLD = 0.2
```

**GPU available**
```python
USE_GPU = True
```

## Project structure

```
OCR_BIBNumber/
├── ocr/
│   ├── config.py          # all tunable parameters
│   ├── detector.py        # YOLOv8 wrapper
│   ├── tracker.py         # ByteTrack wrapper (greedy IOU fallback)
│   ├── preprocess.py      # image enhancement pipeline
│   ├── ocr_utils.py       # ensemble OCR with real confidence
│   ├── logging_csv.py     # structured CSV logger
│   ├── logger.py          # legacy logger (kept for reference)
│   └── __init__.py
├── run.py                 # main entry point
├── ocr_bib.py             # backward-compatible launcher
├── analyze_csv.py         # post-run CSV analysis tool
├── prelabel.py            # dataset pre-labeling utility
├── requirements.txt
└── videos/                # place input video here (not tracked by git)
```

## Troubleshooting

**Video not found** — set `VIDEO_RELATIVE` in `ocr/config.py` to the correct path.

**YOLO model not found** — `yolov8n.pt` downloads automatically on first run (~6 MB). Requires internet access.

**Low FPS** — increase `SKIP_FRAMES` / `SKIP_OCR_FRAMES`, lower `DISPLAY_SCALE`, set `PREPROCESS_USE_NLMEANS = False`.

**Poor OCR accuracy** — lower `OCR_EASYOCR_CONFIDENCE_THRESHOLD` to `0.2`, raise `OCR_BUFFER_SIZE` to `15–20`, confirm the bib is visible and well-lit in the video.

**Tesseract not found** — install it (see Setup step 4) or ignore; the pipeline falls back to EasyOCR only.

**`lap` install fails** — ByteTrack requires `lap` for the Hungarian solver. If the build fails, the tracker automatically falls back to greedy IOU; install a C++ build toolchain or use a pre-built wheel.
