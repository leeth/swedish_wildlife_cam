"""
Type definitions for the wildlife pipeline.
"""

from .data import DetectionResult, ClassificationResult, ProcessingStatus, PipelineStage
from .enums import ProcessingStatus, PipelineStage

__all__ = [
    "DetectionResult",
    "ClassificationResult", 
    "ProcessingStatus",
    "PipelineStage",
]
