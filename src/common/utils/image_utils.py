"""
Image utility functions.
"""

from typing import Tuple, Union, Optional
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def load_image(image_path: Union[str, Path]):
    """Load an image from file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Image as numpy array (BGR format for OpenCV)
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")
        
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    # Load with OpenCV (BGR format)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
        
    return image


def save_image(image, output_path: Union[str, Path], 
               quality: int = 95) -> None:
    """Save an image to file.
    
    Args:
        image: Image as numpy array
        output_path: Path to save the image
        quality: JPEG quality (1-100)
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")
        
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save with OpenCV
    success = cv2.imwrite(str(output_path), image)
    if not success:
        raise ValueError(f"Could not save image: {output_path}")


def resize_image(image, 
                target_size: Tuple[int, int],
                keep_aspect_ratio: bool = True):
    """Resize an image.
    
    Args:
        image: Input image
        target_size: Target size (width, height)
        keep_aspect_ratio: Whether to maintain aspect ratio
        
    Returns:
        Resized image
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")
        
    if keep_aspect_ratio:
        # Calculate scaling factor to fit within target size
        h, w = image.shape[:2]
        target_w, target_h = target_size
        
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    else:
        resized = cv2.resize(image, target_size, interpolation=cv2.INTER_LANCZOS4)
        
    return resized


def normalize_image(image: np.ndarray, 
                   mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
                   std: Tuple[float, float, float] = (0.229, 0.224, 0.225)) -> np.ndarray:
    """Normalize an image for model input.
    
    Args:
        image: Input image (BGR format)
        mean: Mean values for normalization
        std: Standard deviation values for normalization
        
    Returns:
        Normalized image
    """
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Convert to float and normalize
    image_float = image_rgb.astype(np.float32) / 255.0
    
    # Normalize with mean and std
    normalized = (image_float - np.array(mean)) / np.array(std)
    
    return normalized


def get_image_info(image_path: Union[str, Path]) -> dict:
    """Get information about an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with image information
    """
    image_path = Path(image_path)
    
    # Load with PIL for metadata
    with Image.open(image_path) as img:
        info = {
            'path': str(image_path),
            'size': img.size,  # (width, height)
            'mode': img.mode,
            'format': img.format,
            'has_transparency': img.mode in ('RGBA', 'LA', 'P'),
        }
        
        # Get EXIF data if available
        if hasattr(img, '_getexif') and img._getexif() is not None:
            info['has_exif'] = True
        else:
            info['has_exif'] = False
            
    return info


def crop_image(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Crop an image using bounding box coordinates.
    
    Args:
        image: Input image
        bbox: Bounding box (x1, y1, x2, y2)
        
    Returns:
        Cropped image
    """
    x1, y1, x2, y2 = bbox
    return image[y1:y2, x1:x2]


def draw_bbox(image: np.ndarray, bbox: Tuple[int, int, int, int], 
              color: Tuple[int, int, int] = (0, 255, 0),
              thickness: int = 2) -> np.ndarray:
    """Draw a bounding box on an image.
    
    Args:
        image: Input image
        bbox: Bounding box (x1, y1, x2, y2)
        color: BGR color tuple
        thickness: Line thickness
        
    Returns:
        Image with bounding box drawn
    """
    image_copy = image.copy()
    x1, y1, x2, y2 = bbox
    cv2.rectangle(image_copy, (x1, y1), (x2, y2), color, thickness)
    return image_copy
