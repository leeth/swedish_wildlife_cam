"""
Common utilities and base classes for the Wildlife Pipeline.

This package contains shared functionality used across odin, munin, and hugin modules.
"""

__version__ = "0.1.0"
__author__ = "Wildlife Pipeline Team"

# Import commonly used utilities
from .core.base import BaseProcessor, BaseDetector, BaseAnalyzer
from .core.config import ConfigManager, PipelineConfig
from .exceptions import (
    WildlifePipelineError,
    ConfigurationError,
    ProcessingError,
    ValidationError,
)
from .types import (
    DetectionResult,
    ClassificationResult,
    ProcessingStatus,
    PipelineStage,
)

__all__ = [
    # Core classes
    "BaseProcessor",
    "BaseDetector",
    "BaseAnalyzer",
    "ConfigManager",
    "PipelineConfig",
    # Exceptions
    "WildlifePipelineError",
    "ConfigurationError",
    "ProcessingError",
    "ValidationError",
    # Types
    "DetectionResult",
    "ClassificationResult",
    "ProcessingStatus",
    "PipelineStage",
]
