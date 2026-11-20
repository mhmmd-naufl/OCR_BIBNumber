"""Preprocessing utilities for Bib OCR patches.

Expose `preprocess_for_ocr(patch)` which returns a binary/masked image ready for OCR.
Optimized for high accuracy with aggressive denoise, upscale ×4, and sharpening.
"""
import cv2
import numpy as np
from ocr import config


def preprocess_for_ocr(patch):
    """Aggressive preprocessing for better OCR accuracy on bib patches."""
    if patch is None or patch.size == 0:
        return None
    try:
        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    except Exception:
        gray = patch if len(patch.shape) == 2 else cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

    # Upscale ×4 (instead of ×2) for better OCR accuracy
    h, w = gray.shape[:2]
    scale = 4
    gray = cv2.resize(gray, (max(32, w * scale), max(32, h * scale)), interpolation=cv2.INTER_CUBIC)

    # Aggressive denoise: Non-Local Means (removes noise while preserving edges)
    # Controlled by config.PREPROCESS_USE_NLMEANS — disable for faster CPU performance
    if config.PREPROCESS_USE_NLMEANS:
        gray = cv2.fastNlMeansDenoising(gray, h=config.PREPROCESS_DENOISE_H, templateWindowSize=7, searchWindowSize=21)

    # CLAHE (Contrast Limited Adaptive Histogram Equalization) with higher clip limit
    clahe = cv2.createCLAHE(clipLimit=config.PREPROCESS_CLAHE_CLIP, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Bilateral filter for edge-preserving denoise
    gray = cv2.bilateralFilter(gray, config.PREPROCESS_BILATERAL_D, config.PREPROCESS_BILATERAL_SIGMA_COLOR, config.PREPROCESS_BILATERAL_SIGMA_SPACE)

    # Sharpen image for crisper text (unsharp mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    gray = np.clip(gray, 0, 255).astype(np.uint8)

    # Adaptive threshold (more aggressive)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, config.PREPROCESS_THRESH_BLOCK, config.PREPROCESS_THRESH_CONST)

    # Morphological open to remove small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)

    # Median blur to smooth
    th = cv2.medianBlur(th, config.PREPROCESS_MEDIAN_KERNEL)
    return th
