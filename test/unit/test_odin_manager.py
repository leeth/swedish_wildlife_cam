"""
Test odin manager module.

Comprehensive tests for the cost optimization manager.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from odin.manager import CostOptimizationManager
from odin.config import OdinConfig


class TestCostOptimizationManager(unittest.TestCase):
    """Test CostOptimizationManager functionality."""
    
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
        self.mock_config.cost_threshold_percentage = 0.1
    
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
        
        manager = CostOptimizationManager(self.mock_config)
        
        self.assertEqual(manager.config, self.mock_config)
        self.assertEqual(manager.compute_env_name, 'wildlife-detection-compute-test')
        self.assertEqual(manager.job_queue_name, 'wildlife-detection-queue-test')
        self.assertEqual(manager.job_def_name, 'wildlife-detection-job-test')
    
    @patch('boto3.client')
    def test_setup_infrastructure(self, mock_boto3):
        """Test infrastructure setup."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock successful setup
        mock_batch.update_compute_environment.return_value = {'statusCode': 200}
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager.setup_infrastructure(job_count=2, gpu_required=True)
        
        self.assertTrue(result)
        mock_batch.update_compute_environment.assert_called()
    
    @patch('boto3.client')
    def test_setup_infrastructure_failure(self, mock_boto3):
        """Test infrastructure setup failure."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock setup failure
        mock_batch.update_compute_environment.side_effect = Exception('Setup failed')
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager.setup_infrastructure(job_count=1, gpu_required=True)
        
        self.assertFalse(result)
    
    @patch('boto3.client')
    def test_teardown_infrastructure(self, mock_boto3):
        """Test infrastructure teardown."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock successful teardown
        mock_batch.update_compute_environment.return_value = {'statusCode': 200}
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager.teardown_infrastructure()
        
        self.assertTrue(result)
        mock_batch.update_compute_environment.assert_called()
    
    @patch('boto3.client')
    def test_get_compute_environment_status(self, mock_boto3):
        """Test getting compute environment status."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock status response
        mock_status = {
            'computeEnvironments': [{
                'status': 'VALID',
                'computeResources': {'desiredvCpus': 8}
            }]
        }
        mock_batch.describe_compute_environments.return_value = mock_status
        
        manager = CostOptimizationManager(self.mock_config)
        status = manager.get_compute_environment_status()
        
        self.assertEqual(status['status'], 'VALID')
        self.assertEqual(status['computeResources']['desiredvCpus'], 8)
    
    @patch('boto3.client')
    def test_get_compute_environment_status_empty(self, mock_boto3):
        """Test getting compute environment status when empty."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock empty response
        mock_batch.describe_compute_environments.return_value = {'computeEnvironments': []}
        
        manager = CostOptimizationManager(self.mock_config)
        status = manager.get_compute_environment_status()
        
        self.assertEqual(status, {})
    
    @patch('boto3.client')
    def test_get_cost_metrics(self, mock_boto3):
        """Test getting cost metrics."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock status and pricing
        mock_status = {
            'computeResources': {'desiredvCpus': 8}
        }
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [mock_status]
        }
        
        # Mock pricing data
        mock_ec2.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [{'InstanceType': 'g4dn.xlarge', 'SpotPrice': '0.5'}]}
        
        manager = CostOptimizationManager(self.mock_config)
        metrics = manager.get_cost_metrics()
        
        self.assertIn('instance_count', metrics)
        self.assertIn('instance_type', metrics)
        self.assertIn('spot_price_per_hour', metrics)
        self.assertIn('on_demand_price_per_hour', metrics)
        self.assertIn('savings_per_hour', metrics)
    
    @patch('boto3.client')
    def test_get_cost_metrics_error(self, mock_boto3):
        """Test getting cost metrics with error."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock error
        mock_batch.describe_compute_environments.side_effect = Exception('AWS Error')
        
        manager = CostOptimizationManager(self.mock_config)
        metrics = manager.get_cost_metrics()
        
        self.assertEqual(metrics, {})
    
    @patch('boto3.client')
    def test_select_optimal_instance_type_gpu(self, mock_boto3):
        """Test selecting optimal instance type for GPU."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock pricing data
        mock_ec2.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'InstanceType': 'g4dn.xlarge', 'SpotPrice': '0.5'},
                {'InstanceType': 'g4dn.2xlarge', 'SpotPrice': '0.8'}
            ]}
        
        manager = CostOptimizationManager(self.mock_config)
        instance_type, strategy = manager._select_optimal_instance_type(required_gpu=True)
        
        self.assertIn('g4dn', instance_type)
        self.assertIn(strategy, ['spot', 'on-demand'])
    
    @patch('boto3.client')
    def test_select_optimal_instance_type_no_gpu(self, mock_boto3):
        """Test selecting optimal instance type without GPU."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock pricing data
        mock_ec2.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {'InstanceType': 't3.medium', 'SpotPrice': '0.05'},
                {'InstanceType': 't3.large', 'SpotPrice': '0.08'}
            ]}
        
        manager = CostOptimizationManager(self.mock_config)
        instance_type, strategy = manager._select_optimal_instance_type(required_gpu=False)
        
        self.assertIn('t3', instance_type)
        self.assertIn(strategy, ['spot', 'on-demand'])
    
    @patch('boto3.client')
    def test_scale_compute_environment(self, mock_boto3):
        """Test scaling compute environment."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock successful scaling
        mock_batch.update_compute_environment.return_value = {'statusCode': 200}
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager._scale_compute_environment(16)
        
        self.assertTrue(result)
        mock_batch.update_compute_environment.assert_called_with(
            computeEnvironment='wildlife-detection-compute-test',
            desiredvCpus=16
        )
    
    @patch('boto3.client')
    def test_scale_compute_environment_failure(self, mock_boto3):
        """Test scaling compute environment failure."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock scaling failure
        mock_batch.update_compute_environment.side_effect = Exception('Scaling failed')
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager._scale_compute_environment(16)
        
        self.assertFalse(result)
    
    @patch('boto3.client')
    def test_wait_for_compute_environment_ready(self, mock_boto3):
        """Test waiting for compute environment to be ready."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock status progression
        mock_batch.describe_compute_environments.side_effect = [
            {'computeEnvironments': [{'status': 'UPDATING'}]},
            {'computeEnvironments': [{'status': 'VALID'}]}
        ]
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager._wait_for_compute_environment_ready(timeout_minutes=1)
        
        self.assertTrue(result)
    
    @patch('boto3.client')
    def test_wait_for_compute_environment_timeout(self, mock_boto3):
        """Test waiting for compute environment timeout."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock status that never becomes ready
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [{'status': 'UPDATING'}]}
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager._wait_for_compute_environment_ready(timeout_minutes=0.01)  # Very short timeout
        
        self.assertFalse(result)
    
    @patch('boto3.client')
    def test_wait_for_compute_environment_empty(self, mock_boto3):
        """Test waiting for compute environment to be empty."""
        mock_batch = Mock()
        mock_ec2 = Mock()
        mock_cloudwatch = Mock()
        mock_boto3.side_effect = [mock_batch, mock_ec2, mock_cloudwatch]
        
        # Mock status progression to empty
        mock_batch.describe_compute_environments.side_effect = [
            {'computeEnvironments': [{'computeResources': {'desiredvCpus': 8}}]},
            {'computeEnvironments': [{'computeResources': {'desiredvCpus': 0}}]}
        ]
        
        manager = CostOptimizationManager(self.mock_config)
        result = manager._wait_for_compute_environment_empty(timeout_minutes=1)
        
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
