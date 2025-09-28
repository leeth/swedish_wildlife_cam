"""
Configuration loader for cloud-optional pipeline.
"""

from __future__ import annotations
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .storage import create_storage_adapter
from .queue import create_queue_adapter
from .models import create_model_provider
from .runners import create_runner


class CloudConfig:
    """Configuration manager for cloud-optional pipeline."""
    
    def __init__(self, profile: str = "local", config_path: Optional[str] = None):
        self.profile = profile
        self.config_path = config_path or f"profiles/{profile}.yaml"
        self.config = self._load_config()
        
        # Initialize adapters
        self.storage_adapter = self._create_storage_adapter()
        self.queue_adapter = self._create_queue_adapter()
        self.model_provider = self._create_model_provider()
        self.runner = self._create_runner()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Override with environment variables
            config = self._apply_env_overrides(config)
            
            return config
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            return self._get_default_config()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return self._get_default_config()
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Storage overrides
        if os.getenv('STORAGE_ADAPTER'):
            config['storage']['adapter'] = os.getenv('STORAGE_ADAPTER')
        if os.getenv('STORAGE_BASE_PATH'):
            config['storage']['base_path'] = os.getenv('STORAGE_BASE_PATH')
        
        # Queue overrides
        if os.getenv('QUEUE_ADAPTER'):
            config['queue']['adapter'] = os.getenv('QUEUE_ADAPTER')
        
        # Model overrides
        if os.getenv('MODEL_PROVIDER'):
            config['model']['provider'] = os.getenv('MODEL_PROVIDER')
        
        # Runner overrides
        if os.getenv('RUNNER_TYPE'):
            config['runner']['type'] = os.getenv('RUNNER_TYPE')
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'storage': {
                'adapter': 'local',
                'base_path': 'file://./data'
            },
            'queue': {
                'adapter': 'none'
            },
            'model': {
                'provider': 'local',
                'cache_path': 'file://./models'
            },
            'runner': {
                'type': 'local',
                'max_workers': 4
            },
            'pipeline': {
                'stage1': {
                    'model': 'megadetector',
                    'conf_threshold': 0.3
                },
                'stage2': {
                    'enabled': True,
                    'model': 'yolo_cls',
                    'conf_threshold': 0.5
                }
            }
        }
    
    def _create_storage_adapter(self):
        """Create storage adapter from config."""
        storage_config = self.config.get('storage', {})
        adapter_type = storage_config.get('adapter', 'local')
        
        kwargs = {
            'base_path': storage_config.get('base_path', 'file://./data')
        }
        
        if adapter_type == 's3':
            kwargs['region'] = storage_config.get('region', 'eu-north-1')
        elif adapter_type == 'gcs':
            kwargs['project_id'] = storage_config.get('project_id')
        
        return create_storage_adapter(adapter_type, **kwargs)
    
    def _create_queue_adapter(self):
        """Create queue adapter from config."""
        queue_config = self.config.get('queue', {})
        adapter_type = queue_config.get('adapter', 'none')
        
        if adapter_type == 'none':
            return create_queue_adapter(adapter_type)
        
        kwargs = {}
        if adapter_type == 'redis':
            kwargs.update({
                'host': queue_config.get('host', 'localhost'),
                'port': queue_config.get('port', 6379),
                'db': queue_config.get('db', 0)
            })
        elif adapter_type == 'sqs':
            kwargs['region'] = queue_config.get('region', 'eu-north-1')
        elif adapter_type == 'pubsub':
            kwargs['project_id'] = queue_config.get('project_id')
        
        return create_queue_adapter(adapter_type, **kwargs)
    
    def _create_model_provider(self):
        """Create model provider from config."""
        model_config = self.config.get('model', {})
        provider_type = model_config.get('provider', 'local')
        
        kwargs = {
            'cache_path': model_config.get('cache_path', 'file://./models')
        }
        
        if provider_type == 'cloud':
            kwargs['storage_adapter'] = self.storage_adapter
        
        return create_model_provider(provider_type, **kwargs)
    
    def _create_runner(self):
        """Create runner from config."""
        runner_config = self.config.get('runner', {})
        runner_type = runner_config.get('type', 'local')
        
        kwargs = {}
        if runner_type == 'local':
            kwargs['max_workers'] = runner_config.get('max_workers', 4)
        elif runner_type == 'cloud_batch':
            kwargs.update({
                'job_definition': runner_config.get('job_definition', 'wildlife-detection-job'),
                'vcpu': runner_config.get('vcpu', 4),
                'memory': runner_config.get('memory', 8192),
                'gpu_count': runner_config.get('gpu_count', 1),
                'gpu_type': runner_config.get('gpu_type', 'g4dn.xlarge')
            })
        
        return create_runner(
            runner_type,
            self.storage_adapter,
            self.model_provider,
            self.queue_adapter,
            **kwargs
        )
    
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration."""
        return self.config.get('pipeline', {})
    
    def get_stage1_config(self) -> Dict[str, Any]:
        """Get Stage-1 configuration."""
        return self.get_pipeline_config().get('stage1', {})
    
    def get_stage2_config(self) -> Dict[str, Any]:
        """Get Stage-2 configuration."""
        return self.get_pipeline_config().get('stage2', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.get_pipeline_config().get('output', {})
    
    def get_manifest_config(self) -> Dict[str, Any]:
        """Get manifest configuration."""
        return self.get_pipeline_config().get('manifest', {})
    
    def is_stage2_enabled(self) -> bool:
        """Check if Stage-2 is enabled."""
        return self.get_stage2_config().get('enabled', True)
    
    def get_storage_base_path(self) -> str:
        """Get storage base path."""
        return self.config.get('storage', {}).get('base_path', 'file://./data')
    
    def get_manifest_paths(self) -> Dict[str, str]:
        """Get manifest file paths."""
        manifest_config = self.get_manifest_config()
        base_path = self.get_storage_base_path()
        
        return {
            'stage1': f"{base_path}/{manifest_config.get('stage1_path', 'stage1/manifest.jsonl')}",
            'stage2': f"{base_path}/{manifest_config.get('stage2_path', 'stage2/predictions.jsonl')}"
        }
