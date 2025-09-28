# 🛠️ Utilities & Tools

**Odins Ravne** - Utility scripts and tools for wildlife processing

## 📁 Scripts Directory Structure

```
scripts/
├── infrastructure/          # AWS/cloud setup
│   ├── deploy_aws_infrastructure.py
│   ├── create_aws_test_user.py
│   ├── test_aws_setup.py
│   └── deploy_monitoring.py
├── image_tools/             # Image processing utilities
│   ├── fix_camera_timestamps.py
│   ├── test_timestamp_fix.py
│   ├── test_gps_sqlite.py
│   └── test_location_tools.py
├── data_upload/             # Cloud data management
│   ├── upload_to_s3.py
│   ├── sync_data.py
│   └── backup_data.py
└── testing/                 # Test utilities
    ├── performance_test.py
    ├── cost_analysis.py
    └── integration_test.py
```

## 🏗️ Infrastructure Scripts

### AWS Infrastructure Deployment
```bash
# Deploy complete AWS infrastructure
scripts/infrastructure/deploy_aws_infrastructure.py \
  --region eu-north-1 \
  --bucket-name odins-ravne-data \
  --gpu-enabled \
  --spot-instances

# Create test user with minimal permissions
scripts/infrastructure/create_aws_test_user.py \
  --username wildlife-test \
  --permissions s3,batch,ecr

# Test AWS setup
scripts/infrastructure/test_aws_setup.py \
  --test-s3 \
  --test-batch \
  --test-ecr
```

### Monitoring Deployment
```bash
# Deploy CloudWatch monitoring
scripts/infrastructure/deploy_monitoring.py \
  --cloudwatch \
  --alerts \
  --dashboards \
  --cost-monitoring
```

## 🖼️ Image Tools

### Camera Timestamp Correction
```bash
# Fix camera timestamps
scripts/image_tools/fix_camera_timestamps.py \
  --input /path/to/images \
  --target-date "2025-09-07" \
  --extensions jpg,jpeg,tiff \
  --backup

# Test timestamp fix
scripts/image_tools/test_timestamp_fix.py \
  --input /path/to/test/images \
  --expected-date "2025-09-07"
```

### GPS and Location Tools
```bash
# Test GPS extraction
scripts/image_tools/test_gps_sqlite.py \
  --input /path/to/images \
  --database location_classifier.db

# Test location classification
scripts/image_tools/test_location_tools.py \
  --input /path/to/images \
  --radius 10 \
  --output locations.json

# Classify images by location
python -m src.munin.tools.location_classifier classify \
  /path/to/images \
  --sd-card SD001 \
  --recursive

# Interactive location labeling
python -m src.munin.tools.location_labeler --interactive

# Move classified images to cloud
python -m src.munin.tools.location_classifier move \
  /path/to/images \
  s3://my-bucket/wildlife-images/ \
  --dry-run
```

## ☁️ Data Upload Scripts

### S3 Upload
```bash
# Upload data to S3
scripts/data_upload/upload_to_s3.py \
  --local-path /path/to/data \
  --s3-bucket odins-ravne-data \
  --s3-prefix wildlife-data/ \
  --parallel-uploads 10

# Sync data between local and S3
scripts/data_upload/sync_data.py \
  --local-path /path/to/data \
  --s3-bucket odins-ravne-data \
  --direction both \
  --delete-remote
```

### Data Backup
```bash
# Backup data to multiple locations
scripts/data_upload/backup_data.py \
  --source /path/to/data \
  --destinations s3://backup-bucket,gs://backup-bucket \
  --compression gzip \
  --encryption
```

## 🧪 Testing Scripts

### Performance Testing
```bash
# Run performance tests
scripts/testing/performance_test.py \
  --instance-type g4dn.xlarge \
  --batch-size 32 \
  --image-count 1000 \
  --output results.json

# Test different configurations
scripts/testing/performance_test.py \
  --config-file test_configs.yaml \
  --compare-results
```

### Cost Analysis
```bash
# Analyze processing costs
scripts/testing/cost_analysis.py \
  --timeframe 30 \
  --instance-types g4dn.xlarge,g4dn.2xlarge \
  --optimization-suggestions \
  --output cost_report.pdf
```

### Integration Testing
```bash
# Run integration tests
scripts/testing/integration_test.py \
  --test-pipeline \
  --test-cloud \
  --test-database \
  --verbose
```

## 🔧 Utility Functions

### Data Conversion
```python
# Parquet to SQLite conversion
from src.munin.tools.parquet_to_sqlite import ParquetToSQLiteConverter

converter = ParquetToSQLiteConverter()
converter.convert(
    parquet_path="data.parquet",
    sqlite_path="data.db",
    table_name="wildlife_data"
)
```

