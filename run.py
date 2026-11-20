"""Entry point to run the modular bib OCR pipeline.

This script wires detector, tracker, preprocess, ocr, and logger modules together.
It intentionally keeps IO and heavy imports inside functions to keep import time low.

Performance options:
- Set SKIP_FRAMES in config.py to skip frames (e.g., 2 = process every 2nd frame)
- Set DISPLAY_SCALE to reduce display resolution for faster rendering
- Set PREPROCESS_USE_NLMEANS=False in config.py to skip the slow NlMeans denoising step

Logging:
- Detection/tracking/OCR results are logged to CSV (tracking_results.csv)
- Configure CSV_OUTPUT_FILE, OCR_CONF_THRESHOLD_CAPTURE, BBOX_CONF_THRESHOLD_OCCLUSION in config.py
- ocr_confidence in CSV is now the real confidence value from the OCR engine (0.0–1.0)
"""
import os
import time
import cv2
from collections import deque, Counter
from ocr import detector, tracker as tracker_mod, preprocess, ocr_utils, config, logging_csv


# Per-track OCR buffers: track_id → deque of (digits, confidence) tuples
ocr_buffers = {}


def validate_bib_read(text):
    """Simple heuristics to validate OCR read. Return True if plausible bib."""
    if not text or len(text) < config.OCR_MIN_DIGITS:
        return False
    # Reject leading zeros or unreasonably long reads
    if text[0] == '0' or len(text) > 5:
        return False
    return True


def _flush_dead_tracks(active_track_ids):
    """Remove ocr_buffers entries for tracks that no longer exist.

    Called once per frame after tracker.update() to prevent unbounded memory growth
    on long videos with many unique athletes.
    """
    dead_keys = [k for k in ocr_buffers if int(k.split("_")[1]) not in active_track_ids]
    for k in dead_keys:
        del ocr_buffers[k]


