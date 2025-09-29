"""
Data type definitions for the wildlife pipeline.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime

from .enums import ProcessingStatus, PipelineStage


@dataclass
class DetectionResult:
    """Result of object detection."""
    
    # Bounding box coordinates (x1, y1, x2, y2)
    bbox: Tuple[float, float, float, float]
    
    # Detection confidence score
    confidence: float
    
    # Detected class/label
    class_name: str
    
    # Class ID
    class_id: int
    
    # Optional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate detection result."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
            
        if len(self.bbox) != 4:
            raise ValueError("Bounding box must have 4 coordinates")
            
        # Ensure bbox is in correct format (x1, y1, x2, y2)
        x1, y1, x2, y2 = self.bbox
        if x1 >= x2 or y1 >= y2:
            raise ValueError("Invalid bounding box coordinates")


@dataclass
class ClassificationResult:
    """Result of classification."""
    
    # Predicted class
    predicted_class: str
    
    # Classification confidence
    confidence: float
    
    # Class probabilities for all classes
    class_probabilities: Dict[str, float]
    
    # Optional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate classification result."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
            
        if not self.class_probabilities:
            raise ValueError("Class probabilities cannot be empty")
            
        # Validate that probabilities sum to approximately 1
        total_prob = sum(self.class_probabilities.values())
        if not 0.99 <= total_prob <= 1.01:
            raise ValueError("Class probabilities must sum to 1")


@dataclass
class ProcessingResult:
    """Result of processing operation."""
    
    # Processing status
    status: ProcessingStatus
    
    # Processing stage
    stage: PipelineStage
    
    # Input file path
    input_path: Optional[Path] = None
    
    # Output file path
    output_path: Optional[Path] = None
    
    # Processing start time
    start_time: Optional[datetime] = None
    
    # Processing end time
    end_time: Optional[datetime] = None
    
    # Error message if failed
    error_message: Optional[str] = None
    
    # Processing metadata
    metadata: Dict[str, Any] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.COMPLETED
