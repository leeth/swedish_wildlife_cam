"""
Unit tests for cloud runners.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from src.wildlife_pipeline.cloud.runners import (
    LocalRunner, CloudBatchRunner, EventDrivenRunner, create_runner
)
from src.wildlife_pipeline.cloud.interfaces import ManifestEntry, Stage2Entry, StorageLocation


class TestLocalRunner:
    """Test local runner."""
    
    def test_runner_creation(self):
        """Test runner creation."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = LocalRunner(mock_storage, mock_model_provider, max_workers=4)
        assert runner.storage == mock_storage
        assert runner.model_provider == mock_model_provider
        assert runner.max_workers == 4
    
    @patch('src.wildlife_pipeline.cloud.runners.Image')
    @patch('src.wildlife_pipeline.cloud.runners.tqdm')
    def test_run_stage1(self, mock_tqdm, mock_image):
        """Test Stage-1 processing."""
        # Mock storage and model provider
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        mock_model = MagicMock()
        mock_model_provider.load_model.return_value = mock_model
        
        # Mock image files
        mock_image_files = [
            StorageLocation.from_url("file://image1.jpg"),
            StorageLocation.from_url("file://image2.jpg")
        ]
        mock_storage.list.return_value = mock_image_files
        
        # Mock image content
        mock_image_content = b"fake image content"
        mock_storage.get.return_value = mock_image_content
        
        # Mock PIL Image
        mock_pil_image = MagicMock()
        mock_pil_image.size = (640, 480)
        mock_image.open.return_value.__enter__.return_value = mock_pil_image
        
        # Mock model predictions
        mock_detection = MagicMock()
        mock_detection.confidence = 0.8
        mock_detection.bbox = [100, 100, 200, 200]
        mock_model.predict.return_value = [mock_detection]
        
        # Mock tqdm
        mock_tqdm.return_value = mock_image_files
        
        runner = LocalRunner(mock_storage, mock_model_provider, max_workers=4)
        
        # Test Stage-1
        config = {
            'stage1_model': 'test-model',
            'conf_threshold': 0.5,
            'batch_size': 16,
            'image_size': 640
        }
        
        manifest_entries = runner.run_stage1("file://input", "file://output", config)
        
        # Verify results
        assert len(manifest_entries) == 2  # One entry per image
        assert all(isinstance(entry, ManifestEntry) for entry in manifest_entries)
        
        # Verify model was loaded
        mock_model_provider.load_model.assert_called_once_with('test-model')
        
        # Verify storage operations
        assert mock_storage.get.call_count == 2  # One per image
        assert mock_storage.put.call_count == 2  # One crop per image
    
    @patch('src.wildlife_pipeline.cloud.runners.Image')
    @patch('src.wildlife_pipeline.cloud.runners.tqdm')
    def test_run_stage2(self, mock_tqdm, mock_image):
        """Test Stage-2 processing."""
        # Mock storage and model provider
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        mock_model = MagicMock()
        mock_model_provider.load_model.return_value = mock_model
        
        # Mock manifest entries
        manifest_entries = [
            ManifestEntry(
                source_path="file://image1.jpg",
                crop_path="file://crop1.jpg",
                camera_id="camera1",
                timestamp="2025-09-07T10:30:00",
                bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
                det_score=0.8,
                stage1_model="test-model",
                config_hash="abc123"
            )
        ]
        
        # Mock crop content
        mock_crop_content = b"fake crop content"
        mock_storage.get.return_value = mock_crop_content
        
        # Mock PIL Image
        mock_pil_image = MagicMock()
        mock_image.open.return_value.__enter__.return_value = mock_pil_image
        
        # Mock model predictions
        mock_prediction = MagicMock()
        mock_prediction.label = "moose"
        mock_prediction.confidence = 0.9
        mock_model.predict.return_value = mock_prediction
        
        # Mock tqdm
        mock_tqdm.return_value = manifest_entries
        
        runner = LocalRunner(mock_storage, mock_model_provider, max_workers=4)
        
        # Test Stage-2
        config = {
            'stage2_model': 'test-classifier',
            'conf_threshold': 0.5
        }
        
        stage2_entries = runner.run_stage2(manifest_entries, "file://output", config)
        
        # Verify results
        assert len(stage2_entries) == 1
        assert all(isinstance(entry, Stage2Entry) for entry in stage2_entries)
        assert stage2_entries[0].label == "moose"
        assert stage2_entries[0].confidence == 0.9
        
        # Verify model was loaded
        mock_model_provider.load_model.assert_called_once_with('test-classifier')
        
        # Verify storage operations
        mock_storage.get.assert_called_once()
        mock_storage.put.assert_called_once()  # Save predictions
    
    def test_helper_methods(self):
        """Test helper methods."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = LocalRunner(mock_storage, mock_model_provider, max_workers=4)
        
        # Test _extract_camera_id
        camera_id = runner._extract_camera_id("camera1/2025-09-07/image.jpg")
        assert camera_id == "camera1"
        
        # Test _extract_timestamp
        timestamp = runner._extract_timestamp("camera1/2025-09-07/image.jpg")
        assert timestamp is not None
        
        # Test _get_config_hash
        config = {"test": "value"}
        config_hash = runner._get_config_hash(config)
        assert isinstance(config_hash, str)
        assert len(config_hash) > 0


class TestCloudBatchRunner:
    """Test cloud batch runner."""
    
    def test_runner_creation(self):
        """Test runner creation."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = CloudBatchRunner(
            mock_storage, 
            mock_model_provider, 
            job_definition="test-job",
            vcpu=4,
            memory=8192,
            gpu_count=1,
            gpu_type="g4dn.xlarge"
        )
        
        assert runner.storage == mock_storage
        assert runner.model_provider == mock_model_provider
        assert runner.job_definition == "test-job"
        assert runner.vcpu == 4
        assert runner.memory == 8192
        assert runner.gpu_count == 1
        assert runner.gpu_type == "g4dn.xlarge"
    
    def test_submit_batch_job(self):
        """Test batch job submission."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = CloudBatchRunner(mock_storage, mock_model_provider)
        
        job_data = {
            'input_prefix': 's3://input',
            'output_prefix': 's3://output',
            'config': {'batch_size': 16, 'image_size': 640}
        }
        
        job_id = runner._submit_batch_job("stage1", job_data)
        
        # Verify job ID is generated
        assert job_id.startswith("job_stage1_")
        assert len(job_id) > 10
    
    def test_wait_for_job_completion(self):
        """Test job completion waiting."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = CloudBatchRunner(mock_storage, mock_model_provider)
        
        # Should not raise any exceptions
        runner._wait_for_job_completion("test-job-id")
    
    @patch('src.wildlife_pipeline.cloud.runners.time.sleep')
    def test_run_stage1(self, mock_sleep):
        """Test Stage-1 batch job."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        # Mock manifest content
        manifest_content = json.dumps({
            'source_path': 's3://input/image1.jpg',
            'crop_path': 's3://output/crop1.jpg',
            'camera_id': 'camera1',
            'timestamp': '2025-09-07T10:30:00',
            'bbox': {'x1': 100, 'y1': 100, 'x2': 200, 'y2': 200},
            'det_score': 0.8,
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }).encode('utf-8')
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = manifest_content
        
        runner = CloudBatchRunner(mock_storage, mock_model_provider)
        
        config = {
            'stage1_model': 'test-model',
            'conf_threshold': 0.5
        }
        
        manifest_entries = runner.run_stage1("s3://input", "s3://output", config)
        
        # Verify results
        assert len(manifest_entries) == 1
        assert isinstance(manifest_entries[0], ManifestEntry)
        assert manifest_entries[0].camera_id == "camera1"
    
    @patch('src.wildlife_pipeline.cloud.runners.time.sleep')
    def test_run_stage2(self, mock_sleep):
        """Test Stage-2 batch job."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        # Mock predictions content
        predictions_content = json.dumps({
            'crop_path': 's3://output/crop1.jpg',
            'label': 'moose',
            'confidence': 0.9,
            'auto_ok': True,
            'stage2_model': 'test-classifier',
            'stage1_model': 'test-model',
            'config_hash': 'abc123'
        }).encode('utf-8')
        
        # Mock storage operations
        mock_storage.exists.return_value = True
        mock_storage.get.return_value = predictions_content
        
        runner = CloudBatchRunner(mock_storage, mock_model_provider)
        
        # Mock manifest entries
        manifest_entries = [
            ManifestEntry(
                source_path="s3://input/image1.jpg",
                crop_path="s3://output/crop1.jpg",
                camera_id="camera1",
                timestamp="2025-09-07T10:30:00",
                bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
                det_score=0.8,
                stage1_model="test-model",
                config_hash="abc123"
            )
        ]
        
        config = {
            'stage2_model': 'test-classifier',
            'conf_threshold': 0.5
        }
        
        stage2_entries = runner.run_stage2(manifest_entries, "s3://output", config)
        
        # Verify results
        assert len(stage2_entries) == 1
        assert isinstance(stage2_entries[0], Stage2Entry)
        assert stage2_entries[0].label == "moose"
        assert stage2_entries[0].confidence == 0.9


