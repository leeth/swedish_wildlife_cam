"""
Cost Optimization Module

This module provides cost optimization functionality for both Munin and Hugin:
- Infrastructure lifecycle management
- Spot instance support with fallback
- Batch-oriented resource management
- Stage 3 output download
"""

from .batch_workflow import BatchWorkflowManager
from .config import CostOptimizationConfig
from .manager import CostOptimizationManager
from .stage3_downloader import Stage3OutputDownloader

__all__ = [
    'CostOptimizationManager',
    'BatchWorkflowManager',
    'Stage3OutputDownloader',
    'CostOptimizationConfig'
]
