# Wildlife Pipeline Makefile

.PHONY: help up-localstack down-localstack deploy-local run-local destroy-local deploy-aws run-aws build-docker test-local

# Default target
help:
	@echo "Wildlife Pipeline - Available Commands:"
	@echo ""
	@echo "LocalStack Development:"
	@echo "  up-localstack     - Start LocalStack services"
	@echo "  down-localstack    - Stop LocalStack services"
	@echo "  deploy-local       - Deploy to LocalStack"
	@echo "  run-local          - Run pipeline in LocalStack"
	@echo "  destroy-local      - Clean up LocalStack resources"
	@echo ""
	@echo "AWS Production:"
	@echo "  deploy-aws         - Deploy to AWS"
	@echo "  run-aws            - Run pipeline in AWS"
	@echo ""
	@echo "Development:"
	@echo "  build-docker       - Build Docker images"
	@echo "  test-local         - Run local tests"

# LocalStack Development
up-localstack:
	@echo "🚀 Starting LocalStack..."
	docker-compose up -d localstack
	@echo "⏳ Waiting for LocalStack to be ready..."
	sleep 15
	@echo "✅ LocalStack is ready!"

down-localstack:
	@echo "🛑 Stopping LocalStack..."
	docker-compose down

deploy-local: up-localstack
	@echo "📦 Deploying to LocalStack..."
	chmod +x infra/scripts/deploy_localstack.sh
	./infra/scripts/deploy_localstack.sh
	@echo "✅ LocalStack deployment completed!"

run-local:
	@echo "🏃 Running pipeline in LocalStack..."
	awslocal stepfunctions start-execution \
		--state-machine-arn arn:aws:states:us-east-1:000000000000:stateMachine:wildlife-pipeline \
		--input '{"input_uri":"s3://wildlife/raw/cam01/","output_uri":"s3://wildlife/out/run_001/","budget_dkk":25,"use_spot":true,"max_job_duration":1800}'
	@echo "✅ Pipeline execution started!"

destroy-local:
	@echo "🧹 Cleaning up LocalStack resources..."
	awslocal s3 rb s3://wildlife --force || true
	awslocal stepfunctions delete-state-machine --state-machine-arn arn:aws:states:us-east-1:000000000000:stateMachine:wildlife-pipeline || true
	@echo "✅ LocalStack cleanup completed!"

# AWS Production
deploy-aws:
	@echo "☁️ Deploying to AWS..."
	export AWS_DEFAULT_REGION=eu-north-1
	chmod +x infra/scripts/deploy_aws.sh
	./infra/scripts/deploy_aws.sh
	@echo "✅ AWS deployment completed!"

run-aws:
	@echo "🏃 Running pipeline in AWS..."
	export AWS_DEFAULT_REGION=eu-north-1
	@echo "Please run the following command with your actual state machine ARN:"
	@echo "aws stepfunctions start-execution \\"
	@echo "  --state-machine-arn <YOUR_STATE_MACHINE_ARN> \\"
	@echo "  --input '{\"input_uri\":\"s3://your-bucket/raw/cam01/\",\"output_uri\":\"s3://your-bucket/out/run_001/\",\"budget_dkk\":25,\"use_spot\":true,\"max_job_duration\":1800}'"

# Development
build-docker:
	@echo "🐳 Building Docker images..."
	docker build -t wildlife-detector:latest -f docker/munin-detector/Dockerfile .
	@echo "✅ Docker images built!"

test-local:
	@echo "🧪 Running local tests..."
	python -m pytest tests/ -v
	@echo "✅ Tests completed!"

# Utility targets
logs-local:
	@echo "📋 Showing LocalStack logs..."
	docker-compose logs -f localstack

status-local:
	@echo "📊 LocalStack status:"
	awslocal stepfunctions list-state-machines
	awslocal lambda list-functions
	awslocal batch describe-job-queues

# Environment setup
setup-dev:
	@echo "🔧 Setting up development environment..."
	pip install -r requirements.txt
	pip install awscli-local
	@echo "✅ Development environment ready!"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup completed!"

