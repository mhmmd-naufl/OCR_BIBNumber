# BIB Detection & Tracking with OCR - CSV Logging Guide

## Fitur CSV Logging

Sistem ini mencatat setiap deteksi, tracking, dan hasil OCR ke file CSV untuk evaluasi dan analisis.

### File Output
- **Default**: `tracking_results.csv` (configurable via `config.CSV_OUTPUT_FILE`)
- **Format**: CSV dengan header
- **Mode**: Append (tidak menimpa file existing)

### Kolom CSV

| Kolom | Deskripsi | Tipe |
|-------|-----------|------|
| `frame_index` | Nomor frame dalam video (1-based) | Integer |
| `timestamp` | Waktu elapsed dari awal video (detik) | Float |
| `track_id` | Unique ID untuk setiap person yang di-track | Integer |
| `bib_number` | Nomor BIB yang terdeteksi (hasil aggregasi OCR) | String |
| `bbox_x1` | Koordinat X1 bounding box person | Integer |
| `bbox_y1` | Koordinat Y1 bounding box person | Integer |
| `bbox_x2` | Koordinat X2 bounding box person | Integer |
| `bbox_y2` | Koordinat Y2 bounding box person | Integer |
| `bbox_confidence` | Confidence score deteksi person (YOLO) | Float (0.0-1.0) |
| `ocr_confidence` | Confidence score hasil OCR | Float (0.0-1.0) |
| `occlusion_flag` | 1 jika person ter-oklude (bbox_conf <= 0.6), 0 sebaliknya | Integer |
| `capture_flag` | 1 jika pembacaan BIB bagus (ocr_conf >= 0.7), 0 sebaliknya | Integer |

### Konfigurasi

Edit `ocr/config.py`:

```python
# CSV Logging
CSV_OUTPUT_FILE = "tracking_results.csv"  # Nama file CSV output
OCR_CONF_THRESHOLD_CAPTURE = 0.7         # Threshold untuk capture_flag
BBOX_CONF_THRESHOLD_OCCLUSION = 0.6      # Threshold untuk occlusion_flag
```

### Contoh Penggunaan di Code

Sudah terintegrasi di `run.py`. Setiap frame diproses seperti berikut:

```python
from ocr import logging_csv

# Initialize logger (dipanggil di awal)
csv_logger = logging_csv.init_csv_logger("tracking_results.csv")

# Log setiap deteksi (dalam loop video)
logging_csv.log_detection(
    logger=csv_logger,
    frame_index=frame_idx,
    timestamp=time.time() - t_start,
    track_id=tid,
    bib_number="123",  # hasil OCR
    bbox=(x1, y1, x2, y2),
    bbox_confidence=0.95,  # dari YOLO
    ocr_confidence=0.85,   # dari EasyOCR/pytesseract
    occlusion_flag=0,      # 1 jika bbox_conf <= 0.6
    capture_flag=1         # 1 jika ocr_conf >= 0.7
)

# Close logger (dipanggil di akhir)
logging_csv.close_logger(csv_logger)

# Dapatkan statistik
stats = logging_csv.get_logger_stats("tracking_results.csv")
print(stats)
```

### Output CSV Contoh

```
frame_index,timestamp,track_id,bib_number,bbox_x1,bbox_y1,bbox_x2,bbox_y2,bbox_confidence,ocr_confidence,occlusion_flag,capture_flag
1,0.033,1,123,100,50,200,300,0.95,0.85,0,1
2,0.067,1,123,102,51,202,302,0.94,0.85,0,1
3,0.1,1,123,104,52,204,304,0.93,0.82,0,1
4,0.133,2,,250,100,350,350,0.88,,0,0
5,0.167,1,123,106,53,206,306,0.91,0.80,0,1
```

### Interpretasi Flag

**occlusion_flag = 1**: Person kemungkinan ter-oklude oleh object lain → gunakan untuk filtering
**capture_flag = 1**: BIB terdeteksi dengan confidence tinggi → data valid untuk finish-line recognition

