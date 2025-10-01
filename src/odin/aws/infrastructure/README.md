# 🏗️ Infrastructure as Code

Infrastructure definitions and deployment scripts for the Odins Ravne wildlife pipeline system.

## 📁 Structure

```
src/infra/
├── stepfn/                 # Step Functions definitions
│   ├── state_machine.asl.json
│   └── workflows/
├── batch/                  # AWS Batch configurations
│   ├── job_definitions/
│   ├── job_queues/
│   └── compute_environments/
├── cloudformation/         # CloudFormation templates
│   ├── main.yaml
│   ├── parameters/
│   └── outputs/
└── scripts/               # Deployment scripts
    ├── deploy_aws.sh
    ├── deploy_localstack.sh
    └── cleanup.sh
```

## 🎯 Infrastructure Components

### Step Functions

#### `stepfn/state_machine.asl.json`
- **Purpose**: Main workflow orchestration
- **Stages**: GuardBudget → Stage0 → Stage1 → Stage2 → WeatherEnrichment → WriteParquet
- **Error Handling**: Retry logic and fallback mechanisms
- **Timeout**: 2 hours maximum execution

#### `stepfn/workflows/`
- **Purpose**: Reusable workflow components
- **Components**: Parallel processing, error handling, conditional logic
- **Integration**: Lambda functions, Batch jobs, S3 operations

### AWS Batch

#### `batch/job_definitions/`
- **Purpose**: Job definition templates
- **Components**: Container images, resource requirements, environment variables
- **Optimization**: GPU support, memory allocation, timeout settings

#### `batch/job_queues/`
- **Purpose**: Job queue configurations
- **Priority**: High, normal, low priority queues
- **Scaling**: Auto-scaling based on queue depth

#### `batch/compute_environments/`
- **Purpose**: Compute environment definitions
- **Instance Types**: GPU-enabled instances for ML workloads
- **Spot Instances**: Cost optimization with spot pricing
- **Scaling**: Scale to zero when idle

### CloudFormation

#### `cloudformation/main.yaml`
- **Purpose**: Complete infrastructure template
- **Components**: S3, Batch, Lambda, Step Functions, IAM
- **Parameters**: Configurable via parameters
- **Outputs**: Resource ARNs and endpoints

#### `cloudformation/parameters/`
- **Purpose**: Environment-specific parameters
- **Files**: `dev.yaml`, `staging.yaml`, `prod.yaml`
- **Security**: Encrypted parameter storage

## 🚀 Deployment

### Local Development (LocalStack)

```bash
# Start LocalStack
make up-localstack

# Deploy to LocalStack
make deploy-local

# Check status
make status-local
```

### Production (AWS)

```bash
# Deploy to AWS
make deploy-aws

# Check deployment
aws cloudformation describe-stacks --stack-name wildlife-stack
```

### Cleanup

```bash
# Destroy local resources
make destroy-local

# Destroy AWS resources
aws cloudformation delete-stack --stack-name wildlife-stack
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

### Cost Optimization

#### Spot Instances
```yaml
batch:
  compute_environment:
    instance_types: ["g4dn.xlarge", "g4dn.2xlarge"]
    spot_bid_percentage: 70
    max_vcpus: 100
    min_vcpus: 0
    desired_vcpus: 0
```

#### Auto-scaling
```yaml
batch:
  job_queue:
    priority: 1
    compute_environment_order:
      - compute_environment: "gpu-compute-env"
        order: 1
      - compute_environment: "cpu-compute-env"
        order: 2
