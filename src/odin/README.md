# ⚡ Odin - All-Father Infrastructure Management

Odin er All-Father i Odins Ravne systemet og håndterer infrastruktur management, orchestration og cost optimization.

## 🎯 Purpose

Odin orchestrerer hele wildlife pipeline systemet:
- **Infrastructure Management**: AWS setup, teardown og monitoring
- **Pipeline Orchestration**: Stage 0-3 execution management
- **Cost Optimization**: Budget control og spot instance management
- **Resource Management**: Auto-scaling og cleanup

## 🏗️ Architecture

### Core Components

```
src/odin/
├── cli.py                    # Main CLI interface
├── config.py                 # Configuration management
├── infrastructure.py          # AWS infrastructure
├── local_infrastructure.py   # Local infrastructure (LocalStack)
├── pipeline.py               # Pipeline orchestration
├── local_pipeline.py         # Local pipeline execution
├── manager.py                # Cost optimization manager
├── batch_workflow.py         # Batch workflow management
├── validation.py             # Input validation
├── run_report.py             # Execution reporting
├── infrastructure/            # Infrastructure as Code
│   ├── stepfn/              # Step Functions definitions
│   ├── batch/               # AWS Batch configurations
│   ├── cloudformation/      # CloudFormation templates
│   └── scripts/             # Deployment scripts
└── lambdas/                 # Lambda functions
    ├── guard_budget/        # Budget validation
    ├── stage0_exif/         # EXIF processing
    ├── stage2_post/         # Post-processing
    └── weather_enrichment/  # Weather data
```

### Configuration System

```yaml
# conf/profiles/local.yaml
name: "Wildlife Processing World (Local)"
version: "1.0.0"
description: "Local development environment"

infrastructure:
  provider: "local"
  region: "eu-north-1"
  cost_optimized: false
  stack_name: "wildlife-local-stack"
  
  localstack:
    endpoint: "http://localhost:4566"
    services: ["s3", "batch", "iam", "cloudformation", "ec2", "logs"]
    debug: true
    persistence: true
  
  minio:
    endpoint: "http://localhost:9000"
    access_key: "minioadmin"
    secret_key: "minioadmin123"
    secure: false
  
  redis:
    url: "redis://localhost:6379"
    db: 0
  
  postgres:
    url: "postgresql://wildlife:wildlife123@localhost:5432/wildlife"
    pool_size: 10
```

## 🚀 Usage

### Infrastructure Management

```bash
# Setup local infrastructure
python -m src.odin.cli --config conf/profiles/local.yaml infrastructure setup

# Check infrastructure status
python -m src.odin.cli --config conf/profiles/local.yaml infrastructure status

# Teardown infrastructure
python -m src.odin.cli --config conf/profiles/local.yaml infrastructure teardown
```

### Pipeline Execution

```bash
# Run complete pipeline
python -m src.odin.cli --config conf/profiles/local.yaml pipeline run

# Run specific stages
python -m src.odin.cli --config conf/profiles/local.yaml pipeline stage1
python -m src.odin.cli --config conf/profiles/local.yaml pipeline stage2
python -m src.odin.cli --config conf/profiles/local.yaml pipeline stage3
```

### Data Management

```bash
# Upload data to S3
python -m src.odin.cli --config conf/profiles/local.yaml data upload /path/to/data

# Download data from S3
python -m src.odin.cli --config conf/profiles/local.yaml data download s3://bucket/path

# List S3 data
python -m src.odin.cli --config conf/profiles/local.yaml data list
```

### Cost Management

```bash
# Generate cost report
python -m src.odin.cli --config conf/profiles/local.yaml cost report

# Optimize costs
python -m src.odin.cli --config conf/profiles/local.yaml cost optimize
```

## 🔧 Configuration

### Environment Profiles

#### Local Development
```yaml
# conf/profiles/local.yaml
infrastructure:
  provider: "local"
  localstack:
    endpoint: "http://localhost:4566"
  minio:
    endpoint: "http://localhost:9000"
```

#### Cloud Production
```yaml
# conf/profiles/cloud.yaml
infrastructure:
  provider: "aws"
  region: "eu-north-1"
  cost_optimized: true
  stack_name: "wildlife-production-stack"
```

### Cost Optimization Configuration

```yaml
# conf/profiles/cost-optimized.yaml
cost_optimization:
  region: "eu-north-1"
  environment: "production"
  spot_bid_percentage: 70
  max_vcpus: 100
  min_vcpus: 0
  desired_vcpus: 0
  gpu_required: true
  max_parallel_jobs: 10
  cost_threshold_percentage: 0.5
```

## 🏗️ Infrastructure Components

