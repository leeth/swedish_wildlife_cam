"""
Odin - The All-Father (Orchestration & Management)

This module provides orchestration and management functionality:
- Pipeline orchestration and workflow management
- Infrastructure lifecycle management
- Cost optimization and resource management
- Configuration management
- Logging and monitoring
"""

from .manager import CostOptimizationManager
from .batch_workflow import BatchWorkflowManager
from .config import CostOptimizationConfig
from .stage3_downloader import Stage3OutputDownloader
from .pipeline import PipelineManager
from .infrastructure import InfrastructureManager
from .validation import ValidationManager

__all__ = [
    "CostOptimizationManager",
    "BatchWorkflowManager", 
    "Stage3OutputDownloader",
    "CostOptimizationConfig",
    "PipelineManager",
    "InfrastructureManager",
    "ValidationManager",
]
