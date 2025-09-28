from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from .detector import BaseDetector, Detection

class WildlifeDetector(BaseDetector):
    """
    Custom wildlife detector for moose, boar, and roedeer.
    This can be extended to use a custom trained YOLO model.
    """
    
    # Define the target wildlife classes
    WILDLIFE_CLASSES = {
        'moose': 'moose',
        'boar': 'boar', 
        'roedeer': 'roedeer',
        'roe_deer': 'roedeer',  # alternative naming
        'wild_boar': 'boar',    # alternative naming
        'elk': 'moose'          # alternative naming (elk is moose in Europe)
    }
    
    def __init__(self, model_path: str = None, conf: float = 0.35, iou: float = 0.5):
        self.model_path = model_path
        self.conf = conf
        self.iou = iou
        self.model = None
        
        if model_path:
            self._load_model()
    
    def _load_model(self):
        """Load the YOLO model if a path is provided"""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
        except Exception as e:
            print(f"Warning: Could not load model from {self.model_path}: {e}")
            print("Using fallback detection method")
    
    def predict(self, image_path: Path) -> List[Detection]:
        """
        Predict wildlife in the image.
        If a custom model is loaded, use it. Otherwise, use fallback detection.
        """
        if self.model:
            return self._predict_with_model(image_path)
        else:
            return self._predict_fallback(image_path)
    
    def _predict_with_model(self, image_path: Path) -> List[Detection]:
        """Use the loaded YOLO model for prediction"""
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf,
            iou=self.iou,
            imgsz=1280,
            verbose=False
        )
        
        dets: List[Detection] = []
        if not results:
            return dets
            
        r = results[0]
        names = r.names  # class id -> label
        
        if r.boxes is None:
            return dets
            
        for b in r.boxes:
            cls_id = int(b.cls.item())
            label = names.get(cls_id, str(cls_id))
            conf = float(b.conf.item())
            xyxy = [float(v) for v in b.xyxy[0].tolist()]
            
            # Map to our wildlife classes if possible
            mapped_label = self._map_to_wildlife_class(label)
            if mapped_label:
                dets.append(Detection(
                    label=mapped_label, 
                    confidence=conf, 
                    bbox=xyxy
                ))
        
        return dets
    
    def _predict_fallback(self, image_path: Path) -> List[Detection]:
        """
        Fallback detection method when no custom model is available.
        This could be enhanced with other detection methods.
        """
        # For now, return empty list - you would implement your own detection logic here
        # This could include:
        # - Using a different pre-trained model
        # - Rule-based detection
        # - Integration with other wildlife detection APIs
        return []
    
    def _map_to_wildlife_class(self, label: str) -> Optional[str]:
        """Map detected labels to our target wildlife classes"""
        label_lower = label.lower()
        
        # Direct mapping
        if label_lower in self.WILDLIFE_CLASSES:
            return self.WILDLIFE_CLASSES[label_lower]
        
        # Check for partial matches
        for key, value in self.WILDLIFE_CLASSES.items():
            if key in label_lower or label_lower in key:
                return value
        
        # Map common COCO classes that might be misclassified wildlife
        # Based on the actual misclassifications we're seeing
        coco_to_wildlife = {
            'deer': 'roedeer',
            'horse': 'moose',      # Sometimes moose are misclassified as horses
            'cow': 'moose',        # Sometimes moose are misclassified as cows
            'bear': 'boar',        # Sometimes boars are misclassified as bears
            'dog': 'boar',         # Sometimes boars are misclassified as dogs
            'sheep': 'roedeer',    # Sometimes roe deer are misclassified as sheep
            'elephant': 'boar',    # Sometimes boars are misclassified as elephants
        }
        
        return coco_to_wildlife.get(label_lower)
    
    def get_available_classes(self) -> List[str]:
        """Get list of available wildlife classes"""
        return list(set(self.WILDLIFE_CLASSES.values()))
    
    def create_training_config(self, output_path: str = "wildlife_dataset.yaml"):
        """
        Create a YAML configuration file for training a custom YOLO model
        on your wildlife dataset.
        """
        config = {
            'path': './dataset',  # dataset root directory
            'train': 'images/train',  # train images (relative to 'path')
            'val': 'images/val',      # val images (relative to 'path')
            'test': 'images/test',    # test images (optional)
            
            'nc': len(self.get_available_classes()),  # number of classes
            'names': self.get_available_classes()     # class names
        }
        
        with open(output_path, 'w') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False)
        
        print(f"Training configuration saved to {output_path}")
        return config
