"""
Events schema for wildlife pipeline.

Defines the data contract for events.parquet files.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import json


class EventRecord(BaseModel):
    """Single event record in events.parquet."""
    
    # Core identifiers
    event_id: str = Field(..., description="Unique event identifier")
    session_id: str = Field(..., description="Processing session identifier")
    camera_id: str = Field(..., description="Camera identifier")
    
    # Timestamps (all in UTC)
    timestamp_utc: datetime = Field(..., description="Event timestamp in UTC")
    timestamp_original: datetime = Field(..., description="Original camera timestamp")
    timestamp_corrected: datetime = Field(..., description="Time-corrected timestamp")
    
    # Location data
    gps_latitude: Optional[float] = Field(None, description="GPS latitude")
    gps_longitude: Optional[float] = Field(None, description="GPS longitude")
    gps_accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    location_zone: Optional[str] = Field(None, description="Location zone identifier")
    
    # Image metadata
    image_path: str = Field(..., description="Path to image file")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    image_format: str = Field(..., description="Image format (JPEG, PNG, etc.)")
    file_size_bytes: int = Field(..., description="File size in bytes")
    
    # Detection summary
    detection_count: int = Field(0, ge=0, description="Number of detections in image")
    observation_any: bool = Field(False, description="Whether any observations were made")
    
    # Weather data (if enriched)
    temperature_celsius: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_percent: Optional[float] = Field(None, ge=0, le=100, description="Humidity percentage")
    precipitation_mm: Optional[float] = Field(None, ge=0, description="Precipitation in mm")
    wind_speed_ms: Optional[float] = Field(None, ge=0, description="Wind speed in m/s")
    
    # Processing metadata
    processing_version: str = Field(..., description="Processing pipeline version")
    contract_version: str = Field("events_v1", description="Data contract version")
    rule_id: Optional[str] = Field(None, description="Processing rule identifier")
    map_version: Optional[str] = Field(None, description="Camera mapping version")
    
    # Quality indicators
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Image quality score")
    blur_detected: bool = Field(False, description="Whether blur was detected")
    motion_detected: bool = Field(False, description="Whether motion was detected")
    
    @validator('timestamp_utc', 'timestamp_original', 'timestamp_corrected')
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
    
    @validator('observation_any')
    def validate_observation_logic(cls, v, values):
        """Validate observation_any logic."""
        detection_count = values.get('detection_count', 0)
        if v != (detection_count > 0):
            raise ValueError("observation_any must be True when detection_count > 0")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventsSchema(BaseModel):
    """Schema for events.parquet file."""
    
    # Metadata
    contract_version: str = Field("events_v1", description="Data contract version")
    created_at: datetime = Field(..., description="Schema creation timestamp")
    session_id: str = Field(..., description="Processing session identifier")
    
    # Data
    events: List[EventRecord] = Field(..., description="List of event records")
    
    # Statistics
    total_events: int = Field(..., description="Total number of events")
    total_detections: int = Field(..., description="Total number of detections")
    cameras_used: List[str] = Field(..., description="List of cameras used")
    
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
    
    @validator('total_events')
    def validate_total_events(cls, v, values):
        """Validate total events matches data length."""
        events = values.get('events', [])
        if v != len(events):
            raise ValueError("total_events must match length of events list")
        return v
    
    @validator('total_detections')
    def validate_total_detections(cls, v, values):
        """Validate total detections matches sum of detection_count."""
        events = values.get('events', [])
        calculated_total = sum(event.detection_count for event in events)
        if v != calculated_total:
            raise ValueError("total_detections must match sum of detection_count")
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
EVENTS_CONTRACT_VERSION = "events_v1"
EVENTS_SCHEMA_VERSION = "1.0.0"
