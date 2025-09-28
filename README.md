# Odins Ravne 🐦‍⬛

*"Munin brings memories home, Hugin brings thoughts to mind"*

A production-ready, cloud-optional wildlife detection pipeline inspired by Odin's ravens from Norse mythology. Just as Munin (Memory) and Hugin (Thought) served as Odin's eyes and ears, this pipeline serves as your intelligent observer in the wild.

## The Story of Odin's Ravens

In Norse mythology, Odin had two ravens:
- **Munin** (Memory) - The raven who brings back memories and data from the world
- **Hugin** (Thought) - The raven who brings back thoughts and insights

Our pipeline follows this ancient wisdom:

### Munin - The Memory Keeper (Stage 0-2)
*"Munin brings memories home"*
- **Data Ingestion**: Collects raw camera trap data
- **Metadata Extraction**: Preserves EXIF, GPS, and temporal information  
- **Storage**: Safely stores memories in Parquet and manifest files
- **Stage 1**: Detects wildlife and crops regions of interest
- **Stage 2**: Classifies detected animals with confidence

### Hugin - The Thought Bringer (Stage 2+)
*"Hugin brings thoughts to mind"*
- **Analysis**: Processes and interprets the collected memories
- **Insights**: Generates patterns, trends, and behavioral analysis
- **Reporting**: Compresses observations and creates meaningful reports
- **Intelligence**: Provides actionable insights from the data

## What Odins Ravne Does
- Processes images and videos from camera trap data
- Extracts metadata (EXIF + filesystem timestamps + GPS coordinates)
- Runs a **two-stage pipeline**: Stage-1 detection + Stage-2 classification
- Supports **local and cloud execution** with interchangeable adapters
- Outputs structured data (Parquet + manifest files) with:
  - `image_path`, `camera_id`, `timestamp`, `latitude`, `longitude`
  - `observation_any` (bool), `observations` (JSON list of detections)
  - `top_label`, `top_confidence`, `needs_review` (bool)
  - `pipeline_version`, `model_hashes`, `source_etag`

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

### Local Execution

```bash
# 1) Create & activate venv
python -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run Munin Stage-1: Detection and cropping (Memory)
munin-stage1 \
  --profile local \
  --input file://./data/images \
  --output file://./results

# 4) Run Munin Stage-2: Classification (Memory)
munin-stage2 \
  --profile local \
  --manifest file://./results/stage1/manifest.jsonl \
  --output file://./results

# 5) Run Hugin Stage-3: Reporting and compression (Thought)
hugin-stage3 \
  --profile local \
  --manifest file://./results/stage1/manifest.jsonl \
  --predictions file://./results/stage2/predictions.jsonl \
  --output file://./results

# 6) Materialize results to Parquet
munin-materialize \
  --profile local \
  --manifest file://./results/stage1/manifest.jsonl \
  --output file://./results/final.parquet
```

### Cloud Execution (AWS)

```bash
# 1) Deploy infrastructure
aws cloudformation create-stack \
  --stack-name wildlife-detection \
  --template-body file://aws/cloudformation-template.yaml

# 2) Build and push Docker image
docker build -f docker/Dockerfile.aws-gpu -t wildlife-detection:latest .
docker push your-account.dkr.ecr.eu-north-1.amazonaws.com/wildlife-detection:latest

# 3) Run Munin Stage-1: Detection with GPU acceleration (Memory)
munin-stage1 \
  --profile cloud \
  --input s3://wildlife-detection-bucket/data \
  --output s3://wildlife-detection-bucket/results

# 4) Run Munin Stage-2: Classification (Memory)
munin-stage2 \
  --profile cloud \
  --manifest s3://wildlife-detection-bucket/results/stage1/manifest.jsonl \
  --output s3://wildlife-detection-bucket/results

# 5) Run Hugin Stage-3: Reporting and compression (Thought)
hugin-stage3 \
  --profile cloud \
  --manifest s3://wildlife-detection-bucket/results/stage1/manifest.jsonl \
  --predictions s3://wildlife-detection-bucket/results/stage2/predictions.jsonl \
  --output s3://wildlife-detection-bucket/results

# 6) Materialize results
munin-materialize \
  --profile cloud \
  --manifest s3://wildlife-detection-bucket/results/stage1/manifest.jsonl \
  --output s3://wildlife-detection-bucket/results/final.parquet
```

## The Wisdom of Odin's Ravens

### Munin - The Memory Keeper
*"Munin brings memories home"*

Munin is responsible for collecting and preserving all the raw data from your camera traps:

- **Data Ingestion**: Efficiently processes thousands of images and videos
- **Metadata Preservation**: Extracts and stores EXIF data, GPS coordinates, timestamps
- **Quality Control**: Filters out poor quality detections and routes doubtful cases for review
- **Storage**: Safely stores all memories in structured formats (Parquet, manifest files)
- **Stage 1**: Detects wildlife and crops regions of interest
- **Stage 2**: Classifies detected animals with confidence scores

### Hugin - The Thought Bringer  
*"Hugin brings thoughts to mind"*

Hugin processes the memories collected by Munin and transforms them into actionable insights:

- **Pattern Recognition**: Identifies behavioral patterns and movement trends
- **Temporal Analysis**: Compresses observations to avoid duplicate logging
- **Spatial Intelligence**: Analyzes GPS data for habitat usage patterns
- **Reporting**: Generates comprehensive reports and analytics
- **Insights**: Provides actionable intelligence from the collected data

## Architecture

### Cloud-Optional Design
The pipeline supports both local and cloud execution through interchangeable adapters:

