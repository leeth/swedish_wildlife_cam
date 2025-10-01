"""
Wildlife Detector - Minimal implementation for testing
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class Detection:
    """Minimal Detection class"""
    
    def __init__(self, label: str, confidence: float, bbox: List[float], 
                 image_path: str, timestamp: str):
        self.label = label
        self.confidence = confidence
        self.bbox = bbox  # [x_min, y_min, x_max, y_max]
        self.image_path = image_path
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary"""
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "image_path": self.image_path,
            "timestamp": self.timestamp
        }

class BaseDetector:
    """Minimal Base Detector class"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None
    
    def load_model(self):
        """Load detection model"""
        logger.info("Loading detection model...")
        # Minimal implementation
        pass
    
    def detect(self, image_path: str) -> List[Detection]:
        """Detect objects in image"""
        # Minimal implementation - return mock detections
        return [
            Detection(
                label="deer",
                confidence=0.85,
                bbox=[0.1, 0.1, 0.4, 0.4],
                image_path=image_path,
                timestamp="2023-10-27T10:00:00Z"
            )
        ]

class SwedishWildlifeDetector(BaseDetector):
    """Swedish Wildlife Detector implementation"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(model_path)
        self.species_mapping = {
            "deer": "hjort",
            "fox": "räv",
            "boar": "vildsvin",
            "moose": "älg"
        }
    
    def detect_swedish_wildlife(self, image_path: str) -> List[Detection]:
        """Detect Swedish wildlife in image"""
        detections = self.detect(image_path)
        # Translate labels to Swedish
        for detection in detections:
            if detection.label in self.species_mapping:
                detection.label = self.species_mapping[detection.label]
        return detections
