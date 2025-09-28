"""
Unit tests for cloud model providers.
"""

import pytest
import hashlib
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from src.wildlife_pipeline.cloud.models import (
    LocalModelProvider, CloudModelProvider, create_model_provider
)
from src.wildlife_pipeline.cloud.interfaces import StorageLocation


class TestLocalModelProvider:
    """Test local model provider."""
    
    def test_provider_creation(self):
        """Test provider creation."""
        provider = LocalModelProvider(cache_path="file://./models")
        assert provider.cache_path.name == "models"
    
    def test_provider_creation_missing_ultralytics(self):
        """Test provider creation when ultralytics is not available."""
        with patch('src.wildlife_pipeline.cloud.models.ultralytics', None):
            with pytest.raises(ImportError, match="ultralytics package required"):
                LocalModelProvider()
    
    @patch('src.wildlife_pipeline.cloud.models.ultralytics.YOLO')
    def test_load_model(self, mock_yolo):
        """Test model loading."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        provider = LocalModelProvider(cache_path="file://./models")
        model = provider.load_model("yolov8n.pt")
        
        # Verify model was loaded
        assert model == mock_model
        mock_yolo.assert_called_once_with("yolov8n.pt")
    
    @patch('src.wildlife_pipeline.cloud.models.ultralytics.YOLO')
    def test_load_model_with_cache(self, mock_yolo):
        """Test model loading with cache."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data="model content")):
            with patch('pathlib.Path.exists', return_value=True):
                provider = LocalModelProvider(cache_path="file://./models")
                model = provider.load_model("yolov8n.pt")
        
        # Verify model was loaded
        assert model == mock_model
        mock_yolo.assert_called_once_with("yolov8n.pt")
    
    def test_get_model_metadata(self):
        """Test model metadata retrieval."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        metadata = provider.get_model_metadata("yolov8n.pt")
        
        # Verify metadata structure
        assert 'model_name' in metadata
        assert 'model_path' in metadata
        assert 'model_hash' in metadata
        assert 'model_size' in metadata
        assert 'model_type' in metadata
        assert 'model_version' in metadata
        assert 'model_labels' in metadata
        
        # Verify values
        assert metadata['model_name'] == "yolov8n.pt"
        assert metadata['model_path'] == "yolov8n.pt"
        assert metadata['model_type'] == "yolo"
        assert metadata['model_version'] == "8"
        assert isinstance(metadata['model_labels'], list)
    
    def test_get_model_hash(self):
        """Test model hash calculation."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data="model content")):
            with patch('pathlib.Path.exists', return_value=True):
                model_hash = provider.get_model_hash("yolov8n.pt")
        
        # Verify hash is calculated
        assert isinstance(model_hash, str)
        assert len(model_hash) == 64  # SHA-256 hash length
        
        # Verify hash is consistent
        expected_hash = hashlib.sha256(b"model content").hexdigest()
        assert model_hash == expected_hash
    
    def test_get_model_hash_missing_file(self):
        """Test model hash calculation for missing file."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        with patch('pathlib.Path.exists', return_value=False):
            model_hash = provider.get_model_hash("nonexistent.pt")
        
        # Should return None for missing file
        assert model_hash is None
    
    def test_get_model_size(self):
        """Test model size calculation."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        # Mock file operations
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024  # 1 MB
                model_size = provider.get_model_size("yolov8n.pt")
        
        # Verify size is calculated
        assert model_size == 1024 * 1024
    
    def test_get_model_size_missing_file(self):
        """Test model size calculation for missing file."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        with patch('pathlib.Path.exists', return_value=False):
            model_size = provider.get_model_size("nonexistent.pt")
        
        # Should return None for missing file
        assert model_size is None
    
    def test_get_model_labels(self):
        """Test model labels retrieval."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        labels = provider.get_model_labels("yolov8n.pt")
        
        # Verify labels are returned
        assert isinstance(labels, list)
        assert len(labels) > 0
        
        # Verify common COCO labels are present
        common_labels = ['person', 'bicycle', 'car', 'dog', 'cat']
        for label in common_labels:
            assert label in labels


