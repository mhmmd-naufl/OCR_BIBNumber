"""Utility script to analyze tracking_results.csv.

Usage:
    python analyze_csv.py [--file tracking_results.csv] [--stats] [--filter-capture] [--export]
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict


def read_csv(filepath):
    """Read CSV and return list of rows."""
    rows = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        sys.exit(1)
    return rows


def analyze_basic_stats(rows):
    """Print basic statistics."""
    if not rows:
        print("❌ No data in CSV")
        return
    
    print("\n📊 === BASIC STATISTICS ===")
    print(f"Total detections: {len(rows)}")
    
    unique_frames = set()
    unique_tracks = set()
    unique_bibs = set()
    high_conf_captures = 0
    occluded = 0
    
    for row in rows:
        unique_frames.add(row['frame_index'])
        unique_tracks.add(row['track_id'])
        if row['bib_number']:
            unique_bibs.add(row['bib_number'])
        if int(row['capture_flag']) == 1:
            high_conf_captures += 1
        if int(row['occlusion_flag']) == 1:
            occluded += 1
    
    print(f"Unique frames: {len(unique_frames)}")
    print(f"Unique tracks: {len(unique_tracks)}")
    print(f"Unique BIB numbers: {len(unique_bibs)}")
    print(f"High-confidence captures: {high_conf_captures}")
    print(f"Occluded detections: {occluded}")
    print(f"Average bbox confidence: {sum(float(r['bbox_confidence']) for r in rows) / len(rows):.4f}")
    print(f"Average OCR confidence: {sum(float(r['ocr_confidence']) if r['ocr_confidence'] else 0 for r in rows) / len(rows):.4f}")


def analyze_per_track(rows):
    """Print per-track statistics."""
    print("\n📊 === PER-TRACK STATISTICS ===")
    
    track_stats = defaultdict(lambda: {
        'count': 0,
        'bib': None,
        'captures': 0,
        'occluded': 0,
        'avg_conf': 0,
        'frames': []
    })
    
    for row in rows:
        tid = row['track_id']
        track_stats[tid]['count'] += 1
        track_stats[tid]['frames'].append(int(row['frame_index']))
        
        if row['bib_number']:
            track_stats[tid]['bib'] = row['bib_number']
        
        track_stats[tid]['captures'] += int(row['capture_flag'])
        track_stats[tid]['occluded'] += int(row['occlusion_flag'])
        track_stats[tid]['avg_conf'] += float(row['bbox_confidence'])
    
    # Calculate averages
    for tid in track_stats:
        count = track_stats[tid]['count']
        track_stats[tid]['avg_conf'] /= count
        frames = sorted(track_stats[tid]['frames'])
        duration = frames[-1] - frames[0] if len(frames) > 1 else 0
        track_stats[tid]['duration'] = duration
    
    # Print sorted by track ID
    print(f"{'Track ID':<10} {'BIB':<10} {'Frames':<8} {'Captures':<10} {'Occluded':<10} {'Avg Conf':<10} {'Duration'}")
    print("-" * 70)
    for tid in sorted(track_stats.keys(), key=lambda x: int(x)):
        stat = track_stats[tid]
        bib = stat['bib'] if stat['bib'] else "N/A"
        print(f"{tid:<10} {bib:<10} {stat['count']:<8} {stat['captures']:<10} {stat['occluded']:<10} {stat['avg_conf']:<10.4f} {stat['duration']}")


def filter_high_conf_captures(rows):
    """Filter and print high-confidence captures only."""
    print("\n📊 === HIGH-CONFIDENCE CAPTURES ===")
    captures = [r for r in rows if int(r['capture_flag']) == 1]
    
    print(f"Total high-conf captures: {len(captures)}")
    
    if captures:
        # Group by BIB
        by_bib = defaultdict(list)
        for row in captures:
            bib = row['bib_number']
            if bib:
                by_bib[bib].append(row)
        
        print(f"\nFirst detections per BIB:")
        for bib in sorted(by_bib.keys()):
            rows_per_bib = by_bib[bib]
            first = rows_per_bib[0]
            print(f"  BIB {bib}: Frame {first['frame_index']}, Track {first['track_id']}, Time {first['timestamp']}s")


def export_filtered_csv(rows, output_file, filter_capture=False):
    """Export filtered rows to new CSV."""
    if filter_capture:
        rows = [r for r in rows if int(r['capture_flag']) == 1]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if rows:
                fieldnames = rows[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        print(f"✅ Exported {len(rows)} rows to {output_file}")
    except Exception as e:
        print(f"❌ Error exporting CSV: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze tracking_results.csv")
    parser.add_argument('--file', default='tracking_results.csv', help='CSV file path')
    parser.add_argument('--stats', action='store_true', help='Print basic statistics')
    parser.add_argument('--per-track', action='store_true', help='Print per-track statistics')
    parser.add_argument('--captures', action='store_true', help='Filter and print high-conf captures')
    parser.add_argument('--export', help='Export filtered CSV to file')
    parser.add_argument('--filter-capture', action='store_true', help='Export only high-conf captures')
    parser.add_argument('--all', action='store_true', help='Run all analyses')
    
    args = parser.parse_args()
    
    # Read CSV
    rows = read_csv(args.file)
    print(f"✅ Loaded {len(rows)} rows from {args.file}")
    
    # Run analyses
    if args.all or args.stats or (not args.per_track and not args.captures and not args.export):
        analyze_basic_stats(rows)
    
    if args.all or args.per_track:
        analyze_per_track(rows)
    
    if args.all or args.captures:
        filter_high_conf_captures(rows)
    
    if args.export:
        export_filtered_csv(rows, args.export, filter_capture=args.filter_capture)


if __name__ == '__main__':
    main()
