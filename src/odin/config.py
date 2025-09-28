"""
Cost Optimization Configuration

This module provides configuration management for cost optimization features.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class CostOptimizationConfig:
    """Configuration for cost optimization features."""

    # AWS Configuration
    region: str = "eu-north-1"
    environment: str = "production"

    # Spot Instance Configuration
    spot_bid_percentage: int = 70
    spot_fallback_timeout: int = 300  # 5 minutes
    max_retry_attempts: int = 3

    # Infrastructure Configuration
    max_vcpus: int = 100
    min_vcpus: int = 0
    desired_vcpus: int = 0  # Scale to zero when idle
    gpu_required: bool = True

    # Batch Processing Configuration
    max_parallel_jobs: int = 10
    cost_threshold_percentage: float = 0.5  # 50% savings threshold

    # Stage 3 Configuration
    download_stage3: bool = True
    create_local_runner: bool = True
    compression_window_minutes: int = 10
    min_confidence: float = 0.5
    min_duration_seconds: float = 5.0

    # Cost Monitoring
    cost_reporting: bool = True
    cost_monitoring: bool = True

    @classmethod
    def from_file(cls, config_path: str) -> 'CostOptimizationConfig':
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data.get('cost_optimization', {}))

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CostOptimizationConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'region': self.region,
            'environment': self.environment,
            'spot_bid_percentage': self.spot_bid_percentage,
            'spot_fallback_timeout': self.spot_fallback_timeout,
            'max_retry_attempts': self.max_retry_attempts,
            'max_vcpus': self.max_vcpus,
            'min_vcpus': self.min_vcpus,
            'desired_vcpus': self.desired_vcpus,
            'gpu_required': self.gpu_required,
            'max_parallel_jobs': self.max_parallel_jobs,
            'cost_threshold_percentage': self.cost_threshold_percentage,
            'download_stage3': self.download_stage3,
            'create_local_runner': self.create_local_runner,
            'compression_window_minutes': self.compression_window_minutes,
            'min_confidence': self.min_confidence,
            'min_duration_seconds': self.min_duration_seconds,
            'cost_reporting': self.cost_reporting,
            'cost_monitoring': self.cost_monitoring
        }

    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            'cost_optimization': self.to_dict()
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)

    def update(self, **kwargs) -> None:
        """Update configuration with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def validate(self) -> None:
        """Validate configuration values."""
        if not 0 <= self.spot_bid_percentage <= 100:
            raise ValueError("Spot bid percentage must be between 0 and 100")

        if self.max_vcpus < self.min_vcpus:
            raise ValueError("Max vCPUs must be greater than or equal to min vCPUs")

        if self.desired_vcpus < self.min_vcpus or self.desired_vcpus > self.max_vcpus:
            raise ValueError("Desired vCPUs must be between min and max vCPUs")

        if not 0 <= self.cost_threshold_percentage <= 1:
            raise ValueError("Cost threshold percentage must be between 0 and 1")

        if self.compression_window_minutes <= 0:
            raise ValueError("Compression window must be positive")

        if not 0 <= self.min_confidence <= 1:
            raise ValueError("Min confidence must be between 0 and 1")

        if self.min_duration_seconds < 0:
            raise ValueError("Min duration must be non-negative")
