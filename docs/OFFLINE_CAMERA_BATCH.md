# 📷 Offline Camera Batch Processing

**Odins Ravne** - Cost-optimized batch processing for offline camera data

## 🎯 Overview

This feature is designed specifically for processing data from offline cameras where:
- **Time is not a factor** - Cost optimization is always enabled
- **Data is the priority** - Process as much data as possible cost-effectively
- **Batch processing** - Perfect for processing large amounts of offline camera data
- **Spot instances** - Up to 70% cost savings with automatic fallback

## 🚀 Quick Start

### Basic Usage
```bash
# Process offline camera data with cost optimization
scripts/infrastructure/run_offline_camera_batch.sh file:///data/camera1 s3://bucket/output

# With local Stage 3 output download
scripts/infrastructure/run_offline_camera_batch.sh \
  --local-output ./results \
  --download-stage3 \
  file:///data/camera1 s3://bucket/output
```

### Using Munin Cloud CLI Directly
```bash
# Cost-optimized batch processing
python src/munin/cloud/cli.py --profile cloud batch \
  --input file:///data/camera1 \
  --output s3://bucket/output \
  --local-output ./results \
  --download-stage3 \
  --cost-report
```

## 💰 Cost Optimization Features

### 1. **Always-On Cost Optimization**
- **Spot instances**: 50-70% cost savings
- **Automatic fallback**: Falls back to on-demand if spot unavailable
- **Infrastructure lifecycle**: Setup when needed, teardown when done
- **Batch-oriented**: Perfect for offline camera data processing

### 2. **Smart Resource Management**
- **Scale to zero**: Infrastructure costs nothing when idle
- **GPU optimization**: Uses GPU instances only when needed
- **Parallel processing**: Multiple jobs run simultaneously
- **Cost monitoring**: Real-time cost tracking and reporting

### 3. **Offline Camera Optimized**
- **Data-driven**: Optimized for processing large amounts of data
- **Time-independent**: No rush, focus on cost efficiency
- **Batch processing**: Process multiple cameras in batches
- **Local analysis**: Download and analyze results locally

## 📋 Usage Examples

### Process Single Camera
```bash
# Basic processing
scripts/infrastructure/run_offline_camera_batch.sh file:///data/camera1 s3://bucket/output

# With cost optimization settings
scripts/infrastructure/run_offline_camera_batch.sh \
  --spot-bid-percentage 80 \
  --max-vcpus 200 \
  --cost-report \
  file:///data/camera1 s3://bucket/output
```

### Process Multiple Cameras
```bash
# Process camera 1
scripts/infrastructure/run_offline_camera_batch.sh \
  --local-output ./camera1_results \
  --download-stage3 \
  file:///data/camera1 s3://bucket/camera1_output

# Process camera 2
scripts/infrastructure/run_offline_camera_batch.sh \
  --local-output ./camera2_results \
  --download-stage3 \
  file:///data/camera2 s3://bucket/camera2_output
```

### Advanced Configuration
```bash
# High priority processing with custom settings
scripts/infrastructure/run_offline_camera_batch.sh \
  --priority high \
  --spot-bid-percentage 90 \
  --max-vcpus 500 \
  --compression-window 15 \
  --min-confidence 0.6 \
  --cost-report \
  file:///data/camera1 s3://bucket/output
```

## 🔧 Cost Management Commands

### Infrastructure Management
```bash
# Setup infrastructure
python src/munin/cloud/cli.py --profile cloud cost setup --job-count 10

# Check status
python src/munin/cloud/cli.py --profile cloud cost status

# Get cost metrics
python src/munin/cloud/cli.py --profile cloud cost costs

# Teardown infrastructure
python src/munin/cloud/cli.py --profile cloud cost teardown
```

### Stage 3 Output Management
```bash
# Download Stage 3 output
python src/munin/cloud/cli.py --profile cloud cost download-stage3 \
  --cloud-path s3://bucket/output \
  --local-path ./stage3_results \
  --summary \
  --create-runner
```

## 📊 Cost Optimization Strategies

### 1. **Spot Instance Configuration**
```yaml
# profiles/cloud-cost-optimized.yaml
cloud:
  aws:
    compute:
      spot_instances: true
      bid_percentage: 70
      fallback_to_ondemand: true
      max_vcpus: 100
      min_vcpus: 0
      desired_vcpus: 0  # Scale to zero when idle
```

