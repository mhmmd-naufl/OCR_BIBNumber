# OCR BIB Number — Deteksi & Pembacaan Nomor BIB Peserta Lomba

Pipeline real-time yang mendeteksi peserta dalam video perlombaan, menemukan nomor BIB mereka, membaca nomornya lewat OCR, dan mencatat setiap hasil ke CSV.

## Cara Kerja

```
Frame video
  → Deteksi orang dengan YOLOv8
  → ByteTrack (Kalman filter + Hungarian algorithm)
  → Crop area dada → Canny + contour untuk temukan BIB
  → Preprocessing (upscale 4× · denoise · CLAHE · sharpen · adaptive threshold)
  → Ensemble OCR  (EasyOCR + Tesseract)
  → Weighted temporal voting per track
  → CSV log  (12 kolom termasuk real OCR confidence)
```

## Fitur

- **ByteTrack** — prediksi posisi lewat Kalman filter dan assignment optimal lewat Hungarian algorithm, ID tetap stabil saat oklusi dan gerakan cepat
- **Ensemble OCR** — EasyOCR (utama) dan Tesseract (fallback) dengan voting berbasis confidence; confidence asli per-read diteruskan ke CSV
- **Weighted temporal aggregation** — read dengan OCR confidence lebih tinggi punya bobot lebih besar dalam buffer voting per track
- **CSV logging terstruktur** — 12 kolom: frame index, timestamp, track ID, nomor BIB, bounding box, bbox confidence, OCR confidence, occlusion flag, capture flag
- **Analisis post-run** — `analyze_csv.py` menghasilkan breakdown per track, ringkasan capture, dan export terfilter
- **Kontrol performa** — pengaturan skip-frame terpisah untuk deteksi YOLO, OCR, dan NlMeans denoising; display scaling; lazy model loading

## Tech Stack

| Komponen | Library |
|---|---|
| Deteksi orang | YOLOv8n (`ultralytics`) |
| Tracking | ByteTrack via `ultralytics.trackers` |
| Pemrosesan gambar | OpenCV (`opencv-contrib-python`) |
| OCR — utama | EasyOCR |
| OCR — fallback | Tesseract / pytesseract |
| Deep learning | PyTorch ≥ 2.0 |
| Assignment solver | `lap` (Hungarian algorithm) |

## Instalasi

### 1. Clone dan buat virtual environment

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

Install PyTorch terlebih dahulu dari [pytorch.org](https://pytorch.org) — pilih versi CPU atau CUDA sesuai GPU kamu.

```bash
# Contoh CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3. Install dependency lainnya

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract (opsional tapi direkomendasikan)

Tesseract digunakan sebagai fallback OCR dan meningkatkan akurasi ensemble.

| OS | Cara Install |
|---|---|
| Windows | Download dari [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), install ke path default |
| Linux | `sudo apt install tesseract-ocr` |
| macOS | `brew install tesseract` |

EasyOCR mengunduh modelnya (~100 MB) secara otomatis saat pertama kali dijalankan.

### 5. Siapkan video

Letakkan video di `videos/video_input.mp4`, atau ubah `VIDEO_RELATIVE` di `ocr/config.py`.

## Penggunaan

```bash
python run.py
```

Tekan **`q`** untuk berhenti. `ocr_bib.py` adalah alias yang memanggil entry point yang sama.

### Analisis hasil

```bash
# Ringkasan lengkap
python analyze_csv.py --all

# Breakdown per track
python analyze_csv.py --per-track

# Hanya high-confidence captures
python analyze_csv.py --captures

# Export hasil terfilter
python analyze_csv.py --captures --export captures.csv
```

## Output

`tracking_results.csv` ditulis selama pipeline berjalan (mode append — aman jika dihentikan di tengah jalan).

| Kolom | Keterangan |
|---|---|
| `frame_index` | Nomor frame dalam video |
| `timestamp` | Detik sejak video dimulai |
| `track_id` | ID unik yang diberikan ByteTrack |
| `bib_number` | Nomor BIB hasil agregasi (kosong jika belum terbaca) |
| `bbox_x1/y1/x2/y2` | Koordinat bounding box orang (piksel) |
| `bbox_confidence` | Confidence deteksi YOLO (0–1) |
| `ocr_confidence` | Confidence OCR asli dari EasyOCR (0–1) |
| `occlusion_flag` | `1` jika `bbox_confidence ≤ 0.6` (kemungkinan tertutup) |
| `capture_flag` | `1` jika `ocr_confidence ≥ 0.7` (pembacaan berkualitas baik) |

## Konfigurasi

Semua parameter ada di `ocr/config.py`. Untuk sebagian besar kasus, hanya file ini yang perlu diedit.

```python
# Path
VIDEO_RELATIVE = "videos/video_input.mp4"
YOLO_MODEL     = "yolov8n.pt"      # ganti ke yolov8s/m untuk akurasi lebih tinggi

# Performa
SKIP_FRAMES            = 1         # jalankan YOLO setiap N frame
SKIP_OCR_FRAMES        = 3         # jalankan OCR setiap N frame
DISPLAY_SCALE          = 0.75      # perkecil jendela tampilan
USE_GPU                = False     # True jika CUDA tersedia
PREPROCESS_USE_NLMEANS = True      # False = lebih cepat, sedikit kurang bersih

# Tracking
TRACKER_MAX_AGE    = 30            # frame sebelum track yang hilang dihapus
TRACKER_IOU_THRESH = 0.3

# OCR
OCR_BUFFER_SIZE                  = 10
OCR_MIN_DIGITS                   = 2
OCR_USE_ENSEMBLE                 = True
OCR_EASYOCR_CONFIDENCE_THRESHOLD = 0.3

# Threshold logging
BBOX_CONF_THRESHOLD_OCCLUSION = 0.6
OCR_CONF_THRESHOLD_CAPTURE    = 0.7
```

### Skenario tuning umum

**CPU rendah / video FPS tinggi**
```python
SKIP_FRAMES            = 2
SKIP_OCR_FRAMES        = 5
DISPLAY_SCALE          = 0.5
PREPROCESS_USE_NLMEANS = False
```

**Akurasi OCR maksimal**
```python
SKIP_OCR_FRAMES                  = 1
OCR_BUFFER_SIZE                  = 20
OCR_EASYOCR_CONFIDENCE_THRESHOLD = 0.2
```

**GPU tersedia**
```python
USE_GPU = True
```

## Struktur Project

```
OCR_BIBNumber/
├── ocr/
│   ├── config.py          # semua parameter yang bisa diatur
│   ├── detector.py        # wrapper YOLOv8
│   ├── tracker.py         # wrapper ByteTrack (fallback ke greedy IOU)
│   ├── preprocess.py      # pipeline peningkatan kualitas gambar
│   ├── ocr_utils.py       # ensemble OCR dengan real confidence
│   ├── logging_csv.py     # CSV logger terstruktur
│   ├── logger.py          # legacy logger (disimpan sebagai referensi)
│   └── __init__.py
├── run.py                 # entry point utama
├── ocr_bib.py             # launcher backward-compatible
├── analyze_csv.py         # tool analisis CSV setelah run
├── prelabel.py            # utilitas pre-labeling dataset
├── requirements.txt
└── videos/                # letakkan video input di sini (tidak dilacak git)
```

## Troubleshooting

**Video tidak ditemukan** — atur `VIDEO_RELATIVE` di `ocr/config.py` ke path yang benar.

**Model YOLO tidak ditemukan** — `yolov8n.pt` diunduh otomatis saat pertama kali dijalankan (~6 MB). Butuh koneksi internet.

**FPS rendah** — naikkan `SKIP_FRAMES` / `SKIP_OCR_FRAMES`, turunkan `DISPLAY_SCALE`, set `PREPROCESS_USE_NLMEANS = False`.

**Akurasi OCR buruk** — turunkan `OCR_EASYOCR_CONFIDENCE_THRESHOLD` ke `0.2`, naikkan `OCR_BUFFER_SIZE` ke `15–20`, pastikan BIB terlihat jelas dan pencahayaan cukup.

**Tesseract tidak ditemukan** — install sesuai panduan di atas, atau abaikan; pipeline otomatis fallback ke EasyOCR saja.

**Install `lap` gagal** — ByteTrack membutuhkan `lap` untuk Hungarian solver. Jika build gagal, tracker otomatis fallback ke greedy IOU; install C++ build toolchain atau gunakan pre-built wheel.
