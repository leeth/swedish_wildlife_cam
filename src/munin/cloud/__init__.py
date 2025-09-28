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

from .interfaces import (
    StorageAdapter, QueueAdapter, ModelProvider, Runner,
    StorageLocation, ManifestEntry, Stage2Entry, PipelineConfig
)
from .storage import create_storage_adapter, LocalFSAdapter, S3Adapter, GCSAdapter
from .queue import create_queue_adapter, NoQueueAdapter, RedisQueueAdapter, SQSAdapter, PubSubAdapter
from .models import create_model_provider, LocalModelProvider, CloudModelProvider
from .runners import create_runner, LocalRunner, CloudBatchRunner, EventDrivenRunner
from .config import CloudConfig
from .cli import main

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
