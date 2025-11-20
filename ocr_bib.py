from ultralytics import YOLO
import cv2
import os
import numpy as np
from collections import deque, Counter

try:
    import pytesseract
    # 👇 tambahkan baris ini agar Python tahu lokasi Tesseract di Windows
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

# ===============================
# 🔧 CONFIG & HELPER FUNCTIONS
# ===============================

def preprocess_for_ocr(patch):
    """Enhance cropped bib patch to improve OCR accuracy."""
    if patch is None or patch.size == 0:
        return None
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (gray.shape[1] * 2, gray.shape[0] * 2), interpolation=cv2.INTER_LINEAR)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
    th = cv2.medianBlur(th, 3)
    return th


def ocr_read_digits(img):
    """Run OCR on the preprocessed image and return only digit characters."""
    if not TESSERACT_AVAILABLE:
        return ""
    config = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(img, config=config)
    return ''.join(ch for ch in text if ch.isdigit())


# ===============================
# 🎥 MAIN SETUP
# ===============================

video_path = os.path.join("videos", "video_input.mp4")
if not os.path.exists(video_path):
    print("❌ File video tidak ditemukan:", os.path.abspath(video_path))
    exit()

model = YOLO("yolov8n.pt")

# Parameter deteksi
MIN_BIB_AREA = 5000
ASPECT_MIN, ASPECT_MAX = 1.3, 4.0
COLOR_PERSON = (255, 0, 0)
COLOR_BIB = (0, 255, 0)
COLOR_BIB_VALID = (0, 200, 255)  # warna BIB valid (ada angka)
FONT = cv2.FONT_HERSHEY_SIMPLEX
OCR_BUFFER_SIZE = 7
OCR_MIN_DIGITS = 2
ocr_buffers = {}

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("❌ Gagal membuka video.")
    exit()

cv2.namedWindow("YOLOv8 Person + BIB Tracking", cv2.WINDOW_NORMAL)
cv2.resizeWindow("YOLOv8 Person + BIB Tracking", 1280, 720)

print("✅ Mulai deteksi orang + BIB (valid jika ada angka) | Tekan 'q' untuk keluar.")


# NOTE: the main pipeline has been moved to `run.py` in modular form.
# Keep this file as a compatibility launcher.

from run import main

if __name__ == '__main__':
    main()
