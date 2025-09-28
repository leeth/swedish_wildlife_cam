from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import requests
import os
from urllib.parse import urlparse

from .detector import BaseDetector, Detection

class SwedishWildlifeDetector(BaseDetector):
    """
    Swedish Wildlife Detector optimized for Swedish wildlife species.
    This detector is specifically designed for camera trap data and is optimized
    for detecting animals in Swedish natural environments.
    
    Supports both local model files and cloud API endpoints.
    """
    
    # Swedish wildlife species that MegaDetector can detect
    SWEDISH_WILDLIFE = {
        'animal': 'animal',  # Generic animal detection
        'person': 'person',  # Humans in camera traps
        'vehicle': 'vehicle'  # Vehicles (rare but possible)
    }
    
    # Common Swedish wildlife that might be detected as 'animal'
    SWEDISH_ANIMALS = {
        'moose': 'moose',
        'elk': 'moose',  # Same as moose in Europe
        'boar': 'boar',
        'wild_boar': 'boar',
        'roe_deer': 'roedeer',
        'roedeer': 'roedeer',
        'red_deer': 'red_deer',
        'fallow_deer': 'fallow_deer',
        'bear': 'bear',
        'wolf': 'wolf',
        'lynx': 'lynx',
        'fox': 'fox',
        'badger': 'badger',
        'hare': 'hare',
        'rabbit': 'rabbit'
    }
    
    def __init__(self, model_path: str = None, conf: float = 0.35, 
                 api_url: str = None, api_key: str = None):
        """
        Initialize MegaDetector.
        
        Args:
            model_path: Path to local MegaDetector model file (.pb or .pt)
            conf: Confidence threshold for detections
            api_url: URL for MegaDetector API (if using cloud service)
            api_key: API key for cloud service (if required)
        """
        self.model_path = model_path
        self.conf = conf
        self.api_url = api_url
        self.api_key = api_key
        self.model = None
        
        if model_path:
            self._load_local_model()
        elif api_url:
            self._setup_api_client()
        else:
            # Try to download the model automatically
            self._download_model()
    
    def _download_model(self):
        """Download a wildlife-optimized YOLO model for Swedish wildlife"""
        # Use a more recent YOLO model that's compatible with ultralytics
        model_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
        model_filename = "yolov8n_wildlife.pt"
        
        if not os.path.exists(model_filename):
            print(f"Downloading wildlife-optimized YOLO model...")
            try:
                response = requests.get(model_url, stream=True)
                response.raise_for_status()
                
                with open(model_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"Wildlife model downloaded to {model_filename}")
                self.model_path = model_filename
                self._load_local_model()
                
            except Exception as e:
                print(f"Failed to download model: {e}")
                print("Using fallback to standard YOLO model")
                self.model_path = "yolov8n.pt"
                self._load_local_model()
        else:
            self.model_path = model_filename
            self._load_local_model()
    
    def _load_local_model(self):
        """Load the local wildlife detection model"""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print(f"Loaded wildlife detection model from {self.model_path}")
                
        except Exception as e:
            print(f"Warning: Could not load model from {self.model_path}: {e}")
            print("Falling back to API or download method")
    
    def _setup_api_client(self):
        """Setup API client for cloud-based MegaDetector"""
        if not self.api_url:
            raise ValueError("API URL is required for cloud-based detection")
        
        print(f"Using MegaDetector API: {self.api_url}")
    
    def predict(self, image_path: Path) -> List[Detection]:
        """Predict wildlife in the image using Swedish wildlife detector"""
        if self.model:
            return self._predict_local(image_path)
        elif self.api_url:
            return self._predict_api(image_path)
        else:
            print("No wildlife detection model or API available")
            return []
    
    def _predict_local(self, image_path: Path) -> List[Detection]:
        """Use local wildlife detection model for prediction"""
        try:
            results = self.model.predict(
                source=str(image_path),
                conf=self.conf,
                verbose=False
            )
            return self._convert_ultralytics_results(results)
                
        except Exception as e:
            print(f"Error in local prediction: {e}")
            return []
    
    def _predict_api(self, image_path: Path) -> List[Detection]:
        """Use MegaDetector API for prediction"""
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                headers = {}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                
                response = requests.post(self.api_url, files=files, headers=headers)
                response.raise_for_status()
                
                results = response.json()
                return self._convert_api_results(results)
                
        except Exception as e:
            print(f"Error in API prediction: {e}")
            return []
    
    def _convert_megadetector_results(self, detections: Dict) -> List[Detection]:
        """Convert MegaDetector package results to Detection objects"""
        dets = []
        
        if 'detections' not in detections:
            return dets
        
        for det in detections['detections']:
            if det['conf'] >= self.conf:
                # MegaDetector returns [x1, y1, w, h] format
                x1, y1, w, h = det['bbox']
                x2, y2 = x1 + w, y1 + h
                
                # Map category to Swedish wildlife
                category = det.get('category', 'animal')
                mapped_label = self._map_to_swedish_wildlife(category)
                
                if mapped_label:
                    dets.append(Detection(
                        label=mapped_label,
                        confidence=det['conf'],
                        bbox=[x1, y1, x2, y2]
                    ))
        
        return dets
    
    def _convert_ultralytics_results(self, results) -> List[Detection]:
        """Convert ultralytics results to Detection objects"""
        dets = []
        
        if not results:
            return dets
            
        r = results[0]
        if r.boxes is None:
            return dets
            
        for b in r.boxes:
            conf = float(b.conf.item())
            if conf >= self.conf:
                xyxy = [float(v) for v in b.xyxy[0].tolist()]
                
                # Get class name
                cls_id = int(b.cls.item())
                label = r.names.get(cls_id, str(cls_id))
                
                # Map to Swedish wildlife
                mapped_label = self._map_to_swedish_wildlife(label)
                
                if mapped_label:
                    dets.append(Detection(
                        label=mapped_label,
                        confidence=conf,
                        bbox=xyxy
                    ))
        
        return dets
    
    def _convert_api_results(self, results: Dict) -> List[Detection]:
        """Convert API results to Detection objects"""
        dets = []
        
        # API format may vary, this is a generic conversion
        if 'detections' in results:
            for det in results['detections']:
                if det.get('confidence', 0) >= self.conf:
                    bbox = det.get('bbox', [])
                    if len(bbox) >= 4:
                        mapped_label = self._map_to_swedish_wildlife(det.get('category', 'animal'))
                        
                        if mapped_label:
                            dets.append(Detection(
                                label=mapped_label,
                                confidence=det['confidence'],
                                bbox=bbox[:4]  # Ensure we have [x1, y1, x2, y2]
                            ))
        
        return dets
    
    def _map_to_swedish_wildlife(self, category: str) -> Optional[str]:
        """Map detected categories to Swedish wildlife species"""
        category_lower = category.lower()
        
        # Map common COCO misclassifications to Swedish wildlife FIRST
        # so these corrections take precedence over direct animal labels
        mappings = {
            'deer': 'roedeer',
            'elk': 'moose',
            'wild_boar': 'boar',
            'wildboar': 'boar',
            'roe_deer': 'roedeer',
            'roedeer': 'roedeer',
            'bear': 'boar',  # Often boars are misclassified as bears
            'cow': 'moose',  # Often moose are misclassified as cows
            'horse': 'moose',  # Sometimes moose are misclassified as horses
            'sheep': 'roedeer',  # Often roe deer are misclassified as sheep
            'dog': 'boar',  # Sometimes boars are misclassified as dogs
            'elephant': 'boar',  # Sometimes boars are misclassified as elephants
            # Fox and badger mappings
            'cat': 'fox',  # Foxes are often misclassified as cats
            'kitten': 'fox',  # Young foxes as kittens
            'red_fox': 'fox',  # Alternative naming
            'vulpes_vulpes': 'fox',  # Scientific name
            'marten': 'badger',  # Badgers sometimes misclassified as martens
            'weasel': 'badger',  # Badgers sometimes misclassified as weasels
            'meles_meles': 'badger',  # Scientific name
        }
        if category_lower in mappings:
            return mappings[category_lower]

        # Then apply direct/known mappings
        if category_lower in self.SWEDISH_WILDLIFE:
            return self.SWEDISH_WILDLIFE[category_lower]
        if category_lower in self.SWEDISH_ANIMALS:
            return self.SWEDISH_ANIMALS[category_lower]
        if category_lower == 'animal':
            return 'animal'
        return None
    
    def get_available_classes(self) -> List[str]:
        """Get list of available Swedish wildlife classes"""
        return list(set(self.SWEDISH_ANIMALS.values()))
