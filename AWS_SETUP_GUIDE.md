# AWS Setup Guide for Wildlife Pipeline

This guide explains how to set up and test AWS infrastructure for the wildlife pipeline.

## 🎯 Overview

The AWS setup provides:
- **S3 Storage** for images and results
- **AWS Batch** for GPU-enabled image processing
- **ECR Repository** for Docker images
- **CloudFormation** for infrastructure management
- **IAM Roles** for secure access

## 🚀 Quick Start

### 1. Create AWS Test User

```bash
# Create test user with minimal permissions
python scripts/create_aws_test_user.py --username wildlife-pipeline-test

# Test the credentials
python scripts/create_aws_test_user.py --test
```

### 2. Deploy Infrastructure

```bash
# Deploy complete infrastructure
python scripts/deploy_aws_infrastructure.py --complete --region eu-north-1

# Or deploy specific components
python scripts/deploy_aws_infrastructure.py --s3 --ecr --batch
```

### 3. Test Pipeline

```bash
# Run comprehensive tests
python scripts/test_aws_pipeline.py --comprehensive

# Test specific components
python scripts/test_aws_pipeline.py --s3 --batch --gpu
```

## 🔧 Detailed Setup

### Step 1: AWS User Creation

The `create_aws_test_user.py` script creates a minimal IAM user with only the required permissions:

```bash
# Basic user creation
python scripts/create_aws_test_user.py

# Custom username and region
python scripts/create_aws_test_user.py --username my-test-user --region us-east-1

# Test credentials after creation
python scripts/create_aws_test_user.py --test

# Clean up when done
python scripts/create_aws_test_user.py --cleanup
```

**Created Resources:**
- IAM user with programmatic access
- Minimal policy for wildlife pipeline operations
- AWS credentials file profile
- JSON credentials file

### Step 2: Infrastructure Deployment

The `deploy_aws_infrastructure.py` script deploys all necessary AWS resources:

```bash
# Deploy everything
python scripts/deploy_aws_infrastructure.py --complete

# Deploy specific components
python scripts/deploy_aws_infrastructure.py --s3 --ecr --batch --cf
```

**Deployed Resources:**
- **S3 Buckets:**
  - `wildlife-pipeline-data` - Raw images
  - `wildlife-pipeline-results` - Processed results
  - `wildlife-pipeline-models` - Model artifacts
  - `wildlife-pipeline-logs` - Pipeline logs

- **ECR Repository:**
  - `wildlife-pipeline` - Docker images

- **AWS Batch:**
  - Compute environment with GPU support
  - Job queue for processing
  - Job definition for wildlife pipeline

- **IAM Roles:**
  - Batch service role
  - Batch instance role
  - Required policies

### Step 3: Pipeline Testing

The `test_aws_pipeline.py` script validates the complete setup:

```bash
# Test everything
python scripts/test_aws_pipeline.py --comprehensive

# Test specific components
python scripts/test_aws_pipeline.py --s3 --batch --gpu
```

## 📋 AWS Resources

### S3 Buckets

| Bucket Name | Purpose | Access |
|-------------|---------|---------|
| `wildlife-pipeline-data` | Raw images and input data | Read/Write |
| `wildlife-pipeline-results` | Processed results and outputs | Read/Write |
| `wildlife-pipeline-models` | Model artifacts and weights | Read/Write |
| `wildlife-pipeline-logs` | Pipeline logs and monitoring | Write |

### AWS Batch Configuration

**Compute Environment:**
- Type: EC2
- Instance Types: `g4dn.xlarge`, `g4dn.2xlarge`, `p3.2xlarge`
- Min vCPUs: 0
- Max vCPUs: 256
- GPU Support: Enabled

**Job Queue:**
- Name: `wildlife-pipeline-queue`
- Priority: 1
- State: Enabled

**Job Definition:**
- Name: `wildlife-pipeline-job`
- Type: Container
- vCPUs: 4
- Memory: 16GB
- GPU: 1
- Environment Variables:
  - `CUDA_VISIBLE_DEVICES=0`
  - `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`

### IAM Roles and Policies

**Batch Service Role:**
- `AWSBatchServiceRole` policy
- Allows Batch to manage EC2 instances

**Batch Instance Role:**
- `AmazonEC2ContainerRegistryReadOnly` policy
- `CloudWatchLogsFullAccess` policy
- `AmazonS3FullAccess` policy

## 🔍 Testing and Validation

### Test S3 Operations

```bash
# Test S3 access and operations
python scripts/test_aws_setup.py --s3 --bucket wildlife-pipeline-data
```

### Test Batch Job Submission

```bash
# Test Batch job submission
python scripts/test_aws_pipeline.py --batch
```

