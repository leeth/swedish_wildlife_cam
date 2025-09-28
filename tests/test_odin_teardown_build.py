#!/usr/bin/env python3
"""
Unit Tests for Odin Teardown and Build

Tests Odin's infrastructure teardown and build capabilities.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

from odin_teardown import OdinTeardown
from odin_build import OdinBuild

class TestOdinTeardown(unittest.TestCase):
    """Test cases for Odin teardown functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.teardown = OdinTeardown()
    
    def test_teardown_initialization(self):
        """Test teardown initialization."""
        self.assertIsNotNone(self.teardown.region)
        self.assertEqual(self.teardown.region, 'eu-north-1')
        self.assertIsNotNone(self.teardown.cloudformation)
        self.assertIsNotNone(self.teardown.batch)
        self.assertIsNotNone(self.teardown.s3)
        self.assertIsNotNone(self.teardown.iam)
    
    @patch('boto3.client')
    def test_list_stacks(self, mock_boto3):
        """Test listing stacks."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock stack response
        mock_cf.list_stacks.return_value = {
            'StackSummaries': [
                {
                    'StackName': 'wildlife-test-stack',
                    'StackStatus': 'CREATE_COMPLETE'
                },
                {
                    'StackName': 'other-stack',
                    'StackStatus': 'CREATE_COMPLETE'
                }
            ]
        }
        
        stacks = self.teardown.list_stacks()
        
        # Should only return wildlife stacks
        self.assertEqual(len(stacks), 1)
        self.assertEqual(stacks[0]['StackName'], 'wildlife-test-stack')
    
    @patch('boto3.client')
    def test_list_batch_resources(self, mock_boto3):
        """Test listing batch resources."""
        # Mock Batch client
        mock_batch = Mock()
        mock_boto3.return_value = mock_batch
        
        # Mock responses
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [
                {
                    'computeEnvironmentName': 'wildlife-compute',
                    'status': 'VALID'
                }
            ]
        }
        mock_batch.describe_job_queues.return_value = {
            'jobQueues': [
                {
                    'jobQueueName': 'wildlife-queue',
                    'state': 'ENABLED'
                }
            ]
        }
        mock_batch.describe_job_definitions.return_value = {
            'jobDefinitions': [
                {
                    'jobDefinitionName': 'wildlife-job',
                    'status': 'ACTIVE'
                }
            ]
        }
        
        ces, jqs, jds = self.teardown.list_batch_resources()
        
        self.assertEqual(len(ces), 1)
        self.assertEqual(len(jqs), 1)
        self.assertEqual(len(jds), 1)
    
    @patch('boto3.client')
    def test_list_s3_buckets(self, mock_boto3):
        """Test listing S3 buckets."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock bucket response
        mock_s3.list_buckets.return_value = {
            'Buckets': [
                {
                    'Name': 'wildlife-test-bucket',
                    'CreationDate': '2025-01-01T00:00:00Z'
                },
                {
                    'Name': 'other-bucket',
                    'CreationDate': '2025-01-01T00:00:00Z'
                }
            ]
        }
        
        buckets = self.teardown.list_s3_buckets()
        
        # Should only return wildlife buckets
        self.assertEqual(len(buckets), 1)
        self.assertEqual(buckets[0]['Name'], 'wildlife-test-bucket')
    
    @patch('boto3.client')
    def test_teardown_stack_success(self, mock_boto3):
        """Test successful stack teardown."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock stack exists
        mock_cf.describe_stacks.return_value = {
            'Stacks': [{'StackStatus': 'CREATE_COMPLETE'}]
        }
        
        # Mock successful deletion
        mock_cf.delete_stack.return_value = {}
        mock_cf.get_waiter.return_value.wait.return_value = None
        
        result = self.teardown.teardown_stack('test-stack')
        self.assertTrue(result)
    
    @patch('boto3.client')
    def test_teardown_stack_not_exists(self, mock_boto3):
        """Test teardown of non-existent stack."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock stack doesn't exist
        mock_cf.describe_stacks.side_effect = Exception("does not exist")
        
        result = self.teardown.teardown_stack('non-existent-stack')
        self.assertTrue(result)  # Should return True for non-existent stack
    
    @patch('boto3.client')
    def test_teardown_s3_bucket_success(self, mock_boto3):
        """Test successful S3 bucket teardown."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Mock bucket with objects
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'test1.jpg', 'Size': 1000},
                {'Key': 'test2.mp4', 'Size': 2000}
            ]
        }
        
        result = self.teardown.teardown_s3_bucket('test-bucket')
        self.assertTrue(result)
        
        # Verify objects were deleted
        self.assertEqual(mock_s3.delete_object.call_count, 2)
        mock_s3.delete_bucket.assert_called_once()

class TestOdinBuild(unittest.TestCase):
    """Test cases for Odin build functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.build = OdinBuild()
    
    def test_build_initialization(self):
        """Test build initialization."""
        self.assertIsNotNone(self.build.region)
        self.assertEqual(self.build.region, 'eu-north-1')
        self.assertIsNotNone(self.build.config)
        self.assertIsNotNone(self.build.cloudformation)
        self.assertIsNotNone(self.build.ec2)
    
    def test_config_loading(self):
        """Test configuration loading."""
        config = self.build.config
        
        # Test top-level structure
        self.assertIn('name', config)
        self.assertIn('version', config)
        self.assertIn('infrastructure', config)
        self.assertIn('storage', config)
        
        # Test infrastructure structure
        infra = config['infrastructure']
        self.assertIn('batch', infra)
        self.assertIn('region', infra)
        
        # Test batch structure
        batch = infra['batch']
        self.assertIn('compute_environment', batch)
        self.assertIn('job_queue', batch)
    
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
        
        vpc_id, subnet_ids = self.build.get_default_vpc()
        
        self.assertEqual(vpc_id, 'vpc-12345')
        self.assertEqual(len(subnet_ids), 2)
        self.assertIn('subnet-1', subnet_ids)
        self.assertIn('subnet-2', subnet_ids)
    
    def test_generate_cloudformation_template(self):
        """Test CloudFormation template generation."""
        template = self.build.generate_cloudformation_template()
        
        # Test template contains key resources
        self.assertIn('AWSTemplateFormatVersion', template)
        self.assertIn('DataBucket', template)
        self.assertIn('ComputeEnvironment', template)
        self.assertIn('JobQueue', template)
        self.assertIn('BatchJobRole', template)
        self.assertIn('SecurityGroup', template)
    
    @patch('boto3.client')
    def test_deploy_stack_success(self, mock_boto3):
        """Test successful stack deployment."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_boto3.return_value = mock_cf
        
        # Mock successful stack creation
        mock_cf.create_stack.return_value = {'StackId': 'stack-12345'}
        
        # Mock VPC info
        with patch.object(self.build, 'get_default_vpc', return_value=('vpc-123', ['subnet-1'])):
            with patch('time.sleep'):
                with patch.object(mock_cf, 'get_waiter') as mock_waiter:
                    mock_waiter.return_value.wait.return_value = None
                    result = self.build.deploy_stack('test-stack', 'template')
                    self.assertTrue(result)
    
    @patch('boto3.client')
    def test_verify_deployment_success(self, mock_boto3):
        """Test successful deployment verification."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_batch = Mock()
        mock_boto3.side_effect = [mock_cf, mock_batch]
        
        # Mock stack outputs
        mock_cf.describe_stacks.return_value = {
            'Stacks': [{
                'Outputs': [
                    {'OutputKey': 'DataBucket', 'OutputValue': 'test-bucket'},
                    {'OutputKey': 'ComputeEnvironment', 'OutputValue': 'test-ce'}
                ]
            }]
        }
        
        # Mock batch resources
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [
                {
                    'computeEnvironmentName': 'wildlife-compute',
                    'status': 'VALID'
                }
            ]
        }
        mock_batch.describe_job_queues.return_value = {
            'jobQueues': [
                {
                    'jobQueueName': 'wildlife-queue',
                    'state': 'ENABLED'
                }
            ]
        }
        
        result = self.build.verify_deployment('test-stack')
        self.assertTrue(result)
    
    @patch('boto3.client')
    def test_build_all_success(self, mock_boto3):
        """Test successful complete build."""
        # Mock CloudFormation client
        mock_cf = Mock()
        mock_batch = Mock()
        mock_boto3.side_effect = [mock_cf, mock_batch]
        
        # Mock successful stack creation
        mock_cf.create_stack.return_value = {'StackId': 'stack-12345'}
        
        # Mock VPC info
        with patch.object(self.build, 'get_default_vpc', return_value=('vpc-123', ['subnet-1'])):
            with patch.object(self.build, 'generate_cloudformation_template', return_value='template'):
                with patch.object(self.build, 'deploy_stack', return_value=True):
                    with patch.object(self.build, 'verify_deployment', return_value=True):
                        result = self.build.build_all()
                        self.assertTrue(result)

