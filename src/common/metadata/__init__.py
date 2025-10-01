"""
Versioned metadata management for wildlife pipeline.

Handles EXIF correction tables, camera mapping, and metadata manifests.
"""

from .exif_corrections import EXIFCorrectionsManager
from .camera_mapping import CameraMappingManager
from .metadata_manifest import MetadataManifestManager

__all__ = [
    'EXIFCorrectionsManager',
    'CameraMappingManager', 
    'MetadataManifestManager'
]