### Location Classification
```python
# Location classification
from src.munin.tools.location_classifier import LocationClassifier

classifier = LocationClassifier(radius=10)  # 10 meter radius
locations = classifier.classify_images("/path/to/images")
```

### Location Labeling
```python
# Interactive location labeling
from src.munin.tools.location_labeler import LocationLabeler

labeler = LocationLabeler()
labeler.start_labeling_session(
    locations_file="locations.json",
    output_file="labeled_locations.json"
)
```

## 📊 Data Analysis Tools

### Wildlife Analytics
```python
# Wildlife analytics
from src.hugin.analytics_engine import AnalyticsEngine

engine = AnalyticsEngine()
results = engine.analyze_wildlife_data(
    data_path="/path/to/data",
    species=["moose", "boar", "roedeer"],
    time_range=("2025-01-01", "2025-12-31")
)
```

### Observation Compression
```python
# Compress observations
from src.hugin.observation_compressor import ObservationCompressor

compressor = ObservationCompressor(time_window=600)  # 10 minutes
compressed = compressor.compress_observations(
    observations=raw_observations,
    species="moose"
)
```

## 🚀 Deployment Utilities

### Docker Management
```bash
# Build and push Docker images
scripts/deployment/build_docker_images.py \
  --munin \
  --hugin \
  --gpu-enabled \
  --push-to-ecr

# Deploy to AWS Batch
scripts/deployment/deploy_to_batch.py \
  --job-definition wildlife-pipeline \
  --image-uri 123456789012.dkr.ecr.eu-north-1.amazonaws.com/odins-ravne/munin:latest
```

### Configuration Management
```bash
# Generate configuration files
scripts/configuration/generate_configs.py \
  --environment production \
  --region eu-north-1 \
  --output-dir ./configs/

# Validate configuration
scripts/configuration/validate_configs.py \
  --config-file ./configs/production.yaml \
  --check-aws-access
```

## 🔍 Debugging Tools

### Log Analysis
```bash
# Analyze processing logs
scripts/debugging/analyze_logs.py \
  --log-file logs/munin.log \
  --error-patterns \
  --performance-metrics \
  --output report.html
```

### Data Validation
```bash
# Validate data integrity
scripts/debugging/validate_data.py \
  --data-path /path/to/data \
  --check-images \
  --check-metadata \
  --check-database
```

### Performance Profiling
```bash
# Profile performance
scripts/debugging/profile_performance.py \
  --script-path src/munin/process_images.py \
  --input-path /path/to/images \
  --output-profile profile.json
```

## 📈 Monitoring Utilities

### System Monitoring
```bash
# Monitor system resources
scripts/monitoring/system_monitor.py \
  --cpu \
  --memory \
  --gpu \
  --disk \
  --output metrics.json
```

### Wildlife Monitoring
```bash
# Monitor wildlife detection
scripts/monitoring/wildlife_monitor.py \
  --species moose,boar,roedeer \
  --time-window 24h \
  --alert-threshold 10
```

## 🛠️ Maintenance Tools

### Database Maintenance
```bash
# Optimize database
scripts/maintenance/optimize_database.py \
  --database-path data.db \
  --vacuum \
  --reindex \
  --analyze
```

### Cleanup Tools
```bash
# Clean up old data
scripts/maintenance/cleanup_data.py \
  --data-path /path/to/data \
  --older-than 90 \
  --backup-before-delete
```

### Backup Tools
```bash
# Create backup
scripts/maintenance/create_backup.py \
  --source /path/to/data \
  --destination /path/to/backup \
  --compression gzip \
  --encryption
```

## 📚 Usage Examples

### Complete Workflow
```bash
# 1. Setup infrastructure
scripts/infrastructure/deploy_aws_infrastructure.py

# 2. Fix camera timestamps
scripts/image_tools/fix_camera_timestamps.py --input /images --target-date "2025-09-07"

# 3. Process images
src/munin/cli.py ingest /images /output --extensions jpg,mp4

# 4. Upload to cloud
scripts/data_upload/upload_to_s3.py --local-path /output --s3-bucket odins-ravne-data

# 5. Analyze results
src/hugin/cli.py analyze /output --species moose

# 6. Generate report
src/hugin/cli.py report /output --format pdf
```

### Testing Workflow
```bash
# 1. Run performance tests
scripts/testing/performance_test.py --image-count 1000

# 2. Run integration tests
scripts/testing/integration_test.py --test-pipeline

# 3. Analyze costs
scripts/testing/cost_analysis.py --timeframe 30

# 4. Generate test report
scripts/testing/generate_test_report.py --output test_report.html
```

---

**Utilities Status:** ✅ **ACTIVE**  
**Last Updated:** 2025-09-28  
**Version:** 1.0
