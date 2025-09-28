"""
Storage adapters for local and cloud storage.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any
import fsspec
import smart_open
from .interfaces import StorageAdapter, StorageLocation


class LocalFSAdapter(StorageAdapter):
    """Local filesystem storage adapter."""
    
    def __init__(self, base_path: str = "file://./data"):
        self.base_path = Path(base_path.replace("file://", ""))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, location: StorageLocation) -> bytes:
        """Get file content from local filesystem."""
        full_path = self.base_path / location.path
        return full_path.read_bytes()
    
    def put(self, location: StorageLocation, content: bytes) -> None:
        """Put file content to local filesystem."""
        full_path = self.base_path / location.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
    
    def list(self, location: StorageLocation, pattern: str = "*") -> List[StorageLocation]:
        """List files in local directory."""
        full_path = self.base_path / location.path
        if not full_path.exists():
            return []
        
        files = []
        for file_path in full_path.glob(pattern):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.base_path)
                files.append(StorageLocation(
                    url=f"file://{rel_path}",
                    protocol="file",
                    path=str(rel_path)
                ))
        return files
    
    def exists(self, location: StorageLocation) -> bool:
        """Check if file exists in local filesystem."""
        full_path = self.base_path / location.path
        return full_path.exists()
    
    def delete(self, location: StorageLocation) -> None:
        """Delete file from local filesystem."""
        full_path = self.base_path / location.path
        if full_path.exists():
            full_path.unlink()


class S3Adapter(StorageAdapter):
    """S3 storage adapter using boto3."""
    
    def __init__(self, base_path: str = "s3://wildlife-detection-bucket", region: str = "eu-north-1"):
        self.base_path = base_path
        self.region = region
        self._fs = fsspec.filesystem('s3', region=region)
    
    def get(self, location: StorageLocation) -> bytes:
        """Get file content from S3."""
        with smart_open.open(location.url, 'rb', transport_params={'region_name': self.region}) as f:
            return f.read()
    
    def put(self, location: StorageLocation, content: bytes) -> None:
        """Put file content to S3."""
        with smart_open.open(location.url, 'wb', transport_params={'region_name': self.region}) as f:
            f.write(content)
    
    def list(self, location: StorageLocation, pattern: str = "*") -> List[StorageLocation]:
        """List files in S3 bucket/prefix."""
        try:
            files = self._fs.glob(f"{location.path}/{pattern}")
            return [
                StorageLocation(url=f"s3://{f}", protocol="s3", path=f)
                for f in files if not f.endswith('/')
            ]
        except Exception:
            return []
    
    def exists(self, location: StorageLocation) -> bool:
        """Check if file exists in S3."""
        try:
            return self._fs.exists(location.path)
        except Exception:
            return False
    
    def delete(self, location: StorageLocation) -> None:
        """Delete file from S3."""
        try:
            self._fs.rm(location.path)
        except Exception:
            pass


class GCSAdapter(StorageAdapter):
    """Google Cloud Storage adapter."""
    
    def __init__(self, base_path: str = "gs://wildlife-detection-bucket"):
        self.base_path = base_path
        self._fs = fsspec.filesystem('gcs')
    
    def get(self, location: StorageLocation) -> bytes:
        """Get file content from GCS."""
        with smart_open.open(location.url, 'rb') as f:
            return f.read()
    
    def put(self, location: StorageLocation, content: bytes) -> None:
        """Put file content to GCS."""
        with smart_open.open(location.url, 'wb') as f:
            f.write(content)
    
    def list(self, location: StorageLocation, pattern: str = "*") -> List[StorageLocation]:
        """List files in GCS bucket/prefix."""
        try:
            files = self._fs.glob(f"{location.path}/{pattern}")
            return [
                StorageLocation(url=f"gs://{f}", protocol="gs", path=f)
                for f in files if not f.endswith('/')
            ]
        except Exception:
            return []
    
    def exists(self, location: StorageLocation) -> bool:
        """Check if file exists in GCS."""
        try:
            return self._fs.exists(location.path)
        except Exception:
            return False
    
    def delete(self, location: StorageLocation) -> None:
        """Delete file from GCS."""
        try:
            self._fs.rm(location.path)
        except Exception:
            pass


def create_storage_adapter(adapter_type: str, **kwargs) -> StorageAdapter:
    """Factory function to create storage adapters."""
    if adapter_type == "local":
        return LocalFSAdapter(**kwargs)
    elif adapter_type == "s3":
        return S3Adapter(**kwargs)
    elif adapter_type == "gcs":
        return GCSAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown storage adapter type: {adapter_type}")
