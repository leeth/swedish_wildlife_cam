"""
Unit tests for cloud configuration to ensure proper setup.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.wildlife_pipeline.cloud.config import CloudConfig
from src.wildlife_pipeline.cloud.interfaces import StorageLocation


class TestCloudConfig:
    """Test cloud configuration loading and validation."""
    
    def test_local_config_loading(self):
        """Test that local configuration loads correctly."""
        config = CloudConfig(profile="local")
        
        # Test basic properties
        assert config.profile == "local"
        assert config.storage_adapter is not None
        assert config.queue_adapter is not None
        assert config.model_provider is not None
        assert config.runner is not None
        
        # Test adapter types
        assert config.storage_adapter.__class__.__name__ == "LocalFSAdapter"
        assert config.queue_adapter.__class__.__name__ == "NoQueueAdapter"
        assert config.model_provider.__class__.__name__ == "LocalModelProvider"
        assert config.runner.__class__.__name__ == "LocalRunner"
    
    def test_cloud_config_loading(self):
        """Test that cloud configuration loads correctly."""
        config = CloudConfig(profile="cloud")
        
        # Test basic properties
        assert config.profile == "cloud"
        assert config.storage_adapter is not None
        assert config.queue_adapter is not None
        assert config.model_provider is not None
        assert config.runner is not None
        
        # Test adapter types
        assert config.storage_adapter.__class__.__name__ == "S3Adapter"
        assert config.queue_adapter.__class__.__name__ == "SQSAdapter"
        assert config.model_provider.__class__.__name__ == "CloudModelProvider"
        assert config.runner.__class__.__name__ == "CloudBatchRunner"
    
    def test_gpu_configuration(self):
        """Test GPU configuration is properly set."""
        config = CloudConfig(profile="cloud")
        
        # Test GPU settings
        assert hasattr(config.runner, 'gpu_count')
        assert hasattr(config.runner, 'gpu_type')
        assert config.runner.gpu_count == 1
        assert config.runner.gpu_type == "g4dn.xlarge"
    
    def test_pipeline_configuration(self):
        """Test pipeline configuration is properly loaded."""
        config = CloudConfig(profile="cloud")
        
        # Test Stage-1 config
        stage1_config = config.get_stage1_config()
        assert stage1_config['model'] == 'megadetector'
        assert stage1_config['conf_threshold'] == 0.3
        assert stage1_config['batch_size'] == 16
        assert stage1_config['image_size'] == 640
        assert stage1_config['max_images_per_job'] == 1000
        
        # Test Stage-2 config
        stage2_config = config.get_stage2_config()
        assert stage2_config['enabled'] == True
        assert stage2_config['model'] == 'yolo_cls'
        assert stage2_config['conf_threshold'] == 0.5
        assert stage2_config['batch_size'] == 32
        assert stage2_config['image_size'] == 224
    
    def test_manifest_paths(self):
        """Test manifest paths are correctly configured."""
        config = CloudConfig(profile="cloud")
        
        manifest_paths = config.get_manifest_paths()
        assert 'stage1' in manifest_paths
        assert 'stage2' in manifest_paths
        assert manifest_paths['stage1'].endswith('stage1/manifest.jsonl')
        assert manifest_paths['stage2'].endswith('stage2/predictions.jsonl')
    
    def test_stage2_enabled(self):
        """Test that Stage-2 is enabled by default."""
        config = CloudConfig(profile="cloud")
        assert config.is_stage2_enabled() == True
    
    def test_storage_base_path(self):
        """Test storage base path configuration."""
        config = CloudConfig(profile="cloud")
        base_path = config.get_storage_base_path()
        assert base_path.startswith('s3://')
    
    def test_custom_config_file(self):
        """Test loading from custom configuration file."""
        # Create temporary config file
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
            yaml.dump(custom_config, f)
            config_path = f.name
        
        try:
            config = CloudConfig(profile="local", config_path=config_path)
            
            # Test custom settings
            assert config.runner.max_workers == 8
            stage1_config = config.get_stage1_config()
            assert stage1_config['model'] == 'custom-model'
            assert stage1_config['conf_threshold'] == 0.5
            assert config.is_stage2_enabled() == False
            
        finally:
            Path(config_path).unlink()
    
    def test_environment_variable_overrides(self):
        """Test that environment variables override configuration."""
        with patch.dict('os.environ', {
            'STORAGE_ADAPTER': 's3',
            'STORAGE_BASE_PATH': 's3://custom-bucket',
            'QUEUE_ADAPTER': 'sqs',
            'MODEL_PROVIDER': 'cloud',
            'RUNNER_TYPE': 'cloud_batch'
        }):
            config = CloudConfig(profile="local")
            
            # Should be overridden by environment variables
            assert config.storage_adapter.__class__.__name__ == "S3Adapter"
            assert config.queue_adapter.__class__.__name__ == "SQSAdapter"
            assert config.model_provider.__class__.__name__ == "CloudModelProvider"
            assert config.runner.__class__.__name__ == "CloudBatchRunner"
    
    def test_missing_config_file(self):
        """Test behavior when configuration file is missing."""
        config = CloudConfig(profile="nonexistent")
        
        # Should fall back to default configuration
        assert config.profile == "nonexistent"
        assert config.storage_adapter is not None
        assert config.queue_adapter is not None
        assert config.model_provider is not None
        assert config.runner is not None
    
    def test_invalid_config_file(self):
        """Test behavior with invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            config = CloudConfig(profile="local", config_path=config_path)
            
            # Should fall back to default configuration
            assert config.storage_adapter is not None
            assert config.queue_adapter is not None
            assert config.model_provider is not None
            assert config.runner is not None
            
        finally:
            Path(config_path).unlink()


