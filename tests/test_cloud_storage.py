"""
Unit tests for cloud storage adapters.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.wildlife_pipeline.cloud.storage import (
    LocalFSAdapter, S3Adapter, GCSAdapter, create_storage_adapter
)
from src.wildlife_pipeline.cloud.interfaces import StorageLocation


class TestLocalFSAdapter:
    """Test local filesystem storage adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        adapter = LocalFSAdapter(base_path="file://./test-data")
        assert adapter.base_path.name == "test-data"
    
    def test_put_and_get(self):
        """Test put and get operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Test put operation
            location = StorageLocation.from_url("file://test.txt")
            content = b"Hello, World!"
            adapter.put(location, content)
            
            # Test get operation
            retrieved_content = adapter.get(location)
            assert retrieved_content == content
    
    def test_exists(self):
        """Test exists operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Test non-existent file
            location = StorageLocation.from_url("file://nonexistent.txt")
            assert not adapter.exists(location)
            
            # Test existing file
            location = StorageLocation.from_url("file://test.txt")
            content = b"Hello, World!"
            adapter.put(location, content)
            assert adapter.exists(location)
    
    def test_list(self):
        """Test list operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Create test files
            test_files = ["test1.txt", "test2.txt", "test3.jpg"]
            for filename in test_files:
                location = StorageLocation.from_url(f"file://{filename}")
                adapter.put(location, b"test content")
            
            # Test list operation
            files = adapter.list(StorageLocation.from_url("file://"))
            assert len(files) == len(test_files)
            
            # Test pattern filtering
            txt_files = adapter.list(StorageLocation.from_url("file://"), "*.txt")
            assert len(txt_files) == 2
    
    def test_delete(self):
        """Test delete operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Create test file
            location = StorageLocation.from_url("file://test.txt")
            content = b"Hello, World!"
            adapter.put(location, content)
            assert adapter.exists(location)
            
            # Delete file
            adapter.delete(location)
            assert not adapter.exists(location)
    
    def test_directory_creation(self):
        """Test that directories are created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Test nested directory creation
            location = StorageLocation.from_url("file://nested/deep/test.txt")
            content = b"Hello, World!"
            adapter.put(location, content)
            
            # Verify file exists
            assert adapter.exists(location)
            retrieved_content = adapter.get(location)
            assert retrieved_content == content


class TestS3Adapter:
    """Test S3 storage adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        assert adapter.base_path == "s3://test-bucket"
        assert adapter.region == "eu-north-1"
    
    @patch('src.wildlife_pipeline.cloud.storage.smart_open')
    def test_put_operation(self, mock_smart_open):
        """Test put operation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        
        location = StorageLocation.from_url("s3://test-bucket/test.txt")
        content = b"Hello, World!"
        
        # Mock smart_open
        mock_file = MagicMock()
        mock_smart_open.open.return_value.__enter__.return_value = mock_file
        
        adapter.put(location, content)
        
        # Verify smart_open was called correctly
        mock_smart_open.open.assert_called_once()
        mock_file.write.assert_called_once_with(content)
    
    @patch('src.wildlife_pipeline.cloud.storage.smart_open')
    def test_get_operation(self, mock_smart_open):
        """Test get operation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        
        location = StorageLocation.from_url("s3://test-bucket/test.txt")
        expected_content = b"Hello, World!"
        
        # Mock smart_open
        mock_file = MagicMock()
        mock_file.read.return_value = expected_content
        mock_smart_open.open.return_value.__enter__.return_value = mock_file
        
        content = adapter.get(location)
        
        # Verify content
        assert content == expected_content
        mock_smart_open.open.assert_called_once()
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_exists_operation(self, mock_fsspec):
        """Test exists operation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        
        location = StorageLocation.from_url("s3://test-bucket/test.txt")
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fs.exists.return_value = True
        mock_fsspec.filesystem.return_value = mock_fs
        
        exists = adapter.exists(location)
        
        # Verify result
        assert exists == True
        mock_fs.exists.assert_called_once_with(location.path)
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_list_operation(self, mock_fsspec):
        """Test list operation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        
        location = StorageLocation.from_url("s3://test-bucket/")
        expected_files = ["s3://test-bucket/file1.txt", "s3://test-bucket/file2.jpg"]
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fs.glob.return_value = expected_files
        mock_fsspec.filesystem.return_value = mock_fs
        
        files = adapter.list(location)
        
        # Verify result
        assert len(files) == len(expected_files)
        for file in files:
            assert file.protocol == "s3"
            assert file.url.startswith("s3://")
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_delete_operation(self, mock_fsspec):
        """Test delete operation."""
        adapter = S3Adapter(base_path="s3://test-bucket", region="eu-north-1")
        
        location = StorageLocation.from_url("s3://test-bucket/test.txt")
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fsspec.filesystem.return_value = mock_fs
        
        adapter.delete(location)
        
        # Verify delete was called
        mock_fs.rm.assert_called_once_with(location.path)


