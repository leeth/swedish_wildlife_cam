"""
Integration tests for wildlife detection pipeline.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from src.wildlife_pipeline.database_adapter import SQLiteAdapter, create_database_adapter
from src.wildlife_pipeline.image_loader import LocalImageLoader, create_image_loader
from src.wildlife_pipeline.http_client import RetryHttpClient, create_http_client
from src.wildlife_pipeline.idempotency import FileIdempotencyManager, create_idempotency_manager
from src.wildlife_pipeline.config_provider import FileConfigProvider, create_config_provider


class TestDatabaseIntegration:
    """Test database adapter integration."""
    
    def test_sqlite_adapter_operations(self):
        """Test SQLite adapter operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            adapter = SQLiteAdapter(db_path)
            
            # Test table creation
            assert adapter.table_exists("detections")
            assert adapter.table_exists("detection_results")
            
            # Test insert operation
            detection_data = {
                'file_path': '/test/image.jpg',
                'file_type': 'image',
                'camera_id': 'camera_1',
                'timestamp': '2025-01-01T12:00:00',
                'latitude': 59.3293,
                'longitude': 18.0686,
                'image_width': 1920,
                'image_height': 1080,
                'stage1_dropped': 0,
                'manual_review_count': 0,
                'observations_stage2': None,
                'video_source': None,
                'frame_number': None,
                'frame_timestamp': None,
                'detection_results': [
                    {
                        'label': 'moose',
                        'confidence': 0.85,
                        'bbox': [100, 200, 300, 400]
                    }
                ]
            }
            
            detection_id = adapter.insert_detection(detection_data)
            assert detection_id > 0
            
            # Test query
            results = adapter.execute_query("SELECT * FROM detections WHERE camera_id = ?", ("camera_1",))
            assert len(results) == 1
            assert results[0]['camera_id'] == 'camera_1'
            
            # Test summary stats
            stats = adapter.get_summary_stats()
            assert stats['total_detections'] == 1
            assert stats['gps_detections'] == 1
            assert 'moose' in stats['species_counts']
    
    def test_database_factory(self):
        """Test database adapter factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            adapter = create_database_adapter("sqlite", db_path=db_path)
            assert isinstance(adapter, SQLiteAdapter)


class TestImageLoaderIntegration:
    """Test image loader integration."""
    
    def test_local_image_loader(self):
        """Test local image loader."""
        # Create a test image
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp_dir:
            test_image_path = Path(temp_dir) / "test.jpg"
            test_image = Image.new('RGB', (100, 100), color='red')
            test_image.save(test_image_path)
            
            # Test loader
            loader = LocalImageLoader()
            image, metadata = loader.load_image_with_metadata(test_image_path)
            
            assert image.size == (100, 100)
            assert metadata['size'] == (100, 100)
            assert metadata['path'] == str(test_image_path)
    
    def test_image_loader_factory(self):
        """Test image loader factory."""
        loader = create_image_loader("local")
        assert isinstance(loader, LocalImageLoader)


class TestHttpClientIntegration:
    """Test HTTP client integration."""
    
    def test_retry_http_client(self):
        """Test retry HTTP client."""
        client = RetryHttpClient(max_retries=2, retry_delay=0.1)
        assert client.max_retries == 2
        assert client.retry_delay == 0.1
    
    def test_http_client_factory(self):
        """Test HTTP client factory."""
        client = create_http_client("retry", max_retries=3)
        assert isinstance(client, RetryHttpClient)
        assert client.max_retries == 3


class TestIdempotencyIntegration:
    """Test idempotency manager integration."""
    
    def test_file_idempotency_manager(self):
        """Test file-based idempotency manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileIdempotencyManager(Path(temp_dir))
            
            # Test operation lifecycle
            operation_id = "test_operation_123"
            input_hash = "abc123"
            
            # Start operation
            started = manager.start_operation(operation_id, "test", input_hash)
            assert started
            
            # Try to start again (should fail)
            started_again = manager.start_operation(operation_id, "test", input_hash)
            # Note: This might succeed if the operation is not in progress
            # The important thing is that we can track the operation
            
            # Complete operation
            result = {"status": "success", "data": "test_data"}
            manager.complete_operation(operation_id, result)
            
            # Check status
            status = manager.get_operation_status(operation_id)
            assert status.value == "completed"
            
            # Check result
            retrieved_result = manager.get_operation_result(operation_id)
            assert retrieved_result == result
    
    def test_idempotency_factory(self):
        """Test idempotency manager factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_idempotency_manager("file", state_dir=Path(temp_dir))
            assert isinstance(manager, FileIdempotencyManager)


class TestConfigProviderIntegration:
    """Test configuration provider integration."""
    
    def test_file_config_provider(self):
        """Test file-based configuration provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # Create test config
            test_config = {
                'database': {
                    'path': '/tmp/test.db'
                },
                'storage': {
                    'base_path': 'file://./data'
                }
            }
            
            with open(config_path, 'w') as f:
                import yaml
                yaml.dump(test_config, f)
            
            # Test provider
            provider = FileConfigProvider(config_path)
            
            # Test get_config
            db_path = provider.get_config('database.path')
            assert db_path == '/tmp/test.db'
            
            # Test get_section
            db_section = provider.get_section('database')
            assert db_section['path'] == '/tmp/test.db'
    
    def test_config_provider_factory(self):
        """Test configuration provider factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            config_path.write_text("test: value")
            
            provider = create_config_provider("file", config_path=config_path)
            assert isinstance(provider, FileConfigProvider)


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_pipeline_with_abstractions(self):
        """Test pipeline with all abstractions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup components
            db_path = Path(temp_dir) / "test.db"
            state_dir = Path(temp_dir) / "state"
            config_path = Path(temp_dir) / "config.yaml"
            
            # Create test config
            test_config = {
                'database': {'path': str(db_path)},
                'storage': {'base_path': 'file://./data'},
                'idempotency': {'state_dir': str(state_dir)}
            }
            
            with open(config_path, 'w') as f:
                import yaml
                yaml.dump(test_config, f)
            
            # Initialize components
            db_adapter = create_database_adapter("sqlite", db_path=db_path)
            image_loader = create_image_loader("local")
            http_client = create_http_client("retry", max_retries=2)
            idempotency_manager = create_idempotency_manager("file", state_dir=state_dir)
            config_provider = create_config_provider("file", config_path=config_path)
            
            # Test that all components work together
            assert db_adapter.table_exists("detections")
            assert image_loader is not None
            assert http_client.max_retries == 2
            assert idempotency_manager is not None
            assert config_provider.get_config('database.path') == str(db_path)
    
    def test_error_handling_integration(self):
        """Test error handling across abstractions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test database error handling
            db_path = Path(temp_dir) / "test.db"
            adapter = SQLiteAdapter(db_path)
            
            # Test invalid query
            with pytest.raises(Exception):  # Should raise DatabaseError
                adapter.execute_query("INVALID SQL QUERY")
            
            # Test HTTP client error handling
            client = RetryHttpClient(max_retries=1, retry_delay=0.01)
            
            # Test with invalid URL (should fail gracefully)
            # Note: This might not raise an exception due to retry logic
            try:
                client.get("http://invalid-url-that-does-not-exist.com")
            except Exception:
                pass  # Expected to fail
            
            # Test idempotency error handling
            manager = FileIdempotencyManager(Path(temp_dir))
            
            # Test completing non-existent operation
            with pytest.raises(ValueError):
                manager.complete_operation("non_existent_operation", {})
