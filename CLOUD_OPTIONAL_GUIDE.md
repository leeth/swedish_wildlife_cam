# Cloud-Optional Wildlife Detection Pipeline

This guide explains the cloud-optional architecture that allows the same codebase to run both locally and in the cloud with swappable adapters.

## 🏗️ Architecture Overview

The pipeline uses a clean abstraction layer with four core interfaces:

- **StorageAdapter**: Handles file storage (local disk vs S3/GCS)
- **QueueAdapter**: Manages event-driven processing (none/Redis vs SQS/PubSub)
- **ModelProvider**: Loads models (local vs cloud storage)
- **Runner**: Executes pipeline stages (local threads vs cloud batch jobs)

## 📁 Project Structure

```
src/wildlife_pipeline/cloud/
├── interfaces.py      # Core interfaces and data classes
├── storage.py         # Storage adapters (LocalFS, S3, GCS)
├── queue.py          # Queue adapters (None, Redis, SQS, PubSub)
├── models.py         # Model providers (Local, Cloud)
├── runners.py        # Runners (Local, CloudBatch, EventDriven)
├── config.py         # Configuration loader
└── cli.py            # Command-line interface

profiles/
├── local.yaml        # Local configuration profile
└── cloud.yaml        # Cloud configuration profile
```

## 🔧 Configuration Profiles

### Local Profile (`profiles/local.yaml`)

```yaml
storage:
  adapter: "local"
  base_path: "file://./data"

queue:
  adapter: "none"  # No queue for batch processing

model:
  provider: "local"
  cache_path: "file://./models"

runner:
  type: "local"
  max_workers: 4

pipeline:
  stage1:
    model: "megadetector"
    conf_threshold: 0.3
    # ... other stage1 settings
  stage2:
    enabled: true
    model: "yolo_cls"
    conf_threshold: 0.5
```

### Cloud Profile (`profiles/cloud.yaml`)

```yaml
storage:
  adapter: "s3"
  base_path: "s3://wildlife-detection-bucket"
  region: "eu-north-1"

queue:
  adapter: "sqs"
  region: "eu-north-1"
  stage1_queue: "wildlife-stage1-queue"
  stage2_queue: "wildlife-stage2-queue"

model:
  provider: "cloud"
  cache_path: "s3://wildlife-models-bucket"

runner:
  type: "cloud_batch"
  job_definition: "wildlife-detection-job"
  vcpu: 2
  memory: 4096
```

## 🚀 Usage Examples

### Local Processing

```bash
# Stage-1: Detect and crop wildlife
python -m src.wildlife_pipeline.cloud.cli stage1 \
  --profile local \
  --input file://./data \
  --output file://./results

# Stage-2: Classify crops
python -m src.wildlife_pipeline.cloud.cli stage2 \
  --profile local \
  --manifest file://./results/stage1/manifest.jsonl \
  --output file://./results

# Materialize: Create final results
python -m src.wildlife_pipeline.cloud.cli materialize \
  --profile local \
  --manifest file://./results/stage1/manifest.jsonl \
  --output file://./results/final.parquet
```

### Cloud Processing

```bash
# Stage-1: Detect and crop wildlife in cloud
python -m src.wildlife_pipeline.cloud.cli stage1 \
  --profile cloud \
  --input s3://bucket/data \
  --output s3://bucket/results

# Stage-2: Classify crops in cloud
python -m src.wildlife_pipeline.cloud.cli stage2 \
  --profile cloud \
  --manifest s3://bucket/results/stage1/manifest.jsonl \
  --output s3://bucket/results

# Materialize: Create final results
python -m src.wildlife_pipeline.cloud.cli materialize \
  --profile cloud \
  --manifest s3://bucket/results/stage1/manifest.jsonl \
  --output s3://bucket/results/final.parquet
```

## 📊 Data Flow

### Stage-1 Processing

1. **Input**: Raw images from storage
2. **Processing**: Run detection model, filter detections, crop images
3. **Output**: 
   - Cropped images in `stage1/crops/`
   - Manifest file `stage1/manifest.jsonl`

### Stage-2 Processing

1. **Input**: Manifest from Stage-1
2. **Processing**: Run classification model on crops
3. **Output**:
   - Predictions file `stage2/predictions.jsonl`

### Materialization

1. **Input**: Manifest + Predictions
2. **Processing**: Combine data into final format
3. **Output**: CSV/Parquet file with complete results

## 📋 Manifest Schema

### Stage-1 Manifest Entry

