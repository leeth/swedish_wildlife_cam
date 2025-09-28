"""
Model provider for loading and managing models.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from .interfaces import ModelProvider, StorageLocation
from .storage import create_storage_adapter


class LocalModelProvider(ModelProvider):
    """Local model provider."""
    
    def __init__(self, cache_path: str = "file://./models"):
        self.cache_path = cache_path
        self.storage = create_storage_adapter("local", base_path=cache_path)
        self._model_cache = {}
    
    def load_model(self, model_path: str) -> Any:
        """Load model from local path."""
        if model_path in self._model_cache:
            return self._model_cache[model_path]
        
        # Load model based on file extension
        if model_path.endswith('.pt'):
            from ultralytics import YOLO
            model = YOLO(model_path)
        elif model_path.endswith('.onnx'):
            import onnxruntime as ort
            model = ort.InferenceSession(model_path)
        else:
            raise ValueError(f"Unsupported model format: {model_path}")
        
        self._model_cache[model_path] = model
        return model
    
    def get_model_metadata(self, model_path: str) -> Dict[str, Any]:
        """Get model metadata."""
        metadata_path = model_path.replace('.pt', '_metadata.yaml').replace('.onnx', '_metadata.yaml')
        
        try:
            if Path(metadata_path).exists():
                with open(metadata_path, 'r') as f:
                    return yaml.safe_load(f)
        except Exception:
            pass
        
        # Default metadata
        return {
            'model_path': model_path,
            'model_hash': self.get_model_hash(model_path),
            'labels': self._get_default_labels(),
            'input_size': (640, 640),
            'model_type': 'yolo' if model_path.endswith('.pt') else 'onnx'
        }
    
    def get_model_hash(self, model_path: str) -> str:
        """Get model hash for versioning."""
        try:
            with open(model_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return "unknown"
    
    def _get_default_labels(self) -> Dict[str, str]:
        """Get default COCO labels."""
        return {
            '0': 'person', '1': 'bicycle', '2': 'car', '3': 'motorcycle', '4': 'airplane',
            '5': 'bus', '6': 'train', '7': 'truck', '8': 'boat', '9': 'traffic light',
            '10': 'fire hydrant', '11': 'stop sign', '12': 'parking meter', '13': 'bench',
            '14': 'bird', '15': 'cat', '16': 'dog', '17': 'horse', '18': 'sheep',
            '19': 'cow', '20': 'elephant', '21': 'bear', '22': 'zebra', '23': 'giraffe'
        }


class CloudModelProvider(ModelProvider):
    """Cloud model provider with caching."""
    
    def __init__(self, storage_adapter, cache_path: str = "s3://wildlife-models-bucket"):
        self.storage = storage_adapter
        self.cache_path = cache_path
        self._model_cache = {}
    
    def load_model(self, model_path: str) -> Any:
        """Load model from cloud storage with local caching."""
        if model_path in self._model_cache:
            return self._model_cache[model_path]
        
        # Download model if not cached locally
        local_path = self._download_model(model_path)
        
        # Load model
        if model_path.endswith('.pt'):
            from ultralytics import YOLO
            model = YOLO(local_path)
        elif model_path.endswith('.onnx'):
            import onnxruntime as ort
            model = ort.InferenceSession(local_path)
        else:
            raise ValueError(f"Unsupported model format: {model_path}")
        
        self._model_cache[model_path] = model
        return model
    
    def _download_model(self, model_path: str) -> str:
        """Download model from cloud storage to local cache."""
        import tempfile
        import os
        
        # Create local cache directory
        cache_dir = Path.home() / ".wildlife_models"
        cache_dir.mkdir(exist_ok=True)
        
        # Check if already cached
        local_path = cache_dir / Path(model_path).name
        if local_path.exists():
            return str(local_path)
        
        # Download from cloud
        model_location = StorageLocation.from_url(f"{self.cache_path}/{model_path}")
        content = self.storage.get(model_location)
        
        # Save to local cache
        local_path.write_bytes(content)
        return str(local_path)
    
    def get_model_metadata(self, model_path: str) -> Dict[str, Any]:
        """Get model metadata from cloud storage."""
        metadata_path = model_path.replace('.pt', '_metadata.yaml').replace('.onnx', '_metadata.yaml')
        
        try:
            metadata_location = StorageLocation.from_url(f"{self.cache_path}/{metadata_path}")
            if self.storage.exists(metadata_location):
                content = self.storage.get(metadata_location)
                return yaml.safe_load(content.decode('utf-8'))
        except Exception:
            pass
        
        # Default metadata
        return {
            'model_path': model_path,
            'model_hash': self.get_model_hash(model_path),
            'labels': self._get_default_labels(),
            'input_size': (640, 640),
            'model_type': 'yolo' if model_path.endswith('.pt') else 'onnx'
        }
    
    def get_model_hash(self, model_path: str) -> str:
        """Get model hash from cloud storage."""
        try:
            model_location = StorageLocation.from_url(f"{self.cache_path}/{model_path}")
            content = self.storage.get(model_location)
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return "unknown"
    
    def _get_default_labels(self) -> Dict[str, str]:
        """Get default COCO labels."""
        return {
            '0': 'person', '1': 'bicycle', '2': 'car', '3': 'motorcycle', '4': 'airplane',
            '5': 'bus', '6': 'train', '7': 'truck', '8': 'boat', '9': 'traffic light',
            '10': 'fire hydrant', '11': 'stop sign', '12': 'parking meter', '13': 'bench',
            '14': 'bird', '15': 'cat', '16': 'dog', '17': 'horse', '18': 'sheep',
            '19': 'cow', '20': 'elephant', '21': 'bear', '22': 'zebra', '23': 'giraffe'
        }


def create_model_provider(provider_type: str, storage_adapter=None, **kwargs) -> ModelProvider:
    """Factory function to create model providers."""
    if provider_type == "local":
        return LocalModelProvider(**kwargs)
    elif provider_type == "cloud":
        if storage_adapter is None:
            raise ValueError("storage_adapter required for cloud model provider")
        return CloudModelProvider(storage_adapter, **kwargs)
    else:
        raise ValueError(f"Unknown model provider type: {provider_type}")
