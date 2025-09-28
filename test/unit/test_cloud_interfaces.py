"""
Unit tests for cloud interfaces.
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.wildlife_pipeline.cloud.interfaces import (
    StorageLocation, ManifestEntry, Stage2Entry, StorageAdapter, 
    QueueAdapter, ModelProvider, Runner
)


class TestStorageLocation:
    """Test StorageLocation class."""
    
    def test_from_url_file(self):
        """Test parsing file URLs."""
        location = StorageLocation.from_url("file:///path/to/file.txt")
        assert location.protocol == "file"
        assert location.path == "/path/to/file.txt"
        assert location.url == "file:///path/to/file.txt"
    
    def test_from_url_s3(self):
        """Test parsing S3 URLs."""
        location = StorageLocation.from_url("s3://bucket/path/to/file.txt")
        assert location.protocol == "s3"
        assert location.path == "bucket/path/to/file.txt"
        assert location.url == "s3://bucket/path/to/file.txt"
    
    def test_from_url_gcs(self):
        """Test parsing GCS URLs."""
        location = StorageLocation.from_url("gs://bucket/path/to/file.txt")
        assert location.protocol == "gs"
        assert location.path == "bucket/path/to/file.txt"
        assert location.url == "gs://bucket/path/to/file.txt"
    
    def test_from_url_relative(self):
        """Test parsing relative paths."""
        location = StorageLocation.from_url("relative/path/file.txt")
        assert location.protocol == "file"
        assert location.path == "relative/path/file.txt"
        assert location.url == "file://relative/path/file.txt"
    
    def test_from_url_absolute(self):
        """Test parsing absolute paths."""
        location = StorageLocation.from_url("/absolute/path/file.txt")
        assert location.protocol == "file"
        assert location.path == "/absolute/path/file.txt"
        assert location.url == "file:///absolute/path/file.txt"
    
    def test_from_url_windows(self):
        """Test parsing Windows paths."""
        location = StorageLocation.from_url("C:\\path\\to\\file.txt")
        assert location.protocol == "file"
        assert location.path == "C:\\path\\to\\file.txt"
        assert location.url == "file://C:\\path\\to\\file.txt"
    
    def test_from_url_invalid(self):
        """Test parsing invalid URLs."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            StorageLocation.from_url("invalid-url")
    
    def test_from_url_empty(self):
        """Test parsing empty URLs."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            StorageLocation.from_url("")
    
    def test_from_url_none(self):
        """Test parsing None URLs."""
        with pytest.raises(ValueError, match="URL cannot be None"):
            StorageLocation.from_url(None)
    
    def test_equality(self):
        """Test StorageLocation equality."""
        location1 = StorageLocation.from_url("file:///path/to/file.txt")
        location2 = StorageLocation.from_url("file:///path/to/file.txt")
        location3 = StorageLocation.from_url("file:///path/to/other.txt")
        
        assert location1 == location2
        assert location1 != location3
    
    def test_hash(self):
        """Test StorageLocation hashing."""
        location1 = StorageLocation.from_url("file:///path/to/file.txt")
        location2 = StorageLocation.from_url("file:///path/to/file.txt")
        location3 = StorageLocation.from_url("file:///path/to/other.txt")
        
        assert hash(location1) == hash(location2)
        assert hash(location1) != hash(location3)
    
    def test_str(self):
        """Test StorageLocation string representation."""
        location = StorageLocation.from_url("file:///path/to/file.txt")
        assert str(location) == "file:///path/to/file.txt"
    
    def test_repr(self):
        """Test StorageLocation representation."""
        location = StorageLocation.from_url("file:///path/to/file.txt")
        assert repr(location) == "StorageLocation(protocol='file', path='/path/to/file.txt')"


class TestManifestEntry:
    """Test ManifestEntry class."""
    
    def test_creation(self):
        """Test ManifestEntry creation."""
        entry = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert entry.source_path == "file://image.jpg"
        assert entry.crop_path == "file://crop.jpg"
        assert entry.camera_id == "camera1"
        assert entry.timestamp == "2025-09-07T10:30:00"
        assert entry.bbox == {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
        assert entry.det_score == 0.8
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_to_dict(self):
        """Test ManifestEntry to_dict method."""
        entry = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        data = entry.to_dict()
        
        assert data['source_path'] == "file://image.jpg"
        assert data['crop_path'] == "file://crop.jpg"
        assert data['camera_id'] == "camera1"
        assert data['timestamp'] == "2025-09-07T10:30:00"
        assert data['bbox'] == {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
        assert data['det_score'] == 0.8
        assert data['stage1_model'] == "test-model"
        assert data['config_hash'] == "abc123"
    
    def test_from_dict(self):
        """Test ManifestEntry from_dict method."""
        data = {
            'source_path': 'file://image.jpg',
            'crop_path': 'file://crop.jpg',
            'camera_id': 'camera1',
            'timestamp': '2025-09-07T10:30:00',
            'bbox': {'x1': 100, 'y1': 100, 'x2': 200, 'y2': 200},
            'det_score': 0.8,
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }
        
        entry = ManifestEntry.from_dict(data)
        
        assert entry.source_path == "file://image.jpg"
        assert entry.crop_path == "file://crop.jpg"
        assert entry.camera_id == "camera1"
        assert entry.timestamp == "2025-09-07T10:30:00"
        assert entry.bbox == {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
        assert entry.det_score == 0.8
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_from_dict_missing_fields(self):
        """Test ManifestEntry from_dict with missing fields."""
        data = {
            'source_path': 'file://image.jpg',
            'crop_path': 'file://crop.jpg',
            'camera_id': 'camera1',
            'timestamp': '2025-09-07T10:30:00',
            'bbox': {'x1': 100, 'y1': 100, 'x2': 200, 'y2': 200},
            'det_score': 0.8,
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }
        
        # Remove some fields
        del data['camera_id']
        del data['timestamp']
        
        entry = ManifestEntry.from_dict(data)
        
        assert entry.source_path == "file://image.jpg"
        assert entry.crop_path == "file://crop.jpg"
        assert entry.camera_id is None
        assert entry.timestamp is None
        assert entry.bbox == {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
        assert entry.det_score == 0.8
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_equality(self):
        """Test ManifestEntry equality."""
        entry1 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry3 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera2",  # Different camera
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert entry1 == entry2
        assert entry1 != entry3
    
    def test_hash(self):
        """Test ManifestEntry hashing."""
        entry1 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry3 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera2",  # Different camera
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert hash(entry1) == hash(entry2)
        assert hash(entry1) != hash(entry3)


class TestStage2Entry:
    """Test Stage2Entry class."""
    
    def test_creation(self):
        """Test Stage2Entry creation."""
        entry = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert entry.crop_path == "file://crop.jpg"
        assert entry.label == "moose"
        assert entry.confidence == 0.9
        assert entry.auto_ok == True
        assert entry.stage2_model == "test-classifier"
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_to_dict(self):
        """Test Stage2Entry to_dict method."""
        entry = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        data = entry.to_dict()
        
        assert data['crop_path'] == "file://crop.jpg"
        assert data['label'] == "moose"
        assert data['confidence'] == 0.9
        assert data['auto_ok'] == True
        assert data['stage2_model'] == "test-classifier"
        assert data['stage1_model'] == "test-model"
        assert data['config_hash'] == "abc123"
    
    def test_from_dict(self):
        """Test Stage2Entry from_dict method."""
        data = {
            'crop_path': 'file://crop.jpg',
            'label': 'moose',
            'confidence': 0.9,
            'auto_ok': True,
            'stage2_model': 'test-classifier',
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }
        
        entry = Stage2Entry.from_dict(data)
        
        assert entry.crop_path == "file://crop.jpg"
        assert entry.label == "moose"
        assert entry.confidence == 0.9
        assert entry.auto_ok == True
        assert entry.stage2_model == "test-classifier"
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_from_dict_missing_fields(self):
        """Test Stage2Entry from_dict with missing fields."""
        data = {
            'crop_path': 'file://crop.jpg',
            'label': 'moose',
            'confidence': 0.9,
            'auto_ok': True,
            'stage2_model': 'test-classifier',
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }
        
        # Remove some fields
        del data['label']
        del data['confidence']
        
        entry = Stage2Entry.from_dict(data)
        
        assert entry.crop_path == "file://crop.jpg"
        assert entry.label is None
        assert entry.confidence is None
        assert entry.auto_ok == True
        assert entry.stage2_model == "test-classifier"
        assert entry.stage1_model == "test-model"
        assert entry.config_hash == "abc123"
    
    def test_equality(self):
        """Test Stage2Entry equality."""
        entry1 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry3 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="deer",  # Different label
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert entry1 == entry2
        assert entry1 != entry3
    
    def test_hash(self):
        """Test Stage2Entry hashing."""
        entry1 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry3 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="deer",  # Different label
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        assert hash(entry1) == hash(entry2)
        assert hash(entry1) != hash(entry3)


class TestInterfaces:
    """Test interface classes."""
    
    def test_storage_adapter_interface(self):
        """Test StorageAdapter interface."""
        # Test that StorageAdapter is an abstract base class
        assert hasattr(StorageAdapter, '__abstractmethods__')
        assert len(StorageAdapter.__abstractmethods__) > 0
        
        # Test required methods
        required_methods = ['get', 'put', 'exists', 'list', 'delete']
        for method in required_methods:
            assert hasattr(StorageAdapter, method)
    
    def test_queue_adapter_interface(self):
        """Test QueueAdapter interface."""
        # Test that QueueAdapter is an abstract base class
        assert hasattr(QueueAdapter, '__abstractmethods__')
        assert len(QueueAdapter.__abstractmethods__) > 0
        
        # Test required methods
        required_methods = ['send_message', 'receive_messages', 'delete_message']
        for method in required_methods:
            assert hasattr(QueueAdapter, method)
    
    def test_model_provider_interface(self):
        """Test ModelProvider interface."""
        # Test that ModelProvider is an abstract base class
        assert hasattr(ModelProvider, '__abstractmethods__')
        assert len(ModelProvider.__abstractmethods__) > 0
        
        # Test required methods
        required_methods = ['load_model', 'get_model_metadata', 'get_model_hash']
        for method in required_methods:
            assert hasattr(ModelProvider, method)
    
    def test_runner_interface(self):
        """Test Runner interface."""
        # Test that Runner is an abstract base class
        assert hasattr(Runner, '__abstractmethods__')
        assert len(Runner.__abstractmethods__) > 0
        
        # Test required methods
        required_methods = ['run_stage1', 'run_stage2']
        for method in required_methods:
            assert hasattr(Runner, method)


class TestInterfaceIntegration:
    """Test interface integration."""
    
    def test_storage_location_integration(self):
        """Test StorageLocation integration with other classes."""
        # Test that StorageLocation can be used as a key
        location1 = StorageLocation.from_url("file:///path/to/file.txt")
        location2 = StorageLocation.from_url("file:///path/to/file.txt")
        location3 = StorageLocation.from_url("file:///path/to/other.txt")
        
        # Test dictionary usage
        test_dict = {location1: "value1", location3: "value3"}
        assert test_dict[location1] == "value1"
        assert test_dict[location2] == "value1"  # Same location
        assert test_dict[location3] == "value3"
        
        # Test set usage
        test_set = {location1, location2, location3}
        assert len(test_set) == 2  # location1 and location2 are the same
    
    def test_manifest_entry_integration(self):
        """Test ManifestEntry integration with other classes."""
        # Test that ManifestEntry can be used as a key
        entry1 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = ManifestEntry(
            source_path="file://image.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
            det_score=0.8,
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        # Test dictionary usage
        test_dict = {entry1: "value1"}
        assert test_dict[entry1] == "value1"
        assert test_dict[entry2] == "value1"  # Same entry
        
        # Test set usage
        test_set = {entry1, entry2}
        assert len(test_set) == 1  # Same entry
    
    def test_stage2_entry_integration(self):
        """Test Stage2Entry integration with other classes."""
        # Test that Stage2Entry can be used as a key
        entry1 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        entry2 = Stage2Entry(
            crop_path="file://crop.jpg",
            label="moose",
            confidence=0.9,
            auto_ok=True,
            stage2_model="test-classifier",
            stage1_model="test-model",
            config_hash="abc123"
        )
        
        # Test dictionary usage
        test_dict = {entry1: "value1"}
        assert test_dict[entry1] == "value1"
        assert test_dict[entry2] == "value1"  # Same entry
        
        # Test set usage
        test_set = {entry1, entry2}
        assert len(test_set) == 1  # Same entry


if __name__ == '__main__':
    pytest.main([__file__])
