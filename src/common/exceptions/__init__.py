"""
Custom exceptions for the wildlife pipeline.
"""

from .base import WildlifePipelineError, ConfigurationError, ProcessingError, ValidationError

__all__ = [
    "WildlifePipelineError",
    "ConfigurationError",
    "ProcessingError",
    "ValidationError",
]
