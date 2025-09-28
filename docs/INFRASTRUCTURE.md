# 🏗️ Infrastructure Setup & Deployment

**Odins Ravne** - Infrastructure guide for local and cloud deployment

## 🚀 Quick Setup

### Prerequisites
```bash
# Python 3.9+
python --version

# Git
git --version

# Odin CLI (for infrastructure management)
src/odin/cli.py --version

# Munin CLI (for data processing)
src/munin/cli.py --version

# Hugin CLI (for analytics)
src/hugin/cli.py --version
```

### AWS Setup
```bash
# Configure Odin
src/odin/cli.py config setup

# Deploy infrastructure
scripts/infrastructure/deploy_aws_infrastructure.py

# Create test user
scripts/infrastructure/create_aws_test_user.py

# Test AWS access
scripts/infrastructure/test_aws_setup.py
```

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/odins-ravne.git
cd odins-ravne

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Munin
cd src/munin/
pip install -e .

# Install Hugin
cd ../hugin/
pip install -e .
```

## 🐦‍⬛ Munin Setup

### Local Development
```bash
# Basic data ingestion
munin ingest /path/to/images /path/to/output

# With specific extensions
munin ingest /input /output --extensions jpg,mp4,avi

# Process with specific stages
munin process /data --stage1 --stage2

# Upload to cloud
munin upload /data --cloud aws
```

### Configuration
```yaml
# profiles/local.yaml
storage:
  type: local
  base_path: ./data

queue:
  type: none

compute:
  type: local
  max_workers: 4

models:
  detector: "yolov8n.pt"
  confidence: 0.35
```

## 🧠 Hugin Setup

### Local Development
```bash
# Analyze data
hugin analyze /path/to/data

# Generate reports
hugin report /data --format pdf

# Start dashboard
hugin dashboard /data --web
```

### Configuration
```yaml
# profiles/local.yaml
analytics:
  database: "sqlite:///hugin.db"
  cache_size: 1000

visualization:
  theme: "dark"
  export_formats: ["pdf", "png", "svg"]

reporting:
  templates: "./templates/"
  output_dir: "./reports/"
```

## ☁️ Cloud Deployment

### AWS Setup
```bash
# Configure Odin
src/odin/cli.py config setup

# Deploy infrastructure
scripts/infrastructure/deploy_aws_infrastructure.py

# Create test user
scripts/infrastructure/create_aws_test_user.py

# Test AWS access
scripts/infrastructure/test_aws_setup.py
```

### AWS Configuration
```yaml
# profiles/cloud.yaml
storage:
  type: s3
  bucket: "odins-ravne-data"
  region: "eu-north-1"

queue:
  type: sqs
  queue_url: "https://sqs.eu-north-1.amazonaws.com/..."

compute:
  type: batch
  job_definition: "wildlife-pipeline"
  job_queue: "wildlife-queue"

models:
  detector: "s3://odins-ravne-models/yolov8n.pt"
  confidence: 0.35
```

## 🐳 Docker Deployment

### Build Images
```bash
# Build images using Odin
src/odin/cli.py infrastructure build --component munin
src/odin/cli.py infrastructure build --component hugin
```

### Run Containers
```bash
# Run Munin
munin ingest /path/to/data/input /path/to/data/output

# Run Hugin
hugin analyze /path/to/data
```

## 🔧 Development Environment

### IDE Setup
```bash
# VS Code extensions
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-python.mypy-type-checker

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

### Testing
```bash
# Run tests
pytest tests/

# Run specific test categories
pytest tests/test_munin/
pytest tests/test_hugin/

# Run with coverage
pytest --cov=src/ tests/
```

## 📊 Monitoring & Logging

### Local Monitoring
```bash
# Start monitoring dashboard
hugin monitor --web --port 8080

# View logs
tail -f logs/munin.log
tail -f logs/hugin.log
```

### Cloud Monitoring
```bash
# AWS CloudWatch
aws logs describe-log-groups --log-group-name-prefix odins-ravne

# View recent logs
aws logs get-log-events --log-group-name odins-ravne/munin
```

## 🔒 Security Setup

### Local Security
```bash
# Generate API keys
python scripts/security/generate_api_keys.py

# Set up encryption
python scripts/security/setup_encryption.py
```

### Cloud Security
```bash
# Deploy security policies
./scripts/security/deploy_security_policies.py

# Run security audit
./scripts/security/security_audit.py
```

## 🚀 Performance Optimization

### Local Optimization
```bash
# Optimize for CPU
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# Optimize for GPU
export CUDA_VISIBLE_DEVICES=0
```

### Cloud Optimization
```bash
# Deploy optimized infrastructure
./scripts/optimization/deploy_optimized_infrastructure.py

# Configure auto-scaling
./scripts/optimization/configure_autoscaling.py
```

## 🛠️ Troubleshooting

### Common Issues

#### **Import Errors**
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall packages
pip install --force-reinstall -r requirements.txt
```

#### **GPU Issues**
```bash
# Check CUDA installation
nvidia-smi

# Test PyTorch GPU
python -c "import torch; print(torch.cuda.is_available())"
```

#### **AWS Issues**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-bucket-name
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
munin ingest /input /output --verbose
hugin analyze /data --debug
```

## 📚 Additional Resources

- **Local Setup**: [UTILITIES.md](UTILITIES.md)
- **Cloud Optimization**: [CLOUD_OPTIMIZATION.md](CLOUD_OPTIMIZATION.md)
- **API Documentation**: [API.md](API.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Infrastructure Status:** ✅ **ACTIVE**  
**Last Updated:** 2025-09-28  
**Version:** 1.0
