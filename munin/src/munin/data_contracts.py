"""
Data contracts and schemas for wildlife pipeline.

This module defines Pydantic models for:
- Camera metadata and identification
- Detection results and confidence scores
- Review status and manual annotation
- Pipeline artifacts and manifests
- GPS coordinates and timestamps
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import uuid

from pydantic import BaseModel, Field, validator, root_validator
import numpy as np


class CameraInfo(BaseModel):
    """Camera identification and metadata."""
    camera_id: str = Field(..., description="Unique camera identifier")
    location_name: Optional[str] = Field(None, description="Human-readable location name")
    gps_latitude: Optional[float] = Field(None, ge=-90, le=90, description="GPS latitude in decimal degrees")
    gps_longitude: Optional[float] = Field(None, ge=-180, le=180, description="GPS longitude in decimal degrees")
    gps_accuracy_meters: Optional[float] = Field(None, gt=0, description="GPS accuracy in meters")
    elevation_meters: Optional[float] = Field(None, description="Elevation above sea level in meters")
    camera_make: Optional[str] = Field(None, description="Camera manufacturer")
    camera_model: Optional[str] = Field(None, description="Camera model")
    sd_card_id: Optional[str] = Field(None, description="SD card identifier")
    
    @validator('gps_latitude')
    def validate_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('gps_longitude')
    def validate_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v


class DetectionResult(BaseModel):
    """Individual detection result."""
    label: str = Field(..., description="Detected class label")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence score")
    bbox_x1: float = Field(..., ge=0, description="Bounding box left coordinate")
    bbox_y1: float = Field(..., ge=0, description="Bounding box top coordinate")
    bbox_x2: float = Field(..., ge=0, description="Bounding box right coordinate")
    bbox_y2: float = Field(..., ge=0, description="Bounding box bottom coordinate")
    stage1_model: str = Field(..., description="Stage 1 model identifier")
    stage1_confidence: float = Field(..., ge=0, le=1, description="Stage 1 confidence score")
    stage2_model: Optional[str] = Field(None, description="Stage 2 model identifier")
    stage2_confidence: Optional[float] = Field(None, ge=0, le=1, description="Stage 2 confidence score")
    
    @validator('bbox_x2')
    def validate_bbox_x2(cls, v, values):
        if 'bbox_x1' in values and v <= values['bbox_x1']:
            raise ValueError('bbox_x2 must be greater than bbox_x1')
        return v
    
    @validator('bbox_y2')
    def validate_bbox_y2(cls, v, values):
        if 'bbox_y1' in values and v <= values['bbox_y1']:
            raise ValueError('bbox_y2 must be greater than bbox_y1')
        return v


class ReviewStatus(BaseModel):
    """Review and annotation status."""
    needs_review: bool = Field(False, description="Whether manual review is required")
    is_doubtful: bool = Field(False, description="Whether detection is doubtful")
    doubt_reason: Optional[str] = Field(None, description="Reason for doubt")
    manual_annotation: Optional[str] = Field(None, description="Manual annotation if available")
    reviewer_id: Optional[str] = Field(None, description="ID of human reviewer")
    review_timestamp: Optional[datetime] = Field(None, description="When review was completed")
    auto_approved: bool = Field(False, description="Whether auto-approved by pipeline")
    
    @root_validator
    def validate_review_status(cls, values):
        needs_review = values.get('needs_review', False)
        is_doubtful = values.get('is_doubtful', False)
        auto_approved = values.get('auto_approved', False)
        
        # If auto-approved, should not need review
        if auto_approved and needs_review:
            raise ValueError('Auto-approved detections should not need review')
        
        # If doubtful, should need review
        if is_doubtful and not needs_review:
            values['needs_review'] = True
        
        return values


class GPSCoordinates(BaseModel):
    """GPS coordinates with metadata."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    accuracy: Optional[float] = Field(None, gt=0, description="GPS accuracy in meters")
    timestamp: Optional[datetime] = Field(None, description="GPS timestamp")
    source: str = Field("exif", description="Source of GPS data (exif, manual, etc.)")
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class ImageMetadata(BaseModel):
    """Image metadata and EXIF information."""
    file_path: Path = Field(..., description="Path to image file")
    file_size_bytes: int = Field(..., gt=0, description="File size in bytes")
    width: int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")
    datetime_original: Optional[datetime] = Field(None, description="Original capture datetime")
    datetime_digitized: Optional[datetime] = Field(None, description="Digitization datetime")
    datetime_modified: Optional[datetime] = Field(None, description="File modification datetime")
    camera_make: Optional[str] = Field(None, description="Camera manufacturer")
    camera_model: Optional[str] = Field(None, description="Camera model")
    gps: Optional[GPSCoordinates] = Field(None, description="GPS coordinates")
    file_hash: Optional[str] = Field(None, description="File hash for integrity")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if not v.exists():
            raise ValueError(f'File does not exist: {v}')
        return v


