"""Simple CSV logger for OCR results.

Functions:
- init_logger(path): create/open CSV with header
- log_row(path, row_dict): append a row
"""
import csv
import os

FIELDNAMES = ["frame", "track_id", "bbox", "raw_read", "aggregated_read", "timestamp"]


def init_logger(path):
    dirp = os.path.dirname(path)
    if dirp and not os.path.exists(dirp):
        os.makedirs(dirp, exist_ok=True)
    exists = os.path.exists(path)
    f = open(path, "a", newline='', encoding='utf-8')
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if not exists:
        writer.writeheader()
    return f, writer


def log_row(writer, row_dict):
    # row_dict must have keys matching FIELDNAMES
    writer.writerow(row_dict)
    try:
        writer._csv.writerows([])
    except Exception:
        pass
