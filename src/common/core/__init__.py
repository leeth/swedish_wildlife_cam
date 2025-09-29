"""
Core base classes and configuration management.
"""

from .base import BaseProcessor, BaseDetector, BaseAnalyzer
from .config import ConfigManager, PipelineConfig

__all__ = [
    "BaseProcessor",
    "BaseDetector", 
    "BaseAnalyzer",
    "ConfigManager",
    "PipelineConfig",
]