- **Storage**: Local filesystem ↔ S3/GCS
- **Queue**: None/Redis ↔ SQS/PubSub  
- **Compute**: Local threads ↔ AWS Batch/Cloud Run
- **Models**: Local cache ↔ Cloud storage

### Two-Stage Pipeline

**Stage-1: Detection & Filtering**
- Runs MegaDetector or YOLO on images/videos
- Filters detections by confidence, size, aspect ratio, edge proximity
- Crops detected regions with padding
- Routes doubtful detections for manual review
- Outputs: `stage1/manifest.jsonl` + cropped images

**Stage-2: Classification**
- Runs specialized classifier on Stage-1 crops
- Re-classifies confident detections
- Outputs: `stage2/predictions.jsonl`

**Stage-3: Reporting & Compression**
- Compresses video observations to avoid duplicate logging
- Groups detections within time windows (default: 10 minutes)
- Prevents bloated logs from animals staying in frame
- Outputs: `stage3/compressed_observations.json` + `stage3/report.json`

**Materialization**
- Combines Stage-1 and Stage-2 results
- Outputs: `final.parquet` with complete pipeline results

### Output Format

**Parquet Schema:**
```python
{
    'image_path': str,           # Path to original image
    'camera_id': str,           # Camera identifier
    'timestamp': str,           # ISO timestamp
    'latitude': float,          # GPS latitude
    'longitude': float,         # GPS longitude
    'observation_any': bool,    # Any wildlife detected
    'observations': str,        # JSON list of detections
    'top_label': str,           # Highest confidence label
    'top_confidence': float,    # Highest confidence score
    'needs_review': bool,       # Manual review required
    'pipeline_version': str,    # Pipeline version
    'model_hashes': str,        # Model hash values
    'source_etag': str         # Source file ETag
}
```

## SQLite Conversion Tool

Convert Parquet output to SQLite for analysis:

```bash
# Convert Parquet to SQLite
ravne-parquet-to-sqlite \
  --input ./results/final.parquet \
  --output ./results/wildlife.db \
  --table observations

# Query SQLite database
sqlite3 ./results/wildlife.db "SELECT camera_id, COUNT(*) FROM observations GROUP BY camera_id;"
```

## Configuration

### Local Profile (`profiles/local.yaml`)
```yaml
storage:
  adapter: "local"
  base_path: "file://./data"

queue:
  adapter: "none"

model:
  provider: "local"
  cache_path: "file://./models"

runner:
  type: "local"
  max_workers: 4
```

### Cloud Profile (`profiles/cloud.yaml`)
```yaml
storage:
  adapter: "s3"
  base_path: "s3://wildlife-detection-bucket"

queue:
  adapter: "sqs"
  region: "eu-north-1"

model:
  provider: "cloud"
  cache_path: "s3://wildlife-models-bucket"

runner:
  type: "cloud_batch"
  vcpu: 4
  memory: 8192
  gpu_count: 1
  gpu_type: "g4dn.xlarge"
```

## Features

### Swedish Wildlife Detection
- **Optimized models**: MegaDetector + Swedish wildlife classifier
- **Supported species**: Moose, wild boar, roe deer, red fox, badger
- **Intelligent mapping**: Maps COCO classes to Swedish wildlife
- **Confidence filtering**: Routes doubtful detections for manual review

### Video Processing
- **Frame extraction**: Configurable interval and max frames
- **Supported formats**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- **GPU acceleration**: Optimized for AWS Batch with NVIDIA GPUs
- **Batch processing**: Process multiple videos in parallel

### GPS Integration
- **EXIF extraction**: Automatic GPS coordinate extraction
- **Coordinate validation**: Ensures valid latitude/longitude
- **Multiple formats**: Supports various EXIF GPS formats

### Cloud Optimization
- **GPU acceleration**: NVIDIA T4/V100 GPU support
- **Spot instances**: 70% cost reduction with fault tolerance
- **Auto-scaling**: Scale to zero when idle
- **Batch processing**: Optimized for large datasets

## Development

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run cloud-specific tests
pytest tests/test_cloud_*.py -v

# Run logging tests
pytest tests/test_logging.py -v

# Run with coverage
pytest tests/ --cov=src.wildlife_pipeline --cov-report=html
```

### Logging
The pipeline includes comprehensive logging throughout all stages:

```python
from src.wildlife_pipeline.logging_config import get_logger, setup_pipeline_logging

# Setup pipeline logging
logger = setup_pipeline_logging("INFO", log_dir=Path("./logs"))

# Get module-specific logger
stage_logger = get_logger("wildlife_pipeline.stages", "DEBUG")
```

**Logging Features:**
- **Structured logging** with JSON context
- **Stage-specific methods** (log_stage_start, log_stage_complete, log_stage_error)
- **Detection statistics** (log_detection_stats)
- **Video processing** (log_video_processing)
- **Compression statistics** (log_compression_stats)
- **Progress tracking** (log_processing_progress)
- **File and console output** with configurable levels

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 src/ tests/
black src/ tests/
```

## Documentation

- **[Cloud-Optional Guide](CLOUD_OPTIONAL_GUIDE.md)**: Complete cloud architecture documentation
- **[AWS GPU Deployment](AWS_GPU_DEPLOYMENT_GUIDE.md)**: AWS Batch setup with GPU optimization
- **[Swedish Wildlife Detector](SWEDISH_WILDLIFE_DETECTOR_GUIDE.md)**: Model-specific documentation
- **[Camera Timestamp Fix](CAMERA_TIMESTAMP_FIX_GUIDE.md)**: EXIF timestamp correction utility
- **[GPS & SQLite Guide](GPS_SQLITE_GUIDE.md)**: GPS extraction and database integration
