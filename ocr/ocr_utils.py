"""OCR wrappers and helpers.

This module prefers EasyOCR (if installed) for digit recognition with confidence filtering
and ensemble voting, falling back to pytesseract when EasyOCR is not available.
The public function `ocr_read_digits(img)` returns a digits-only string (or empty string).

Ensemble strategy:
- If both engines return the same result → return it (high confidence)
- If both disagree → return the one with higher per-read confidence (EasyOCR wins on tie)
- If only one returns a result → return that one
- Real EasyOCR confidence (avg per detection) is returned alongside the text via
  ocr_read_digits_with_conf() for use in CSV logging.
"""
import cv2
from ocr import config as ocr_config

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
        _easyocr_reader = easyocr.Reader(list(lang_list), gpu=gpu)
    return _easyocr_reader


def _ocr_easyocr_with_confidence(img, conf_threshold=0.3):
    """Use EasyOCR with confidence filtering.

    EasyOCR readtext() returns a list of 3-tuples: (bbox, text, confidence).
    Returns (digits_string, avg_confidence).
    """
    try:
        reader = _get_easyocr_reader(gpu=ocr_config.USE_GPU)
        # detail=1 → list of (bbox, text, confidence)
        results = reader.readtext(img, detail=1, paragraph=False)
        if not results:
            return "", 0.0

        filtered = [(text, conf) for (_bbox, text, conf) in results if conf >= conf_threshold]
        if not filtered:
            return "", 0.0

        digits = ''.join(ch for text, _ in filtered for ch in text if ch.isdigit())
        avg_conf = sum(conf for _, conf in filtered) / len(filtered)
        return digits, avg_conf
    except Exception:
        return "", 0.0


def _ocr_pytesseract(img):
    """Use pytesseract for OCR (digits only). Returns (digits_string, confidence).

    Tesseract does not expose per-character confidence easily via image_to_string,
    so confidence is fixed at 0.5 when a result is found (used only for tie-breaking).
    """
    try:
        cfg = "--psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(img, config=cfg)
        digits = ''.join(ch for ch in text if ch.isdigit())
        return (digits, 0.5) if digits else ("", 0.0)
    except Exception:
        return "", 0.0


def ocr_read_digits_with_conf(img):
    """Return (digits, confidence) using ensemble of available OCR engines.

    confidence is a float 0.0–1.0 reflecting how reliable the read is:
    - 1.0  : both engines agree
    - avg  : only EasyOCR result used (its avg detection confidence)
    - 0.5  : only Tesseract result used
    - 0.0  : no result
    """
    if img is None:
        return "", 0.0

    # EasyOCR expects RGB; preprocess output is grayscale binary — pass as-is
    # (both EasyOCR and Tesseract handle single-channel images)
    try:
        if len(img.shape) == 3 and img.shape[2] == 3:
            img_in = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img_in = img
    except Exception:
        img_in = img

    easy_digits, easy_conf = ("", 0.0)
    if EASYOCR_AVAILABLE and ocr_config.USE_GPU is not None:
        easy_digits, easy_conf = _ocr_easyocr_with_confidence(
            img_in, conf_threshold=ocr_config.OCR_EASYOCR_CONFIDENCE_THRESHOLD
        )

    tess_digits, tess_conf = ("", 0.0)
    if TESSERACT_AVAILABLE:
        tess_digits, tess_conf = _ocr_pytesseract(img_in)

    # Ensemble decision
    if not ocr_config.OCR_USE_ENSEMBLE:
        # Ensemble disabled: prefer EasyOCR, fall back to Tesseract
        if easy_digits:
            return easy_digits, easy_conf
        return tess_digits, tess_conf

    if easy_digits and tess_digits:
        if easy_digits == tess_digits:
            # Perfect agreement → boost confidence to 1.0
            return easy_digits, 1.0
        # Disagreement → pick the engine with higher confidence
        if easy_conf >= tess_conf:
            return easy_digits, easy_conf
        return tess_digits, tess_conf

    # Only one engine returned a result
    if easy_digits:
        return easy_digits, easy_conf
    return tess_digits, tess_conf


def ocr_read_digits(img) -> str:
    """Convenience wrapper — returns digits string only (drops confidence).

    Use ocr_read_digits_with_conf() when you need the confidence value.
    """
    digits, _ = ocr_read_digits_with_conf(img)
    return digits
