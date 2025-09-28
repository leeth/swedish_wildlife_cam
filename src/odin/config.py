"""
Odin Configuration Management

Handles loading and managing Odin configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class OdinConfig:
    """Odin configuration manager."""
    
    def __init__(self, config_path: Path):
        """Initialize configuration from file."""
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_region(self) -> str:
        """Get AWS region."""
        return self.get('infrastructure.region', 'eu-north-1')
    
    def set_region(self, region: str) -> None:
        """Set AWS region."""
        self.set('infrastructure.region', region)
    
    def get_bucket_name(self) -> str:
        """Get S3 bucket name."""
        return self.get('storage.s3_bucket', 'wildlife-pipeline-data')
    
    def get_stack_name(self) -> str:
        """Get CloudFormation stack name."""
        return self.get('infrastructure.stack_name', 'wildlife-odin-infrastructure')
    
    def get_compute_environment_name(self) -> str:
        """Get AWS Batch compute environment name."""
        return self.get('infrastructure.batch.compute_environment.name', 'wildlife-compute-production')
    
    def get_job_queue_name(self) -> str:
        """Get AWS Batch job queue name."""
        return self.get('infrastructure.batch.job_queue.name', 'wildlife-queue-production')
    
    def get_instance_types(self) -> list:
        """Get instance types for compute environment."""
        return self.get('infrastructure.batch.compute_environment.instance_types', ['m5.large', 'm5.xlarge'])
    
    def get_min_vcpus(self) -> int:
        """Get minimum vCPUs for compute environment."""
        return self.get('infrastructure.batch.compute_environment.min_vcpus', 0)
    
    def get_max_vcpus(self) -> int:
        """Get maximum vCPUs for compute environment."""
        return self.get('infrastructure.batch.compute_environment.max_vcpus', 8)
    
    def get_desired_vcpus(self) -> int:
        """Get desired vCPUs for compute environment."""
        return self.get('infrastructure.batch.compute_environment.desired_vcpus', 0)
    
    def get_subnets(self) -> list:
        """Get subnet IDs for compute environment."""
        return self.get('infrastructure.batch.compute_environment.subnets', [])
    
    def get_security_groups(self) -> list:
        """Get security group IDs for compute environment."""
        return self.get('infrastructure.batch.compute_environment.security_groups', [])
    
    def get_instance_role(self) -> str:
        """Get instance role ARN for compute environment."""
        return self.get('infrastructure.batch.compute_environment.instance_role', '')
    
    def get_service_role(self) -> str:
        """Get service role ARN for compute environment."""
        return self.get('infrastructure.batch.compute_environment.service_role', '')
    
    def get_job_definitions(self) -> Dict[str, Any]:
        """Get job definitions configuration."""
        return self.get('infrastructure.batch.job_definitions', {})
    
    def get_pipeline_stages(self) -> Dict[str, Any]:
        """Get pipeline stages configuration."""
        return self.get('pipeline.stages', {})
    
    def get_storage_prefixes(self) -> Dict[str, str]:
        """Get storage prefixes configuration."""
        return self.get('storage.prefixes', {})
    
    def is_cost_optimized(self) -> bool:
        """Check if cost optimization is enabled."""
        return self.get('infrastructure.cost_optimized', True)
    
    def get_provider(self) -> str:
        """Get cloud provider."""
        return self.get('infrastructure.provider', 'aws')
    
    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