### Local Infrastructure (LocalStack)

- **LocalStack**: AWS API emulator
- **MinIO**: S3-compatible storage
- **Redis**: Caching and job queues
- **PostgreSQL**: Metadata storage

### AWS Infrastructure

- **S3**: Data storage
- **Batch**: Compute jobs
- **Lambda**: Serverless functions
- **Step Functions**: Workflow orchestration
- **CloudFormation**: Infrastructure as code

## 📊 Monitoring & Logging

### Session-Based Logging

```python
from src.odin.logging_config import get_logger

# Get session logger
logger = get_logger(component="odin")

# Log infrastructure events
logger.info("Setting up infrastructure...")
logger.error("Infrastructure setup failed", exc_info=True)
```

### Cost Monitoring

```python
from src.odin.manager import CostOptimizationManager

# Initialize cost manager
manager = CostOptimizationManager(config)

# Get cost report
costs = manager.get_cost_report()
print(f"Total cost: {costs['total']} DKK")
```

## 🔐 Security & Credentials

### Environment Variables

```bash
# AWS Configuration
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="eu-north-1"

# Pipeline Configuration
export WILDLIFE_PIPELINE_ENV="development"
export WILDLIFE_PIPELINE_BUDGET="1000"
export WILDLIFE_PIPELINE_MAX_IMAGES="1000"
```

### Security Best Practices

- ✅ **Use IAM roles** instead of access keys when possible
- ✅ **Rotate credentials** regularly
- ✅ **Use least privilege** - only grant necessary permissions
- ✅ **Enable MFA** on AWS accounts
- ✅ **Monitor access** with CloudTrail

## 🧪 Testing

### Unit Tests

```bash
# Run Odin tests
python -m pytest test/unit/test_odin*.py -v

# Run specific test
python -m pytest test/unit/test_odin_manager.py -v
```

### Integration Tests

```bash
# Test infrastructure setup
python -m pytest test/integration/test_infrastructure.py -v

# Test pipeline execution
python -m pytest test/integration/test_pipeline.py -v
```

## 📈 Performance Optimization

### Cost Optimization Features

- **Spot Instances**: Up to 90% cost savings
- **Auto-scaling**: Scale to zero when idle
- **Batch Processing**: Efficient resource utilization
- **Cost Monitoring**: Real-time cost tracking
- **Budget Alerts**: Automatic budget enforcement

### Resource Management

- **GPU Optimization**: Automatic GPU selection
- **Memory Management**: Efficient memory usage
- **Storage Optimization**: Intelligent data lifecycle
- **Network Optimization**: Reduced data transfer costs

## 🔄 Workflow Integration

### Step Functions Integration

```python
# Start Step Functions execution
from src.odin.pipeline import PipelineManager

pipeline = PipelineManager(config)
execution = pipeline.start_step_functions_execution({
    "input_uri": "s3://bucket/input/",
    "output_uri": "s3://bucket/output/",
    "budget_dkk": 25,
    "use_spot": True,
    "max_job_duration": 1800
})
```

### Batch Job Management

```python
# Submit batch job
from src.odin.batch_workflow import BatchWorkflowManager

batch_manager = BatchWorkflowManager(config)
job = batch_manager.submit_job({
    "job_name": "wildlife-detection",
    "job_definition": "wildlife-detection-job",
    "job_queue": "wildlife-detection-queue"
})
```

## 🚀 Deployment

### Local Development

```bash
# Start LocalStack
make up-localstack

# Deploy to LocalStack
make deploy-local

# Run pipeline locally
make run-local
```

### Production (AWS)

```bash
# Deploy to AWS
make deploy-aws

# Run pipeline in AWS
make run-aws
```

### Cleanup

```bash
# Stop LocalStack
make down-localstack

# Destroy local resources
make destroy-local
```

## 📚 API Reference

### CLI Commands

```bash
# Infrastructure
python -m src.odin.cli infrastructure {setup|teardown|status}

# Pipeline
python -m src.odin.cli pipeline {run|stage1|stage2|stage3}

# Data
python -m src.odin.cli data {upload|download|list}

# Cost
python -m src.odin.cli cost {report|optimize}
```

### Python API

```python
from src.odin.config import OdinConfig
from src.odin.infrastructure import InfrastructureManager
from src.odin.pipeline import PipelineManager

# Initialize configuration
config = OdinConfig.from_file("conf/profiles/local.yaml")

# Setup infrastructure
infra = InfrastructureManager(config)
infra.setup()

# Run pipeline
pipeline = PipelineManager(config)
pipeline.run()
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Make your changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under MIT License - see LICENSE file for details.

---

**Odin** - All-Father of the Wildlife Intelligence System
