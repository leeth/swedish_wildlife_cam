#!/bin/bash

# Start local services without requiring Docker daemon
echo "🚀 Starting Wildlife Pipeline Local Services..."

# Check if Docker is accessible
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is accessible, starting full stack..."
    
    # Start all services
    echo "🏗️ Starting infrastructure services..."
    docker-compose -f conf/docker/docker-compose.local.yml up -d localstack minio redis postgres
    
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    echo "🔍 Checking service status..."
    docker-compose -f conf/docker/docker-compose.local.yml ps
    
    echo "✅ Infrastructure services started!"
    echo ""
    echo "🌐 Available services:"
    echo "  - LocalStack: http://localhost:4566"
    echo "  - MinIO: http://localhost:9000 (Console: http://localhost:9001)"
    echo "  - Redis: redis://localhost:6379"
    echo "  - PostgreSQL: postgresql://wildlife:wildlife123@localhost:5432/wildlife"
    
else
    echo "❌ Docker is not accessible"
    echo "🔧 Please fix Docker permissions first:"
    echo "  1. Start Docker Desktop"
    echo "  2. Run: sudo usermod -aG docker \$USER"
    echo "  3. Log out and log back in"
    echo "  4. Or run: make fix-docker"
    echo ""
    echo "🔄 Alternative: Start services manually:"
    echo "  - Start Docker Desktop"
    echo "  - Run: docker-compose -f conf/docker/docker-compose.local.yml up -d"
fi
