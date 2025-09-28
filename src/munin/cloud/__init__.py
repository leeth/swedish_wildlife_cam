"""
Cloud-optional wildlife detection pipeline.

This module provides a cloud-optional architecture with swappable adapters for:
- Storage (local disk vs S3/GCS)
- Queue (none/Redis vs SQS/PubSub)
- Compute (local threads vs serverless jobs)
- Models (local vs cloud storage)

Usage:
    # Local processing
    python -m wildlife_pipeline.cloud.cli stage1 --profile local --input file://./data --output file://./results

    # Cloud processing
    python -m wildlife_pipeline.cloud.cli stage1 --profile cloud --input s3://bucket/data --output s3://bucket/results
"""

from .cli import main
from .config import CloudConfig
from .interfaces import (
    ManifestEntry,
    ModelProvider,
    PipelineConfig,
    QueueAdapter,
    Runner,
    Stage2Entry,
    StorageAdapter,
    StorageLocation,
)
from .models import CloudModelProvider, LocalModelProvider, create_model_provider
from .queue import (
    NoQueueAdapter,
    PubSubAdapter,
    RedisQueueAdapter,
    SQSAdapter,
    create_queue_adapter,
)
from .runners import CloudBatchRunner, EventDrivenRunner, LocalRunner, create_runner
from .storage import GCSAdapter, LocalFSAdapter, S3Adapter, create_storage_adapter

__all__ = [
    # Interfaces
    'StorageAdapter', 'QueueAdapter', 'ModelProvider', 'Runner',
    'StorageLocation', 'ManifestEntry', 'Stage2Entry', 'PipelineConfig',

    # Storage
    'create_storage_adapter', 'LocalFSAdapter', 'S3Adapter', 'GCSAdapter',

    # Queue
    'create_queue_adapter', 'NoQueueAdapter', 'RedisQueueAdapter', 'SQSAdapter', 'PubSubAdapter',

    # Models
    'create_model_provider', 'LocalModelProvider', 'CloudModelProvider',

    # Runners
    'create_runner', 'LocalRunner', 'CloudBatchRunner', 'EventDrivenRunner',

    # Configuration
    'CloudConfig',

    # CLI
    'main'
]
