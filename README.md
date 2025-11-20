# OCR BIB Detection & Tracking System

Sistem otomatis untuk mendeteksi, melacak, dan membaca nomor BIB (race bib) peserta pada video menggunakan YOLOv8, tracking IOU-based, dan OCR ensemble (EasyOCR + Tesseract).

## Fitur Utama

- **Deteksi Orang Real-time**: Menggunakan YOLOv8 untuk mendeteksi orang dalam video
- **Tracking Konsisten**: SimpleTracker berbasis IoU untuk memberikan ID stabil ke setiap orang
- **Pembacaan BIB Akurat**: 
  - Deteksi otomatis region BIB dari orang yang terdeteksi
  - Preprocessing canggih (denoise, upscale 4x, contrast enhancement)
  - Ensemble OCR voting (EasyOCR + Tesseract untuk hasil lebih andal)
- **Temporal Aggregation**: Buffer voting per-track untuk mengurangi noise dan meningkatkan akurasi
- **Comprehensive Logging**: CSV dengan 12 kolom mencakup confidence scores, occlusion flags, capture flags
- **Performance Optimized**:
  - Frame-skipping untuk deteksi & OCR (tracking tetap continuous)
  - Display scaling untuk rendering smooth
  - Lazy loading model untuk startup cepat
  - FPS real-time counter

## Instalasi

### Prasyarat
- Python 3.8+
- Windows/Linux/macOS

### Step 1: Clone Repository & Setup Virtual Environment

```bash
# Buat virtual environment
python -m venv venv

# Aktivasi (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Aktivasi (Linux/macOS)
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Konfigurasi OCR Engines (Optional tapi Recommended)

#### EasyOCR (Recommended - Primary)
EasyOCR akan diunduh otomatis saat pertama kali dijalankan (~100MB untuk model English).

#### Tesseract OCR (Fallback - Optional di Windows)
1. Download installer dari: https://github.com/UB-Mannheim/tesseract/wiki
2. Install default path (`C:\Program Files\Tesseract-OCR`)
3. Atau set environment variable: `TESSERACT_PATH=C:\path\to\tesseract.exe`

Jika keduanya tersedia, sistem akan menggunakan ensemble voting untuk akurasi maksimal.

### Step 4: Verifikasi Setup

```bash
# Test import
python -c "import cv2, ultralytics, easyocr; print('All OK')"
```

## Quick Start

### Persiapan Video Input
Simpan video input ke folder `videos/` dengan nama `video_input.mp4` atau ubah path di `ocr/config.py`.

### Jalankan Pipeline

```bash
python run.py
```

atau

```bash
python ocr_bib.py
```

### Kontrol Saat Running
- **'q'** - Quit application
- **Tracking window** - Menampilkan video dengan bounding boxes hijau (orang), merah/kuning (BIB terdeteksi/valid)

### Output
- **`tracking_results.csv`** - Log detail semua deteksi dengan kolom:
  - `frame_index`: Nomor frame
  - `timestamp`: Waktu dalam video (detik)
  - `track_id`: ID pelacak unik
  - `bib_number`: Nomor BIB yang dibaca
  - `bbox_x1, bbox_y1, bbox_x2, bbox_y2`: Koordinat bounding box
  - `bbox_confidence`: Confidence skor deteksi orang (0-1)
  - `ocr_confidence`: Confidence skor pembacaan BIB (0-1)
  - `occlusion_flag`: 1 jika orang tertutup/rendah confidence (≤0.6)
  - `capture_flag`: 1 jika BIB terbaca dengan confidence tinggi (≥0.7)

- **Console Output** - Statistik akhir:
  - Total detections
  - Unique tracks
  - Unique BIBs
  - Capture rate (%)
  - Occlusion rate (%)

## Konfigurasi & Tuning

Semua parameter tunable tersentralisasi di **`ocr/config.py`**. Edit file ini tanpa mengubah code lain:

### Parameter Penting

```python
# Video
VIDEO_PATH = "videos/video_input.mp4"
DISPLAY_SCALE = 0.75  # Semakin kecil = rendering lebih cepat

# Model YOLO
YOLO_MODEL = "yolov8n.pt"  # nano (cepat) atau yolov8s/m/l (akurat)
PERSON_CONF_THRESH = 0.5   # Confidence threshold deteksi orang

