# AWS GPU-Optimized Deployment Guide

This guide explains how to deploy the wildlife detection pipeline on AWS with GPU optimization for image processing.

## 🎯 Overview

The pipeline is optimized for:
- **GPU-accelerated image processing** with NVIDIA T4/V100 GPUs
- **Batch processing** with AWS Batch
- **Cost optimization** with Spot instances
- **Auto-scaling** based on workload
- **High throughput** for large image datasets

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   S3 Storage    │    │  AWS Batch      │    │  CloudWatch     │
│                 │    │                 │    │                 │
│ • Raw images    │───▶│ • GPU instances │───▶│ • Logs & Metrics│
│ • Crops         │    │ • Spot pricing  │    │ • Monitoring    │
│ • Results       │    │ • Auto-scaling  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

### 2. Deploy Infrastructure

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name wildlife-detection \
  --template-body file://aws/cloudformation-template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
               ParameterKey=VpcId,ParameterValue=vpc-12345678 \
               ParameterKey=SubnetIds,ParameterValue=subnet-12345678,subnet-87654321 \
               ParameterKey=MaxVCpus,ParameterValue=100 \
  --capabilities CAPABILITY_NAMED_IAM
```

### 3. Build and Push Docker Image

```bash
# Build GPU-optimized image
docker build -f docker/Dockerfile.aws-gpu -t wildlife-detection:latest .

# Tag for ECR
docker tag wildlife-detection:latest your-account.dkr.ecr.eu-north-1.amazonaws.com/wildlife-detection:latest

# Push to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.eu-north-1.amazonaws.com
docker push your-account.dkr.ecr.eu-north-1.amazonaws.com/wildlife-detection:latest
```

### 4. Run Pipeline

```bash
# Stage-1: Detection and cropping
python -m src.wildlife_pipeline.cloud.cli stage1 \
  --profile cloud \
  --input s3://wildlife-detection-production-123456789/data \
  --output s3://wildlife-detection-production-123456789/results

# Stage-2: Classification
python -m src.wildlife_pipeline.cloud.cli stage2 \
  --profile cloud \
  --manifest s3://wildlife-detection-production-123456789/results/stage1/manifest.jsonl \
  --output s3://wildlife-detection-production-123456789/results

# Materialize results
python -m src.wildlife_pipeline.cloud.cli materialize \
  --profile cloud \
  --manifest s3://wildlife-detection-production-123456789/results/stage1/manifest.jsonl \
  --output s3://wildlife-detection-production-123456789/results/final.parquet
```

## 🔧 Configuration

### GPU Instance Types

| Instance Type | GPU | vCPUs | Memory | Use Case |
|---------------|-----|-------|--------|----------|
| g4dn.xlarge   | 1x T4 | 4 | 16 GB | Small batches |
| g4dn.2xlarge  | 1x T4 | 8 | 32 GB | Medium batches |
| g4dn.4xlarge  | 1x T4 | 16 | 64 GB | Large batches |
| p3.2xlarge   | 1x V100 | 8 | 61 GB | High performance |
| p3.8xlarge   | 4x V100 | 32 | 244 GB | Maximum performance |

### Batch Configuration

```yaml
# profiles/cloud.yaml
runner:
  type: "cloud_batch"
  vcpu: 4
  memory: 8192
  gpu_count: 1
  gpu_type: "g4dn.xlarge"
  instance_types: ["g4dn.xlarge", "g4dn.2xlarge", "p3.2xlarge"]

pipeline:
  stage1:
    batch_size: 16  # Process 16 images per GPU batch
    image_size: 640  # Optimized for YOLO models
    max_images_per_job: 1000  # Limit per batch job
  stage2:
    batch_size: 32  # Larger batch for classification
    image_size: 224  # Standard for classification models
```

## 📊 Performance Optimization

### GPU Memory Management

```python
# Environment variables for GPU optimization
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
OPENCV_GPU_ENABLED=1
```

### Batch Processing

- **Batch Size**: 16 images per GPU batch (Stage-1), 32 for Stage-2
- **Image Size**: 640x640 for detection, 224x224 for classification
- **Job Limits**: 1000 images per job to prevent timeouts

### Cost Optimization

- **Spot Instances**: 70% discount on compute costs
- **Auto-scaling**: Scale to zero when idle
- **Right-sizing**: Choose appropriate instance types

## 🔍 Monitoring

### CloudWatch Metrics

```bash
# Monitor batch jobs
aws logs describe-log-groups --log-group-name-prefix /aws/batch/wildlife-detection