### Test GPU Processing

```bash
# Test GPU-enabled processing
python scripts/test_aws_pipeline.py --gpu
```

### Test Complete Pipeline

```bash
# Test end-to-end pipeline
python scripts/test_aws_pipeline.py --e2e
```

## 🚀 Running the Pipeline

### Local Development

```bash
# Test locally with cloud profile
python -m src.wildlife_pipeline.cloud.cli stage1 --profile cloud --input s3://wildlife-pipeline-data/test/
```

### Cloud Execution

```bash
# Submit Batch job
python -m src.wildlife_pipeline.cloud.cli stage1 --profile cloud --input s3://wildlife-pipeline-data/ --output s3://wildlife-pipeline-results/
```

## 🔧 Configuration

### AWS Credentials

The setup creates a profile in `~/.aws/credentials`:

```ini
[wildlife-pipeline-test]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = eu-north-1
```

### Environment Variables

```bash
# Set AWS profile
export AWS_PROFILE=wildlife-pipeline-test

# Set region
export AWS_DEFAULT_REGION=eu-north-1
```

### Cloud Configuration

The `profiles/cloud.yaml` file configures the cloud execution:

```yaml
storage:
  adapter: "s3"
  base_path: "s3://wildlife-pipeline-data"

queue:
  adapter: "sqs"
  queue_url: "https://sqs.eu-north-1.amazonaws.com/account/queue"

model:
  provider: "cloud"
  base_path: "s3://wildlife-pipeline-models"

runner:
  type: "cloud_batch"
  job_queue: "wildlife-pipeline-queue"
  job_definition: "wildlife-pipeline-job"
```

## 🛠️ Troubleshooting

### Common Issues

**1. S3 Access Denied:**
```bash
# Check bucket permissions
aws s3 ls s3://wildlife-pipeline-data
```

**2. Batch Job Fails:**
```bash
# Check job logs
aws logs describe-log-groups --log-group-name-prefix /aws/batch
```

**3. GPU Not Available:**
```bash
# Check instance types in region
aws ec2 describe-instance-types --filters Name=instance-type,Values=g4dn.*
```

### Debug Mode

```bash
# Enable verbose logging
export AWS_SDK_LOAD_CONFIG=1
export AWS_PROFILE=wildlife-pipeline-test

# Run with debug output
python scripts/test_aws_pipeline.py --comprehensive -v
```

### Cleanup

```bash
# Clean up test user
python scripts/create_aws_test_user.py --cleanup

# Delete S3 buckets (manual)
aws s3 rb s3://wildlife-pipeline-data --force
aws s3 rb s3://wildlife-pipeline-results --force
aws s3 rb s3://wildlife-pipeline-models --force
aws s3 rb s3://wildlife-pipeline-logs --force

# Delete ECR repository (manual)
aws ecr delete-repository --repository-name wildlife-pipeline --force

# Delete Batch resources (manual)
aws batch delete-compute-environment --compute-environment wildlife-pipeline-compute
aws batch delete-job-queue --job-queue wildlife-pipeline-queue
```

## 📊 Monitoring and Logging

### CloudWatch Logs

- **Batch Jobs:** `/aws/batch/wildlife-pipeline`
- **Application Logs:** `/aws/lambda/wildlife-pipeline`

### CloudWatch Metrics

- **Batch Jobs:** Job count, duration, success rate
- **S3 Operations:** Request count, data transfer
- **EC2 Instances:** CPU, memory, GPU utilization

### Cost Monitoring

- **S3 Storage:** Data storage costs
- **Batch Compute:** Instance hours and GPU costs
- **Data Transfer:** In/out data transfer costs

## 🔒 Security Considerations

### IAM Best Practices

1. **Least Privilege:** Only grant necessary permissions
2. **Regular Rotation:** Rotate access keys regularly
3. **Audit Logging:** Enable CloudTrail for audit logs
4. **MFA:** Enable multi-factor authentication

### Data Security

1. **Encryption:** Enable S3 server-side encryption
2. **Access Control:** Use bucket policies for access control
3. **Network Security:** Use VPC for network isolation
4. **Data Retention:** Set up lifecycle policies

## 📚 Additional Resources

- [AWS Batch Documentation](https://docs.aws.amazon.com/batch/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS IAM Documentation](https://docs.aws.amazon.com/iam/)
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)

## 🤝 Support

For issues with AWS setup:

1. Check the troubleshooting section above
2. Review AWS CloudTrail logs
3. Check AWS Batch job logs
4. Verify IAM permissions
5. Test with minimal configuration

## 📄 License

This AWS setup is part of the wildlife pipeline project and follows the same MIT License.
