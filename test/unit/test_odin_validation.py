"""
Test odin validation module.

Comprehensive tests for the validation utilities.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from odin.validation import (
    ValidationError,
    validate_path,
    validate_s3_path,
    validate_url,
    validate_environment_variable,
    sanitize_log_data,
    validate_sql_identifier,
    validate_numeric_range,
    validate_string_length
)


class TestValidationModule(unittest.TestCase):
    """Test validation module functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_validate_path_valid_cases(self):
        """Test valid path validation."""
        # Test relative path
        result = validate_path('data/images/test.jpg', allow_absolute=True)
        self.assertIsInstance(result, Path)
        
        # Test absolute path when allowed
        result = validate_path('/tmp/test', allow_absolute=True)
        self.assertIsInstance(result, Path)
    
    def test_validate_path_invalid_cases(self):
        """Test invalid path validation."""
        # Test path traversal
        with self.assertRaises(ValidationError):
            validate_path('../etc/passwd')
        
        with self.assertRaises(ValidationError):
            validate_path('../../../etc/passwd')
        
        # Test absolute path when not allowed
        with self.assertRaises(ValidationError):
            validate_path('/etc/passwd', allow_absolute=False)
        
        # Test dangerous characters
        with self.assertRaises(ValidationError):
            validate_path('test; rm -rf /')
        
        with self.assertRaises(ValidationError):
            validate_path('test | cat /etc/passwd')
    
    def test_validate_s3_path_valid_cases(self):
        """Test valid S3 path validation."""
        valid_paths = [
            's3://my-bucket/path/to/file.json',
            's3://test-bucket-123/data.csv',
            's3://bucket.with.dots/file.txt'
        ]
        
        for s3_path in valid_paths:
            result = validate_s3_path(s3_path)
            self.assertIn('bucket', result)
            self.assertIn('key', result)
    
    def test_validate_s3_path_invalid_cases(self):
        """Test invalid S3 path validation."""
        invalid_paths = [
            'not-s3://bucket/key',
            's3://bucket',
            's3://bucket/',
            's3://invalid-bucket-name!@#/key',
            's3://a/key',  # Too short
            's3://' + 'a' * 64 + '/key'  # Too long
        ]
        
        for s3_path in invalid_paths:
            with self.assertRaises(ValidationError):
                validate_s3_path(s3_path)
    
    def test_validate_url_valid_cases(self):
        """Test valid URL validation."""
        valid_urls = [
            'https://example.com',
            'http://localhost:8080',
            's3://bucket/key',
            'file:///path/to/file'
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            self.assertEqual(result, url)
    
    def test_validate_url_invalid_cases(self):
        """Test invalid URL validation."""
        invalid_urls = [
            'not-a-url',
            'ftp://example.com',  # Unsupported scheme
            'javascript:alert(1)',  # Dangerous scheme
            '',
            'http://'  # Missing netloc
        ]
        
        for url in invalid_urls:
            with self.assertRaises(ValidationError):
                validate_url(url)
    
    def test_validate_environment_variable(self):
        """Test environment variable validation."""
        # Test existing variable
        os.environ['TEST_VAR'] = 'test_value'
        result = validate_environment_variable('TEST_VAR', required=True)
        self.assertEqual(result, 'test_value')
        
        # Test missing required variable
        with self.assertRaises(ValidationError):
            validate_environment_variable('NONEXISTENT_VAR', required=True)
        
        # Test optional variable
        result = validate_environment_variable('NONEXISTENT_VAR', required=False)
        self.assertIsNone(result)
        
        # Test empty variable
        os.environ['EMPTY_VAR'] = ''
        with self.assertRaises(ValidationError):
            validate_environment_variable('EMPTY_VAR', required=True)
    
    def test_sanitize_log_data(self):
        """Test log data sanitization."""
        test_data = {
            'username': 'test_user',
            'password': 'secret123',
            'aws_access_key': 'AKIAIOSFODNN7EXAMPLE',
            'normal_data': 'this should not be redacted',
            'nested': {
                'password': 'nested_secret',
                'public_info': 'this is public'
            }
        }
        
        sanitized = sanitize_log_data(test_data)
        
        # Check sensitive data is redacted
        self.assertEqual(sanitized['password'], '***REDACTED***')
        self.assertEqual(sanitized['aws_access_key'], '***REDACTED***')
        
        # Check normal data is preserved
        self.assertEqual(sanitized['username'], 'test_user')
        self.assertEqual(sanitized['normal_data'], 'this should not be redacted')
        
        # Check nested data
        self.assertEqual(sanitized['nested']['password'], '***REDACTED***')
        self.assertEqual(sanitized['nested']['public_info'], 'this is public')
    
    def test_validate_sql_identifier(self):
        """Test SQL identifier validation."""
        # Test valid identifiers
        valid_identifiers = ['table_name', 'column_name', 'user_id', '_private']
        for identifier in valid_identifiers:
            result = validate_sql_identifier(identifier)
            self.assertEqual(result, identifier)
        
        # Test invalid identifiers
        invalid_identifiers = [
            '',  # Empty
            '123invalid',  # Starts with number
            'table-name',  # Contains hyphen
            'table.name',  # Contains dot
            'table name',  # Contains space
            'SELECT',  # SQL keyword
            'DROP',  # SQL keyword
        ]
        
        for identifier in invalid_identifiers:
            with self.assertRaises(ValidationError):
                validate_sql_identifier(identifier)
    
    def test_validate_numeric_range(self):
        """Test numeric range validation."""
        # Test valid ranges
        result = validate_numeric_range(5, min_val=0, max_val=10)
        self.assertEqual(result, 5)
        
        # Test out of range
        with self.assertRaises(ValidationError):
            validate_numeric_range(15, min_val=0, max_val=10)
        
        with self.assertRaises(ValidationError):
            validate_numeric_range(-5, min_val=0, max_val=10)
        
        # Test non-numeric
        with self.assertRaises(ValidationError):
            validate_numeric_range('not_a_number')
    
    def test_validate_string_length(self):
        """Test string length validation."""
        # Test valid lengths
        result = validate_string_length('hello', min_length=3, max_length=10)
        self.assertEqual(result, 'hello')
        
        # Test invalid lengths
        with self.assertRaises(ValidationError):
            validate_string_length('hi', min_length=3, max_length=10)
        
        with self.assertRaises(ValidationError):
            validate_string_length('very_long_string', min_length=3, max_length=10)
        
        # Test non-string
        with self.assertRaises(ValidationError):
            validate_string_length(123)


if __name__ == '__main__':
    unittest.main()