class TestEventDrivenRunner:
    """Test event-driven runner."""
    
    def test_runner_creation(self):
        """Test runner creation."""
        mock_storage = MagicMock()
        mock_queue = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = EventDrivenRunner(mock_storage, mock_queue, mock_model_provider)
        
        assert runner.storage == mock_storage
        assert runner.queue == mock_queue
        assert runner.model_provider == mock_model_provider
    
    def test_run_stage1(self):
        """Test Stage-1 event-driven processing."""
        mock_storage = MagicMock()
        mock_queue = MagicMock()
        mock_model_provider = MagicMock()
        
        # Mock image files
        mock_image_files = [
            StorageLocation.from_url("s3://input/image1.jpg"),
            StorageLocation.from_url("s3://input/image2.jpg")
        ]
        mock_storage.list.return_value = mock_image_files
        
        runner = EventDrivenRunner(mock_storage, mock_queue, mock_model_provider)
        
        config = {
            'stage1_model': 'test-model',
            'conf_threshold': 0.5
        }
        
        manifest_entries = runner.run_stage1("s3://input", "s3://output", config)
        
        # Verify messages were sent
        assert mock_queue.send_message.call_count == 2
        
        # Verify message content
        call_args = mock_queue.send_message.call_args_list
        for i, args in enumerate(call_args):
            queue_name, message = args[0]
            assert queue_name == "stage1-queue"
            assert message['stage'] == 'stage1'
            assert message['input_path'] == mock_image_files[i].url
            assert message['output_prefix'] == "s3://output"
            assert message['config'] == config
        
        # Should return empty list for event-driven
        assert manifest_entries == []
    
    def test_run_stage2(self):
        """Test Stage-2 event-driven processing."""
        mock_storage = MagicMock()
        mock_queue = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = EventDrivenRunner(mock_storage, mock_queue, mock_model_provider)
        
        # Mock manifest entries
        manifest_entries = [
            ManifestEntry(
                source_path="s3://input/image1.jpg",
                crop_path="s3://output/crop1.jpg",
                camera_id="camera1",
                timestamp="2025-09-07T10:30:00",
                bbox={"x1": 100, "y1": 100, "x2": 200, "y2": 200},
                det_score=0.8,
                stage1_model="test-model",
                config_hash="abc123"
            )
        ]
        
        config = {
            'stage2_model': 'test-classifier',
            'conf_threshold': 0.5
        }
        
        stage2_entries = runner.run_stage2(manifest_entries, "s3://output", config)
        
        # Verify messages were sent
        assert mock_queue.send_message.call_count == 1
        
        # Verify message content
        call_args = mock_queue.send_message.call_args
        queue_name, message = call_args[0]
        assert queue_name == "stage2-queue"
        assert message['stage'] == 'stage2'
        assert message['output_prefix'] == "s3://output"
        assert message['config'] == config
        assert 'manifest_entry' in message
        
        # Should return empty list for event-driven
        assert stage2_entries == []


