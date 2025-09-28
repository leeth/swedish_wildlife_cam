# Munin 🐦‍⬛

*"Munin brings memories home"*

**Munin** is the Memory Keeper of Odin's Ravens - responsible for collecting, processing, and preserving all wildlife detection data from camera traps.

## The Memory Keeper

In Norse mythology, Munin (Memory) was one of Odin's ravens who brought back memories and data from the world. Our Munin does the same for wildlife detection:

- **Data Ingestion**: Efficiently processes thousands of images and videos
- **Metadata Preservation**: Extracts and stores EXIF data, GPS coordinates, timestamps
- **Quality Control**: Filters out poor quality detections and routes doubtful cases for review
- **Storage**: Safely stores all memories in structured formats (Parquet, manifest files)
- **Stage 1**: Detects wildlife and crops regions of interest
- **Stage 2**: Classifies detected animals with confidence scores

## Quickstart

### Installation

```bash
# Install Munin
pip install munin

# Or install from source
git clone https://github.com/odins-ravne/munin.git
cd munin
pip install -e .
```

### Basic Usage

```bash
# Data ingestion and processing
munin-ingest --input ./data/images --output ./results

# Stage 1: Detection and cropping
munin-stage1 --profile local --input ./data --output ./results

# Stage 2: Classification
munin-stage2 --profile local --manifest ./results/stage1/manifest.jsonl --output ./results

# Materialize results
munin-materialize --profile local --manifest ./results/stage1/manifest.jsonl --output ./results/final.parquet
```

### Cloud Usage (AWS)

```bash
# Stage 1: Detection with GPU acceleration
munin-stage1 --profile cloud --input s3://bucket/data --output s3://bucket/results

# Stage 2: Classification
munin-stage2 --profile cloud --manifest s3://bucket/results/stage1/manifest.jsonl --output s3://bucket/results

# Materialize results
munin-materialize --profile cloud --manifest s3://bucket/results/stage1/manifest.jsonl --output s3://bucket/results/final.parquet
```

## Features

### Data Ingestion
- **Parallel Processing**: Multi-threaded file processing
- **EXIF Extraction**: GPS coordinates, timestamps, camera metadata
- **Video Support**: Frame extraction from MP4, AVI, MOV, etc.
- **Format Support**: JPG, PNG, TIFF, WebP, and more

### Detection & Classification
- **Stage 1**: Wildlife detection with confidence filtering
- **Stage 2**: Species classification with Swedish wildlife focus
- **Quality Control**: Routes doubtful detections for manual review
- **GPU Acceleration**: Optimized for NVIDIA GPUs

### Storage & Output
- **Parquet Format**: Efficient columnar storage
- **Manifest Files**: JSONL format for pipeline artifacts
- **Metadata Preservation**: Complete EXIF and GPS data
- **Cloud Storage**: S3, GCS, and local filesystem support

## Architecture

### Munin Pipeline Stages

**Stage 0: Data Ingestion**
- File discovery and metadata extraction
- EXIF data processing
- GPS coordinate extraction
- File integrity validation

**Stage 1: Detection**
- Wildlife detection using YOLO/MegaDetector
- Confidence filtering
- Bounding box cropping
- Quality assessment

**Stage 2: Classification**
- Species classification
- Confidence scoring
- Auto-approval logic
- Manual review routing

**Materialization**
- Combine all stages into final output
- Generate Parquet files
- Create manifest summaries

### Cloud-Optional Design

Munin supports both local and cloud execution:

- **Storage**: Local filesystem ↔ S3/GCS
- **Queue**: None/Redis ↔ SQS/PubSub  
- **Compute**: Local threads ↔ AWS Batch/Cloud Run
- **Models**: Local cache ↔ Cloud storage

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

## Output Format

### Parquet Schema
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

## Development

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src.munin --cov-report=html
```

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
ruff check src/ tests/
black src/ tests/
```

## Documentation

- **[Munin Guide](docs/MUNIN_GUIDE.md)**: Complete usage documentation
- **[AWS Deployment](docs/AWS_DEPLOYMENT.md)**: Cloud deployment guide
- **[API Reference](docs/API_REFERENCE.md)**: Complete API documentation

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/odins-ravne/munin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/odins-ravne/munin/discussions)
- **Documentation**: [Read the Docs](https://munin.readthedocs.io)

---

*"Munin brings memories home"* - Let Munin be your memory keeper for wildlife detection! 🐦‍⬛
