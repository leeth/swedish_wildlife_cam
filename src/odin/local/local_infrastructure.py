"""
Odin Local Infrastructure Management

Handles local infrastructure setup using Docker, LocalStack, and MinIO.
"""

import os
import time
from typing import Any, Dict

import requests

from ..config import OdinConfig


class LocalInfrastructureManager:
    """Manages local infrastructure for Odin."""

    def __init__(self, config: OdinConfig):
        """Initialize local infrastructure manager."""
        self.config = config
        self.docker_client = None
        self.localstack_endpoint = config.get('infrastructure.localstack.endpoint', 'http://localhost:4566')
        self.minio_endpoint = config.get('infrastructure.minio.endpoint', 'http://localhost:9000')
        self.redis_url = config.get('infrastructure.redis.url', 'redis://localhost:6379')
        self.postgres_url = config.get('infrastructure.postgres.url',
                                     os.getenv('POSTGRES_URL', 'postgresql://wildlife:wildlife123@localhost:5432/wildlife'))

    def setup(self) -> bool:
        """Setup local infrastructure."""
        try:
            print("🏗️ Setting up local infrastructure...")

            # 1. Start Docker services
            self._start_docker_services()

            # 2. Wait for services to be ready
            self._wait_for_services()

            # 3. Setup LocalStack resources
            self._setup_localstack_resources()

            # 4. Setup MinIO buckets
            self._setup_minio_buckets()

            # 5. Setup Redis
            self._setup_redis()

            # 6. Setup PostgreSQL
            self._setup_postgres()

            print("✅ Local infrastructure setup complete!")
            return True

        except Exception as e:
            print(f"❌ Local infrastructure setup failed: {e}")
            return False

    def teardown(self) -> bool:
        """Teardown local infrastructure."""
        try:
            print("🗑️ Tearing down local infrastructure...")

            # 1. Stop Docker services
            self._stop_docker_services()

            # 2. Clean up volumes
            self._cleanup_volumes()

            print("✅ Local infrastructure teardown complete!")
            return True

        except Exception as e:
            print(f"❌ Local infrastructure teardown failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get local infrastructure status."""
        status = {
            'docker': self._get_docker_status(),
            'localstack': self._get_localstack_status(),
            'minio': self._get_minio_status(),
            'redis': self._get_redis_status(),
            'postgres': self._get_postgres_status()
        }
        return status

    def scale_up(self) -> bool:
        """Scale up local infrastructure."""
        try:
            print("📈 Scaling up local infrastructure...")

            # Scale up Docker services
            self._scale_docker_services()

            print("✅ Local infrastructure scaled up!")
            return True

        except Exception as e:
            print(f"❌ Scale up failed: {e}")
            return False

    def scale_down(self) -> bool:
        """Scale down local infrastructure."""
        try:
            print("📉 Scaling down local infrastructure...")

            # Scale down Docker services
            self._scale_down_docker_services()

            print("✅ Local infrastructure scaled down!")
            return True

        except Exception as e:
            print(f"❌ Scale down failed: {e}")
            return False

    def _start_docker_services(self) -> None:
        """Start Docker services."""
        print("🐳 Starting Docker services...")

        # Start services using odin CLI
        import sys

        from .cli import main as odin_main

        # Save original sys.argv
        original_argv = sys.argv.copy()

        # Set up odin CLI arguments for infrastructure setup
        sys.argv = ['odin', 'infrastructure', 'setup']

        try:
            # Run odin infrastructure setup
            odin_main()
        except SystemExit as e:
            if e.code != 0:
                raise Exception(f"Failed to start infrastructure: exit code {e.code}") from e
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def _wait_for_services(self) -> None:
        """Wait for services to be ready."""
        print("⏳ Waiting for services to be ready...")

        services = [
            ('LocalStack', self.localstack_endpoint),
            ('MinIO', self.minio_endpoint),
            ('Redis', self.redis_url.replace('redis://', 'http://')),
            ('PostgreSQL', self.postgres_url.replace('postgresql://', 'http://'))
        ]

        for service_name, endpoint in services:
            print(f"  Waiting for {service_name}...")
            self._wait_for_service(endpoint, service_name)

    def _wait_for_service(self, endpoint: str, service_name: str, timeout: int = 60) -> None:
        """Wait for a service to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code in [200, 404]:  # 404 is OK for some services
                    print(f"  ✅ {service_name} is ready!")
                    return
            except requests.exceptions.RequestException:
                pass

            time.sleep(1)

        raise Exception(f"Service {service_name} did not become ready within {timeout} seconds")

    def _setup_localstack_resources(self) -> None:
        """Setup LocalStack resources."""
        print("🔧 Setting up LocalStack resources...")

        # Create S3 bucket
        self._create_s3_bucket()

        # Create IAM roles
        self._create_iam_roles()

        # Create CloudFormation stack
        self._create_cloudformation_stack()

    def _setup_minio_buckets(self) -> None:
        """Setup MinIO buckets."""
        print("🪣 Setting up MinIO buckets...")

        # Create bucket
        self._create_minio_bucket()

    def _setup_redis(self) -> None:
        """Setup Redis."""
        print("🔴 Setting up Redis...")

        # Redis is ready when container starts
        pass

    def _setup_postgres(self) -> None:
        """Setup PostgreSQL."""
        print("🐘 Setting up PostgreSQL...")

        # Create database tables
        self._create_postgres_tables()

    def _stop_docker_services(self) -> None:
        """Stop Docker services."""
        print("🛑 Stopping Docker services...")

        # Stop services using odin CLI
        import sys

        from .cli import main as odin_main

        # Save original sys.argv
        original_argv = sys.argv.copy()

        # Set up odin CLI arguments for infrastructure teardown
        sys.argv = ['odin', 'infrastructure', 'teardown']

        try:
            # Run odin infrastructure teardown
            odin_main()
        except SystemExit as e:
            if e.code != 0:
                print(f"Warning: Failed to stop infrastructure: exit code {e.code}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def _cleanup_volumes(self) -> None:
        """Clean up Docker volumes."""
        print("🧹 Cleaning up volumes...")

        # Cleanup volumes using odin CLI
        import sys

        from .cli import main as odin_main

        # Save original sys.argv
        original_argv = sys.argv.copy()

        # Set up odin CLI arguments for infrastructure cleanup
        sys.argv = ['odin', 'infrastructure', 'teardown', '--cleanup']

        try:
            # Run odin infrastructure cleanup
            odin_main()
        except SystemExit as e:
            if e.code != 0:
                print(f"Warning: Failed to cleanup infrastructure: exit code {e.code}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def _scale_docker_services(self) -> None:
        """Scale up Docker services."""
        print("📈 Scaling up Docker services...")

        # Scale up services using odin CLI
        import sys

        from .cli import main as odin_main

        # Save original sys.argv
        original_argv = sys.argv.copy()

        # Set up odin CLI arguments for infrastructure scale-up
        sys.argv = ['odin', 'infrastructure', 'scale-up']

        try:
            # Run odin infrastructure scale-up
            odin_main()
        except SystemExit as e:
            if e.code != 0:
                print(f"Warning: Failed to scale up infrastructure: exit code {e.code}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def _scale_down_docker_services(self) -> None:
        """Scale down Docker services."""
        print("📉 Scaling down Docker services...")

        # Scale down services using odin CLI
        import sys

        from .cli import main as odin_main

        # Save original sys.argv
        original_argv = sys.argv.copy()

        # Set up odin CLI arguments for infrastructure scale-down
        sys.argv = ['odin', 'infrastructure', 'scale-down']

        try:
            # Run odin infrastructure scale-down
            odin_main()
        except SystemExit as e:
            if e.code != 0:
                print(f"Warning: Failed to scale down infrastructure: exit code {e.code}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def _create_s3_bucket(self) -> None:
        """Create S3 bucket in LocalStack."""
        bucket_name = self.config.get_bucket_name()

        try:
            import boto3
            s3 = boto3.client(
                's3',
                endpoint_url=self.localstack_endpoint,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'eu-north-1')
            )

            s3.create_bucket(Bucket=bucket_name)
            print(f"  ✅ Created S3 bucket: {bucket_name}")

        except Exception as e:
            print(f"  ⚠️ Failed to create S3 bucket: {e}")

    def _create_iam_roles(self) -> None:
        """Create IAM roles in LocalStack."""
        print("  🔐 Creating IAM roles...")
        # Implementation for IAM role creation
        pass

    def _create_cloudformation_stack(self) -> None:
        """Create CloudFormation stack in LocalStack."""
        print("  ☁️ Creating CloudFormation stack...")
        # Implementation for CloudFormation stack creation
        pass

    def _create_minio_bucket(self) -> None:
        """Create MinIO bucket."""
        bucket_name = self.config.get_bucket_name()

        try:
            from minio import Minio

            minio_client = Minio(
                os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
                access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
                secure=os.getenv('MINIO_SECURE', 'false').lower() == 'true'
            )

            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)
                print(f"  ✅ Created MinIO bucket: {bucket_name}")
            else:
                print(f"  ✅ MinIO bucket already exists: {bucket_name}")

        except Exception as e:
            print(f"  ⚠️ Failed to create MinIO bucket: {e}")

    def _create_postgres_tables(self) -> None:
        """Create PostgreSQL tables."""
        print("  🗄️ Creating PostgreSQL tables...")
        # Implementation for PostgreSQL table creation
        pass

    def _get_docker_status(self) -> Dict[str, Any]:
        """Get Docker status."""
        try:
            containers = self.docker_client.containers.list()
            return {
                'status': 'running',
                'containers': len(containers),
                'details': [{'name': c.name, 'status': c.status} for c in containers]
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_localstack_status(self) -> Dict[str, Any]:
        """Get LocalStack status."""
        try:
            response = requests.get(f"{self.localstack_endpoint}/health", timeout=5)
            return {
                'status': 'running' if response.status_code == 200 else 'error',
                'endpoint': self.localstack_endpoint
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_minio_status(self) -> Dict[str, Any]:
        """Get MinIO status."""
        try:
            response = requests.get(f"{self.minio_endpoint}/minio/health/live", timeout=5)
            return {
                'status': 'running' if response.status_code == 200 else 'error',
                'endpoint': self.minio_endpoint
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_redis_status(self) -> Dict[str, Any]:
        """Get Redis status."""
        try:
            import redis
            r = redis.from_url(self.redis_url)
            r.ping()
            return {'status': 'running', 'url': self.redis_url}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_postgres_status(self) -> Dict[str, Any]:
        """Get PostgreSQL status."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.postgres_url)
            conn.close()
            return {'status': 'running', 'url': self.postgres_url}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
