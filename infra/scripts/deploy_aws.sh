#!/bin/bash
# Deploy wildlife pipeline to AWS.

set -e

# Configuration
REGION="${AWS_DEFAULT_REGION:-eu-north-1}"
BUCKET_NAME="${BUCKET_NAME:-wildlife-pipeline-$(date +%s)}"
STACK_NAME="${STACK_NAME:-wildlife-pipeline}"

echo "🚀 Deploying wildlife pipeline to AWS..."

# Create S3 bucket
echo "📦 Creating S3 bucket..."
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file infra/cloudformation/template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        BucketName=$BUCKET_NAME \
        Environment=prod \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

# Get stack outputs
echo "📋 Getting stack outputs..."
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
    --output text \
    --region $REGION)

echo "✅ AWS deployment completed!"
echo ""
echo "🚀 To start a pipeline execution, run:"
echo "aws stepfunctions start-execution \\"
echo "  --state-machine-arn $STATE_MACHINE_ARN \\"
echo "  --input '{\"input_uri\":\"s3://$BUCKET_NAME/raw/cam01/\",\"output_uri\":\"s3://$BUCKET_NAME/out/run_001/\",\"budget_dkk\":25,\"use_spot\":true,\"max_job_duration\":1800}'"

