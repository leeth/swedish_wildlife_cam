"""
Test odin stage3 downloader module.

Comprehensive tests for the stage3 output downloader.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.odin.stage3_downloader import Stage3OutputDownloader
from src.odin.config import OdinConfig


class TestStage3OutputDownloader(unittest.TestCase):
    """Test Stage3OutputDownloader functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'test_config.yaml'
        
        # Create a mock config
        self.mock_config = Mock()
        self.mock_config.region = 'eu-north-1'
        self.mock_config.environment = 'test'
        self.mock_config.bucket_name = 'test-bucket'
    
    def tearDown(self):
        """Clean up test environment."""
        if self.config_file.exists():
            self.config_file.unlink()
    
    @patch('boto3.client')
    def test_downloader_initialization(self, mock_boto3):
        """Test downloader initialization."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        self.assertEqual(downloader.config, self.mock_config)
        self.assertEqual(downloader.s3, mock_s3)
    
    @patch('boto3.client')
    def test_download_stage3_output_s3(self, mock_boto3):
        """Test downloading stage3 output from S3."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 operations
        mock_s3.download_file.return_value = None
        mock_s3.head_object.return_value = {'ContentLength': 1024}
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader.download_stage3_output(
            cloud_output_path='s3://test-bucket/output',
            local_output_path=Path(self.temp_dir) / 'output'
        )
        
        self.assertEqual(result['status'], 'completed')
        self.assertIn('downloaded_files', result)
        self.assertIn('total_size_bytes', result)
        self.assertIn('download_time', result)
    
    @patch('boto3.client')
    def test_download_stage3_output_local(self, mock_boto3):
        """Test downloading stage3 output from local path."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test files
        test_dir = Path(self.temp_dir) / 'test_output'
        test_dir.mkdir()
        (test_dir / 'compressed_observations.json').write_text('{"test": "data"}')
        (test_dir / 'report.json').write_text('{"summary": "test"}')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader.download_stage3_output(
            cloud_output_path=f'file://{test_dir}',
            local_output_path=Path(self.temp_dir) / 'output'
        )
        
        self.assertEqual(result['status'], 'completed')
        self.assertIn('downloaded_files', result)
    
    @patch('boto3.client')
    def test_download_stage3_output_error(self, mock_boto3):
        """Test downloading stage3 output with error."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 error
        mock_s3.download_file.side_effect = Exception('S3 download failed')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader.download_stage3_output(
            cloud_output_path='s3://test-bucket/output',
            local_output_path=Path(self.temp_dir) / 'output'
        )
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_download_file_s3_success(self, mock_boto3):
        """Test downloading file from S3 successfully."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 operations
        mock_s3.download_file.return_value = None
        mock_s3.head_object.return_value = {'ContentLength': 1024}
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader._download_file(
            s3_path='s3://test-bucket/path/to/file.json',
            local_path=Path(self.temp_dir) / 'file.json'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['size_bytes'], 1024)
        self.assertEqual(result['cloud_path'], 's3://test-bucket/path/to/file.json')
    
    @patch('boto3.client')
    def test_download_file_s3_failure(self, mock_boto3):
        """Test downloading file from S3 with failure."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 error
        mock_s3.download_file.side_effect = Exception('S3 download failed')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader._download_file(
            s3_path='s3://test-bucket/path/to/file.json',
            local_path=Path(self.temp_dir) / 'file.json'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_download_file_local_success(self, mock_boto3):
        """Test downloading file from local path successfully."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test file
        test_file = Path(self.temp_dir) / 'test_file.json'
        test_file.write_text('{"test": "data"}')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader._download_file(
            s3_path=f'file://{test_file}',
            local_path=Path(self.temp_dir) / 'copied_file.json'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['size_bytes'], len('{"test": "data"}'))
        self.assertTrue(Path(self.temp_dir / 'copied_file.json').exists())
    
    @patch('boto3.client')
    def test_download_file_local_failure(self, mock_boto3):
        """Test downloading file from local path with failure."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        result = downloader._download_file(
            s3_path='file:///non/existent/file.json',
            local_path=Path(self.temp_dir) / 'copied_file.json'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_get_additional_files_s3(self, mock_boto3):
        """Test getting additional files from S3."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 list objects
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'output/stage3/compressed_observations.json'},
                {'Key': 'output/stage3/report.json'},
                {'Key': 'output/stage3/additional_file.json'},
                {'Key': 'output/stage3/another_file.csv'}
            ]
        }
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        additional_files = downloader._get_additional_files('s3://test-bucket/output')
        
        self.assertEqual(len(additional_files), 2)
        self.assertIn('s3://test-bucket/output/stage3/additional_file.json', additional_files)
        self.assertIn('s3://test-bucket/output/stage3/another_file.csv', additional_files)
    
    @patch('boto3.client')
    def test_get_additional_files_local(self, mock_boto3):
        """Test getting additional files from local path."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test directory structure
        test_dir = Path(self.temp_dir) / 'test_output'
        test_dir.mkdir()
        (test_dir / 'compressed_observations.json').write_text('{}')
        (test_dir / 'report.json').write_text('{}')
        (test_dir / 'additional_file.json').write_text('{}')
        (test_dir / 'another_file.csv').write_text('data')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        additional_files = downloader._get_additional_files(f'file://{test_dir}')
        
        self.assertEqual(len(additional_files), 2)
        self.assertIn(f'file://{test_dir}/additional_file.json', additional_files)
        self.assertIn(f'file://{test_dir}/another_file.csv', additional_files)
    
    @patch('boto3.client')
    def test_get_stage3_summary_success(self, mock_boto3):
        """Test getting stage3 summary successfully."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test files
        test_dir = Path(self.temp_dir) / 'test_output'
        test_dir.mkdir()
        
        # Create compressed observations file
        observations_data = {
            'observations': [
                {'species': 'deer', 'confidence': 0.9, 'timestamp': '2023-01-01T00:00:00Z'},
                {'species': 'fox', 'confidence': 0.8, 'timestamp': '2023-01-01T01:00:00Z'}
            ]
        }
        (test_dir / 'compressed_observations.json').write_text(str(observations_data))
        
        # Create report file
        report_data = {
            'summary': {
                'total_observations': 2,
                'species_count': {'deer': 1, 'fox': 1},
                'camera_count': {'camera1': 2}
            }
        }
        (test_dir / 'report.json').write_text(str(report_data))
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        summary = downloader.get_stage3_summary(test_dir)
        
        self.assertEqual(summary['total_observations'], 2)
        self.assertEqual(summary['species_count']['deer'], 1)
        self.assertEqual(summary['species_count']['fox'], 1)
        self.assertEqual(summary['camera_count']['camera1'], 2)
    
    @patch('boto3.client')
    def test_get_stage3_summary_missing_files(self, mock_boto3):
        """Test getting stage3 summary with missing files."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create empty directory
        test_dir = Path(self.temp_dir) / 'empty_output'
        test_dir.mkdir()
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        summary = downloader.get_stage3_summary(test_dir)
        
        self.assertIn('error', summary)
    
    @patch('boto3.client')
    def test_create_local_stage3_runner(self, mock_boto3):
        """Test creating local stage3 runner."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test directory with files
        test_dir = Path(self.temp_dir) / 'test_output'
        test_dir.mkdir()
        (test_dir / 'compressed_observations.json').write_text('{"observations": []}')
        (test_dir / 'report.json').write_text('{"summary": {}}')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        runner_path = downloader.create_local_stage3_runner(test_dir)
        
        self.assertIsNotNone(runner_path)
        self.assertTrue(Path(runner_path).exists())
        self.assertTrue(Path(runner_path).stat().st_mode & 0o755)  # Check executable permissions
    
    @patch('boto3.client')
    def test_create_local_stage3_runner_missing_files(self, mock_boto3):
        """Test creating local stage3 runner with missing files."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create empty directory
        test_dir = Path(self.temp_dir) / 'empty_output'
        test_dir.mkdir()
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        runner_path = downloader.create_local_stage3_runner(test_dir)
        
        self.assertIsNone(runner_path)
    
    @patch('boto3.client')
    def test_validate_s3_path(self, mock_boto3):
        """Test S3 path validation."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        # Test valid S3 path
        result = downloader._validate_s3_path('s3://test-bucket/path/to/file.json')
        self.assertTrue(result['valid'])
        self.assertEqual(result['bucket'], 'test-bucket')
        self.assertEqual(result['key'], 'path/to/file.json')
        
        # Test invalid S3 path
        result = downloader._validate_s3_path('not-s3://bucket/key')
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_get_file_size_s3(self, mock_boto3):
        """Test getting file size from S3."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 head object
        mock_s3.head_object.return_value = {'ContentLength': 2048}
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        size = downloader._get_file_size('s3://test-bucket/path/to/file.json')
        
        self.assertEqual(size, 2048)
    
    @patch('boto3.client')
    def test_get_file_size_local(self, mock_boto3):
        """Test getting file size from local path."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Create test file
        test_file = Path(self.temp_dir) / 'test_file.json'
        test_file.write_text('{"test": "data"}')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        size = downloader._get_file_size(f'file://{test_file}')
        
        self.assertEqual(size, len('{"test": "data"}'))
    
    @patch('boto3.client')
    def test_get_file_size_error(self, mock_boto3):
        """Test getting file size with error."""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock S3 error
        mock_s3.head_object.side_effect = Exception('S3 error')
        
        downloader = Stage3OutputDownloader(self.mock_config)
        
        size = downloader._get_file_size('s3://test-bucket/path/to/file.json')
        
        self.assertEqual(size, 0)


if __name__ == '__main__':
    unittest.main()