### 2. **Batch Processing Configuration**
```yaml
pipeline:
  cost_optimization:
    enabled: true
    spot_preferred: true
    fallback_timeout: 300  # 5 minutes
    cost_threshold: 0.5    # 50% savings threshold
    max_parallel_jobs: 10
    offline_camera_optimized: true
```

### 3. **Storage Optimization**
```yaml
storage:
  lifecycle:
    transition_to_ia: 30    # days
    transition_to_glacier: 90  # days
    delete_old_versions: 30  # days
```

## 🎯 Best Practices for Offline Camera Data

### 1. **Data Organization**
- **Camera-specific folders**: Organize data by camera ID
- **Batch processing**: Process multiple cameras in batches
- **Local staging**: Stage data locally before cloud processing
- **Result organization**: Keep results organized by camera

### 2. **Cost Optimization**
- **Spot instances**: Always use spot instances for cost savings
- **Batch processing**: Process multiple jobs together
- **Local analysis**: Download and analyze results locally
- **Infrastructure lifecycle**: Setup when needed, teardown when done

### 3. **Processing Workflow**
```bash
# 1. Organize data by camera
mkdir -p data/camera1 data/camera2 data/camera3

# 2. Process each camera with cost optimization
for camera in camera1 camera2 camera3; do
  scripts/infrastructure/run_offline_camera_batch.sh \
    --local-output ./results/$camera \
    --download-stage3 \
    file:///data/$camera s3://bucket/$camera_output
done

# 3. Analyze results locally
python ./results/camera1/run_stage3_local.py
python ./results/camera2/run_stage3_local.py
python ./results/camera3/run_stage3_local.py
```

## 📈 Monitoring and Reporting

### Cost Monitoring
```bash
# Check current costs
python src/munin/cloud/cli.py --profile cloud cost costs

# Monitor infrastructure status
python src/munin/cloud/cli.py --profile cloud cost status
```

### Cost Reports
The system generates detailed cost reports including:
- **Spot vs on-demand costs**: Cost savings from spot instances
- **Processing costs**: Cost per job processed
- **Storage costs**: S3 storage and transfer costs
- **Infrastructure costs**: Compute environment costs
- **Total cost breakdown**: Complete cost analysis

### Performance Metrics
- **Jobs processed**: Number of jobs completed
- **Success rate**: Percentage of successful jobs
- **Processing time**: Total processing time
- **Cost per job**: Average cost per job processed
- **Savings percentage**: Cost savings from optimization

## 🛠️ Troubleshooting

### Common Issues

#### 1. **Spot Instance Interruptions**
```bash
# Check spot instance status
aws ec2 describe-spot-instance-requests --region eu-north-1

# Monitor spot pricing
aws ec2 describe-spot-price-history \
  --instance-types g4dn.xlarge \
  --product-descriptions "Linux/UNIX" \
  --region eu-north-1
```

#### 2. **Infrastructure Scaling Issues**
```bash
# Check compute environment status
python src/munin/cloud/cli.py --profile cloud cost status

# Force teardown
python src/munin/cloud/cli.py --profile cloud cost teardown
```

#### 3. **Stage 3 Download Issues**
```bash
# Check S3 permissions
aws s3 ls s3://your-bucket/output/stage3/

# Test download manually
python src/munin/cloud/cli.py --profile cloud cost download-stage3 \
  --cloud-path s3://your-bucket/output \
  --local-path ./test_download
```

## 🔒 Security Considerations

### IAM Permissions
The cost optimization features require additional IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSpotPriceHistory",
        "ec2:DescribeSpotFleetRequests",
        "ec2:RequestSpotFleet",
        "ec2:CancelSpotFleetRequests",
        "batch:UpdateComputeEnvironment",
        "batch:DescribeComputeEnvironments",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

### Cost Controls
- **Budget alerts**: Set up AWS Budgets for cost monitoring
- **Resource tagging**: Tag resources for cost allocation
- **Access logging**: Enable CloudTrail for audit trails

## 📚 Additional Resources

- [AWS Spot Instances Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html)
- [AWS Batch Documentation](https://docs.aws.amazon.com/batch/)
- [Cost Optimization Best Practices](https://aws.amazon.com/pricing/cost-optimization/)
- [CloudFormation Templates](aws/cloudformation-template-cost-optimized.yaml)

## 🤝 Support

For issues and questions:
- **GitHub Issues**: Create an issue in the repository
- **Documentation**: Check this guide and inline documentation
- **AWS Support**: For AWS-specific issues

---

**Happy cost-optimized offline camera processing! 📷💰**
