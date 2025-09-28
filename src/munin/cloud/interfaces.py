"""
Core interfaces for cloud-optional wildlife detection pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins


@dataclass
class StorageLocation:
    """Represents a storage location with protocol and path."""
    url: str  # file://, s3://, gs://
    protocol: str  # file, s3, gs
    path: str  # actual path without protocol

    @classmethod
    def from_url(cls, url: str) -> StorageLocation:
        """Parse URL into protocol and path."""
        if url.startswith('file://'):
            return cls(url=url, protocol='file', path=url[7:])
        elif url.startswith('s3://'):
            return cls(url=url, protocol='s3', path=url[5:])
        elif url.startswith('gs://'):
            return cls(url=url, protocol='gs', path=url[5:])
        else:
            # Assume local file
            return cls(url=f"file://{url}", protocol='file', path=url)


@dataclass
class ManifestEntry:
    """Stage-1 manifest entry."""
    source_path: str
    crop_path: str
    camera_id: str
    timestamp: str
    bbox: dict[str, float]  # x1, y1, x2, y2
    det_score: float
    stage1_model: str
    config_hash: str
    latitude: float | None = None
    longitude: float | None = None
    image_width: int | None = None
    image_height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'source_path': self.source_path,
            'crop_path': self.crop_path,
            'camera_id': self.camera_id,
            'timestamp': self.timestamp,
            'bbox': self.bbox,
            'det_score': self.det_score,
            'stage1_model': self.stage1_model,
            'config_hash': self.config_hash,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'image_width': self.image_width,
            'image_height': self.image_height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestEntry:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Stage2Entry:
    """Stage-2 prediction entry."""
    crop_path: str
    label: str
    confidence: float
    auto_ok: bool
    stage2_model: str
    stage1_model: str
    config_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'crop_path': self.crop_path,
            'label': self.label,
            'confidence': self.confidence,
            'auto_ok': self.auto_ok,
            'stage2_model': self.stage2_model,
            'stage1_model': self.stage1_model,
            'config_hash': self.config_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stage2Entry:
        """Create from dictionary."""
        return cls(**data)


class StorageAdapter(ABC):
    """Abstract storage adapter for local/cloud storage."""

    @abstractmethod
    def get(self, location: StorageLocation) -> bytes:
        """Get file content from storage location."""
        pass

    @abstractmethod
    def put(self, location: StorageLocation, content: bytes) -> None:
        """Put file content to storage location."""
        pass

    @abstractmethod
    def list(self, location: StorageLocation, pattern: str = "*") -> builtins.list[StorageLocation]:
        """List files in storage location."""
        pass

    @abstractmethod
    def exists(self, location: StorageLocation) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def delete(self, location: StorageLocation) -> None:
        """Delete file from storage."""
        pass


class QueueAdapter(ABC):
    """Abstract queue adapter for event-driven processing."""

    @abstractmethod
    def send_message(self, queue_name: str, message: dict[str, Any]) -> None:
        """Send message to queue."""
        pass

    @abstractmethod
    def receive_messages(self, queue_name: str, max_messages: int = 10) -> list[dict[str, Any]]:
        """Receive messages from queue."""
        pass

    @abstractmethod
    def delete_message(self, queue_name: str, message_id: str) -> None:
        """Delete message from queue."""
        pass


class ModelProvider(ABC):
    """Abstract model provider for loading models."""

    @abstractmethod
    def load_model(self, model_path: str) -> Any:
        """Load model from path."""
        pass

    @abstractmethod
    def get_model_metadata(self, model_path: str) -> dict[str, Any]:
        """Get model metadata (hash, labels, etc.)."""
        pass

    @abstractmethod
    def get_model_hash(self, model_path: str) -> str:
        """Get model hash for versioning."""
        pass


class Runner(ABC):
    """Abstract runner for executing pipeline stages."""

    @abstractmethod
    def run_stage1(self, input_prefix: str, output_prefix: str, config: dict[str, Any]) -> list[ManifestEntry]:
        """Run Stage-1 processing."""
        pass

    @abstractmethod
    def run_stage2(self, manifest_entries: list[ManifestEntry], output_prefix: str, config: dict[str, Any]) -> list[Stage2Entry]:
        """Run Stage-2 processing."""
        pass


class PipelineConfig:
    """Pipeline configuration with profile support."""

    def __init__(self, profile: str = "local"):
        self.profile = profile
        self.storage_adapter: StorageAdapter | None = None
        self.queue_adapter: QueueAdapter | None = None
        self.model_provider: ModelProvider | None = None
        self.runner: Runner | None = None

        # Load profile-specific configuration
        self._load_profile(profile)

    def _load_profile(self, profile: str):
        """Load configuration from profile."""
        # This will be implemented to load from profiles/{profile}.yaml
        pass
