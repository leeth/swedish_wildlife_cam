#!/usr/bin/env python3
"""
Unit Tests for Odin - The All-Knowing Father

Tests Odin's infrastructure management and pipeline capabilities.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

from odin import Odin

class TestOdin(unittest.TestCase):
    """Test cases for Odin infrastructure management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    def test_odin_initialization(self):
        """Test Odin initialization."""
        self.assertIsNotNone(self.odin.config)
        self.assertEqual(self.odin.config['name'], "Wildlife Processing World")
        self.assertEqual(self.odin.region, "eu-north-1")
        self.assertEqual(self.odin.bucket_name, "wildlife-test-production-696852893392")
    
    @patch('boto3.client')
    def test_get_default_vpc(self, mock_boto3):
        """Test getting default VPC."""
        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        
        # Mock VPC response
        mock_ec2.describe_vpcs.return_value = {
            'Vpcs': [{'VpcId': 'vpc-12345'}]
        }
        mock_ec2.describe_subnets.return_value = {
            'Subnets': [
                {'SubnetId': 'subnet-1'},
                {'SubnetId': 'subnet-2'}
            ]
        }
        
        vpc_id, subnet_ids = self.odin.get_default_vpc()
        
        self.assertEqual(vpc_id, 'vpc-12345')
        self.assertEqual(len(subnet_ids), 2)
        self.assertIn('subnet-1', subnet_ids)
        self.assertIn('subnet-2', subnet_ids)
    
    @patch('boto3.client')
    def test_check_infrastructure_exists(self, mock_boto3):
        """Test checking if infrastructure exists."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock successful stack response
        mock_cf.describe_stacks.return_value = {
            'Stacks': [{'StackStatus': 'CREATE_COMPLETE'}]
        }
        
        result = self.odin.check_infrastructure_exists()
        self.assertTrue(result)
    
    @patch('boto3.client')
    def test_check_infrastructure_not_exists(self, mock_boto3):
        """Test checking when infrastructure doesn't exist."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock stack not found
        mock_cf.describe_stacks.side_effect = Exception("does not exist")
        
        result = self.odin.check_infrastructure_exists()
        self.assertFalse(result)
    
    @patch('boto3.client')
    def test_upload_data(self, mock_boto3):
        """Test data upload functionality."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock test data directory
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir') as mock_iterdir:
                # Mock file objects
                mock_file1 = Mock()
                mock_file1.is_file.return_value = True
                mock_file1.name = 'test1.jpg'
                mock_file1.stat.return_value.st_size = 1000
                
                mock_file2 = Mock()
                mock_file2.is_file.return_value = True
                mock_file2.name = 'test2.mp4'
                mock_file2.stat.return_value.st_size = 2000
                
                mock_iterdir.return_value = [mock_file1, mock_file2]
                
                result = self.odin.upload_data('test_data')
                
                self.assertTrue(result)
                self.assertEqual(mock_s3.upload_file.call_count, 2)
    
    @patch('boto3.client')
    def test_get_status(self, mock_boto3):
        """Test status reporting."""
        # Mock clients
        mock_cf = Mock()
        mock_batch = Mock()
        mock_s3 = Mock()
        
        mock_boto3.side_effect = [mock_cf, mock_batch, mock_s3]
        
        # Mock responses
        mock_cf.describe_stacks.return_value = {
            'Stacks': [{'StackStatus': 'CREATE_COMPLETE'}]
        }
        
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [{
                'computeEnvironmentName': 'wildlife-compute-production',
                'status': 'VALID',
                'computeResources': {
                    'desiredvCpus': 0,
                    'maxvCpus': 8
                }
            }]
        }
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'test.jpg', 'Size': 1000}]
        }
        
        # Should not raise exception
        try:
            self.odin.get_status()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"get_status raised {e}")
    
    def test_config_loading(self):
        """Test configuration loading."""
        self.assertIn('infrastructure', self.odin.config)
        self.assertIn('storage', self.odin.config)
        self.assertIn('pipeline', self.odin.config)
        
        # Test infrastructure config
        infra = self.odin.config['infrastructure']
        self.assertEqual(infra['region'], 'eu-north-1')
        self.assertTrue(infra['cost_optimized'])
        
        # Test storage config
        storage = self.odin.config['storage']
        self.assertEqual(storage['s3_bucket'], 'wildlife-test-production-696852893392')
        
        # Test pipeline config
        pipeline = self.odin.config['pipeline']
        self.assertIn('stages', pipeline)

class TestOdinInfrastructure(unittest.TestCase):
    """Test cases for Odin infrastructure management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    @patch('boto3.client')
    def test_setup_infrastructure(self, mock_boto3):
        """Test infrastructure setup."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock successful stack creation
        mock_cf.create_stack.return_value = {'StackId': 'stack-12345'}
        
        # Mock VPC info
        with patch.object(self.odin, 'get_default_vpc', return_value=('vpc-123', ['subnet-1'])):
            with patch.object(self.odin, 'check_infrastructure_exists', return_value=False):
                with patch('time.sleep'):
                    result = self.odin.setup_infrastructure()
                    self.assertTrue(result)
    
    @patch('boto3.client')
    def test_deploy_cloudformation_stack(self, mock_boto3):
        """Test CloudFormation stack deployment."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock successful stack creation
        mock_cf.create_stack.return_value = {'StackId': 'stack-12345'}
        
        # Mock VPC info
        with patch.object(self.odin, 'get_default_vpc', return_value=('vpc-123', ['subnet-1'])):
            with patch('time.sleep'):
                result = self.odin.deploy_cloudformation_stack()
                self.assertTrue(result)

class TestOdinPipeline(unittest.TestCase):
    """Test cases for Odin pipeline execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    @patch('boto3.client')
    def test_run_pipeline_stage0(self, mock_boto3):
        """Test running pipeline stage 0 (upload)."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock test data directory
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir') as mock_iterdir:
                # Mock file objects
                mock_file = Mock()
                mock_file.is_file.return_value = True
                mock_file.name = 'test.jpg'
                mock_file.stat.return_value.st_size = 1000
                
                mock_iterdir.return_value = [mock_file]
                
                result = self.odin.run_pipeline('test_data', ['stage0'])
                self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_run_stage1(self, mock_subprocess):
        """Test running stage 1 (manifest creation)."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage1()
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_run_stage2(self, mock_subprocess):
        """Test running stage 2 (detection)."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage2()
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_run_stage3(self, mock_subprocess):
        """Test running stage 3 (reporting)."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage3()
        self.assertTrue(result)

class TestOdinCleanup(unittest.TestCase):
    """Test cases for Odin cleanup functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    @patch('boto3.client')
    def test_cleanup_infrastructure(self, mock_boto3):
        """Test infrastructure cleanup."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_cf, mock_s3]
        
        # Mock S3 bucket listing
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'test.jpg', 'Size': 1000}]
        }
        
        # Mock time.sleep to avoid actual waiting
        with patch('time.sleep'):
            with patch('builtins.input', return_value='ODIN CLEANUP'):
                result = self.odin.cleanup()
                self.assertTrue(result)

if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOdin))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinInfrastructure))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinCleanup))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
