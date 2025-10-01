"""
YOLO Classifier Adapter - Minimal implementation for testing
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class YOLOClassifier:
    """Minimal YOLO Classifier implementation"""
    
    def __init__(self, model_path: Optional[str] = None, 
                 confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.classes = [
            "deer", "fox", "boar", "moose", "human", "other"
        ]
    
    def load_model(self):
        """Load YOLO model"""
        logger.info("Loading YOLO model...")
        # Minimal implementation
        pass
    
    def classify(self, image_path: str) -> List[Dict[str, Any]]:
        """Classify objects in image"""
        # Minimal implementation - return mock classifications
        return [
            {
                "label": "deer",
                "confidence": 0.85,
                "bbox": [0.1, 0.1, 0.4, 0.4],
                "class_id": 0
            }
        ]
    
    def predict(self, image_path: str) -> List[Dict[str, Any]]:
        """Predict objects in image"""
        return self.classify(image_path)
    
    def get_classes(self) -> List[str]:
        """Get available classes"""
        return self.classes