class TestCloudConfigValidation:
    """Test configuration validation and error handling."""
    
    def test_storage_adapter_creation(self):
        """Test storage adapter creation with different types."""
        config = CloudConfig(profile="local")
        
        # Test local storage
        assert config.storage_adapter.__class__.__name__ == "LocalFSAdapter"
        
        # Test cloud storage
        cloud_config = CloudConfig(profile="cloud")
        assert cloud_config.storage_adapter.__class__.__name__ == "S3Adapter"
    
    def test_queue_adapter_creation(self):
        """Test queue adapter creation with different types."""
        config = CloudConfig(profile="local")
        
        # Test no queue
        assert config.queue_adapter.__class__.__name__ == "NoQueueAdapter"
        
        # Test cloud queue
        cloud_config = CloudConfig(profile="cloud")
        assert cloud_config.queue_adapter.__class__.__name__ == "SQSAdapter"
    
    def test_model_provider_creation(self):
        """Test model provider creation with different types."""
        config = CloudConfig(profile="local")
        
        # Test local model provider
        assert config.model_provider.__class__.__name__ == "LocalModelProvider"
        
        # Test cloud model provider
        cloud_config = CloudConfig(profile="cloud")
        assert cloud_config.model_provider.__class__.__name__ == "CloudModelProvider"
    
    def test_runner_creation(self):
        """Test runner creation with different types."""
        config = CloudConfig(profile="local")
        
        # Test local runner
        assert config.runner.__class__.__name__ == "LocalRunner"
        assert hasattr(config.runner, 'max_workers')
        assert config.runner.max_workers == 4
        
        # Test cloud runner
        cloud_config = CloudConfig(profile="cloud")
        assert cloud_config.runner.__class__.__name__ == "CloudBatchRunner"
        assert hasattr(cloud_config.runner, 'gpu_count')
        assert hasattr(cloud_config.runner, 'gpu_type')
        assert cloud_config.runner.gpu_count == 1
        assert cloud_config.runner.gpu_type == "g4dn.xlarge"
    
    def test_gpu_configuration_validation(self):
        """Test GPU configuration validation."""
        cloud_config = CloudConfig(profile="cloud")
        
        # Test GPU settings are properly configured
        assert cloud_config.runner.gpu_count == 1
        assert cloud_config.runner.gpu_type == "g4dn.xlarge"
        assert cloud_config.runner.vcpu == 4
        assert cloud_config.runner.memory == 8192
        
        # Test that runner has required attributes
        assert hasattr(cloud_config.runner, 'job_definition')
        assert hasattr(cloud_config.runner, 'storage')
        assert hasattr(cloud_config.runner, 'model_provider')
    
    def test_pipeline_configuration_validation(self):
        """Test pipeline configuration validation."""
        config = CloudConfig(profile="cloud")
        
        # Test Stage-1 configuration
        stage1_config = config.get_stage1_config()
        required_keys = ['model', 'conf_threshold', 'batch_size', 'image_size', 'max_images_per_job']
        for key in required_keys:
            assert key in stage1_config, f"Missing key: {key}"
        
        # Test Stage-2 configuration
        stage2_config = config.get_stage2_config()
        required_keys = ['enabled', 'model', 'conf_threshold', 'batch_size', 'image_size']
        for key in required_keys:
            assert key in stage2_config, f"Missing key: {key}"
        
        # Test output configuration
        output_config = config.get_output_config()
        assert 'format' in output_config
        assert 'partition_by' in output_config
    
    def test_manifest_configuration_validation(self):
        """Test manifest configuration validation."""
        config = CloudConfig(profile="cloud")
        
        manifest_paths = config.get_manifest_paths()
        assert 'stage1' in manifest_paths
        assert 'stage2' in manifest_paths
        
        # Test paths are properly formatted
        assert manifest_paths['stage1'].endswith('stage1/manifest.jsonl')
        assert manifest_paths['stage2'].endswith('stage2/predictions.jsonl')
        
        # Test paths use correct storage protocol
        assert manifest_paths['stage1'].startswith('s3://')
        assert manifest_paths['stage2'].startswith('s3://')


