"""
Image loading abstraction for wildlife detection pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image
import io

from .cloud.interfaces import StorageAdapter, StorageLocation


class ImageLoader(ABC):
    """Abstract image loader for different storage backends."""
    
    @abstractmethod
    def load_image(self, image_path: Path) -> Image.Image:
        """Load an image from the given path."""
        pass
    
    @abstractmethod
    def load_image_with_metadata(self, image_path: Path) -> Tuple[Image.Image, dict]:
        """Load an image with metadata."""
        pass


class StorageImageLoader(ImageLoader):
    """Image loader that uses storage adapter."""
    
    def __init__(self, storage_adapter: StorageAdapter):
        self.storage_adapter = storage_adapter
    
    def load_image(self, image_path: Path) -> Image.Image:
        """Load an image using storage adapter."""
        try:
            # Convert path to StorageLocation
            location = StorageLocation.from_url(str(image_path))
            
            # Get image data from storage
            image_data = self.storage_adapter.get(location)
            
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            return image
            
        except Exception as e:
            raise ImageLoadError(f"Failed to load image {image_path}: {e}")
    
    def load_image_with_metadata(self, image_path: Path) -> Tuple[Image.Image, dict]:
        """Load an image with metadata."""
        image = self.load_image(image_path)
        
        # Extract basic metadata
        metadata = {
            'size': image.size,
            'mode': image.mode,
            'format': image.format,
            'path': str(image_path)
        }
        
        return image, metadata


class LocalImageLoader(ImageLoader):
    """Local filesystem image loader."""
    
    def load_image(self, image_path: Path) -> Image.Image:
        """Load an image from local filesystem."""
        try:
            if not image_path.exists():
                raise ImageLoadError(f"Image file not found: {image_path}")
            
            image = Image.open(image_path).convert("RGB")
            return image
            
        except Exception as e:
            raise ImageLoadError(f"Failed to load image {image_path}: {e}")
    
    def load_image_with_metadata(self, image_path: Path) -> Tuple[Image.Image, dict]:
        """Load an image with metadata."""
        image = self.load_image(image_path)
        
        # Extract basic metadata
        metadata = {
            'size': image.size,
            'mode': image.mode,
            'format': image.format,
            'path': str(image_path),
            'exists': image_path.exists(),
            'stat': image_path.stat() if image_path.exists() else None
        }
        
        return image, metadata


class ImageLoadError(Exception):
    """Image loading error."""
    pass


def create_image_loader(loader_type: str, storage_adapter: Optional[StorageAdapter] = None) -> ImageLoader:
    """Factory function to create image loaders."""
    if loader_type == "storage" and storage_adapter:
        return StorageImageLoader(storage_adapter)
    elif loader_type == "local":
        return LocalImageLoader()
    else:
        raise ValueError(f"Unsupported image loader type: {loader_type}")
