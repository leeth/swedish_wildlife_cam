"""
Configuration management for the wildlife pipeline.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
import json

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from ..exceptions import ConfigurationError


@dataclass
class PipelineConfig:
    """Configuration for the wildlife pipeline."""
    
    # Model configuration
    model_path: Optional[str] = None
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    
    # Processing configuration
    batch_size: int = 32
    max_workers: int = 4
    timeout: int = 300
    
    # Storage configuration
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    temp_path: Optional[str] = None
    
    # Cloud configuration
    aws_region: Optional[str] = None
    gcp_project: Optional[str] = None
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Additional configuration
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            raise ConfigurationError("Confidence threshold must be between 0 and 1")
            
        if self.nms_threshold < 0 or self.nms_threshold > 1:
            raise ConfigurationError("NMS threshold must be between 0 and 1")
            
        if self.batch_size <= 0:
            raise ConfigurationError("Batch size must be positive")
            
        if self.max_workers <= 0:
            raise ConfigurationError("Max workers must be positive")


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[PipelineConfig] = None
        
    def load_config(self, 
                   config_path: Optional[Union[str, Path]] = None,
                   env_file: Optional[Union[str, Path]] = None) -> PipelineConfig:
        """Load configuration from file and environment.
        
        Args:
            config_path: Path to configuration file
            env_file: Path to environment file
            
        Returns:
            Loaded configuration
        """
        if config_path:
            self.config_path = Path(config_path)
            
        if env_file and DOTENV_AVAILABLE:
            load_dotenv(env_file)
        elif env_file and not DOTENV_AVAILABLE:
            self.logger.warning("python-dotenv not available, skipping .env file loading")
            
        config_dict = {}
        
        # Load from file if it exists
        if self.config_path and self.config_path.exists():
            config_dict.update(self._load_from_file(self.config_path))
            
        # Load from environment variables
        config_dict.update(self._load_from_env())
        
        # Create configuration object
        self._config = PipelineConfig(**config_dict)
        return self._config
        
    def _load_from_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    if YAML_AVAILABLE:
                        return yaml.safe_load(f) or {}
                    else:
                        raise ConfigurationError("YAML support not available. Install PyYAML.")
                elif config_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_path}: {e}")
            
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Returns:
            Configuration dictionary from environment
        """
        config = {}
        
        # Map environment variables to config fields
        env_mapping = {
            'WILDLIFE_MODEL_PATH': 'model_path',
            'WILDLIFE_CONFIDENCE_THRESHOLD': 'confidence_threshold',
            'WILDLIFE_BATCH_SIZE': 'batch_size',
            'WILDLIFE_MAX_WORKERS': 'max_workers',
            'WILDLIFE_INPUT_PATH': 'input_path',
            'WILDLIFE_OUTPUT_PATH': 'output_path',
            'WILDLIFE_AWS_REGION': 'aws_region',
            'WILDLIFE_GCP_PROJECT': 'gcp_project',
            'WILDLIFE_LOG_LEVEL': 'log_level',
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_key in ['confidence_threshold', 'nms_threshold']:
                    config[config_key] = float(value)
                elif config_key in ['batch_size', 'max_workers', 'timeout']:
                    config[config_key] = int(value)
                else:
                    config[config_key] = value
                    
        return config
        
    def get_config(self) -> Optional[PipelineConfig]:
        """Get the current configuration.
        
        Returns:
            Current configuration or None if not loaded
        """
        return self._config
        
    def save_config(self, config: PipelineConfig, 
                   output_path: Union[str, Path]) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save
            output_path: Path to save configuration
        """
        output_path = Path(output_path)
        
        # Convert dataclass to dictionary
        config_dict = {
            'model_path': config.model_path,
            'confidence_threshold': config.confidence_threshold,
            'nms_threshold': config.nms_threshold,
            'batch_size': config.batch_size,
            'max_workers': config.max_workers,
            'timeout': config.timeout,
            'input_path': config.input_path,
            'output_path': config.output_path,
            'temp_path': config.temp_path,
            'aws_region': config.aws_region,
            'gcp_project': config.gcp_project,
            'log_level': config.log_level,
            'log_file': config.log_file,
            'custom_config': config.custom_config,
        }
        
        try:
            with open(output_path, 'w') as f:
                if output_path.suffix.lower() in ['.yaml', '.yml']:
                    if YAML_AVAILABLE:
                        yaml.dump(config_dict, f, default_flow_style=False)
                    else:
                        raise ConfigurationError("YAML support not available. Install PyYAML.")
                elif output_path.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2)
                else:
                    raise ConfigurationError(f"Unsupported output format: {output_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {output_path}: {e}")
