#!/usr/bin/env python3
"""
Simple Unit Tests for Odin - The All-Knowing Father

Basic tests for Odin's core functionality.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch
from pathlib import Path

# Add scripts to path
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

from odin import Odin

class TestOdinBasic(unittest.TestCase):
    """Basic test cases for Odin."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    def test_odin_initialization(self):
        """Test Odin initialization."""
        self.assertIsNotNone(self.odin.config)
        self.assertEqual(self.odin.config['name'], "Wildlife Processing World")
        self.assertEqual(self.odin.region, "eu-north-1")
        self.assertEqual(self.odin.bucket_name, "wildlife-test-production-696852893392")
    
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
    
    def test_odin_commands(self):
        """Test Odin command structure."""
        # Test that main commands exist
        self.assertTrue(hasattr(self.odin, 'setup_infrastructure'))
        self.assertTrue(hasattr(self.odin, 'run_pipeline'))
        self.assertTrue(hasattr(self.odin, 'get_status'))
        self.assertTrue(hasattr(self.odin, 'cleanup'))
    
    def test_odin_pipeline_stages(self):
        """Test pipeline stage methods."""
        # Test that stage methods exist
        self.assertTrue(hasattr(self.odin, 'run_stage1'))
        self.assertTrue(hasattr(self.odin, 'run_stage2'))
        self.assertTrue(hasattr(self.odin, 'run_stage3'))
    
    @patch('boto3.client')
    def test_get_status_no_errors(self, mock_boto3):
        """Test status reporting doesn't crash."""
        # Mock clients to avoid actual AWS calls
        mock_cf = Mock()
        mock_batch = Mock()
        mock_s3 = Mock()
        
        mock_boto3.side_effect = [mock_cf, mock_batch, mock_s3]
        
        # Mock responses
        mock_cf.describe_stacks.side_effect = Exception("Stack not found")
        mock_batch.describe_compute_environments.return_value = {'computeEnvironments': []}
        mock_s3.list_objects_v2.side_effect = Exception("Bucket not found")
        
        # Should not raise exception
        try:
            self.odin.get_status()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"get_status raised {e}")
    
    def test_odin_yaml_structure(self):
        """Test odin.yaml structure."""
        config = self.odin.config
        
        # Test top-level structure
        self.assertIn('name', config)
        self.assertIn('version', config)
        self.assertIn('description', config)
        
        # Test infrastructure structure
        infra = config['infrastructure']
        self.assertIn('provider', infra)
        self.assertIn('region', infra)
        self.assertIn('batch', infra)
        
        # Test batch structure
        batch = infra['batch']
        self.assertIn('compute_environment', batch)
        self.assertIn('job_queue', batch)
        self.assertIn('job_definitions', batch)
        
        # Test storage structure
        storage = config['storage']
        self.assertIn('s3_bucket', storage)
        self.assertIn('prefixes', storage)
        
        # Test pipeline structure
        pipeline = config['pipeline']
        self.assertIn('stages', pipeline)

class TestOdinMocked(unittest.TestCase):
    """Test cases with mocked AWS calls."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.odin = Odin()
    
    def test_setup_infrastructure_structure(self):
        """Test infrastructure setup method exists."""
        # Test that setup method exists and is callable
        self.assertTrue(hasattr(self.odin, 'setup_infrastructure'))
        self.assertTrue(callable(getattr(self.odin, 'setup_infrastructure')))
    
    @patch('subprocess.run')
    def test_run_stage1_mocked(self, mock_subprocess):
        """Test running stage 1 with mocked subprocess."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage1()
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_run_stage2_mocked(self, mock_subprocess):
        """Test running stage 2 with mocked subprocess."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage2()
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_run_stage3_mocked(self, mock_subprocess):
        """Test running stage 3 with mocked subprocess."""
        # Mock successful subprocess
        mock_subprocess.return_value = Mock(returncode=0, stderr='')
        
        result = self.odin.run_stage3()
        self.assertTrue(result)

if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOdinBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestOdinMocked))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
