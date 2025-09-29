#!/bin/bash
# Deploy wildlife pipeline to LocalStack for local development.

set -e

# Configuration
REGION="eu-north-1"
ACCOUNT_ID="000000000000"
BUCKET_NAME="wildlife"
STACK_NAME="wildlife-pipeline-local"

echo "🚀 Deploying wildlife pipeline to LocalStack..."

# Start LocalStack if not running
if ! docker ps | grep -q localstack; then
    echo "Starting LocalStack..."
    docker-compose up -d localstack
    sleep 10
fi

# Set AWS CLI to use LocalStack
export AWS_ENDPOINT_URL="http://localhost:4566"
export AWS_DEFAULT_REGION="$REGION"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"

# Create S3 bucket
echo "📦 Creating S3 bucket..."
awslocal s3 mb s3://$BUCKET_NAME || true

# Create IAM roles
echo "🔐 Creating IAM roles..."

# Step Functions execution role
awslocal iam create-role \
    --role-name stepfn-exec \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "states.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' || true

# Lambda execution role
awslocal iam create-role \
    --role-name lambda-exec \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' || true

# Batch service role
awslocal iam create-role \
    --role-name batch-service \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "batch.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' || true

# Batch instance role
awslocal iam create-role \
    --role-name batch-instance \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' || true

# Attach policies
echo "📋 Attaching policies..."
awslocal iam attach-role-policy \
    --role-name stepfn-exec \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSStepFunctionsFullAccess || true

awslocal iam attach-role-policy \
    --role-name lambda-exec \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || true

awslocal iam attach-role-policy \
    --role-name batch-service \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole || true

awslocal iam attach-role-policy \
    --role-name batch-instance \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role || true

# Create Lambda functions
echo "🔧 Creating Lambda functions..."

# Guard Budget Lambda
awslocal lambda create-function \
    --function-name guard-budget \
    --runtime python3.11 \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-exec \
    --handler handler.handler \
    --zip-file fileb://dist/guard_budget.zip \
    --timeout 60 || true

# Stage 0 EXIF Lambda
awslocal lambda create-function \
    --function-name stage0-exif \
    --runtime python3.11 \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-exec \
    --handler handler.handler \
    --zip-file fileb://dist/stage0_exif.zip \
    --timeout 300 || true

# Stage 2 Post Lambda
awslocal lambda create-function \
    --function-name stage2-post \
    --runtime python3.11 \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-exec \
    --handler handler.handler \
    --zip-file fileb://dist/stage2_post.zip \
    --timeout 300 || true

# Weather Enrichment Lambda
awslocal lambda create-function \
    --function-name weather-enrichment \
    --runtime python3.11 \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-exec \
    --handler handler.handler \
    --zip-file fileb://dist/weather_enrichment.zip \
    --timeout 300 || true

# Write Parquet Lambda
awslocal lambda create-function \
    --function-name write-parquet \
    --runtime python3.11 \
    --role arn:aws:iam::$ACCOUNT_ID:role/lambda-exec \
    --handler handler.handler \
    --zip-file fileb://dist/write_parquet.zip \
    --timeout 300 || true

# Create Batch compute environment
echo "🖥️ Creating Batch compute environment..."
awslocal batch create-compute-environment \
    --cli-input-json file://infra/batch/compute_environment.json || true

# Create Batch job queue
echo "📋 Creating Batch job queue..."
awslocal batch create-job-queue \
    --cli-input-json file://infra/batch/job_queue.json || true

# Create Batch job definition
echo "📝 Creating Batch job definition..."
awslocal batch register-job-definition \
    --cli-input-json file://infra/batch/job_definition.json || true

# Create Step Functions state machine
echo "🔄 Creating Step Functions state machine..."
awslocal stepfunctions create-state-machine \
    --name wildlife-pipeline \
    --definition file://infra/stepfn/state_machine.asl.json \
    --role-arn arn:aws:iam::$ACCOUNT_ID:role/stepfn-exec || true

echo "✅ LocalStack deployment completed!"
echo ""
echo "🚀 To start a pipeline execution, run:"
echo "awslocal stepfunctions start-execution \\"
echo "  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:wildlife-pipeline \\"
echo "  --input '{\"input_uri\":\"s3://$BUCKET_NAME/raw/cam01/\",\"output_uri\":\"s3://$BUCKET_NAME/out/run_001/\",\"budget_dkk\":25,\"use_spot\":true,\"max_job_duration\":1800}'"

