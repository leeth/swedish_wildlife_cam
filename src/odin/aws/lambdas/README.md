# 🚀 Lambda Functions

Lambda functions for the Odins Ravne wildlife pipeline system.

## 📁 Structure

```
src/lambdas/
├── guard_budget/           # Budget validation
├── guard_inputs/           # Input validation
├── stage0_exif/           # EXIF processing
├── stage2_post/           # Post-processing
├── weather_enrichment/    # Weather data enrichment
├── write_parquet/         # Final output generation
└── batch_fallback/        # Batch job fallback
```

## 🎯 Functions Overview

### Guard Functions

#### `guard_budget/`
- **Purpose**: Validates cost estimates before starting pipeline
- **Input**: Budget parameters, cost estimates
- **Output**: Approval/rejection decision
- **Timeout**: 30 seconds

#### `guard_inputs/`
- **Purpose**: Validates input data and parameters
- **Input**: S3 paths, file formats, metadata
- **Output**: Validation results
- **Timeout**: 30 seconds

### Processing Functions

#### `stage0_exif/`
- **Purpose**: EXIF data extraction and time correction
- **Input**: S3 paths to images/videos
- **Output**: Processed EXIF data
- **Timeout**: 5 minutes

#### `stage2_post/`
- **Purpose**: Post-processing and GPS clustering
- **Input**: Detection results from Stage 1
- **Output**: Clustered observations
- **Timeout**: 10 minutes

#### `weather_enrichment/`
- **Purpose**: Weather data enrichment for positive observations
- **Input**: GPS coordinates, timestamps
- **Output**: Weather data
- **Timeout**: 5 minutes

#### `write_parquet/`
- **Purpose**: Final output generation
- **Input**: Processed data from all stages
- **Output**: Parquet files in S3
- **Timeout**: 5 minutes

#### `batch_fallback/`
- **Purpose**: Fallback for failed batch jobs
- **Input**: Batch job parameters
- **Output**: Alternative processing results
- **Timeout**: 15 minutes

## 🚀 Deployment

### Local Development

```bash
# Deploy to LocalStack
make deploy-local

# Test individual functions
python -m src.lambdas.guard_budget.handler
python -m src.lambdas.stage0_exif.handler
```

### Production (AWS)

```bash
# Deploy to AWS
make deploy-aws

# Test functions
aws lambda invoke --function-name wildlife-guard-budget response.json
aws lambda invoke --function-name wildlife-stage0-exif response.json
```

## 🔧 Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_DEFAULT_REGION=eu-north-1
AWS_S3_BUCKET=wildlife-bucket

# Pipeline Configuration
WILDLIFE_PIPELINE_ENV=production
WILDLIFE_PIPELINE_BUDGET=1000
WILDLIFE_PIPELINE_MAX_IMAGES=1000

# Weather API
YR_NO_API_KEY=your-yr-api-key
```

### Function Configuration

Each function includes:
- `handler.py` - Main function logic
- `requirements.txt` - Function dependencies
- `Dockerfile` - Container configuration (if needed)
- `test_handler.py` - Unit tests

## 🧪 Testing

### Unit Tests

```bash
# Test all functions
python -m pytest src/lambdas/ -v

# Test specific function
python -m pytest src/lambdas/guard_budget/ -v
```

### Integration Tests

```bash
# Test with LocalStack
make deploy-local
python -m pytest test/integration/test_lambdas.py -v
```

## 📊 Monitoring

### CloudWatch Logs

Each function logs to CloudWatch with structured logging:

```python
import json
import logging

logger = logging.getLogger(__name__)

def handler(event, context):
    logger.info("Function started", extra={
        "function_name": context.function_name,
        "request_id": context.aws_request_id,
        "event": event
    })
    
    try:
        # Function logic
        result = process_data(event)
        
        logger.info("Function completed successfully", extra={
            "result": result
        })
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except Exception as e:
        logger.error("Function failed", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

### Metrics

Functions automatically report:
- Execution duration
- Memory usage
- Error rates
- Invocation counts

## 🔐 Security

### IAM Permissions

Each function has minimal required permissions:

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

### Environment Variables

- Never hardcode secrets
- Use AWS Systems Manager Parameter Store
- Encrypt sensitive data
- Rotate credentials regularly

## 📈 Performance

### Optimization Tips

- **Memory**: Allocate appropriate memory (128MB - 3GB)
- **Timeout**: Set reasonable timeouts (30s - 15min)
- **Cold Start**: Use provisioned concurrency for critical functions
- **Dependencies**: Minimize package size
- **Connection Pooling**: Reuse connections when possible

### Cost Optimization

- **Spot Instances**: Use for batch processing
- **Reserved Capacity**: For predictable workloads
- **Auto-scaling**: Scale to zero when idle
- **Monitoring**: Track costs and optimize

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add function logic
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under MIT License - see LICENSE file for details.

---

**Lambda Functions** - Serverless processing for the Wildlife Intelligence System