class TestCloudModelProvider:
    """Test cloud model provider."""
    
    def test_provider_creation(self):
        """Test provider creation."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        assert provider.storage == mock_storage
        assert provider.cache_path == "s3://models-bucket"
    
    def test_provider_creation_missing_ultralytics(self):
        """Test provider creation when ultralytics is not available."""
        with patch('src.wildlife_pipeline.cloud.models.ultralytics', None):
            mock_storage = MagicMock()
            with pytest.raises(ImportError, match="ultralytics package required"):
                CloudModelProvider(mock_storage)
    
    @patch('src.wildlife_pipeline.cloud.models.ultralytics.YOLO')
    def test_load_model(self, mock_yolo):
        """Test model loading."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        
        model = provider.load_model("yolov8n.pt")
        
        # Verify model was loaded
        assert model == mock_model
        mock_yolo.assert_called_once_with("yolov8n.pt")
        
        # Verify storage operations
        mock_storage.exists.assert_called_once()
        mock_storage.get.assert_called_once()
    
    @patch('src.wildlife_pipeline.cloud.models.ultralytics.YOLO')
    def test_load_model_missing_in_storage(self, mock_yolo):
        """Test model loading when model is missing in storage."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = False
        
        model = provider.load_model("yolov8n.pt")
        
        # Verify model was loaded from local cache
        assert model == mock_model
        mock_yolo.assert_called_once_with("yolov8n.pt")
        
        # Verify storage was checked
        mock_storage.exists.assert_called_once()
    
    def test_get_model_metadata(self):
        """Test model metadata retrieval."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        
        metadata = provider.get_model_metadata("yolov8n.pt")
        
        # Verify metadata structure
        assert 'model_name' in metadata
        assert 'model_path' in metadata
        assert 'model_hash' in metadata
        assert 'model_size' in metadata
        assert 'model_type' in metadata
        assert 'model_version' in metadata
        assert 'model_labels' in metadata
        
        # Verify values
        assert metadata['model_name'] == "yolov8n.pt"
        assert metadata['model_path'] == "yolov8n.pt"
        assert metadata['model_type'] == "yolo"
        assert metadata['model_version'] == "8"
        assert isinstance(metadata['model_labels'], list)
    
    def test_get_model_hash(self):
        """Test model hash calculation."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        
        model_hash = provider.get_model_hash("yolov8n.pt")
        
        # Verify hash is calculated
        assert isinstance(model_hash, str)
        assert len(model_hash) == 64  # SHA-256 hash length
        
        # Verify hash is consistent
        expected_hash = hashlib.sha256(b"model content").hexdigest()
        assert model_hash == expected_hash
    
    def test_get_model_hash_missing_file(self):
        """Test model hash calculation for missing file."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = False
        
        model_hash = provider.get_model_hash("nonexistent.pt")
        
        # Should return None for missing file
        assert model_hash is None
    
    def test_get_model_size(self):
        """Test model size calculation."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        
        model_size = provider.get_model_size("yolov8n.pt")
        
        # Verify size is calculated
        assert model_size == len(b"model content")
    
    def test_get_model_size_missing_file(self):
        """Test model size calculation for missing file."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations
        mock_storage.exists.return_value = False
        
        model_size = provider.get_model_size("nonexistent.pt")
        
        # Should return None for missing file
        assert model_size is None
    
    def test_get_model_labels(self):
        """Test model labels retrieval."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        labels = provider.get_model_labels("yolov8n.pt")
        
        # Verify labels are returned
        assert isinstance(labels, list)
        assert len(labels) > 0
        
        # Verify common COCO labels are present
        common_labels = ['person', 'bicycle', 'car', 'dog', 'cat']
        for label in common_labels:
            assert label in labels


class TestCreateModelProvider:
    """Test model provider factory function."""
    
    def test_create_local_provider(self):
        """Test creating local model provider."""
        provider = create_model_provider("local", cache_path="file://./models")
        assert isinstance(provider, LocalModelProvider)
        assert provider.cache_path.name == "models"
    
    def test_create_cloud_provider(self):
        """Test creating cloud model provider."""
        mock_storage = MagicMock()
        provider = create_model_provider("cloud", storage_adapter=mock_storage, cache_path="s3://models-bucket")
        assert isinstance(provider, CloudModelProvider)
        assert provider.storage == mock_storage
        assert provider.cache_path == "s3://models-bucket"
    
    def test_create_cloud_provider_missing_storage(self):
        """Test creating cloud model provider without storage adapter."""
        with pytest.raises(ValueError, match="storage_adapter required for cloud model provider"):
            create_model_provider("cloud", cache_path="s3://models-bucket")
    
    def test_create_invalid_provider(self):
        """Test creating invalid model provider."""
        with pytest.raises(ValueError, match="Unknown model provider type"):
            create_model_provider("invalid", cache_path="file://./models")


class TestModelProviderIntegration:
    """Test model provider integration."""
    
    def test_local_provider_integration(self):
        """Test local model provider integration."""
        provider = LocalModelProvider(cache_path="file://./models")
        
        # Test that provider has required methods
        assert hasattr(provider, 'load_model')
        assert hasattr(provider, 'get_model_metadata')
        assert hasattr(provider, 'get_model_hash')
        assert hasattr(provider, 'get_model_size')
        assert hasattr(provider, 'get_model_labels')
        
        # Test that methods are callable
        assert callable(provider.load_model)
        assert callable(provider.get_model_metadata)
        assert callable(provider.get_model_hash)
        assert callable(provider.get_model_size)
        assert callable(provider.get_model_labels)
    
    def test_cloud_provider_integration(self):
        """Test cloud model provider integration."""
        mock_storage = MagicMock()
        provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Test that provider has required methods
        assert hasattr(provider, 'load_model')
        assert hasattr(provider, 'get_model_metadata')
        assert hasattr(provider, 'get_model_hash')
        assert hasattr(provider, 'get_model_size')
        assert hasattr(provider, 'get_model_labels')
        
        # Test that methods are callable
        assert callable(provider.load_model)
        assert callable(provider.get_model_metadata)
        assert callable(provider.get_model_hash)
        assert callable(provider.get_model_size)
        assert callable(provider.get_model_labels)
    
    def test_model_provider_interface_consistency(self):
        """Test that all model providers implement the same interface."""
        mock_storage = MagicMock()
        
        providers = [
            LocalModelProvider(cache_path="file://./models"),
            CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        ]
        
        for provider in providers:
            # Test that all providers have required methods
            assert hasattr(provider, 'load_model')
            assert hasattr(provider, 'get_model_metadata')
            assert hasattr(provider, 'get_model_hash')
            assert hasattr(provider, 'get_model_size')
            assert hasattr(provider, 'get_model_labels')
            
            # Test that methods are callable
            assert callable(provider.load_model)
            assert callable(provider.get_model_metadata)
            assert callable(provider.get_model_hash)
            assert callable(provider.get_model_size)
            assert callable(provider.get_model_labels)
    
    def test_model_metadata_consistency(self):
        """Test that model metadata is consistent across providers."""
        mock_storage = MagicMock()
        
        local_provider = LocalModelProvider(cache_path="file://./models")
        cloud_provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock storage operations for cloud provider
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        
        local_metadata = local_provider.get_model_metadata("yolov8n.pt")
        cloud_metadata = cloud_provider.get_model_metadata("yolov8n.pt")
        
        # Verify metadata keys are consistent
        assert set(local_metadata.keys()) == set(cloud_metadata.keys())
        
        # Verify required keys are present
        required_keys = ['model_name', 'model_path', 'model_hash', 'model_size', 'model_type', 'model_version', 'model_labels']
        for key in required_keys:
            assert key in local_metadata
            assert key in cloud_metadata
    
    def test_model_hash_consistency(self):
        """Test that model hash calculation is consistent."""
        mock_storage = MagicMock()
        
        local_provider = LocalModelProvider(cache_path="file://./models")
        cloud_provider = CloudModelProvider(mock_storage, cache_path="s3://models-bucket")
        
        # Mock file operations for local provider
        with patch('builtins.open', mock_open(read_data="model content")):
            with patch('pathlib.Path.exists', return_value=True):
                local_hash = local_provider.get_model_hash("yolov8n.pt")
        
        # Mock storage operations for cloud provider
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = b"model content"
        cloud_hash = cloud_provider.get_model_hash("yolov8n.pt")
        
        # Verify hashes are consistent
        assert local_hash == cloud_hash
        assert local_hash == hashlib.sha256(b"model content").hexdigest()
        assert cloud_hash == hashlib.sha256(b"model content").hexdigest()


if __name__ == '__main__':
    pytest.main([__file__])
