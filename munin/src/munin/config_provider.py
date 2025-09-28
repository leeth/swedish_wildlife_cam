"""
Configuration provider abstraction for wildlife detection pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from pathlib import Path
import yaml
import os
import json
from dataclasses import dataclass


@dataclass
class ConfigSource:
    """Configuration source information."""
    source_type: str  # 'file', 'env', 'default'
    path: Optional[str] = None
    priority: int = 0  # Higher number = higher priority


class ConfigProvider(ABC):
    """Abstract configuration provider."""
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        pass
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get a configuration section."""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        pass
    
    @abstractmethod
    def reload_config(self) -> None:
        """Reload configuration from source."""
        pass


class FileConfigProvider(ConfigProvider):
    """File-based configuration provider."""
    
    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.config = {}
        self.sources = []
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                self.sources.append(ConfigSource('file', str(self.config_path), priority=1))
            except (yaml.YAMLError, IOError) as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                self.config = {}
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        env_overrides = {}
        
        for key, value in os.environ.items():
            if key.startswith('WILDLIFE_'):
                # Convert WILDLIFE_SECTION_KEY to section.key
                config_key = key[9:].lower().replace('_', '.')
                env_overrides[config_key] = value
        
        # Merge environment overrides
        for key, value in env_overrides.items():
            self._set_nested_value(self.config, key, value)
        
        if env_overrides:
            self.sources.append(ConfigSource('env', priority=2))
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any):
        """Set a nested configuration value."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get a nested configuration value."""
        keys = key.split('.')
        current = config
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        
        return current
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._get_nested_value(self.config, key) or default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get a configuration section."""
        return self.config.get(section, {})
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._set_nested_value(self.config, key, value)
    
    def reload_config(self) -> None:
        """Reload configuration from source."""
        self.config = {}
        self.sources = []
        self._load_config()


class EnvConfigProvider(ConfigProvider):
    """Environment variable configuration provider."""
    
    def __init__(self, prefix: str = "WILDLIFE_"):
        self.prefix = prefix
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix):].lower().replace('_', '.')
                self._set_nested_value(self.config, config_key, value)
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any):
        """Set a nested configuration value."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get a nested configuration value."""
        keys = key.split('.')
        current = config
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        
        return current
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._get_nested_value(self.config, key) or default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get a configuration section."""
        return self.config.get(section, {})
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._set_nested_value(self.config, key, value)
    
    def reload_config(self) -> None:
        """Reload configuration from source."""
        self.config = {}
        self._load_config()


class CompositeConfigProvider(ConfigProvider):
    """Composite configuration provider that combines multiple sources."""
    
    def __init__(self, providers: List[ConfigProvider]):
        self.providers = providers
        # Sort by priority (higher number = higher priority)
        self.providers.sort(key=lambda p: getattr(p, 'priority', 0), reverse=True)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from the first provider that has it."""
        for provider in self.providers:
            value = provider.get_config(key)
            if value is not None:
                return value
        return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get a configuration section, merging from all providers."""
        merged_section = {}
        for provider in self.providers:
            section_data = provider.get_section(section)
            if section_data:
                merged_section.update(section_data)
        return merged_section
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value in the first provider."""
        if self.providers:
            self.providers[0].set_config(key, value)
    
    def reload_config(self) -> None:
        """Reload configuration from all providers."""
        for provider in self.providers:
            provider.reload_config()


def create_config_provider(provider_type: str = "file", **kwargs) -> ConfigProvider:
    """Factory function to create configuration providers."""
    if provider_type == "file":
        return FileConfigProvider(**kwargs)
    elif provider_type == "env":
        return EnvConfigProvider(**kwargs)
    elif provider_type == "composite":
        providers = kwargs.get('providers', [])
        return CompositeConfigProvider(providers)
    else:
        raise ValueError(f"Unsupported configuration provider type: {provider_type}")