# Check job status
aws batch describe-jobs --jobs job-12345678-1234-1234-1234-123456789012
```

### Key Metrics

- **Job Success Rate**: >95% target
- **Average Processing Time**: <30 minutes per 1000 images
- **GPU Utilization**: >80% target
- **Cost per Image**: <$0.01 target

## 🛠️ Troubleshooting

### Common Issues

1. **GPU Not Available**
   ```bash
   # Check instance type
   aws batch describe-compute-environments --compute-environments wildlife-detection-compute
   
   # Verify GPU drivers
   nvidia-smi
   ```

2. **Out of Memory**
   ```bash
   # Reduce batch size
   export BATCH_SIZE=8
   export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:256
   ```

3. **Job Timeout**
   ```bash
   # Increase timeout or reduce images per job
   export MAX_IMAGES_PER_JOB=500
   ```

### Debug Commands

```bash
# Check job logs
aws logs get-log-events \
  --log-group-name /aws/batch/wildlife-detection \
  --log-stream-name batch/job-12345678

# Monitor GPU usage
nvidia-smi -l 1

# Check batch queue
aws batch describe-job-queues --job-queues wildlife-detection-queue
```

## 💰 Cost Estimation

### Instance Costs (eu-north-1)

| Instance Type | On-Demand | Spot (70% off) | Use Case |
|---------------|-----------|----------------|----------|
| g4dn.xlarge   | $0.526/hour | $0.158/hour | Development |
| g4dn.2xlarge  | $0.752/hour | $0.226/hour | Production |
| p3.2xlarge   | $3.06/hour | $0.918/hour | High performance |

### Processing Costs

- **1000 images**: ~$0.50 (g4dn.xlarge, 30 minutes)
- **10,000 images**: ~$5.00 (g4dn.xlarge, 5 hours)
- **100,000 images**: ~$50.00 (g4dn.xlarge, 50 hours)

## 🔒 Security

### IAM Roles

- **BatchServiceRole**: Manages batch compute environment
- **BatchJobRole**: Executes batch jobs with S3 access
- **BatchInstanceRole**: EC2 instances with minimal permissions

### Network Security

- **VPC**: Isolated network environment
- **Security Groups**: Restrictive ingress/egress rules
- **Private Subnets**: No direct internet access

### Data Protection

- **Encryption**: S3 server-side encryption
- **Access Logging**: CloudTrail for audit
- **Backup**: S3 versioning and lifecycle policies

## 📈 Scaling

### Auto-scaling

```yaml
# Compute environment auto-scaling
compute:
  min_vcpus: 0
  max_vcpus: 100
  desired_vcpus: 10
  spot_instances: true
```

### Manual Scaling

```bash
# Update compute environment
aws batch update-compute-environment \
  --compute-environment wildlife-detection-compute \
  --compute-resources minvCpus=0,maxvCpus=200,desiredvCpus=20
```

## 🚀 Advanced Features

### Event-Driven Processing

```yaml
# Enable SQS for event-driven processing
queue:
  adapter: "sqs"
  region: "eu-north-1"
  stage1_queue: "wildlife-stage1-queue"
  stage2_queue: "wildlife-stage2-queue"
```

### Multi-Region Deployment

```bash
# Deploy in multiple regions
aws cloudformation create-stack \
  --stack-name wildlife-detection-eu-west-1 \
  --template-body file://aws/cloudformation-template.yaml \
  --region eu-west-1
```

### Cost Optimization

- **Reserved Instances**: For predictable workloads
- **Spot Fleet**: For fault-tolerant applications
- **Right-sizing**: Monitor and adjust instance types

## 📚 Next Steps

1. **Monitor Performance**: Set up CloudWatch dashboards
2. **Optimize Costs**: Use Spot instances and reserved capacity
3. **Scale Globally**: Deploy in multiple regions
4. **Automate**: Set up CI/CD pipelines
5. **Secure**: Implement additional security measures

The AWS GPU-optimized deployment provides a robust, scalable solution for wildlife detection at scale! 🚀
