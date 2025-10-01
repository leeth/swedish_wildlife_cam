"""
Data contract schemas for wildlife pipeline.

Defines Pydantic models for data validation and JSON Schema generation.
"""

from .events import EventsSchema, EventRecord
from .detections import DetectionsSchema, DetectionRecord
from .metadata import MetadataSchema, ContractVersion

__all__ = [
    'EventsSchema',
    'EventRecord', 
    'DetectionsSchema',
    'DetectionRecord',
    'MetadataSchema',
    'ContractVersion'
]
