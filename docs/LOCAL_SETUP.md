# Local Odin Setup

This document describes how to run Odin locally without real AWS infrastructure.

## 🏗️ Local Infrastructure

Odin can run locally using:

- **LocalStack** - AWS API emulator
- **MinIO** - S3-compatible storage
- **Docker** - Containerized processing
- **Redis** - Job queues and caching
- **PostgreSQL** - Metadata storage

## 🚀 Quick Start

### 1. Start Local Infrastructure

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Check status
docker-compose -f docker-compose.local.yml ps
```

### 2. Test Odin CLI

```bash
# Test with local configuration
./scripts/odin --config odin.local.yaml infrastructure status

# Run complete pipeline
./scripts/odin --config odin.local.yaml pipeline run
```

### 3. Run Local Tests

```bash
# Run comprehensive local tests
./scripts/test_local_odin.sh
```

## 📋 Available Services

### LocalStack (AWS Emulator)
- **Endpoint**: http://localhost:4566
- **Services**: S3, Batch, IAM, CloudFormation, EC2, Logs
- **Access Key**: test
- **Secret Key**: test

### MinIO (S3 Storage)
- **Endpoint**: http://localhost:9000
- **Console**: http://localhost:9001
- **Access Key**: minioadmin
- **Secret Key**: minioadmin123

### Redis (Caching)
- **Endpoint**: redis://localhost:6379
- **Database**: 0

### PostgreSQL (Metadata)
- **Endpoint**: postgresql://wildlife:wildlife123@localhost:5432/wildlife
- **Database**: wildlife

## 🔧 Configuration

### Local Configuration (`odin.local.yaml`)

```yaml
infrastructure:
  provider: "local"
  localstack:
    endpoint: "http://localhost:4566"
  minio:
    endpoint: "http://localhost:9000"
  redis:
    url: "redis://localhost:6379"
  postgres:
    url: "postgresql://wildlife:wildlife123@localhost:5432/wildlife"
```

## 🐳 Docker Services

### Core Services
- `localstack` - AWS API emulator
- `minio` - S3-compatible storage
- `redis` - Caching and job queues
- `postgres` - Metadata storage

### Processing Services
- `wildlife-worker` - Processing containers
- `wildlife-scheduler` - Job scheduling

## 📊 Monitoring

### Service Health
```bash
# Check LocalStack
curl http://localhost:4566/health

# Check MinIO
curl http://localhost:9000/minio/health/live

# Check Redis
redis-cli ping

# Check PostgreSQL
psql postgresql://wildlife:wildlife123@localhost:5432/wildlife -c "SELECT 1"
```

### Docker Status
```bash
# Check running containers
docker ps

# Check logs
docker-compose -f docker-compose.local.yml logs
```

## 🧪 Testing

### Unit Tests
```bash
# Run unit tests
./scripts/run_tests.sh
```

### Integration Tests
```bash
# Run local integration tests
./scripts/test_local_odin.sh
```

### Manual Testing
```bash
# Test infrastructure
./scripts/odin --config odin.local.yaml infrastructure status

# Test pipeline
./scripts/odin --config odin.local.yaml pipeline run

# Test data management
./scripts/odin --config odin.local.yaml data list
```

## 🗑️ Cleanup

### Stop Services
```bash
# Stop all services
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes
docker-compose -f docker-compose.local.yml down -v
```

### Clean Data
```bash
# Remove all data
rm -rf localstack-data minio-data redis-data postgres-data
```

## 🔍 Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Check if ports 4566, 9000, 6379, 5432 are available
   - Use `docker-compose down` to free ports

2. **Service Not Ready**
   - Wait for services to start (30-60 seconds)
   - Check logs: `docker-compose logs <service>`

3. **Permission Issues**
   - Ensure Docker has proper permissions
   - Check volume mounts

4. **Network Issues**
   - Ensure Docker network is created
   - Check container connectivity

### Debug Commands

```bash
# Check service logs
docker-compose -f docker-compose.local.yml logs <service>

# Check container status
docker ps -a

# Check network
docker network ls

# Check volumes
docker volume ls
```

## 📚 Additional Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [MinIO Documentation](https://docs.min.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Redis Documentation](https://redis.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