# Frame Skipping (untuk performance)
SKIP_FRAMES = 1             # Proses setiap 1 frame
SKIP_OCR_FRAMES = 3         # OCR hanya setiap 3 frame (tracking tetap update setiap frame)

# OCR
OCR_BUFFER_SIZE = 10        # Jumlah frame untuk aggregation voting
OCR_MIN_DIGITS = 2          # Min digit di BIB
EASYOCR_CONFIDENCE_THRESHOLD = 0.3  # Threshold filter hasil EasyOCR

# Logging Thresholds
OCCLUSION_FLAG_THRESHOLD = 0.6      # Jika bbox_conf ≤ ini = occluded
CAPTURE_FLAG_CONFIDENCE = 0.7       # Jika ocr_conf ≥ ini = captured

# BIB Detection
MIN_BIB_AREA = 100          # Pixel area minimal untuk dianggap BIB
BIB_ASPECT_MIN = 0.2        # Aspect ratio min
BIB_ASPECT_MAX = 0.8        # Aspect ratio max

# Preprocessing
PREPROCESS_UPSCALE_FACTOR = 4       # 2x → 4x untuk detail lebih baik
PREPROCESS_DENOISE_H = 10           # Denoising strength
PREPROCESS_CLAHE_CLIP = 4.0         # Contrast enhancement
```

### Tuning Guide

**Untuk Video Berkualitas Rendah (FPS Rendah / Lag):**
```python
DISPLAY_SCALE = 0.5         # Kurangi resolusi display
SKIP_FRAMES = 2             # Skip lebih banyak frame
SKIP_OCR_FRAMES = 5         # OCR lebih jarang
YOLO_MODEL = "yolov8n.pt"   # Pakai nano model
```

**Untuk Akurasi OCR Maksimal:**
```python
SKIP_FRAMES = 1             # Proses setiap frame
SKIP_OCR_FRAMES = 1         # OCR setiap frame
OCR_BUFFER_SIZE = 20        # Buffer voting lebih besar
PREPROCESS_UPSCALE_FACTOR = 4
EASYOCR_CONFIDENCE_THRESHOLD = 0.2  # Lebih permissif
```

**Untuk GPU Support (jika tersedia):**
```python
USE_GPU = True              # Di config.py
```

## Analisis Results

Setelah pipeline selesai, analisis CSV output:

```bash
# Statistik keseluruhan
python analyze_csv.py tracking_results.csv --all

# Per-track breakdown
python analyze_csv.py tracking_results.csv --per-track

# Hanya high-confidence captures
python analyze_csv.py tracking_results.csv --captures

# Export ke CSV baru
python analyze_csv.py tracking_results.csv --export cleaned_results.csv

# Statistik detail
python analyze_csv.py tracking_results.csv --stats
```

## Arsitektur Pipeline

```
┌─────────────────┐
│  Video Input    │
│  (VideoCapture) │
└────────┬────────┘
         │
    ┌────▼────┐
    │  YOLO   │ (Skip Detection setiap SKIP_FRAMES frame)
    │ Detector│
    └────┬────┘
         │
    ┌────▼────────┐
    │   Tracker   │ (Update SETIAP frame → smooth tracking)
    │  (IOU-based)│
    └────┬────────┘
         │
    ┌────▼─────────────────────┐
    │ BIB Region Detection      │
    │ (Canny + Contour Filter)  │
    └────┬─────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Preprocessing (setiap frame)   │
    │ - Denoise, Upscale 4x         │
    │ - CLAHE Contrast              │
    │ - Bilateral Filter            │
    │ - Adaptive Threshold          │
    │ - Morphological Ops           │
    │ - Unsharp Masking             │
    └────┬──────────────────────────┘
         │
    ┌────▼────────────────────────┐
    │ OCR (setiap SKIP_OCR_FRAMES) │
    │ Ensemble: EasyOCR + Tesseract│
    │ + Confidence Filtering       │
    └────┬────────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Temporal Aggregation      │
    │ (Buffer Voting per-track) │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────┐
    │ Validation Heuristics  │
    │ - No leading zeros     │
    │ - Length validation    │
    │ - Pattern checks       │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │ CSV Logging            │
    │ (12 columns + flags)   │
    └────┬──────────────────┘
         │
    ┌────▼──────────────┐
    │ Display + FPS     │
    │ (Scaled for speed) │
    └───────────────────┘
