#!/bin/bash

# Alternative service startup without Docker daemon
echo "🚀 Starting Wildlife Pipeline Services (Alternative Method)..."

# Check if we can use Docker
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is accessible, starting services..."
    
    # Start services with docker-compose
    echo "🏗️ Starting infrastructure services..."
    docker-compose -f conf/docker/docker-compose.local.yml up -d
    
    echo "⏳ Waiting for services to be ready..."
    sleep 15
    
    echo "🔍 Checking service status..."
    docker-compose -f conf/docker/docker-compose.local.yml ps
    
else
    echo "❌ Docker is not accessible"
    echo "🔧 Please start Docker Desktop manually:"
    echo "  1. Open Docker Desktop on Windows"
    echo "  2. Wait for it to start completely"
    echo "  3. Try again"
    echo ""
    echo "🔄 Alternative: Start services manually:"
    echo "  - Start Docker Desktop"
    echo "  - Run: docker-compose -f conf/docker/docker-compose.local.yml up -d"
    echo ""
    echo "📋 Manual service startup:"
    echo "  - LocalStack: docker run -d -p 4566:4566 localstack/localstack:latest"
    echo "  - MinIO: docker run -d -p 9000:9000 -p 9001:9001 minio/minio:latest"
    echo "  - Redis: docker run -d -p 6379:6379 redis:7-alpine"
    echo "  - PostgreSQL: docker run -d -p 5432:5432 -e POSTGRES_DB=wildlife -e POSTGRES_USER=wildlife -e POSTGRES_PASSWORD=wildlife123 postgres:15-alpine"
fi