class PipelineArtifact(BaseModel):
    """Pipeline artifact with metadata."""
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique artifact ID")
    artifact_type: str = Field(..., description="Type of artifact (crop, prediction, manifest)")
    source_path: Path = Field(..., description="Source file path")
    artifact_path: Path = Field(..., description="Path to artifact file")
    pipeline_stage: str = Field(..., description="Pipeline stage (stage1, stage2, stage3)")
    model_hash: str = Field(..., description="Model hash for reproducibility")
    config_hash: str = Field(..., description="Configuration hash")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    file_size_bytes: int = Field(..., gt=0, description="Artifact file size")
    
    @validator('artifact_type')
    def validate_artifact_type(cls, v):
        allowed_types = ['crop', 'prediction', 'manifest', 'parquet', 'log']
        if v not in allowed_types:
            raise ValueError(f'Artifact type must be one of: {allowed_types}')
        return v


class ManifestEntry(BaseModel):
    """Stage 1 manifest entry."""
    source_path: Path = Field(..., description="Source image path")
    crop_path: Path = Field(..., description="Cropped image path")
    camera_id: str = Field(..., description="Camera identifier")
    timestamp: datetime = Field(..., description="Image timestamp")
    bbox: List[float] = Field(..., min_items=4, max_items=4, description="Bounding box [x1, y1, x2, y2]")
    det_score: float = Field(..., ge=0, le=1, description="Detection confidence score")
    stage1_model: str = Field(..., description="Stage 1 model identifier")
    config_hash: str = Field(..., description="Configuration hash")
    
    @validator('bbox')
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError('Bounding box must have exactly 4 coordinates')
        x1, y1, x2, y2 = v
        if x2 <= x1 or y2 <= y1:
            raise ValueError('Invalid bounding box coordinates')
        return v


class Stage2Entry(BaseModel):
    """Stage 2 prediction entry."""
    crop_path: Path = Field(..., description="Cropped image path")
    label: str = Field(..., description="Predicted class label")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence")
    auto_ok: bool = Field(..., description="Whether auto-approved")
    stage2_model: str = Field(..., description="Stage 2 model identifier")
    stage1_model: str = Field(..., description="Stage 1 model identifier")
    config_hash: str = Field(..., description="Configuration hash")
    processing_time_ms: Optional[float] = Field(None, gt=0, description="Processing time in milliseconds")


