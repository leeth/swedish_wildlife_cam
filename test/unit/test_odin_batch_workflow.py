"""
Test odin batch workflow module.

Comprehensive tests for the batch workflow management.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from odin.batch_workflow import BatchWorkflowManager
from odin.config import OdinConfig


class TestBatchWorkflowManager(unittest.TestCase):
    """Test BatchWorkflowManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'test_config.yaml'
        
        # Create a mock config
        self.mock_config = Mock()
        self.mock_config.region = 'eu-north-1'
        self.mock_config.environment = 'test'
        self.mock_config.gpu_required = True
        self.mock_config.spot_bid_percentage = 70
        self.mock_config.max_vcpus = 100
    
    def tearDown(self):
        """Clean up test environment."""
        if self.config_file.exists():
            self.config_file.unlink()
    
    @patch('boto3.client')
    def test_manager_initialization(self, mock_boto3):
        """Test manager initialization."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        manager = BatchWorkflowManager(self.mock_config)
        
        self.assertEqual(manager.config, self.mock_config)
        self.assertEqual(manager.batch, mock_batch)
        self.assertEqual(manager.ec2, mock_ec2)
        self.assertEqual(manager.cloudwatch, mock_cloudwatch)
    
    @patch('boto3.client')
    def test_process_batch_success(self, mock_boto3):
        """Test successful batch processing."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock successful job submission
        mock_batch.submit_job.return_value = {'jobId': 'test-job-123'}
        
        manager = BatchWorkflowManager(self.mock_config)
        
        batch_config = {
            'batch_id': 'test-batch',
            'jobs': [{
                'name': 'test-job',
                'parameters': {'input_path': 's3://test/input', 'output_path': 's3://test/output'},
                'gpu_required': True,
                'priority': 'normal'
            }],
            'gpu_required': True,
            'max_parallel_jobs': 1
        }
        
        result = manager.process_batch(batch_config)
        
        self.assertEqual(result['status'], 'submitted')
        self.assertIn('job_results', result)
        self.assertEqual(len(result['job_results']), 1)
        self.assertEqual(result['job_results'][0]['job_id'], 'test-job-123')
    
    @patch('boto3.client')
    def test_process_batch_failure(self, mock_boto3):
        """Test batch processing failure."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job submission failure
        mock_batch.submit_job.side_effect = Exception('Job submission failed')
        
        manager = BatchWorkflowManager(self.mock_config)
        
        batch_config = {
            'batch_id': 'test-batch',
            'jobs': [{
                'name': 'test-job',
                'parameters': {'input_path': 's3://test/input', 'output_path': 's3://test/output'},
                'gpu_required': True,
                'priority': 'normal'
            }],
            'gpu_required': True,
            'max_parallel_jobs': 1
        }
        
        result = manager.process_batch(batch_config)
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_submit_single_job(self, mock_boto3):
        """Test submitting a single job."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock successful job submission
        mock_batch.submit_job.return_value = {'jobId': 'test-job-123'}
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job = {
            'name': 'test-job',
            'parameters': {'input_path': 's3://test/input', 'output_path': 's3://test/output'},
            'gpu_required': True,
            'priority': 'normal'
        }
        
        result = manager._submit_single_job(job, gpu_required=True)
        
        self.assertEqual(result['status'], 'submitted')
        self.assertEqual(result['job_id'], 'test-job-123')
        mock_batch.submit_job.assert_called_once()
    
    @patch('boto3.client')
    def test_submit_single_job_failure(self, mock_boto3):
        """Test single job submission failure."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job submission failure
        mock_batch.submit_job.side_effect = Exception('Job submission failed')
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job = {
            'name': 'test-job',
            'parameters': {'input_path': 's3://test/input', 'output_path': 's3://test/output'},
            'gpu_required': True,
            'priority': 'normal'
        }
        
        result = manager._submit_single_job(job, gpu_required=True)
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_monitor_jobs(self, mock_boto3):
        """Test monitoring jobs."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job status
        mock_batch.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobStatus': 'SUCCEEDED',
                'jobName': 'test-job'
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_results = [{
            'job_id': 'test-job-123',
            'status': 'submitted'
        }]
        
        result = manager._monitor_jobs(job_results)
        
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['job_results']), 1)
        self.assertEqual(result['job_results'][0]['status'], 'succeeded')
    
    @patch('boto3.client')
    def test_monitor_single_job(self, mock_boto3):
        """Test monitoring a single job."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job status
        mock_batch.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobStatus': 'SUCCEEDED',
                'jobName': 'test-job'
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_result = {
            'job_id': 'test-job-123',
            'status': 'submitted'
        }
        
        result = manager._monitor_single_job(job_result)
        
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['job_id'], 'test-job-123')
    
    @patch('boto3.client')
    def test_monitor_single_job_failed(self, mock_boto3):
        """Test monitoring a failed job."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock failed job status
        mock_batch.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobStatus': 'FAILED',
                'jobName': 'test-job',
                'statusReason': 'Job failed due to error'
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_result = {
            'job_id': 'test-job-123',
            'status': 'submitted'
        }
        
        result = manager._monitor_single_job(job_result)
        
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['job_id'], 'test-job-123')
        self.assertIn('error', result)
    
    @patch('boto3.client')
    def test_monitor_single_job_running(self, mock_boto3):
        """Test monitoring a running job."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock running job status
        mock_batch.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobStatus': 'RUNNING',
                'jobName': 'test-job'
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_result = {
            'job_id': 'test-job-123',
            'status': 'submitted'
        }
        
        result = manager._monitor_single_job(job_result)
        
        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['job_id'], 'test-job-123')
    
    @patch('boto3.client')
    def test_get_job_status(self, mock_boto3):
        """Test getting job status."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job status
        mock_batch.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobStatus': 'SUCCEEDED',
                'jobName': 'test-job',
                'createdAt': 1234567890,
                'startedAt': 1234567891,
                'stoppedAt': 1234567892
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        status = manager._get_job_status('test-job-123')
        
        self.assertEqual(status['job_id'], 'test-job-123')
        self.assertEqual(status['status'], 'succeeded')
        self.assertIn('created_at', status)
        self.assertIn('started_at', status)
        self.assertIn('stopped_at', status)
    
    @patch('boto3.client')
    def test_get_job_status_not_found(self, mock_boto3):
        """Test getting status for non-existent job."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock empty job list
        mock_batch.describe_jobs.return_value = {'jobs': []}
        
        manager = BatchWorkflowManager(self.mock_config)
        
        status = manager._get_job_status('non-existent-job')
        
        self.assertEqual(status['job_id'], 'non-existent-job')
        self.assertEqual(status['status'], 'not_found')
    
    @patch('boto3.client')
    def test_get_job_status_error(self, mock_boto3):
        """Test getting job status with error."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock error
        mock_batch.describe_jobs.side_effect = Exception('AWS Error')
        
        manager = BatchWorkflowManager(self.mock_config)
        
        status = manager._get_job_status('test-job-123')
        
        self.assertEqual(status['job_id'], 'test-job-123')
        self.assertEqual(status['status'], 'error')
        self.assertIn('error', status)
    
    @patch('boto3.client')
    def test_create_job_definition(self, mock_boto3):
        """Test creating job definition."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job definition creation
        mock_batch.register_job_definition.return_value = {'jobDefinitionArn': 'arn:aws:batch:region:account:job-definition/test'}
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_def = manager._create_job_definition('test-job', 'test-image', gpu_required=True)
        
        self.assertIsNotNone(job_def)
        mock_batch.register_job_definition.assert_called_once()
    
    @patch('boto3.client')
    def test_create_job_definition_failure(self, mock_boto3):
        """Test job definition creation failure."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job definition creation failure
        mock_batch.register_job_definition.side_effect = Exception('Job definition creation failed')
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_def = manager._create_job_definition('test-job', 'test-image', gpu_required=True)
        
        self.assertIsNone(job_def)
    
    @patch('boto3.client')
    def test_get_job_definition(self, mock_boto3):
        """Test getting job definition."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock job definition
        mock_batch.describe_job_definitions.return_value = {
            'jobDefinitions': [{
                'jobDefinitionArn': 'arn:aws:batch:region:account:job-definition/test',
                'jobDefinitionName': 'test-job',
                'revision': 1
            }]
        }
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_def = manager._get_job_definition('test-job')
        
        self.assertIsNotNone(job_def)
        self.assertEqual(job_def['jobDefinitionName'], 'test-job')
    
    @patch('boto3.client')
    def test_get_job_definition_not_found(self, mock_boto3):
        """Test getting non-existent job definition."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock empty job definitions
        mock_batch.describe_job_definitions.return_value = {'jobDefinitions': []}
        
        manager = BatchWorkflowManager(self.mock_config)
        
        job_def = manager._get_job_definition('non-existent-job')
        
        self.assertIsNone(job_def)


if __name__ == '__main__':
    unittest.main()