### Analisis CSV

Gunakan pandas untuk analisis:

```python
import pandas as pd

df = pd.read_csv("tracking_results.csv")

# Total deteksi
print(f"Total rows: {len(df)}")

# Unique person IDs
print(f"Unique tracks: {df['track_id'].nunique()}")

# Unique BIB numbers
print(f"Unique BIBs: {df['bib_number'].nunique()}")

# Filter high-quality captures
good_captures = df[df['capture_flag'] == 1]
print(f"High-confidence captures: {len(good_captures)}")

# Filter non-occluded detections
not_occluded = df[df['occlusion_flag'] == 0]
print(f"Non-occluded detections: {len(not_occluded)}")

# Per-track statistics
per_track = df.groupby('track_id').agg({
    'frame_index': 'count',
    'bib_number': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else None,
    'capture_flag': 'sum'
})
print(per_track)
```

### Performance Notes

- Logging dilakukan **setiap frame** (tidak ada skip) untuk completeness
- File di-flush ke disk immediately setelah setiap write (jaminan data tidak hilang)
- Overhead logging minimal (~0.1-0.2ms per frame)
- File bisa menjadi besar untuk video panjang (~ 5-10 KB per 1000 frame)

## API Reference

### `init_csv_logger(filepath: str) -> dict`
Initialize CSV logger. Creates file with header if baru.

**Parameters:**
- `filepath` (str): Path ke CSV file

**Returns:**
- dict dengan keys 'file' dan 'writer'

**Example:**
```python
logger = logging_csv.init_csv_logger("tracking_results.csv")
```

---

### `log_detection(logger: dict, frame_index: int, timestamp: float, ...)`
Log satu deteksi ke CSV.

**Parameters:**
- `logger` (dict): Dari `init_csv_logger()`
- `frame_index` (int): Frame number
- `timestamp` (float): Elapsed time dalam detik
- `track_id` (int): Unique ID person
- `bib_number` (str): Nomor BIB (atau empty string)
- `bbox` (tuple): (x1, y1, x2, y2)
- `bbox_confidence` (float): Confidence person detection
- `ocr_confidence` (float): Confidence OCR reading
- `occlusion_flag` (int): 1 atau 0
- `capture_flag` (int): 1 atau 0

**Example:**
```python
logging_csv.log_detection(
    logger=csv_logger,
    frame_index=100,
    timestamp=3.33,
    track_id=5,
    bib_number="456",
    bbox=(120, 80, 220, 350),
    bbox_confidence=0.92,
    ocr_confidence=0.88,
    occlusion_flag=0,
    capture_flag=1
)
```

---

### `close_logger(logger: dict) -> None`
Close CSV file handle.

**Example:**
```python
logging_csv.close_logger(csv_logger)
```

---

### `get_logger_stats(filepath: str) -> dict`
Baca CSV dan return statistik ringkas.

**Parameters:**
- `filepath` (str): Path ke CSV file

**Returns:**
- dict dengan keys: `total_rows`, `unique_tracks`, `unique_bibs`, `high_confidence_captures`, `occluded_detections`

**Example:**
```python
stats = logging_csv.get_logger_stats("tracking_results.csv")
print(f"Total detections: {stats['total_rows']}")
```

## Troubleshooting

### CSV file tidak ter-create
- Pastikan direktori write-able
- Cek permissions di `ocr/config.py`

### Data tidak ter-save
- Pastikan `close_logger()` dipanggil sebelum program exit
- File di-flush setiap write, jadi seharusnya aman

### File terlalu besar
- Naikkan `SKIP_OCR_FRAMES` di config untuk reduce frame processing
- Atau gunakan multiple runs dan merge CSV

### Parsing error saat baca CSV
- Pastikan menggunakan correct delimiter (default: comma)
- Use `pd.read_csv()` untuk robust parsing

