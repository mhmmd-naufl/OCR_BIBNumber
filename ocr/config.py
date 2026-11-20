# Video / model paths
VIDEO_RELATIVE = "videos/video_input.mp4"
YOLO_MODEL = "yolov8n.pt"  # default YOLOv8 small model name (ultralytics)

# Detection / ROI
MIN_BIB_AREA = 5000
ASPECT_MIN = 1.3
ASPECT_MAX = 4.0
PERSON_CONF_THRESH = 0.5

# OCR
OCR_BUFFER_SIZE = 10  # increased from 7 for better consistency
OCR_MIN_DIGITS = 2

# OCR Engine Confidence & Ensemble
OCR_EASYOCR_CONFIDENCE_THRESHOLD = 0.3  # only accept EasyOCR detections above this confidence (0.0-1.0)
OCR_USE_ENSEMBLE = True  # if True, ensemble vote between EasyOCR and pytesseract

# Preprocessing Tuning (aggressive for better accuracy)
PREPROCESS_DENOISE_H = 10  # fastNlMeansDenoising h parameter (higher = more denoise, slower)
PREPROCESS_CLAHE_CLIP = 4.0  # CLAHE clipLimit (higher = more contrast)
PREPROCESS_BILATERAL_D = 9  # bilateral filter diameter
PREPROCESS_BILATERAL_SIGMA_COLOR = 100  # bilateral sigma color
PREPROCESS_BILATERAL_SIGMA_SPACE = 100  # bilateral sigma space
PREPROCESS_THRESH_BLOCK = 13  # adaptive threshold block size (must be odd)
PREPROCESS_THRESH_CONST = 2  # adaptive threshold constant
PREPROCESS_MEDIAN_KERNEL = 5  # median blur kernel size (must be odd)

# Tracker
TRACKER_MAX_AGE = 30
TRACKER_IOU_THRESH = 0.3

# Performance tuning
SKIP_FRAMES = 1  # process YOLO detection every N frames (1=every frame, 2=every 2nd, etc)
SKIP_OCR_FRAMES = 3  # run OCR preprocessing every N frames (can be slower; tracker updates every frame)
DISPLAY_SCALE = 0.75  # scale down display for faster rendering (0.75 = 75% size)
USE_GPU = False  # set True if you have CUDA GPU — used by EasyOCR and YOLO

# Preprocessing performance vs accuracy trade-off
# fastNlMeansDenoising is very slow on 4× upscaled images (~100–200ms per patch on CPU).
# Set False to skip it and rely on CLAHE + bilateral only (much faster, slight accuracy drop).
PREPROCESS_USE_NLMEANS = True

# Display colors (BGR format)
COLOR_PERSON = (255, 0, 0)        # blue for person bbox
COLOR_BIB = (0, 255, 0)           # green for bib candidate (no read)
COLOR_BIB_VALID = (0, 200, 255)   # orange for bib with valid read
FONT = "HERSHEY_SIMPLEX"

# Display window
WINDOW_NAME = "YOLOv8 Person + BIB Tracking"
WINDOW_SIZE = (1280, 720)

# CSV Logging
CSV_OUTPUT_FILE = "tracking_results.csv"  # CSV file for logging detections
OCR_CONF_THRESHOLD_CAPTURE = 0.7  # OCR confidence threshold for capture_flag (set to 1 if >= this)
BBOX_CONF_THRESHOLD_OCCLUSION = 0.6  # BBox confidence threshold for occlusion_flag (set to 1 if <= this)