class TestOdinTeardownBuildIntegration(unittest.TestCase):
    """Integration tests for teardown and build."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.teardown = OdinTeardown()
        self.build = OdinBuild()
    
    def test_teardown_build_cycle(self):
        """Test complete teardown and build cycle."""
        # Test that both teardown and build can be initialized
        self.assertIsNotNone(self.teardown)
        self.assertIsNotNone(self.build)
        
        # Test that they use the same region
        self.assertEqual(self.teardown.region, self.build.region)
    
    @patch('boto3.client')
    def test_list_resources_after_build(self, mock_boto3):
        """Test listing resources after build."""
        # Mock clients
        mock_cf = Mock()
        mock_batch = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_cf, mock_batch, mock_s3]
        
        # Mock resources after build
        mock_cf.list_stacks.return_value = {
            'StackSummaries': [
                {
                    'StackName': 'wildlife-odin-infrastructure',
                    'StackStatus': 'CREATE_COMPLETE'
                }
            ]
        }
        
        mock_batch.describe_compute_environments.return_value = {
            'computeEnvironments': [
                {
                    'computeEnvironmentName': 'wildlife-compute-production',
                    'status': 'VALID'
                }
            ]
        }
        
        mock_batch.describe_job_queues.return_value = {
            'jobQueues': [
                {
                    'jobQueueName': 'wildlife-queue-production',
                    'state': 'ENABLED'
                }
            ]
        }
        
        mock_s3.list_buckets.return_value = {
            'Buckets': [
                {
                    'Name': 'wildlife-test-production-696852893392',
                    'CreationDate': '2025-01-01T00:00:00Z'
                }
            ]
        }
        
        # Test listing resources
        stacks = self.teardown.list_stacks()
        ces, jqs, jds = self.teardown.list_batch_resources()
        buckets = self.teardown.list_s3_buckets()
        
        # Should find wildlife resources
        self.assertEqual(len(stacks), 1)
        self.assertEqual(len(ces), 1)
        self.assertEqual(len(jqs), 1)
        self.assertEqual(len(buckets), 1)

if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOdinTeardown))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinBuild))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinTeardownBuildIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
