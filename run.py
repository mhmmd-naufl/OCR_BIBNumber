"""Entry point to run the modular bib OCR pipeline.

This script wires detector, tracker, preprocess, ocr, and logger modules together.
It intentionally keeps IO and heavy imports inside functions to keep import time low.

Performance options:
- Set SKIP_FRAMES in config.py to skip frames (e.g., 2 = process every 2nd frame)
- Set DISPLAY_SCALE to reduce display resolution for faster rendering

Logging:
- Detection/tracking/OCR results are logged to CSV (tracking_results.csv)
- Configure CSV_OUTPUT_FILE, OCR_CONF_THRESHOLD_CAPTURE, BBOX_CONF_THRESHOLD_OCCLUSION in config.py
"""
import os
import time
import cv2
from collections import deque, Counter
from ocr import detector, tracker as tracker_mod, preprocess, ocr_utils, logger, config, logging_csv


# Global buffer for per-track OCR aggregation
ocr_buffers = {}


def validate_bib_read(text):
    """Simple heuristics to validate OCR read. Return True if plausible bib."""
    if not text or len(text) < config.OCR_MIN_DIGITS:
        return False
    # Reject if leading zeros or very long
    if text[0] == '0' or len(text) > 5:
        return False
    return True


def main(video_path=None, output_csv="ocr_results.csv"):
    video_path = video_path or config.VIDEO_RELATIVE
    if not os.path.exists(video_path):
        print("❌ Video file not found:", os.path.abspath(video_path))
        return

    # load model lazily
    try:
        model = detector.load_model(config.YOLO_MODEL)
    except Exception as e:
        print("Error loading detector:", e)
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Gagal membuka video.")
        return

    # tracker
    tr = tracker_mod.SimpleTracker(max_age=config.TRACKER_MAX_AGE, iou_threshold=config.TRACKER_IOU_THRESH)

    # Initialize CSV logger
    csv_logger = logging_csv.init_csv_logger(config.CSV_OUTPUT_FILE)

    # logger
    f, writer = logger.init_logger(output_csv)

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
        
        # Skip YOLO detection for speed (but tracker still updates every frame)
        if frame_idx % config.SKIP_FRAMES == 0:
            detections = detector.detect_people(frame, model=model, conf_thresh=config.PERSON_CONF_THRESH)
        else:
            detections = []  # No new detections, tracker will age existing tracks
        
        # Tracker ALWAYS updates (every frame) for smooth continuous tracking
        tracks = tr.update(detections)

        for trk in tracks:
            tid = trk['id']
            x1, y1, x2, y2 = map(int, trk['bbox'])
            conf = trk.get('conf', 0.0)

            # draw person
            cv2.rectangle(frame, (x1, y1), (x2, y2), config.COLOR_PERSON, 2)
            cv2.putText(frame, f"ID:{tid} {conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

            # ROI
            roi_y1 = int(y1 + (y2 - y1) * 0.4)
            roi_y2 = int(y1 + (y2 - y1) * 0.9)
            roi = frame[roi_y1:roi_y2, x1:x2]
            if roi.size == 0:
                continue

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5,5), 0)
            edges = cv2.Canny(blur, 40, 120)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                bx, by, bw, bh = cv2.boundingRect(contour)
                area = bw * bh
                aspect = bw / float(bh) if bh>0 else 0
                if area > config.MIN_BIB_AREA and config.ASPECT_MIN < aspect < config.ASPECT_MAX:
                    bib_patch = roi[by:by+bh, bx:bx+bw]
                    
                    # Skip OCR preprocessing on some frames for speed
                    if frame_idx % config.SKIP_OCR_FRAMES == 0:
                        pre = preprocess.preprocess_for_ocr(bib_patch)
                        digits = ocr_utils.ocr_read_digits(pre) if pre is not None else ""
                    else:
                        digits = ""
                    
                    # logging per-track (always, for buffer aggregation)
                    key = f"track_{tid}"
                    buf = ocr_buffers.get(key)
                    if buf is None:
                        buf = deque(maxlen=config.OCR_BUFFER_SIZE)
                        ocr_buffers[key] = buf
                    if digits:
                        buf.append(digits)

                    agg = ""
                    if len(buf)>0:
                        most_common = Counter(buf).most_common(1)[0][0]
                        if validate_bib_read(most_common):
                            agg = most_common

                    color = config.COLOR_BIB_VALID if agg else config.COLOR_BIB
                    label = f"BIB: {agg}" if agg else "BIB?"

                    cv2.rectangle(roi, (bx,by), (bx+bw, by+bh), color, 2)
                    abs_x, abs_y = x1+bx, roi_y1+by
                    cv2.putText(frame, label, (abs_x, abs_y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    # Log to CSV (every frame for completeness)
                    ocr_confidence = 1.0 if agg else 0.0  # High conf if we have aggregated read
                    occlusion_flag = 1 if conf <= config.BBOX_CONF_THRESHOLD_OCCLUSION else 0
                    capture_flag = 1 if ocr_confidence >= config.OCR_CONF_THRESHOLD_CAPTURE else 0
                    
                    logging_csv.log_detection(
                        logger=csv_logger,
                        frame_index=frame_idx,
                        timestamp=time.time() - t_start,
                        track_id=tid,
                        bib_number=agg if agg else "",
                        bbox=(x1, y1, x2, y2),
                        bbox_confidence=conf,
                        ocr_confidence=ocr_confidence,
                        occlusion_flag=occlusion_flag,
                        capture_flag=capture_flag
                    )

        # Display with FPS counter and optional scaling
        if config.DISPLAY_SCALE < 1.0:
            h, w = frame.shape[:2]
            frame_disp = cv2.resize(frame, (int(w * config.DISPLAY_SCALE), int(h * config.DISPLAY_SCALE)))
        else:
            frame_disp = frame
        
        fps_counter.append(time.time() - t_frame)
        fps = len(fps_counter) / (sum(fps_counter) + 1e-6) if fps_counter else 0
        cv2.putText(frame_disp, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow(config.WINDOW_NAME, frame_disp)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    f.close()
    logging_csv.close_logger(csv_logger)
    
    # Print logging statistics
    stats = logging_csv.get_logger_stats(config.CSV_OUTPUT_FILE)
    print(f"\n📊 Logging Summary:")
    print(f"  Total detections: {stats['total_rows']}")
    print(f"  Unique tracks: {stats['unique_tracks']}")
    print(f"  Unique BIBs: {stats['unique_bibs']}")
    print(f"  High-confidence captures: {stats['high_confidence_captures']}")
    print(f"  Occluded detections: {stats['occluded_detections']}")
    print(f"  Results saved to: {config.CSV_OUTPUT_FILE}")
    print("✅ Done.")


if __name__ == '__main__':
    # minimal invocation
    main()
