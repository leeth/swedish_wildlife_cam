"""
Abstract base classes for the wildlife pipeline components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

from ..types import DetectionResult, ClassificationResult, ProcessingStatus


class BaseProcessor(ABC):
    """Base class for all processors in the wildlife pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the processor with optional configuration.
        
        Args:
            config: Configuration dictionary for the processor
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._status = ProcessingStatus.IDLE
        
    @property
    def status(self) -> ProcessingStatus:
        """Get the current processing status."""
        return self._status
        
    def _set_status(self, status: ProcessingStatus) -> None:
        """Set the processing status."""
        self._status = status
        self.logger.debug(f"Status changed to: {status}")
        
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process the input data.
        
        Args:
            input_data: The data to process
            
        Returns:
            Processed data
            
        Raises:
            ProcessingError: If processing fails
        """
        pass
        
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data before processing.
        
        Args:
            input_data: The data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return input_data is not None
        
    def cleanup(self) -> None:
        """Cleanup resources used by the processor."""
        self.logger.debug("Cleaning up processor resources")


class BaseDetector(BaseProcessor):
    """Base class for detection components."""
    
    def __init__(self, model_path: Optional[Union[str, Path]] = None, **kwargs):
        """Initialize the detector.
        
        Args:
            model_path: Path to the model file
            **kwargs: Additional configuration parameters
        """
        super().__init__(**kwargs)
        self.model_path = Path(model_path) if model_path else None
        self.model = None
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the detection model."""
        pass
        
    @abstractmethod
    def detect(self, image_data: Any) -> List[DetectionResult]:
        """Detect objects in the image.
        
        Args:
            image_data: Image data to analyze
            
        Returns:
            List of detection results
        """
        pass
        
    def process(self, input_data: Any) -> List[DetectionResult]:
        """Process input data through detection.
        
        Args:
            input_data: Image data to process
            
        Returns:
            List of detection results
        """
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data for detection")
            
        self._set_status(ProcessingStatus.PROCESSING)
        try:
            results = self.detect(input_data)
            self._set_status(ProcessingStatus.COMPLETED)
            return results
        except Exception as e:
            self._set_status(ProcessingStatus.FAILED)
            self.logger.error(f"Detection failed: {e}")
            raise


class BaseAnalyzer(BaseProcessor):
    """Base class for analysis components."""
    
    def __init__(self, **kwargs):
        """Initialize the analyzer."""
        super().__init__(**kwargs)
        
    @abstractmethod
    def analyze(self, data: Any) -> ClassificationResult:
        """Analyze the data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Classification result
        """
        pass
        
    def process(self, input_data: Any) -> ClassificationResult:
        """Process input data through analysis.
        
        Args:
            input_data: Data to process
            
        Returns:
            Classification result
        """
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data for analysis")
            
        self._set_status(ProcessingStatus.PROCESSING)
        try:
            result = self.analyze(input_data)
            self._set_status(ProcessingStatus.COMPLETED)
            return result
        except Exception as e:
            self._set_status(ProcessingStatus.FAILED)
            self.logger.error(f"Analysis failed: {e}")
            raise