class TestGCSAdapter:
    """Test Google Cloud Storage adapter."""
    
    def test_adapter_creation(self):
        """Test adapter creation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        assert adapter.base_path == "gs://test-bucket"
    
    @patch('src.wildlife_pipeline.cloud.storage.smart_open')
    def test_put_operation(self, mock_smart_open):
        """Test put operation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        
        location = StorageLocation.from_url("gs://test-bucket/test.txt")
        content = b"Hello, World!"
        
        # Mock smart_open
        mock_file = MagicMock()
        mock_smart_open.open.return_value.__enter__.return_value = mock_file
        
        adapter.put(location, content)
        
        # Verify smart_open was called correctly
        mock_smart_open.open.assert_called_once()
        mock_file.write.assert_called_once_with(content)
    
    @patch('src.wildlife_pipeline.cloud.storage.smart_open')
    def test_get_operation(self, mock_smart_open):
        """Test get operation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        
        location = StorageLocation.from_url("gs://test-bucket/test.txt")
        expected_content = b"Hello, World!"
        
        # Mock smart_open
        mock_file = MagicMock()
        mock_file.read.return_value = expected_content
        mock_smart_open.open.return_value.__enter__.return_value = mock_file
        
        content = adapter.get(location)
        
        # Verify content
        assert content == expected_content
        mock_smart_open.open.assert_called_once()
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_exists_operation(self, mock_fsspec):
        """Test exists operation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        
        location = StorageLocation.from_url("gs://test-bucket/test.txt")
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fs.exists.return_value = True
        mock_fsspec.filesystem.return_value = mock_fs
        
        exists = adapter.exists(location)
        
        # Verify result
        assert exists == True
        mock_fs.exists.assert_called_once_with(location.path)
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_list_operation(self, mock_fsspec):
        """Test list operation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        
        location = StorageLocation.from_url("gs://test-bucket/")
        expected_files = ["gs://test-bucket/file1.txt", "gs://test-bucket/file2.jpg"]
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fs.glob.return_value = expected_files
        mock_fsspec.filesystem.return_value = mock_fs
        
        files = adapter.list(location)
        
        # Verify result
        assert len(files) == len(expected_files)
        for file in files:
            assert file.protocol == "gs"
            assert file.url.startswith("gs://")
    
    @patch('src.wildlife_pipeline.cloud.storage.fsspec')
    def test_delete_operation(self, mock_fsspec):
        """Test delete operation."""
        adapter = GCSAdapter(base_path="gs://test-bucket")
        
        location = StorageLocation.from_url("gs://test-bucket/test.txt")
        
        # Mock filesystem
        mock_fs = MagicMock()
        mock_fsspec.filesystem.return_value = mock_fs
        
        adapter.delete(location)
        
        # Verify delete was called
        mock_fs.rm.assert_called_once_with(location.path)


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


class TestCreateStorageAdapter:
    """Test storage adapter factory function."""
    
    def test_create_local_adapter(self):
        """Test creating local adapter."""
        adapter = create_storage_adapter("local", base_path="file://./test")
        assert isinstance(adapter, LocalFSAdapter)
        assert adapter.base_path.name == "test"
    
    def test_create_s3_adapter(self):
        """Test creating S3 adapter."""
        adapter = create_storage_adapter("s3", base_path="s3://test-bucket", region="eu-north-1")
        assert isinstance(adapter, S3Adapter)
        assert adapter.base_path == "s3://test-bucket"
        assert adapter.region == "eu-north-1"
    
    def test_create_gcs_adapter(self):
        """Test creating GCS adapter."""
        adapter = create_storage_adapter("gcs", base_path="gs://test-bucket")
        assert isinstance(adapter, GCSAdapter)
        assert adapter.base_path == "gs://test-bucket"
    
    def test_create_invalid_adapter(self):
        """Test creating invalid adapter."""
        with pytest.raises(ValueError, match="Unknown storage adapter type"):
            create_storage_adapter("invalid", base_path="file://./test")


class TestStorageAdapterIntegration:
    """Test storage adapter integration."""
    
    def test_local_adapter_integration(self):
        """Test local adapter integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
            
            # Test complete workflow
            location = StorageLocation.from_url("file://test.txt")
            content = b"Hello, World!"
            
            # Put content
            adapter.put(location, content)
            
            # Verify exists
            assert adapter.exists(location)
            
            # Get content
            retrieved_content = adapter.get(location)
            assert retrieved_content == content
            
            # List files
            files = adapter.list(StorageLocation.from_url("file://"))
            assert len(files) == 1
            assert files[0].url == location.url
            
            # Delete content
            adapter.delete(location)
            assert not adapter.exists(location)
    
    def test_storage_location_consistency(self):
        """Test storage location consistency."""
        # Test that StorageLocation maintains consistency
        url = "s3://bucket/path/to/file.txt"
        location = StorageLocation.from_url(url)
        
        assert location.url == url
        assert location.protocol == "s3"
        assert location.path == "bucket/path/to/file.txt"
        
        # Test round-trip
        location2 = StorageLocation.from_url(location.url)
        assert location2.url == location.url
        assert location2.protocol == location.protocol
        assert location2.path == location.path


if __name__ == '__main__':
    pytest.main([__file__])
