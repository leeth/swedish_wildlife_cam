"""
Odin Local Pipeline Management

Handles local pipeline execution using Docker containers.
"""

import os
import time
from typing import Any, Dict, Optional

import docker

from .config import OdinConfig


class LocalPipelineManager:
    """Manages local pipeline execution for Odin."""

    def __init__(self, config: OdinConfig):
        """Initialize local pipeline manager."""
        self.config = config
        self.docker_client = docker.from_env()
        self.network_name = config.get('infrastructure.docker.network', 'wildlife-network')

    def run_complete_pipeline(self) -> bool:
        """Run complete pipeline (stages 1-3)."""
        try:
            print("🚀 Running complete local pipeline...")

            # Run all stages in sequence
            if self.run_stage1() and self.run_stage2() and self.run_stage3():
                print("✅ Complete local pipeline finished!")
                return True

            print("❌ Local pipeline failed!")
            return False

        except Exception as e:
            print(f"❌ Local pipeline execution failed: {e}")
            return False

    def run_stage1(self) -> bool:
        """Run stage 1 (manifest creation) locally."""
        try:
            print("📋 Running stage 1 (manifest) locally...")

            # Run stage 1 in Docker container
            container = self._run_stage_container('stage1')

            if container:
                print("✅ Stage 1 complete!")
                return True
            else:
                print("❌ Stage 1 failed!")
                return False

        except Exception as e:
            print(f"❌ Stage 1 failed: {e}")
            return False

    def run_stage2(self) -> bool:
        """Run stage 2 (detection) locally."""
        try:
            print("🔍 Running stage 2 (detection) locally...")

            # Run stage 2 in Docker container
            container = self._run_stage_container('stage2')

            if container:
                print("✅ Stage 2 complete!")
                return True
            else:
                print("❌ Stage 2 failed!")
                return False

        except Exception as e:
            print(f"❌ Stage 2 failed: {e}")
            return False

    def run_stage3(self) -> bool:
        """Run stage 3 (reporting) locally."""
        try:
            print("📊 Running stage 3 (reporting) locally...")

            # Run stage 3 in Docker container
            container = self._run_stage_container('stage3')

            if container:
                print("✅ Stage 3 complete!")
                return True
            else:
                print("❌ Stage 3 failed!")
                return False

        except Exception as e:
            print(f"❌ Stage 3 failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get local pipeline status."""
        try:
            status = {
                'stage1': self._get_stage_status('stage1'),
                'stage2': self._get_stage_status('stage2'),
                'stage3': self._get_stage_status('stage3'),
                'overall': self._get_overall_status()
            }
            return status

        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return {}

    def _run_stage_container(self, stage: str) -> Optional[docker.models.containers.Container]:
        """Run a stage in a Docker container."""
        try:
            print(f"🐳 Running {stage} in Docker container...")

            # Get stage configuration
            stage_config = self.config.get(f'pipeline.stages.{stage}')
            if not stage_config:
                print(f"❌ No configuration found for stage: {stage}")
                return None

            # Prepare environment variables
            env_vars = {
                'AWS_ENDPOINT_URL': 'http://localstack:4566',
                'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                'AWS_DEFAULT_REGION': 'eu-north-1',
                'MINIO_ENDPOINT': 'http://minio:9000',
                'MINIO_ACCESS_KEY': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                'MINIO_SECRET_KEY': os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
                'REDIS_URL': 'redis://redis:6379',
                'POSTGRES_URL': 'postgresql://wildlife:wildlife123@postgres:5432/wildlife',
                'STAGE': stage
            }

            # Prepare volumes
            volumes = {
                './test_data': {'bind': '/app/test_data', 'mode': 'ro'},
                './output': {'bind': '/app/output', 'mode': 'rw'}
            }

            # Run container
            container = self.docker_client.containers.run(
                image='wildlife-pipeline-starter_wildlife-worker:latest',
                environment=env_vars,
                volumes=volumes,
                network=self.network_name,
                detach=True,
                remove=True,
                name=f'wildlife-{stage}-{int(time.time())}'
            )

            # Wait for container to complete
            result = container.wait(timeout=1800)  # 30 minutes timeout

            if result['StatusCode'] == 0:
                print(f"✅ {stage} completed successfully!")
                return container
            else:
                print(f"❌ {stage} failed with exit code: {result['StatusCode']}")
                return None

        except Exception as e:
            print(f"❌ Failed to run {stage} container: {e}")
            return None

    def _get_stage_status(self, stage: str) -> Dict[str, Any]:
        """Get status for a specific stage."""
        try:
            # Check for running containers
            containers = self.docker_client.containers.list(
                filters={'name': f'wildlife-{stage}'}
            )

            if containers:
                container = containers[0]
                return {
                    'stage': stage,
                    'status': 'running',
                    'container_id': container.id,
                    'timestamp': time.time()
                }
            else:
                return {
                    'stage': stage,
                    'status': 'idle',
                    'timestamp': time.time()
                }

        except Exception as e:
            return {
                'stage': stage,
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

    def _get_overall_status(self) -> Dict[str, Any]:
        """Get overall pipeline status."""
        try:
            # Check all containers
            containers = self.docker_client.containers.list(
                filters={'name': 'wildlife-'}
            )

            running_containers = [c for c in containers if c.status == 'running']

            return {
                'status': 'running' if running_containers else 'idle',
                'running_containers': len(running_containers),
                'total_containers': len(containers),
                'timestamp': time.time()
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }
