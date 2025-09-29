"""
Munin - Memory Keeper (Data Ingestion & Processing)

This module handles data ingestion, processing, and storage for the wildlife pipeline:
- Data ingestion from various sources
- Video and image processing
- Model optimization and inference
- Cloud storage management
"""

from .data_ingestion import DataIngestionManager
from .video_processor import VideoProcessor
from .wildlife_detector import WildlifeDetector
from .swedish_wildlife_detector import SwedishWildlifeDetector
from .classification_engine import ClassificationEngine
from .model_optimizer import ModelOptimizer
from .storage_manager import StorageManager
from .exif_extractor import EXIFExtractor
from .detection_filter import DetectionFilter

__all__ = [
    "DataIngestionManager",
    "VideoProcessor", 
    "WildlifeDetector",
    "SwedishWildlifeDetector",
    "ClassificationEngine",
    "ModelOptimizer",
    "StorageManager",
    "EXIFExtractor",
    "DetectionFilter",
]