def main(video_path=None, output_csv="ocr_results.csv"):
    video_path = video_path or config.VIDEO_RELATIVE
    if not os.path.exists(video_path):
        print("❌ Video file not found:", os.path.abspath(video_path))
        return

    # Load model lazily
    try:
        model = detector.load_model(config.YOLO_MODEL)
    except Exception as e:
        print("Error loading detector:", e)
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Gagal membuka video.")
        return

    # Tracker
    tr = tracker_mod.SimpleTracker(max_age=config.TRACKER_MAX_AGE, iou_threshold=config.TRACKER_IOU_THRESH)

    # CSV logger (structured, 12-column)
    csv_logger = logging_csv.init_csv_logger(config.CSV_OUTPUT_FILE)

    cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(config.WINDOW_NAME, *config.WINDOW_SIZE)

    frame_idx = 0
    print("✅ Pipeline started. Press 'q' to quit.")
    fps_counter = deque(maxlen=30)
    t_start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        t_frame = time.time()

        # YOLO detection — skip frames for performance
        if frame_idx % config.SKIP_FRAMES == 0:
            detections = detector.detect_people(frame, model=model, conf_thresh=config.PERSON_CONF_THRESH)
        else:
            detections = []

        # Tracker updates every frame for smooth continuous tracking
        tracks = tr.update(detections)

        # Clean up buffers for dead tracks (fix memory leak)
        active_ids = {trk['id'] for trk in tracks}
        _flush_dead_tracks(active_ids)

        for trk in tracks:
            tid = trk['id']
            x1, y1, x2, y2 = map(int, trk['bbox'])
            conf = trk.get('conf', 0.0)

            # Draw person bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), config.COLOR_PERSON, 2)
            cv2.putText(frame, f"ID:{tid} {conf:.2f}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Crop chest ROI (40–90% of bounding box height)
            roi_y1 = int(y1 + (y2 - y1) * 0.4)
            roi_y2 = int(y1 + (y2 - y1) * 0.9)
            roi = frame[roi_y1:roi_y2, x1:x2]
            if roi.size == 0:
                continue

            # Canny + contour heuristic to find bib rectangle inside ROI
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 40, 120)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                bx, by, bw, bh = cv2.boundingRect(contour)
                area = bw * bh
                aspect = bw / float(bh) if bh > 0 else 0
                if area > config.MIN_BIB_AREA and config.ASPECT_MIN < aspect < config.ASPECT_MAX:
                    bib_patch = roi[by:by + bh, bx:bx + bw]

                    # OCR — skip some frames for performance
                    raw_digits = ""
                    raw_conf = 0.0
                    if frame_idx % config.SKIP_OCR_FRAMES == 0:
                        pre = preprocess.preprocess_for_ocr(bib_patch)
                        if pre is not None:
                            raw_digits, raw_conf = ocr_utils.ocr_read_digits_with_conf(pre)

                    # Per-track temporal buffer: accumulate (digits, confidence) pairs
                    key = f"track_{tid}"
                    if key not in ocr_buffers:
                        ocr_buffers[key] = deque(maxlen=config.OCR_BUFFER_SIZE)
                    if raw_digits:
                        ocr_buffers[key].append((raw_digits, raw_conf))

                    # Aggregate: weighted vote — reads with higher confidence weigh more
                    agg = ""
                    agg_conf = 0.0
                    buf = ocr_buffers[key]
                    if buf:
                        # Sum confidence per unique digit string
                        vote_weights = {}
                        for d, c in buf:
                            vote_weights[d] = vote_weights.get(d, 0.0) + c
                        best = max(vote_weights, key=vote_weights.get)
                        if validate_bib_read(best):
                            agg = best
                            # Average confidence of all reads that voted for this result
                            votes_for_best = [c for d, c in buf if d == best]
                            agg_conf = sum(votes_for_best) / len(votes_for_best)

                    # Draw bib box and label
                    color = config.COLOR_BIB_VALID if agg else config.COLOR_BIB
                    label = f"BIB: {agg}" if agg else "BIB?"
                    cv2.rectangle(roi, (bx, by), (bx + bw, by + bh), color, 2)
                    abs_x, abs_y = x1 + bx, roi_y1 + by
                    cv2.putText(frame, label, (abs_x, abs_y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    # Log to CSV with real OCR confidence
                    occlusion_flag = 1 if conf <= config.BBOX_CONF_THRESHOLD_OCCLUSION else 0
                    capture_flag = 1 if agg_conf >= config.OCR_CONF_THRESHOLD_CAPTURE else 0

                    logging_csv.log_detection(
                        logger=csv_logger,
                        frame_index=frame_idx,
                        timestamp=time.time() - t_start,
                        track_id=tid,
                        bib_number=agg,
                        bbox=(x1, y1, x2, y2),
                        bbox_confidence=conf,
                        ocr_confidence=agg_conf,
                        occlusion_flag=occlusion_flag,
                        capture_flag=capture_flag
                    )

        # Display with optional scaling and FPS overlay
        if config.DISPLAY_SCALE < 1.0:
            h, w = frame.shape[:2]
            frame_disp = cv2.resize(frame, (int(w * config.DISPLAY_SCALE), int(h * config.DISPLAY_SCALE)))
        else:
            frame_disp = frame

        fps_counter.append(time.time() - t_frame)
        fps = len(fps_counter) / (sum(fps_counter) + 1e-6) if fps_counter else 0
        cv2.putText(frame_disp, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow(config.WINDOW_NAME, frame_disp)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    logging_csv.close_logger(csv_logger)

    # Print end-of-run summary
    stats = logging_csv.get_logger_stats(config.CSV_OUTPUT_FILE)
    print(f"\n📊 Logging Summary:")
    print(f"  Total detections : {stats['total_rows']}")
    print(f"  Unique tracks    : {stats['unique_tracks']}")
    print(f"  Unique BIBs      : {stats['unique_bibs']}")
    print(f"  High-conf captures: {stats['high_confidence_captures']}")
    print(f"  Occluded detections: {stats['occluded_detections']}")
    print(f"  Results saved to : {config.CSV_OUTPUT_FILE}")
    print("✅ Done.")


if __name__ == '__main__':
    main()