```

## Troubleshooting

### Error: "Video file not found"
**Solusi:** Pastikan `VIDEO_PATH` di `ocr/config.py` benar. Gunakan absolute path atau relative path dari workspace root.

### Error: "YOLO model not found"
**Solusi:** Model akan diunduh otomatis dari Ultralytics. Pastikan koneksi internet tersedia. Model disimpan di `~/.cache/ultralytics/`.

### Error: "No module named easyocr"
**Solusi:** Install dengan `pip install easyocr`. Download model pertama kali ~100MB.

### Error: "Tesseract is not installed"
**Solusi:** 
- (Windows) Download dari https://github.com/UB-Mannheim/tesseract/wiki dan install
- (Linux) `sudo apt-get install tesseract-ocr`
- (macOS) `brew install tesseract`
- Atau disable Tesseract di code (hanya gunakan EasyOCR)

### FPS Rendah / Video Lag
**Solusi:**
- Kurangi `DISPLAY_SCALE` (misal 0.5)
- Naikkan `SKIP_FRAMES` (misal 2-3)
- Naikkan `SKIP_OCR_FRAMES` (misal 5-10)
- Gunakan `yolov8n.pt` (nano model)
- Set `USE_GPU = False` jika GPU tidak optimal

### OCR Accuracy Rendah
**Solusi:**
- Turunkan `EASYOCR_CONFIDENCE_THRESHOLD` (misal 0.2)
- Naikkan `OCR_BUFFER_SIZE` (misal 15-20)
- Pastikan video cukup terang & BIB terlihat jelas
- Cek `PREPROCESS_UPSCALE_FACTOR = 4` (jangan dikecilkan)

### CSV Output Kosong
**Solusi:**
- Pastikan ada orang terdeteksi (cek YOLO display)
- Pastikan ada region BIB terdeteksi (cek red/yellow boxes)
- Naikkan `PERSON_CONF_THRESH` turun (misal 0.3) jika deteksi terlalu ketat

## Project Structure

```
Test OCR/
├── ocr/                          # Main package
│   ├── __init__.py
│   ├── config.py                 # ⭐ CENTRAL: Semua parameter tunable
│   ├── detector.py               # YOLO wrapper
│   ├── tracker.py                # SimpleTracker (IOU-based)
│   ├── preprocess.py             # Image enhancement pipeline
│   ├── ocr_utils.py              # Ensemble OCR (EasyOCR + Tesseract)
│   ├── logger.py                 # Legacy logger
│   └── logging_csv.py            # CSV logging dengan flags
├── run.py                        # ⭐ Main entry point
├── ocr_bib.py                    # Backward-compatible launcher
├── analyze_csv.py                # CSV analysis utility
├── requirements.txt              # Dependencies
├── README.md                      # Dokumentasi (file ini)
├── CSV_LOGGING_GUIDE.md          # CSV schema & API reference
├── .gitignore                    # Files to exclude from Git
├── videos/                       # Input folder (not in repo)
│   └── video_input.mp4
└── tracking_results.csv          # Output (not in repo)
```

## Dependencies

Lihat `requirements.txt` untuk list lengkap. Highlight:
- **ultralytics** - YOLOv8
- **opencv-python** - Video & image processing
- **numpy** - Numerical operations
- **easyocr** - Primary OCR engine
- **pytesseract** - Tesseract wrapper (optional)
- **torch** - Deep learning backbone

Untuk GPU support (PyTorch), install dari: https://pytorch.org

## Performance Notes

- **Lazy Loading**: Model YOLO dimuat saat pertama kali digunakan (bukan saat startup)
- **Continuous Tracking**: Tracker selalu update (setiap frame) untuk smooth trajectory
- **Selective Detection**: YOLO & OCR dijalankan setiap N frame untuk speed
- **Display Scaling**: Default 0.75x untuk rendering smooth
- **Buffer Voting**: Per-track temporal aggregation mengurangi false positives

## Contributing

Untuk kontribusi, fork repository dan submit pull requests dengan deskripsi perubahan.

## License

[Tambahkan license info jika diperlukan]

## Contact

Untuk pertanyaan atau bug reports, buka GitHub Issues.

---

**Last Updated**: 2024 | Python 3.8+