class TestCreateRunner:
    """Test runner factory function."""
    
    def test_create_local_runner(self):
        """Test creating local runner."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = create_runner(
            "local",
            mock_storage,
            mock_model_provider,
            max_workers=8
        )
        
        assert isinstance(runner, LocalRunner)
        assert runner.max_workers == 8
    
    def test_create_cloud_batch_runner(self):
        """Test creating cloud batch runner."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = create_runner(
            "cloud_batch",
            mock_storage,
            mock_model_provider,
            job_definition="test-job",
            vcpu=8,
            memory=16384,
            gpu_count=2,
            gpu_type="p3.2xlarge"
        )
        
        assert isinstance(runner, CloudBatchRunner)
        assert runner.job_definition == "test-job"
        assert runner.vcpu == 8
        assert runner.memory == 16384
        assert runner.gpu_count == 2
        assert runner.gpu_type == "p3.2xlarge"
    
    def test_create_event_driven_runner(self):
        """Test creating event-driven runner."""
        mock_storage = MagicMock()
        mock_queue = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = create_runner(
            "event_driven",
            mock_storage,
            mock_model_provider,
            queue_adapter=mock_queue
        )
        
        assert isinstance(runner, EventDrivenRunner)
        assert runner.queue == mock_queue
    
    def test_create_event_driven_runner_missing_queue(self):
        """Test creating event-driven runner without queue adapter."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        with pytest.raises(ValueError, match="queue_adapter required for event_driven runner"):
            create_runner(
                "event_driven",
                mock_storage,
                mock_model_provider
            )
    
    def test_create_invalid_runner(self):
        """Test creating invalid runner."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        with pytest.raises(ValueError, match="Unknown runner type"):
            create_runner(
                "invalid",
                mock_storage,
                mock_model_provider
            )


