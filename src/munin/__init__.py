"""
Munin - Memory Keeper (Data Ingestion & Processing)

This module handles data ingestion, processing, and storage for the wildlife pipeline:
- Data ingestion from various sources
- Video and image processing
- Model optimization and inference
- Cloud storage management
"""

from .data_ingestion import OptimizedFileWalker, OptimizedExifExtractor, OptimizedImageProcessor
from .video_processor import OptimizedVideoProcessor
from .wildlife_detector import YOLODetector
from .swedish_wildlife_detector import SwedishWildlifeDetector
from .classification_engine import YOLOClassifier
from .model_optimizer import ModelOptimizer
from .storage_manager import WildlifeDatabase
from .exif_extractor import EXIFExtractor
from .detection_filter import DetectionFilter

__all__ = [
    "OptimizedFileWalker",
    "OptimizedExifExtractor", 
    "OptimizedImageProcessor",
    "OptimizedVideoProcessor", 
    "YOLODetector",
    "SwedishWildlifeDetector",
    "YOLOClassifier",
    "ModelOptimizer",
    "WildlifeDatabase",
    "EXIFExtractor",
    "DetectionFilter",
]
