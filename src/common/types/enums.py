"""
Enums for the wildlife pipeline.
"""

from enum import Enum, auto


class ProcessingStatus(Enum):
    """Status of processing operations."""
    IDLE = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class PipelineStage(Enum):
    """Stages of the wildlife pipeline."""
    INGESTION = "ingestion"
    DETECTION = "detection"
    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
