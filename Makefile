# Wildlife Pipeline Makefile

.PHONY: help up-localstack down-localstack deploy-local run-local destroy-local deploy-aws run-aws build-docker test-local doctor-local

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
	@echo "  doctor-local       - Sanity check LocalStack services"
	@echo ""
	@echo "AWS Production:"
	@echo "  deploy-aws         - Deploy to AWS"
	@echo "  run-aws            - Run pipeline in AWS"
	@echo ""
	@echo "Development:"
	@echo "  test-local         - Run local tests"

# LocalStack Development
up-localstack:
	@echo "🚀 Starting LocalStack..."
	docker-compose -f conf/docker/docker-compose.yml up -d localstack
	@echo "⏳ Waiting for LocalStack to be ready..."
	sleep 15
	@echo "✅ LocalStack is ready!"

down-localstack:
	@echo "🛑 Stopping LocalStack..."
	docker-compose -f conf/docker/docker-compose.yml down

deploy-local: up-localstack
	@echo "📦 Deploying to LocalStack..."
	chmod +x src/odin/infrastructure/scripts/deploy_localstack.sh
	./src/odin/infrastructure/scripts/deploy_localstack.sh
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
	@echo "☁️ Deploying to AWS (EU-NORTH-1 ONLY)..."
	export AWS_DEFAULT_REGION=eu-north-1
	chmod +x src/odin/aws/infrastructure/scripts/deploy_aws.sh
	./src/odin/aws/infrastructure/scripts/deploy_aws.sh
	@echo "✅ AWS deployment completed in EU-NORTH-1!"

run-aws:
	@echo "🏃 Running pipeline in AWS..."
	export AWS_DEFAULT_REGION=eu-north-1
	@echo "Please run the following command with your actual state machine ARN:"

# CI/CD Targets
lint:
	@echo "🔍 Running linting..."
	ruff check .
	ruff format --check .

typecheck:
	@echo "🔍 Running type checking..."
	mypy src/

test:
	@echo "🧪 Running tests..."
	pytest --cov=src --cov-report=xml --cov-report=html

schema:
	@echo "📊 Generating schemas..."
	python -c "from src.common.schemas.events import EventsSchema; EventsSchema().to_json_schema_file('models/schemas/events_v1.json')"
	python -c "from src.common.schemas.detections import DetectionsSchema; DetectionsSchema().to_json_schema_file('models/schemas/detections_v1.json')"
	python -c "from src.common.schemas.metadata import MetadataSchema; MetadataSchema().to_json_schema_file('models/schemas/metadata_v1.json')"

ge:
	@echo "🧪 Running Great Expectations tests..."
	python -c "from tests.expectations.events_v1_suite import validate_events_dataframe; print('Events validation passed')"
	python -c "from tests.expectations.detections_v1_suite import validate_detections_dataframe; print('Detections validation passed')"

build:
	@echo "🐳 Building Docker image..."
	docker buildx build --tag wildlife-pipeline:latest --cache-from type=gha --cache-to type=gha,mode=max .
	@echo "aws stepfunctions start-execution \\"
	@echo "  --state-machine-arn <YOUR_STATE_MACHINE_ARN> \\"
	@echo "  --input '{\"input_uri\":\"s3://your-bucket/raw/cam01/\",\"output_uri\":\"s3://your-bucket/out/run_001/\",\"budget_dkk\":25,\"use_spot\":true,\"max_job_duration\":1800}'"

# Development

test-local:
	@echo "🧪 Running local tests..."
	python -m pytest tests/ -v
	@echo "✅ Tests completed!"

# Utility targets
logs-local:
	@echo "📋 Showing LocalStack logs..."
	docker-compose -f conf/docker/docker-compose.yml logs -f localstack

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

# Doctor - Sanity check LocalStack services
doctor-local:
	@echo "🩺 Checking LocalStack services..."
	@echo "📊 LocalStack version:"
	@awslocal --version || echo "❌ awslocal not found"
	@echo ""
	@echo "🔍 Step Functions:"
	@awslocal stepfunctions list-state-machines --region=eu-north-1 || echo "❌ Step Functions not available"
	@echo ""
	@echo "🔍 Lambda:"
	@awslocal lambda list-functions --region=eu-north-1 || echo "❌ Lambda not available"
	@echo ""
	@echo "🔍 Batch:"
	@awslocal batch describe-job-queues --region=eu-north-1 || echo "❌ Batch not available"
	@echo ""
	@echo "🔍 S3:"
	@awslocal s3 ls --region=eu-north-1 || echo "❌ S3 not available"
	@echo ""
	@echo "🔍 CloudWatch Logs:"
	@awslocal logs describe-log-groups --region=eu-north-1 || echo "❌ CloudWatch Logs not available"
	@echo ""
	@echo "✅ LocalStack health check completed!"


# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose -f conf/docker/docker-compose.yml down -v
	docker system prune -f
	@echo "✅ Cleanup completed!"