```

## 📊 Monitoring

### CloudWatch Metrics

- **Step Functions**: Execution duration, success rate, error rate
- **Lambda**: Invocation count, duration, error rate
- **Batch**: Job count, queue depth, compute utilization
- **S3**: Request count, data transfer, storage usage

### Cost Monitoring

- **Budget Alerts**: Automatic budget enforcement
- **Cost Reports**: Daily, weekly, monthly reports
- **Resource Tagging**: Cost allocation by project
- **Spot Instance Savings**: Track spot instance savings

### Logging

- **Centralized Logging**: All logs in CloudWatch
- **Structured Logging**: JSON format for easy parsing
- **Log Retention**: 30 days for development, 90 days for production
- **Log Aggregation**: Cross-service log correlation

## 🔐 Security

### IAM Roles

#### Step Functions Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "batch:SubmitJob",
        "batch:DescribeJobs",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Lambda Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::wildlife-bucket/*"
    }
  ]
}
```

### Network Security

- **VPC**: Isolated network environment
- **Security Groups**: Restrictive inbound/outbound rules
- **NAT Gateway**: Secure outbound internet access
- **Private Subnets**: Lambda and Batch in private subnets

### Data Security

- **Encryption**: S3 server-side encryption
- **Access Control**: Bucket policies and IAM
- **Data Lifecycle**: Automatic data retention policies
- **Backup**: Cross-region replication

## 📈 Performance

### Optimization Strategies

#### Compute Optimization
- **GPU Instances**: Use GPU for ML workloads
- **Spot Instances**: 70% cost savings
- **Auto-scaling**: Scale to zero when idle
- **Resource Right-sizing**: Match resources to workload

#### Storage Optimization
- **S3 Storage Classes**: Intelligent tiering
- **Data Compression**: Reduce storage costs
- **Lifecycle Policies**: Automatic data archiving
- **Cross-region Replication**: Data availability

#### Network Optimization
- **VPC Endpoints**: Reduce data transfer costs
- **CloudFront**: CDN for static content
- **Data Transfer**: Minimize cross-region transfers
- **Connection Pooling**: Reuse connections

### Cost Optimization

#### Budget Controls
- **Daily Budget**: $50/day for development
- **Monthly Budget**: $1000/month for production
- **Alert Thresholds**: 80% budget usage alerts
- **Automatic Shutdown**: Stop resources at budget limit

#### Resource Optimization
- **Spot Instances**: Use spot for batch jobs
- **Reserved Instances**: For predictable workloads
- **Auto-scaling**: Scale down during low usage
- **Resource Tagging**: Track costs by project

## 🧪 Testing

### Infrastructure Tests

```bash
# Test CloudFormation template
aws cloudformation validate-template --template-body file://src/infra/cloudformation/main.yaml

# Test Step Functions definition
aws stepfunctions validate-state-machine --definition file://src/infra/stepfn/state_machine.asl.json
```

### Integration Tests

```bash
# Test complete deployment
python -m pytest test/integration/test_infrastructure.py -v

# Test individual components
python -m pytest test/integration/test_step_functions.py -v
python -m pytest test/integration/test_batch.py -v
```

## 🔄 CI/CD

### Deployment Pipeline

1. **Code Commit**: Trigger deployment
2. **Template Validation**: Validate CloudFormation
3. **Security Scan**: Check for security issues
4. **Deploy Staging**: Deploy to staging environment
5. **Integration Tests**: Run integration tests
6. **Deploy Production**: Deploy to production
7. **Health Check**: Verify deployment

### Automated Testing

- **Infrastructure Tests**: Validate templates
- **Security Tests**: Check for vulnerabilities
- **Performance Tests**: Load testing
- **Cost Tests**: Budget validation

## 📚 Documentation

### Architecture Diagrams

- **System Overview**: High-level architecture
- **Data Flow**: Data processing pipeline
- **Security Model**: Security architecture
- **Cost Model**: Cost optimization strategies

### Runbooks

- **Deployment**: Step-by-step deployment guide
- **Troubleshooting**: Common issues and solutions
- **Monitoring**: Monitoring and alerting setup
- **Maintenance**: Regular maintenance tasks

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add infrastructure components
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under MIT License - see LICENSE file for details.

---

**Infrastructure as Code** - Scalable and cost-optimized infrastructure for the Wildlife Intelligence System
