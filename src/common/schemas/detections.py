"""
Detections schema for wildlife pipeline.

Defines the data contract for detections.parquet files.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, validator
import json


class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    
    x_min: float = Field(..., ge=0, description="Minimum x coordinate")
    y_min: float = Field(..., ge=0, description="Minimum y coordinate")
    x_max: float = Field(..., ge=0, description="Maximum x coordinate")
    y_max: float = Field(..., ge=0, description="Maximum y coordinate")
    
    @validator('x_max')
    def validate_x_max(cls, v, values):
        """Validate x_max > x_min."""
        x_min = values.get('x_min', 0)
        if v <= x_min:
            raise ValueError("x_max must be greater than x_min")
        return v
    
    @validator('y_max')
    def validate_y_max(cls, v, values):
        """Validate y_max > y_min."""
        y_min = values.get('y_min', 0)
        if v <= y_min:
            raise ValueError("y_max must be greater than y_min")
        return v
    
    def is_within_image(self, image_width: int, image_height: int) -> bool:
        """Check if bounding box is within image bounds."""
        return (
            self.x_min >= 0 and self.x_max <= image_width and
            self.y_min >= 0 and self.y_max <= image_height
        )


class DetectionRecord(BaseModel):
    """Single detection record in detections.parquet."""
    
    # Core identifiers
    detection_id: str = Field(..., description="Unique detection identifier")
    event_id: str = Field(..., description="Associated event identifier")
    session_id: str = Field(..., description="Processing session identifier")
    camera_id: str = Field(..., description="Camera identifier")
    
    # Timestamps (all in UTC)
    timestamp_utc: datetime = Field(..., description="Detection timestamp in UTC")
    timestamp_original: datetime = Field(..., description="Original camera timestamp")
    
    # Detection data
    label: str = Field(..., description="Detection label (species/object)")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence [0,1]")
    bounding_box: BoundingBox = Field(..., description="Bounding box coordinates")
    
    # Image context
    image_path: str = Field(..., description="Path to image file")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    
    # Location data
    gps_latitude: Optional[float] = Field(None, description="GPS latitude")
    gps_longitude: Optional[float] = Field(None, description="GPS longitude")
    location_zone: Optional[str] = Field(None, description="Location zone identifier")
    
    # Species information
    species: Optional[str] = Field(None, description="Species name")
    species_confidence: Optional[float] = Field(None, ge=0, le=1, description="Species confidence")
    age_class: Optional[str] = Field(None, description="Age class (adult, juvenile, etc.)")
    sex: Optional[str] = Field(None, description="Sex (male, female, unknown)")
    
    # Detection metadata
    detection_method: str = Field(..., description="Detection method (yolo, manual, etc.)")
    model_version: str = Field(..., description="Model version used")
    processing_version: str = Field(..., description="Processing pipeline version")
    contract_version: str = Field("detections_v1", description="Data contract version")
    
    # Quality indicators
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Detection quality score")
    blur_detected: bool = Field(False, description="Whether blur was detected")
    occlusion_level: Optional[float] = Field(None, ge=0, le=1, description="Occlusion level [0,1]")
    
    # Processing metadata
    rule_id: Optional[str] = Field(None, description="Processing rule identifier")
    map_version: Optional[str] = Field(None, description="Camera mapping version")
    
    @validator('timestamp_utc', 'timestamp_original')
    def validate_utc_timestamps(cls, v):
        """Ensure all timestamps are UTC."""
        if v.tzinfo is None:
            raise ValueError("Timestamp must have timezone info")
        if v.tzinfo.utcoffset(v).total_seconds() != 0:
            raise ValueError("Timestamp must be in UTC")
        return v
    
    @validator('gps_latitude')
    def validate_latitude(cls, v):
        """Validate GPS latitude."""
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v
    
    @validator('gps_longitude')
    def validate_longitude(cls, v):
        """Validate GPS longitude."""
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    @validator('bounding_box')
    def validate_bounding_box_within_image(cls, v, values):
        """Validate bounding box is within image bounds."""
        image_width = values.get('image_width')
        image_height = values.get('image_height')
        if image_width and image_height:
            if not v.is_within_image(image_width, image_height):
                raise ValueError("Bounding box must be within image bounds")
        return v
    
    @validator('label')
    def validate_label_whitelist(cls, v):
        """Validate label is in whitelist."""
        # Define allowed labels (can be expanded)
        allowed_labels = {
            'deer', 'roe_deer', 'red_deer', 'moose', 'elk',
            'boar', 'wild_boar', 'bear', 'wolf', 'lynx',
            'fox', 'red_fox', 'badger', 'otter', 'beaver',
            'bird', 'eagle', 'owl', 'crow', 'raven',
            'human', 'vehicle', 'bicycle', 'motorcycle',
            'unknown', 'other'
        }
        if v.lower() not in allowed_labels:
            raise ValueError(f"Label '{v}' not in allowed whitelist")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DetectionsSchema(BaseModel):
    """Schema for detections.parquet file."""
    
    # Metadata
    contract_version: str = Field("detections_v1", description="Data contract version")
    created_at: datetime = Field(..., description="Schema creation timestamp")
    session_id: str = Field(..., description="Processing session identifier")
    
    # Data
    detections: List[DetectionRecord] = Field(..., description="List of detection records")
    
    # Statistics
    total_detections: int = Field(..., description="Total number of detections")
    unique_events: int = Field(..., description="Number of unique events")
    cameras_used: List[str] = Field(..., description="List of cameras used")
    species_detected: List[str] = Field(..., description="List of species detected")
    
    # Confidence statistics
    avg_confidence: float = Field(..., ge=0, le=1, description="Average confidence")
    min_confidence: float = Field(..., ge=0, le=1, description="Minimum confidence")
    max_confidence: float = Field(..., ge=0, le=1, description="Maximum confidence")
    
    # Processing info
    processing_version: str = Field(..., description="Processing pipeline version")
    rule_id: Optional[str] = Field(None, description="Processing rule identifier")
    map_version: Optional[str] = Field(None, description="Camera mapping version")
    
    @validator('created_at')
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            raise ValueError("Timestamp must have timezone info")
        if v.tzinfo.utcoffset(v).total_seconds() != 0:
            raise ValueError("Timestamp must be in UTC")
        return v
    
    @validator('total_detections')
    def validate_total_detections(cls, v, values):
        """Validate total detections matches data length."""
        detections = values.get('detections', [])
        if v != len(detections):
            raise ValueError("total_detections must match length of detections list")
        return v
    
    @validator('unique_events')
    def validate_unique_events(cls, v, values):
        """Validate unique events count."""
        detections = values.get('detections', [])
        unique_events = len(set(detection.event_id for detection in detections))
        if v != unique_events:
            raise ValueError("unique_events must match count of unique event_ids")
        return v
    
    @validator('avg_confidence', 'min_confidence', 'max_confidence')
    def validate_confidence_stats(cls, v, values):
        """Validate confidence statistics."""
        detections = values.get('detections', [])
        if detections:
            confidences = [d.confidence for d in detections]
            if v == values.get('avg_confidence'):
                expected = sum(confidences) / len(confidences)
                if abs(v - expected) > 1e-6:
                    raise ValueError("avg_confidence must match calculated average")
            elif v == values.get('min_confidence'):
                expected = min(confidences)
                if v != expected:
                    raise ValueError("min_confidence must match minimum confidence")
            elif v == values.get('max_confidence'):
                expected = max(confidences)
                if v != expected:
                    raise ValueError("max_confidence must match maximum confidence")
        return v
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema for this model."""
        return self.schema()
    
    def to_json_schema_file(self, filepath: str) -> None:
        """Save JSON Schema to file."""
        schema = self.to_json_schema()
        with open(filepath, 'w') as f:
            json.dump(schema, f, indent=2)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Contract version constants
DETECTIONS_CONTRACT_VERSION = "detections_v1"
DETECTIONS_SCHEMA_VERSION = "1.0.0"
