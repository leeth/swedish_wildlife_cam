#!/bin/bash

# Manual LocalStack startup script
echo "🚀 Starting LocalStack manually..."

# Check if we can use Docker
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is accessible, starting LocalStack services..."
    
    # Start LocalStack
    echo "🏗️ Starting LocalStack..."
    docker run -d \
        --name wildlife-localstack \
        -p 4566:4566 \
        -p 4510-4559:4510-4559 \
        -e SERVICES=s3,lambda,logs,iam,cloudwatch,stepfunctions,batch,ecs,ecr,events \
        -e DEBUG=1 \
        -e LAMBDA_EXECUTOR=docker-reuse \
        -e DOCKER_HOST=unix:///var/run/docker.sock \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$(pwd)/infra:/opt/code/infra" \
        localstack/localstack:latest
    
    echo "⏳ Waiting for LocalStack to be ready..."
    sleep 20
    
    # Check if LocalStack is running
    if docker ps | grep -q wildlife-localstack; then
        echo "✅ LocalStack is running!"
        echo "🌐 LocalStack endpoint: http://localhost:4566"
        echo "📊 Services available: S3, Lambda, Step Functions, Batch, etc."
        
        # Test LocalStack
        echo "🧪 Testing LocalStack..."
        curl -s http://localhost:4566/_localstack/health > /dev/null && echo "✅ LocalStack health check passed" || echo "⚠️ LocalStack health check failed"
        
    else
        echo "❌ LocalStack failed to start"
        exit 1
    fi
    
else
    echo "❌ Docker is not accessible"
    echo "🔧 Please start Docker Desktop manually and try again"
    echo "   Or run: make fix-docker"
    exit 1
fi
