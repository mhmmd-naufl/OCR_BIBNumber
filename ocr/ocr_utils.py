"""OCR wrappers and helpers.

This module prefers EasyOCR (if installed) for digit recognition with confidence filtering
and ensemble voting, falling back to pytesseract when EasyOCR is not available.
The public function `ocr_read_digits(img)` returns a digits-only string (or empty string).
"""
from typing import Optional
import cv2
from collections import Counter

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception:
    easyocr = None
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    TESSERACT_AVAILABLE = False


_easyocr_reader = None


def _get_easyocr_reader(lang_list=("en",), gpu=False):
    global _easyocr_reader
    if _easyocr_reader is None:
        # Create reader lazily (may be heavy because it loads torch)
        _easyocr_reader = easyocr.Reader(list(lang_list), gpu=gpu)
    return _easyocr_reader


def _ocr_easyocr_with_confidence(img, conf_threshold=0.3) -> str:
    """Use EasyOCR with confidence filtering. Only accept high-confidence detections."""
    try:
        reader = _get_easyocr_reader(gpu=False)
        # detail=1 returns list of (text, confidence) tuples
        results = reader.readtext(img, detail=1, paragraph=False)
        if not results:
            return ""
        # Filter by confidence threshold and extract digits
        high_conf_texts = [text for text, conf in results if conf >= conf_threshold]
        if not high_conf_texts:
            return ""
        text = "".join(high_conf_texts)
        return ''.join(ch for ch in text if ch.isdigit())
    except Exception:
        return ""


def _ocr_pytesseract(img) -> str:
    """Use pytesseract for OCR (fallback or ensemble)."""
    try:
        config = "--psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(img, config=config)
        return ''.join(ch for ch in text if ch.isdigit())
    except Exception:
        return ""


def ocr_read_digits(img) -> str:
    """Return digits read from image using ensemble voting.

    Tries EasyOCR (confidence-filtered) and pytesseract. If both return non-empty,
    uses majority voting. Otherwise returns the non-empty result (or empty if all fail).
    """
    if img is None:
        return ""

    # Ensure image is in a format EasyOCR/pytesseract expect (RGB or grayscale)
    try:
        if len(img.shape) == 3 and img.shape[2] == 3:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = img
    except Exception:
        img_rgb = img

    # Collect results from both engines (ensemble)
    easyocr_result = ""
    if EASYOCR_AVAILABLE:
        easyocr_result = _ocr_easyocr_with_confidence(img_rgb, conf_threshold=0.3)

    pytesseract_result = ""
    if TESSERACT_AVAILABLE:
        pytesseract_result = _ocr_pytesseract(img_rgb)

    # Ensemble voting: if both return results, prefer the one with more digits or majority vote
    if easyocr_result and pytesseract_result:
        # If both are the same, return it
        if easyocr_result == pytesseract_result:
            return easyocr_result
        # If different, prefer longer result (more likely to be complete)
        return easyocr_result if len(easyocr_result) >= len(pytesseract_result) else pytesseract_result

    # Return whichever is available
    return easyocr_result or pytesseract_result
