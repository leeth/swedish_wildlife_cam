"""
Metadata schemas for wildlife pipeline.

Defines versioned metadata and contract information.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import json


class ContractVersion(BaseModel):
    """Data contract version information."""
    
    version: str = Field(..., description="Contract version (e.g., 'events_v1')")
    schema_version: str = Field(..., description="Schema version (e.g., '1.0.0')")
    created_at: datetime = Field(..., description="Contract creation timestamp")
    description: str = Field(..., description="Contract description")
    
    @validator('created_at')
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            raise ValueError("Timestamp must have timezone info")
        if v.tzinfo.utcoffset(v).total_seconds() != 0:
            raise ValueError("Timestamp must be in UTC")
        return v


class EXIFCorrectionRecord(BaseModel):
    """EXIF correction record for camera time adjustments."""
    
    camera_id: str = Field(..., description="Camera identifier")
    delta_seconds: int = Field(..., description="Time correction in seconds")
    effective_from: datetime = Field(..., description="Effective from timestamp")
    effective_to: Optional[datetime] = Field(None, description="Effective to timestamp")
    rule_id: str = Field(..., description="Correction rule identifier")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    @validator('effective_from', 'effective_to', 'created_at')
    def validate_utc_timestamps(cls, v):
        """Ensure all timestamps are UTC."""
        if v is not None:
            if v.tzinfo is None:
                raise ValueError("Timestamp must have timezone info")
            if v.tzinfo.utcoffset(v).total_seconds() != 0:
                raise ValueError("Timestamp must be in UTC")
        return v
    
    @validator('effective_to')
    def validate_effective_period(cls, v, values):
        """Validate effective period."""
        effective_from = values.get('effective_from')
        if v is not None and effective_from and v <= effective_from:
            raise ValueError("effective_to must be after effective_from")
        return v


class CameraMappingRecord(BaseModel):
    """Camera mapping record for stable camera identification."""
    
    camera_id: str = Field(..., description="Stable camera identifier")
    physical_serial: str = Field(..., description="Physical camera serial number")
    alias: Optional[str] = Field(None, description="Camera alias")
    effective_from: datetime = Field(..., description="Effective from timestamp")
    effective_to: Optional[datetime] = Field(None, description="Effective to timestamp")
    map_version: str = Field(..., description="Mapping version")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    @validator('effective_from', 'effective_to', 'created_at')
    def validate_utc_timestamps(cls, v):
        """Ensure all timestamps are UTC."""
        if v is not None:
            if v.tzinfo is None:
                raise ValueError("Timestamp must have timezone info")
            if v.tzinfo.utcoffset(v).total_seconds() != 0:
                raise ValueError("Timestamp must be in UTC")
        return v
    
    @validator('effective_to')
    def validate_effective_period(cls, v, values):
        """Validate effective period."""
        effective_from = values.get('effective_from')
        if v is not None and effective_from and v <= effective_from:
            raise ValueError("effective_to must be after effective_from")
        return v


class MetadataManifest(BaseModel):
    """Metadata manifest for versioned metadata."""
    
    # Manifest metadata
    manifest_version: str = Field("1.0.0", description="Manifest version")
    created_at: datetime = Field(..., description="Manifest creation timestamp")
    
    # Current versions
    current_exif_corrections: str = Field(..., description="Current EXIF corrections version")
    current_camera_mapping: str = Field(..., description="Current camera mapping version")
    
    # File references
    exif_corrections_file: str = Field(..., description="EXIF corrections file path")
    camera_mapping_file: str = Field(..., description="Camera mapping file path")
    
    # Checksums
    exif_corrections_checksum: str = Field(..., description="EXIF corrections file checksum")
    camera_mapping_checksum: str = Field(..., description="Camera mapping file checksum")
    
    # Processing info
    processing_version: str = Field(..., description="Processing pipeline version")
    rule_id: Optional[str] = Field(None, description="Processing rule identifier")
    
    @validator('created_at')
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            raise ValueError("Timestamp must have timezone info")
        if v.tzinfo.utcoffset(v).total_seconds() != 0:
            raise ValueError("Timestamp must be in UTC")
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


class MetadataSchema(BaseModel):
    """Schema for versioned metadata."""
    
    # Contract information
    contract_version: str = Field("metadata_v1", description="Data contract version")
    created_at: datetime = Field(..., description="Schema creation timestamp")
    
    # EXIF corrections
    exif_corrections: List[EXIFCorrectionRecord] = Field(..., description="EXIF correction records")
    
    # Camera mappings
    camera_mappings: List[CameraMappingRecord] = Field(..., description="Camera mapping records")
    
    # Statistics
    total_cameras: int = Field(..., description="Total number of cameras")
    active_cameras: int = Field(..., description="Number of active cameras")
    
    # Processing info
    processing_version: str = Field(..., description="Processing pipeline version")
    rule_id: Optional[str] = Field(None, description="Processing rule identifier")
    
    @validator('created_at')
    def validate_utc_timestamp(cls, v):
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            raise ValueError("Timestamp must have timezone info")
        if v.tzinfo.utcoffset(v).total_seconds() != 0:
            raise ValueError("Timestamp must be in UTC")
        return v
    
    @validator('total_cameras')
    def validate_total_cameras(cls, v, values):
        """Validate total cameras count."""
        camera_mappings = values.get('camera_mappings', [])
        if v != len(camera_mappings):
            raise ValueError("total_cameras must match length of camera_mappings")
        return v
    
    @validator('active_cameras')
    def validate_active_cameras(cls, v, values):
        """Validate active cameras count."""
        camera_mappings = values.get('camera_mappings', [])
        now = datetime.utcnow().replace(tzinfo=None)
        active_count = sum(
            1 for mapping in camera_mappings
            if mapping.effective_to is None or mapping.effective_to > now
        )
        if v != active_count:
            raise ValueError("active_cameras must match count of active mappings")
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
METADATA_CONTRACT_VERSION = "metadata_v1"
METADATA_SCHEMA_VERSION = "1.0.0"