```json
{
  "source_path": "s3://bucket/images/camera1/2025-09-07/image1.jpg",
  "crop_path": "s3://bucket/crops/camera1/2025-09-07/crop1.jpg",
  "camera_id": "camera_1",
  "timestamp": "2025-09-07T10:30:00",
  "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
  "det_score": 0.85,
  "stage1_model": "megadetector",
  "config_hash": "abc123",
  "latitude": 59.3293,
  "longitude": 18.0686,
  "image_width": 1920,
  "image_height": 1080
}
```

### Stage-2 Prediction Entry

```json
{
  "crop_path": "s3://bucket/crops/camera1/2025-09-07/crop1.jpg",
  "label": "moose",
  "confidence": 0.92,
  "auto_ok": true,
  "stage2_model": "yolo_cls",
  "stage1_model": "megadetector",
  "config_hash": "abc123"
}
```

## 🔄 Execution Modes

### A) Local Batch (Quick Development)

- **Storage**: Local filesystem
- **Queue**: None (direct processing)
- **Compute**: Local threads/processes
- **Use case**: Development, testing, small datasets

### B) Cloud Batch (Scalable Processing)

- **Storage**: S3/GCS
- **Queue**: None (batch jobs)
- **Compute**: AWS Batch / Cloud Run Jobs
- **Use case**: Large datasets, production processing

### C) Event-Driven (Real-time)

- **Storage**: S3/GCS
- **Queue**: SQS/PubSub
- **Compute**: Serverless functions
- **Use case**: Real-time processing, auto-scaling

## 🛠️ Adapter Implementation

### Storage Adapters

```python
# Local filesystem
storage = LocalFSAdapter(base_path="file://./data")

# S3
storage = S3Adapter(base_path="s3://bucket", region="eu-north-1")

# Google Cloud Storage
storage = GCSAdapter(base_path="gs://bucket")
```

### Queue Adapters

```python
# No queue (batch processing)
queue = NoQueueAdapter()

# Redis (local event-driven)
queue = RedisQueueAdapter(host="localhost", port=6379)

# AWS SQS (cloud event-driven)
queue = SQSAdapter(region="eu-north-1")

# Google Pub/Sub (cloud event-driven)
queue = PubSubAdapter(project_id="my-project")
```

### Model Providers

```python
# Local models
model_provider = LocalModelProvider(cache_path="file://./models")

# Cloud models with caching
model_provider = CloudModelProvider(
    storage_adapter=storage,
    cache_path="s3://models-bucket"
)
```

### Runners

```python
# Local execution
runner = LocalRunner(storage, model_provider, max_workers=4)

# Cloud batch execution
runner = CloudBatchRunner(storage, model_provider, job_definition="my-job")

# Event-driven execution
runner = EventDrivenRunner(storage, queue, model_provider)
```

## 🔧 Environment Variables

Override configuration with environment variables:

```bash
export STORAGE_ADAPTER="s3"
export STORAGE_BASE_PATH="s3://my-bucket"
export QUEUE_ADAPTER="sqs"
export MODEL_PROVIDER="cloud"
export RUNNER_TYPE="cloud_batch"
```

## 📈 Benefits

### Code Reusability
- Same codebase for local and cloud
- No code duplication
- Easy testing and development

### Scalability
- Start local, scale to cloud
- Event-driven processing
- Auto-scaling capabilities

### Cost Optimization
- Use local resources for development
- Scale to cloud for production
- Pay only for what you use

### Flexibility
- Mix and match adapters
- Easy to add new storage/queue providers
- Configuration-driven behavior

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python scripts/test_cloud_architecture.py
```

Expected output:
```
Testing cloud-optional architecture...
✅ Local configuration test passed
✅ Cloud configuration test passed
✅ Storage adapters test passed
✅ Manifest schema test passed
✅ CLI interface test passed

🎉 All tests passed! Cloud-optional architecture is working correctly.
```

## 🚀 Deployment

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Use local profile: `--profile local`
3. Process data: `python -m src.wildlife_pipeline.cloud.cli stage1 ...`

### Cloud Production
1. Set up cloud resources (S3, SQS, Batch)
2. Configure credentials
3. Use cloud profile: `--profile cloud`
4. Deploy with infrastructure as code

### Hybrid Approach
1. Develop locally with `--profile local`
2. Test with cloud storage: `--profile cloud`
3. Deploy to production with full cloud setup

## 📚 Next Steps

1. **Infrastructure Setup**: Configure AWS/GCP resources
2. **CI/CD Pipeline**: Automate deployment
3. **Monitoring**: Add logging and metrics
4. **Optimization**: Tune performance for your use case
5. **Scaling**: Implement auto-scaling policies

The cloud-optional architecture provides a solid foundation for building scalable wildlife detection pipelines that can grow with your needs!