class ObservationRecord(BaseModel):
    """Final observation record for analytics."""
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique observation ID")
    image_path: Path = Field(..., description="Source image path")
    camera_id: str = Field(..., description="Camera identifier")
    timestamp: datetime = Field(..., description="Observation timestamp")
    gps: Optional[GPSCoordinates] = Field(None, description="GPS coordinates")
    observations: List[DetectionResult] = Field(default_factory=list, description="Detection results")
    top_label: Optional[str] = Field(None, description="Top prediction label")
    top_confidence: Optional[float] = Field(None, ge=0, le=1, description="Top prediction confidence")
    needs_review: bool = Field(False, description="Whether manual review is required")
    review_status: Optional[ReviewStatus] = Field(None, description="Review status")
    pipeline_version: str = Field(..., description="Pipeline version")
    model_hashes: Dict[str, str] = Field(..., description="Model hashes used")
    source_etag: Optional[str] = Field(None, description="Source file ETag")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('top_label')
    def set_top_label(cls, v, values):
        if v is None and 'observations' in values:
            observations = values['observations']
            if observations:
                # Set top label from highest confidence observation
                top_obs = max(observations, key=lambda x: x.confidence)
                return top_obs.label
        return v
    
    @validator('top_confidence')
    def set_top_confidence(cls, v, values):
        if v is None and 'observations' in values:
            observations = values['observations']
            if observations:
                # Set top confidence from highest confidence observation
                top_obs = max(observations, key=lambda x: x.confidence)
                return top_obs.confidence
        return v


class CompressedObservation(BaseModel):
    """Compressed observation for Stage 3 reporting."""
    camera_id: str = Field(..., description="Camera identifier")
    species: str = Field(..., description="Species label")
    start_time: datetime = Field(..., description="Observation start time")
    end_time: datetime = Field(..., description="Observation end time")
    duration_seconds: float = Field(..., gt=0, description="Total duration in seconds")
    max_confidence: float = Field(..., ge=0, le=1, description="Maximum confidence score")
    avg_confidence: float = Field(..., ge=0, le=1, description="Average confidence score")
    frame_count: int = Field(..., gt=0, description="Number of frames")
    timeline: List[Dict[str, Any]] = Field(default_factory=list, description="Timeline of detections")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class PipelineConfig(BaseModel):
    """Pipeline configuration with validation."""
    stage1_confidence: float = Field(0.3, ge=0, le=1, description="Stage 1 confidence threshold")
    min_relative_area: float = Field(0.003, ge=0, le=1, description="Minimum relative area")
    max_relative_area: float = Field(0.8, ge=0, le=1, description="Maximum relative area")
    min_aspect_ratio: float = Field(0.2, gt=0, description="Minimum aspect ratio")
    max_aspect_ratio: float = Field(5.0, gt=0, description="Maximum aspect ratio")
    edge_margin_px: int = Field(12, ge=0, description="Edge margin in pixels")
    crop_padding: float = Field(0.15, ge=0, le=1, description="Crop padding ratio")
    stage2_confidence: float = Field(0.5, ge=0, le=1, description="Stage 2 confidence threshold")
    compression_window_minutes: int = Field(10, gt=0, description="Compression window in minutes")
    min_duration_seconds: float = Field(5.0, ge=0, description="Minimum duration for compression")
    
    @validator('max_relative_area')
    def validate_max_area(cls, v, values):
        if 'min_relative_area' in values and v <= values['min_relative_area']:
            raise ValueError('Max relative area must be greater than min relative area')
        return v
    
    @validator('max_aspect_ratio')
    def validate_max_aspect(cls, v, values):
        if 'min_aspect_ratio' in values and v <= values['min_aspect_ratio']:
            raise ValueError('Max aspect ratio must be greater than min aspect ratio')
        return v


# Utility functions for data validation
def validate_camera_id(camera_id: str) -> bool:
    """Validate camera ID format."""
    return bool(camera_id and len(camera_id.strip()) > 0)


def validate_gps_coordinates(lat: float, lon: float) -> bool:
    """Validate GPS coordinates."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_confidence_score(score: float) -> bool:
    """Validate confidence score."""
    return 0 <= score <= 1


def validate_bbox_coordinates(bbox: List[float]) -> bool:
    """Validate bounding box coordinates."""
    if len(bbox) != 4:
        return False
    x1, y1, x2, y2 = bbox
    return x2 > x1 and y2 > y1 and all(coord >= 0 for coord in bbox)
