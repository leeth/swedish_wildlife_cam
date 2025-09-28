# Infrastructure Scripts

This directory contains scripts for AWS infrastructure setup and management.

## Scripts

### `create_aws_test_user.py`
Creates a minimal AWS IAM user for testing the wildlife pipeline.

**Usage:**
```bash
# Create test user
python create_aws_test_user.py --username wildlife-pipeline-test

# Test credentials
python create_aws_test_user.py --test

# Cleanup
python create_aws_test_user.py --cleanup
```

### `deploy_aws_infrastructure.py`
Deploys complete AWS infrastructure for the wildlife pipeline.

**Usage:**
```bash
# Deploy everything
python deploy_aws_infrastructure.py --complete

# Deploy specific components
python deploy_aws_infrastructure.py --s3 --ecr --batch
```

### `test_aws_setup.py`
Tests AWS service access and configuration.

**Usage:**
```bash
# Test all services
python test_aws_setup.py --comprehensive

# Test specific services
python test_aws_setup.py --s3 --batch --gpu
```

### `test_aws_pipeline.py`
Tests the complete AWS pipeline execution.

**Usage:**
```bash
# Test everything
python test_aws_pipeline.py --comprehensive

# Test specific components
python test_aws_pipeline.py --s3 --batch --gpu
```

## Resources Created

- **S3 Buckets:** Data, results, models, logs
- **ECR Repository:** Docker images
- **AWS Batch:** GPU-enabled compute
- **IAM Roles:** Minimal permissions
- **CloudFormation:** Infrastructure stack

## Prerequisites

- AWS CLI configured
- Python 3.8+
- boto3 library
- Appropriate AWS permissions

## Security

All scripts use minimal IAM permissions and follow AWS security best practices.
