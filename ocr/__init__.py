"""OCR package: modular helpers for bib detection and OCR.

This package contains small modules:
- detector: load/run object detector (YOLOv8 wrapper)
- tracker: lightweight IOU tracker
- preprocess: image preprocessing for OCR
- ocr_utils: wrapper for pytesseract/EasyOCR
- logger: CSV logger for results
- config: default parameters

The modules are intentionally small and import-light to keep startup time low.
"""
__all__ = [
    "detector",
    "tracker",
    "preprocess",
    "ocr_utils",
    "logger",
    "config",
]
