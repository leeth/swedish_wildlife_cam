"""
Odin - The All-Father (Orchestration & Management)

This module provides orchestration and management functionality:
- Pipeline orchestration and workflow management
- Infrastructure lifecycle management
- Cost optimization and resource management
- Configuration management
- Logging and monitoring
"""

from .config import OdinConfig, CostOptimizationConfig
from .validation import ValidationManager
from .run_report import RunReportGenerator
from .stage3_downloader import Stage3OutputDownloader

# Import from submodules
from .aws import InfrastructureManager, PipelineManager, CostOptimizationManager, BatchWorkflowManager
from .local import LocalInfrastructureManager, LocalPipelineManager

__all__ = [
    "OdinConfig",
    "CostOptimizationConfig",
    "ValidationManager",
    "RunReportGenerator",
    "Stage3OutputDownloader",
    "InfrastructureManager",
    "PipelineManager", 
    "CostOptimizationManager",
    "BatchWorkflowManager",
    "LocalInfrastructureManager",
    "LocalPipelineManager",
]