class TestRunnerIntegration:
    """Test runner integration."""
    
    def test_local_runner_integration(self):
        """Test local runner integration."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = LocalRunner(mock_storage, mock_model_provider, max_workers=4)
        
        # Test that runner has required methods
        assert hasattr(runner, 'run_stage1')
        assert hasattr(runner, 'run_stage2')
        assert callable(runner.run_stage1)
        assert callable(runner.run_stage2)
    
    def test_cloud_batch_runner_integration(self):
        """Test cloud batch runner integration."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = CloudBatchRunner(mock_storage, mock_model_provider)
        
        # Test that runner has required methods
        assert hasattr(runner, 'run_stage1')
        assert hasattr(runner, 'run_stage2')
        assert callable(runner.run_stage1)
        assert callable(runner.run_stage2)
    
    def test_event_driven_runner_integration(self):
        """Test event-driven runner integration."""
        mock_storage = MagicMock()
        mock_queue = MagicMock()
        mock_model_provider = MagicMock()
        
        runner = EventDrivenRunner(mock_storage, mock_queue, mock_model_provider)
        
        # Test that runner has required methods
        assert hasattr(runner, 'run_stage1')
        assert hasattr(runner, 'run_stage2')
        assert callable(runner.run_stage1)
        assert callable(runner.run_stage2)
    
    def test_runner_interface_consistency(self):
        """Test that all runners implement the same interface."""
        mock_storage = MagicMock()
        mock_model_provider = MagicMock()
        mock_queue = MagicMock()
        
        runners = [
            LocalRunner(mock_storage, mock_model_provider),
            CloudBatchRunner(mock_storage, mock_model_provider),
            EventDrivenRunner(mock_storage, mock_queue, mock_model_provider)
        ]
        
        for runner in runners:
            # Test that all runners have required methods
            assert hasattr(runner, 'run_stage1')
            assert hasattr(runner, 'run_stage2')
            assert callable(runner.run_stage1)
            assert callable(runner.run_stage2)


if __name__ == '__main__':
    pytest.main([__file__])
