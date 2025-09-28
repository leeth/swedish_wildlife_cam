# Wildlife Image Pipeline (Python)

A minimal, production‑friendly starter to:
- Read images from a folder structure organized per **camera**
- Extract metadata (EXIF + filesystem timestamps)
- Run a **pluggable detector** (YOLO by default) to classify wildlife observations
- Output a dataset (CSV/Parquet) with:
  - `image_path`
  - `camera_id`
  - `timestamp`
  - `observation_any` (bool)
  - `observations` (JSON list of `{label, confidence, bbox}`)
  - `top_label`, `top_confidence`

## Folder structure (input)

### Images
```
/path/to/images/
  camera_A/
    2025-08-01/
      IMG_0001.JPG
      IMG_0002.JPG
  camera_B/
    IMG_1001.JPG
```

### Videos (NEW!)
```
/path/to/videos/
  camera_A/
    2025-08-01/
      video_001.mp4
      video_002.avi
  camera_B/
    video_003.mov
```

> The pipeline infers `camera_id` from the first folder below the root (e.g., `camera_A`).
> Videos are processed by extracting frames at regular intervals for wildlife detection.

## Quickstart

```bash
# 1) Create & activate venv (example for bash)
python -m venv .venv
source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) (Optional) Test ultralytics is available
python -c "import ultralytics; print('ultralytics ok')"

# 4) Run pipeline on images
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/images \
  --output /path/to/output.csv \
  --model megadetector \
  --conf-thres 0.35

# 5) Run pipeline on videos (NEW!)
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/videos \
  --output /path/to/output.csv \
  --model megadetector \
  --process-videos \
  --frame-interval 30 \
  --max-frames 100
```

### Notes on models
- **Swedish Wildlife Detector** (`--model megadetector`): Optimized for Swedish wildlife (moose, boar, roe deer, fox, badger)
- **Default YOLO detector** (`--model yolov8n.pt`): Generic object detection with custom class mapping
- You can use any `.pt` model compatible with `ultralytics` (e.g., a Roboflow wildlife model)

### Video Processing (NEW!)
- **Frame extraction**: Videos are processed by extracting frames at regular intervals
- **Supported formats**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- **Frame interval**: Control how often frames are extracted (default: every 30th frame)
- **Max frames**: Limit frames per video for performance (default: 100)
- **Output**: Video summaries + individual frame detections

### Output
- Choose `--write csv` or `--write parquet`.
- Each row summarizes detections per image and stores the raw detection list as JSON for later analysis.

### Cursor (AI IDE) tips
- Open this folder in **Cursor**.
- Start with `src/wildlife_pipeline/detector.py` and `run_pipeline.py`.
- Use Cursor’s “Ask” or “Fix” on specific functions to iterate quickly.
- Add tests later (e.g., `pytest`) as you stabilize the schema.

## Roadmap
- Add model auto‑download & caching
- Batch inference with GPU/FP16
- Optional **Megadetector** adapter (camera‑trap optimized animal/person/vehicle classifier)
- Telegram/Slack notifications for specific species
- Streamlit dashboard for reviewing predictions
