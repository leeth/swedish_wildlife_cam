"""
Unit tests for cloud CLI functionality.
"""

import pytest
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from src.wildlife_pipeline.cloud.cli import main


class TestCloudCLI:
    """Test cloud CLI functionality."""
    
    def test_cli_help(self):
        """Test CLI help command."""
        with patch('sys.argv', ['cloud-cli', '--help']):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_stage1_help(self):
        """Test CLI stage1 help command."""
        with patch('sys.argv', ['cloud-cli', 'stage1', '--help']):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_stage2_help(self):
        """Test CLI stage2 help command."""
        with patch('sys.argv', ['cloud-cli', 'stage2', '--help']):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_materialize_help(self):
        """Test CLI materialize help command."""
        with patch('sys.argv', ['cloud-cli', 'materialize', '--help']):
            with pytest.raises(SystemExit):
                main()
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_stage1_local(self, mock_config_class):
        """Test CLI stage1 with local profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock runner
        mock_runner = MagicMock()
        mock_runner.run_stage1.return_value = []
        mock_config.runner = mock_runner
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.list.return_value = []
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'stage1', 
            '--profile', 'local',
            '--input', 'file://./test-input',
            '--output', 'file://./test-output'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="local")
        
        # Verify runner was called
        mock_runner.run_stage1.assert_called_once()
        call_args = mock_runner.run_stage1.call_args
        assert call_args[0][0] == "file://./test-input"
        assert call_args[0][1] == "file://./test-output"
        assert isinstance(call_args[0][2], dict)
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_stage1_cloud(self, mock_config_class):
        """Test CLI stage1 with cloud profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock runner
        mock_runner = MagicMock()
        mock_runner.run_stage1.return_value = []
        mock_config.runner = mock_runner
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.list.return_value = []
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'stage1', 
            '--profile', 'cloud',
            '--input', 's3://test-bucket/input',
            '--output', 's3://test-bucket/output'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="cloud")
        
        # Verify runner was called
        mock_runner.run_stage1.assert_called_once()
        call_args = mock_runner.run_stage1.call_args
        assert call_args[0][0] == "s3://test-bucket/input"
        assert call_args[0][1] == "s3://test-bucket/output"
        assert isinstance(call_args[0][2], dict)
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_stage2_local(self, mock_config_class):
        """Test CLI stage2 with local profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock runner
        mock_runner = MagicMock()
        mock_runner.run_stage2.return_value = []
        mock_config.runner = mock_runner
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get.return_value = b'{"source_path": "file://test.jpg", "crop_path": "file://crop.jpg", "camera_id": "camera1", "timestamp": "2025-09-07T10:30:00", "bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "det_score": 0.8, "stage1_model": "test-model", "config_hash": "abc123"}'
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'stage2', 
            '--profile', 'local',
            '--manifest', 'file://./test-manifest.jsonl',
            '--output', 'file://./test-output'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="local")
        
        # Verify runner was called
        mock_runner.run_stage2.assert_called_once()
        call_args = mock_runner.run_stage2.call_args
        assert len(call_args[0][0]) == 1  # One manifest entry
        assert call_args[0][1] == "file://./test-output"
        assert isinstance(call_args[0][2], dict)
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_stage2_cloud(self, mock_config_class):
        """Test CLI stage2 with cloud profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock runner
        mock_runner = MagicMock()
        mock_runner.run_stage2.return_value = []
        mock_config.runner = mock_runner
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get.return_value = b'{"source_path": "s3://test-bucket/image.jpg", "crop_path": "s3://test-bucket/crop.jpg", "camera_id": "camera1", "timestamp": "2025-09-07T10:30:00", "bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "det_score": 0.8, "stage1_model": "test-model", "config_hash": "abc123"}'
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'stage2', 
            '--profile', 'cloud',
            '--manifest', 's3://test-bucket/manifest.jsonl',
            '--output', 's3://test-bucket/output'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="cloud")
        
        # Verify runner was called
        mock_runner.run_stage2.assert_called_once()
        call_args = mock_runner.run_stage2.call_args
        assert len(call_args[0][0]) == 1  # One manifest entry
        assert call_args[0][1] == "s3://test-bucket/output"
        assert isinstance(call_args[0][2], dict)
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_materialize_local(self, mock_config_class):
        """Test CLI materialize with local profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get.return_value = b'{"source_path": "file://test.jpg", "crop_path": "file://crop.jpg", "camera_id": "camera1", "timestamp": "2025-09-07T10:30:00", "bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "det_score": 0.8, "stage1_model": "test-model", "config_hash": "abc123"}'
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'materialize', 
            '--profile', 'local',
            '--manifest', 'file://./test-manifest.jsonl',
            '--output', 'file://./test-output.parquet'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="local")
        
        # Verify storage operations
        mock_storage.get.assert_called_once()
        mock_storage.put.assert_called_once()  # Save materialized data
    
    @patch('src.wildlife_pipeline.cloud.cli.CloudConfig')
    def test_cli_materialize_cloud(self, mock_config_class):
        """Test CLI materialize with cloud profile."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock storage
        mock_storage = MagicMock()
        mock_storage.get.return_value = b'{"source_path": "s3://test-bucket/image.jpg", "crop_path": "s3://test-bucket/crop.jpg", "camera_id": "camera1", "timestamp": "2025-09-07T10:30:00", "bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "det_score": 0.8, "stage1_model": "test-model", "config_hash": "abc123"}'
        mock_config.storage_adapter = mock_storage
        
        with patch('sys.argv', [
            'cloud-cli', 'materialize', 
            '--profile', 'cloud',
            '--manifest', 's3://test-bucket/manifest.jsonl',
            '--output', 's3://test-bucket/output.parquet'
        ]):
            main()
        
        # Verify configuration was loaded
        mock_config_class.assert_called_once_with(profile="cloud")
        
        # Verify storage operations
        mock_storage.get.assert_called_once()
        mock_storage.put.assert_called_once()  # Save materialized data
    
    def test_cli_invalid_command(self):
        """Test CLI with invalid command."""
        with patch('sys.argv', ['cloud-cli', 'invalid-command']):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_missing_required_args(self):
        """Test CLI with missing required arguments."""
        with patch('sys.argv', ['cloud-cli', 'stage1']):
            with pytest.raises(SystemExit):
                main()
    
    def test_cli_invalid_profile(self):
        """Test CLI with invalid profile."""
        with patch('sys.argv', [
            'cloud-cli', 'stage1', 
            '--profile', 'invalid',
            '--input', 'file://./test-input',
            '--output', 'file://./test-output'
        ]):
            # Should not raise exception, just use default configuration
            main()


class TestCloudCLIIntegration:
    """Test cloud CLI integration."""
    
    def test_cli_with_custom_config(self):
        """Test CLI with custom configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            custom_config = {
                'storage': {
                    'adapter': 'local',
                    'base_path': 'file://./custom-data'
                },
                'queue': {
                    'adapter': 'none'
                },
                'model': {
                    'provider': 'local',
                    'cache_path': 'file://./custom-models'
                },
                'runner': {
                    'type': 'local',
                    'max_workers': 8
                },
                'pipeline': {
                    'stage1': {
                        'model': 'custom-model',
                        'conf_threshold': 0.5
                    },
                    'stage2': {
                        'enabled': False
                    }
                }
            }
            import yaml
            yaml.dump(custom_config, f)
            config_path = f.name
        
        try:
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--config', config_path,
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception
                main()
                
        finally:
            Path(config_path).unlink()
    
    def test_cli_environment_variable_overrides(self):
        """Test CLI with environment variable overrides."""
        with patch.dict('os.environ', {
            'STORAGE_ADAPTER': 's3',
            'STORAGE_BASE_PATH': 's3://custom-bucket',
            'QUEUE_ADAPTER': 'sqs',
            'MODEL_PROVIDER': 'cloud',
            'RUNNER_TYPE': 'cloud_batch'
        }):
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception
                main()
    
    def test_cli_stage1_with_stage2_disabled(self):
        """Test CLI stage1 when stage2 is disabled."""
        with patch('sys.argv', [
            'cloud-cli', 'stage1', 
            '--profile', 'local',
            '--input', 'file://./test-input',
            '--output', 'file://./test-output'
        ]):
            # Should not raise exception
            main()
    
    def test_cli_stage2_with_stage2_disabled(self):
        """Test CLI stage2 when stage2 is disabled."""
        with patch('sys.argv', [
            'cloud-cli', 'stage2', 
            '--profile', 'local',
            '--manifest', 'file://./test-manifest.jsonl',
            '--output', 'file://./test-output'
        ]):
            # Should not raise exception
            main()
    
    def test_cli_materialize_with_stage2_disabled(self):
        """Test CLI materialize when stage2 is disabled."""
        with patch('sys.argv', [
            'cloud-cli', 'materialize', 
            '--profile', 'local',
            '--manifest', 'file://./test-manifest.jsonl',
            '--output', 'file://./test-output.parquet'
        ]):
            # Should not raise exception
            main()


class TestCloudCLIErrorHandling:
    """Test cloud CLI error handling."""
    
    def test_cli_configuration_error(self):
        """Test CLI with configuration error."""
        with patch('src.wildlife_pipeline.cloud.cli.CloudConfig') as mock_config_class:
            mock_config_class.side_effect = Exception("Configuration error")
            
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception, just print error
                main()
    
    def test_cli_runner_error(self):
        """Test CLI with runner error."""
        with patch('src.wildlife_pipeline.cloud.cli.CloudConfig') as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            # Mock runner that raises exception
            mock_runner = MagicMock()
            mock_runner.run_stage1.side_effect = Exception("Runner error")
            mock_config.runner = mock_runner
            
            # Mock storage
            mock_storage = MagicMock()
            mock_storage.list.return_value = []
            mock_config.storage_adapter = mock_storage
            
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception, just print error
                main()
    
    def test_cli_storage_error(self):
        """Test CLI with storage error."""
        with patch('src.wildlife_pipeline.cloud.cli.CloudConfig') as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            # Mock storage that raises exception
            mock_storage = MagicMock()
            mock_storage.list.side_effect = Exception("Storage error")
            mock_config.storage_adapter = mock_storage
            
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception, just print error
                main()
    
    def test_cli_model_provider_error(self):
        """Test CLI with model provider error."""
        with patch('src.wildlife_pipeline.cloud.cli.CloudConfig') as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            # Mock model provider that raises exception
            mock_model_provider = MagicMock()
            mock_model_provider.load_model.side_effect = Exception("Model provider error")
            mock_config.model_provider = mock_model_provider
            
            # Mock runner
            mock_runner = MagicMock()
            mock_runner.run_stage1.side_effect = Exception("Model provider error")
            mock_config.runner = mock_runner
            
            # Mock storage
            mock_storage = MagicMock()
            mock_storage.list.return_value = []
            mock_config.storage_adapter = mock_storage
            
            with patch('sys.argv', [
                'cloud-cli', 'stage1', 
                '--profile', 'local',
                '--input', 'file://./test-input',
                '--output', 'file://./test-output'
            ]):
                # Should not raise exception, just print error
                main()


if __name__ == '__main__':
    pytest.main([__file__])