class TestCloudConfigIntegration:
    """Test integration between configuration components."""
    
    def test_storage_integration(self):
        """Test storage adapter integration."""
        config = CloudConfig(profile="local")
        
        # Test storage operations
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello, World!")
            
            location = StorageLocation.from_url(f"file://{test_file}")
            
            # Test get operation
            content = config.storage_adapter.get(location)
            assert content.decode('utf-8') == "Hello, World!"
            
            # Test exists operation
            assert config.storage_adapter.exists(location)
    
    def test_model_provider_integration(self):
        """Test model provider integration."""
        config = CloudConfig(profile="local")
        
        # Test model provider has required methods
        assert hasattr(config.model_provider, 'load_model')
        assert hasattr(config.model_provider, 'get_model_metadata')
        assert hasattr(config.model_provider, 'get_model_hash')
    
    def test_runner_integration(self):
        """Test runner integration."""
        config = CloudConfig(profile="local")
        
        # Test runner has required methods
        assert hasattr(config.runner, 'run_stage1')
        assert hasattr(config.runner, 'run_stage2')
    
    def test_queue_integration(self):
        """Test queue adapter integration."""
        config = CloudConfig(profile="local")
        
        # Test queue adapter has required methods
        assert hasattr(config.queue_adapter, 'send_message')
        assert hasattr(config.queue_adapter, 'receive_messages')
        assert hasattr(config.queue_adapter, 'delete_message')
    
    def test_configuration_consistency(self):
        """Test that configuration is consistent across components."""
        config = CloudConfig(profile="cloud")
        
        # Test that all components are properly initialized
        assert config.storage_adapter is not None
        assert config.queue_adapter is not None
        assert config.model_provider is not None
        assert config.runner is not None
        
        # Test that components can work together
        assert hasattr(config.runner, 'storage')
        assert hasattr(config.runner, 'model_provider')
        
        # Test that model provider has storage adapter
        if hasattr(config.model_provider, 'storage'):
            assert config.model_provider.storage is not None


class TestCloudConfigErrorHandling:
    """Test error handling in configuration loading."""
    
    def test_invalid_profile(self):
        """Test handling of invalid profile."""
        config = CloudConfig(profile="invalid")
        
        # Should fall back to default configuration
        assert config.storage_adapter is not None
        assert config.queue_adapter is not None
        assert config.model_provider is not None
        assert config.runner is not None
    
    def test_missing_required_keys(self):
        """Test handling of missing required configuration keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            incomplete_config = {
                'storage': {
                    'adapter': 'local'
                    # Missing base_path
                }
                # Missing other required sections
            }
            yaml.dump(incomplete_config, f)
            config_path = f.name
        
        try:
            config = CloudConfig(profile="local", config_path=config_path)
            
            # Should fall back to default configuration
            assert config.storage_adapter is not None
            assert config.queue_adapter is not None
            assert config.model_provider is not None
            assert config.runner is not None
            
        finally:
            Path(config_path).unlink()
    
    def test_invalid_adapter_type(self):
        """Test handling of invalid adapter types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            invalid_config = {
                'storage': {
                    'adapter': 'invalid_adapter',
                    'base_path': 'file://./data'
                },
                'queue': {
                    'adapter': 'invalid_queue'
                },
                'model': {
                    'provider': 'invalid_provider',
                    'cache_path': 'file://./models'
                },
                'runner': {
                    'type': 'invalid_runner'
                }
            }
            yaml.dump(invalid_config, f)
            config_path = f.name
        
        try:
            # Should raise ValueError for invalid adapter types
            with pytest.raises(ValueError):
                CloudConfig(profile="local", config_path=config_path)
                
        finally:
            Path(config_path).unlink()


if __name__ == '__main__':
    pytest.main([__file__])
