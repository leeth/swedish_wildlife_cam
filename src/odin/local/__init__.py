"""
Odin Local - Local development and testing components

This package contains all local development functionality:
- LocalStack infrastructure management
- Local pipeline execution
- Development utilities
"""

from .local_infrastructure import LocalInfrastructureManager
from .local_pipeline import LocalPipelineManager

__all__ = [
    'LocalInfrastructureManager',
    'LocalPipelineManager'
]

