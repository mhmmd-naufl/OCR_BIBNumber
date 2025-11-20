"""CSV Logging module for BIB detection, tracking, and OCR results.

This module handles writing detection/tracking/OCR results to a CSV file.
Automatically creates file with header if it doesn't exist, and appends new records.

Usage:
    logger = init_csv_logger("tracking_results.csv")
    log_detection(logger, frame_index=0, timestamp=0.0, track_id=1, bib_number="123", ...)
    close_logger(logger)
"""
import csv
import os
from datetime import datetime
from typing import Optional, Tuple


def init_csv_logger(filepath: str) -> dict:
    """Initialize CSV logger. Creates file with header if it doesn't exist.
    
    Args:
        filepath: Path to CSV file (e.g., "tracking_results.csv")
    
    Returns:
        dict with 'file' and 'writer' for use in log_detection()
    """
    file_exists = os.path.exists(filepath)
    
    # Open file in append mode
    f = open(filepath, 'a', newline='', encoding='utf-8')
    writer = csv.DictWriter(f, fieldnames=[
        'frame_index', 'timestamp', 'track_id', 'bib_number',
        'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2',
        'bbox_confidence', 'ocr_confidence',
        'occlusion_flag', 'capture_flag'
    ])
    
    # Write header only if file is new
    if not file_exists:
        writer.writeheader()
        print(f"✅ CSV logger initialized: {filepath}")
    else:
        print(f"✅ CSV logger appending to: {filepath}")
    
    return {'file': f, 'writer': writer}


def log_detection(
    logger: dict,
    frame_index: int,
    timestamp: float,
    track_id: int,
    bib_number: str,
    bbox: Tuple[int, int, int, int],  # (x1, y1, x2, y2)
    bbox_confidence: float,
    ocr_confidence: float,
    occlusion_flag: int = 0,
    capture_flag: int = 0
) -> None:
    """Log a single detection to CSV.
    
    Args:
        logger: dict from init_csv_logger()
        frame_index: Frame number in video
        timestamp: Time elapsed since video start (seconds)
        track_id: Unique tracking ID for person
        bib_number: Detected BIB number (string, e.g., "123")
        bbox: Bounding box tuple (x1, y1, x2, y2)
        bbox_confidence: Confidence of person detection (0.0-1.0)
        ocr_confidence: Confidence of OCR reading (0.0-1.0)
        occlusion_flag: 1 if bbox_confidence <= 0.6 (occluded), 0 otherwise
        capture_flag: 1 if ocr_confidence > 0.7 (good read), 0 otherwise
    """
    x1, y1, x2, y2 = bbox
    
    row = {
        'frame_index': frame_index,
        'timestamp': round(timestamp, 3),  # ms precision
        'track_id': track_id,
        'bib_number': bib_number if bib_number else "",
        'bbox_x1': x1,
        'bbox_y1': y1,
        'bbox_x2': x2,
        'bbox_y2': y2,
        'bbox_confidence': round(bbox_confidence, 4),
        'ocr_confidence': round(ocr_confidence, 4),
        'occlusion_flag': int(occlusion_flag),
        'capture_flag': int(capture_flag)
    }
    
    logger['writer'].writerow(row)
    logger['file'].flush()  # Force write to disk immediately


def close_logger(logger: dict) -> None:
    """Close CSV file handle."""
    if logger and logger.get('file'):
        logger['file'].close()
        print("✅ CSV logger closed.")


def get_logger_stats(filepath: str) -> dict:
    """Read CSV and return simple statistics.
    
    Args:
        filepath: Path to CSV file
    
    Returns:
        dict with counts (total_rows, unique_tracks, unique_bibs, etc.)
    """
    if not os.path.exists(filepath):
        return {'total_rows': 0, 'error': f'File not found: {filepath}'}
    
    stats = {
        'total_rows': 0,
        'unique_tracks': set(),
        'unique_bibs': set(),
        'high_confidence_captures': 0,
        'occluded_detections': 0
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_rows'] += 1
                stats['unique_tracks'].add(row['track_id'])
                if row['bib_number']:
                    stats['unique_bibs'].add(row['bib_number'])
                if int(row['capture_flag']) == 1:
                    stats['high_confidence_captures'] += 1
                if int(row['occlusion_flag']) == 1:
                    stats['occluded_detections'] += 1
        
        # Convert sets to counts
        stats['unique_tracks'] = len(stats['unique_tracks'])
        stats['unique_bibs'] = len(stats['unique_bibs'])
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats
