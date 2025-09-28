"""
Cost Optimization Module

This module provides cost optimization functionality for both Munin and Hugin:
- Infrastructure lifecycle management
- Spot instance support with fallback
- Batch-oriented resource management
- Stage 3 output download
"""

from .manager import CostOptimizationManager
from .batch_workflow import BatchWorkflowManager
from .stage3_downloader import Stage3OutputDownloader
from .config import CostOptimizationConfig

__all__ = [
    'CostOptimizationManager',
    'BatchWorkflowManager', 
    'Stage3OutputDownloader',
    'CostOptimizationConfig'
]
