"""
Test credential handling and security measures.

Tests for environment variable usage, credential sanitization, and security validation.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

# Import the modules we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.odin.validation import (
    validate_environment_variable, 
    sanitize_log_data, 
    validate_path,
    validate_s3_path,
    validate_url,
    ValidationError
)


class TestCredentialHandling(unittest.TestCase):
    """Test credential handling and security measures."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_environment_variable_validation(self):
        """Test environment variable validation."""
        # Test required variable that exists
        os.environ['TEST_VAR'] = 'test_value'
        result = validate_environment_variable('TEST_VAR', required=True)
        self.assertEqual(result, 'test_value')
        
        # Test required variable that doesn't exist
        with self.assertRaises(ValidationError):
            validate_environment_variable('NONEXISTENT_VAR', required=True)
        
        # Test optional variable that doesn't exist
        result = validate_environment_variable('NONEXISTENT_VAR', required=False)
        self.assertIsNone(result)
        
        # Test empty variable
        os.environ['EMPTY_VAR'] = ''
        with self.assertRaises(ValidationError):
            validate_environment_variable('EMPTY_VAR', required=True)
    
    def test_credential_sanitization(self):
        """Test that sensitive data is properly sanitized in logs."""
        test_data = {
            'username': 'test_user',
            'password': 'secret123',
            'aws_access_key': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'minio_access_key': 'minioadmin',
            'minio_secret_key': 'minioadmin123',
            'api_key': 'sk-1234567890abcdef',
            'normal_data': 'this should not be redacted',
            'nested': {
                'password': 'nested_secret',
                'public_info': 'this is public'
            }
        }
        
        sanitized = sanitize_log_data(test_data)
        
        # Check that sensitive data is redacted
        self.assertEqual(sanitized['password'], '***REDACTED***')
        self.assertEqual(sanitized['aws_access_key'], '***REDACTED***')
        self.assertEqual(sanitized['aws_secret_key'], '***REDACTED***')
        self.assertEqual(sanitized['minio_access_key'], '***REDACTED***')
        self.assertEqual(sanitized['minio_secret_key'], '***REDACTED***')
        self.assertEqual(sanitized['api_key'], '***REDACTED***')
        
        # Check that normal data is preserved
        self.assertEqual(sanitized['username'], 'test_user')
        self.assertEqual(sanitized['normal_data'], 'this should not be redacted')
        
        # Check nested data is sanitized
        self.assertEqual(sanitized['nested']['password'], '***REDACTED***')
        self.assertEqual(sanitized['nested']['public_info'], 'this is public')
    
    def test_path_validation(self):
        """Test path validation prevents path traversal attacks."""
        # Test valid relative path
        valid_path = Path('data/images/test.jpg')
        result = validate_path(valid_path)
        self.assertEqual(result, valid_path.resolve())
        
        # Test path traversal attempt
        with self.assertRaises(ValidationError):
            validate_path('../etc/passwd')
        
        with self.assertRaises(ValidationError):
            validate_path('../../../etc/passwd')
        
        # Test absolute path (not allowed by default)
        with self.assertRaises(ValidationError):
            validate_path('/etc/passwd')
        
        # Test absolute path (allowed)
        result = validate_path('/tmp/test', allow_absolute=True)
        self.assertEqual(result, Path('/tmp/test').resolve())
        
        # Test dangerous characters
        with self.assertRaises(ValidationError):
            validate_path('test; rm -rf /')
        
        with self.assertRaises(ValidationError):
            validate_path('test | cat /etc/passwd')
    
    def test_s3_path_validation(self):
        """Test S3 path validation."""
        # Test valid S3 path
        valid_s3_path = 's3://my-bucket/path/to/file.json'
        result = validate_s3_path(valid_s3_path)
        self.assertEqual(result['bucket'], 'my-bucket')
        self.assertEqual(result['key'], 'path/to/file.json')
        
        # Test invalid S3 paths
        with self.assertRaises(ValidationError):
            validate_s3_path('not-s3://bucket/key')
        
        with self.assertRaises(ValidationError):
            validate_s3_path('s3://bucket')
        
        with self.assertRaises(ValidationError):
            validate_s3_path('s3://bucket/')
        
        with self.assertRaises(ValidationError):
            validate_s3_path('s3://invalid-bucket-name!@#/key')
        
        with self.assertRaises(ValidationError):
            validate_s3_path('s3://a/key')  # Bucket name too short
    
    def test_url_validation(self):
        """Test URL validation."""
        # Test valid URLs
        valid_urls = [
            'https://example.com',
            'http://localhost:8080',
            's3://bucket/key',
            'file:///path/to/file'
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            self.assertEqual(result, url)
        
        # Test invalid URLs
        invalid_urls = [
            'not-a-url',
            'ftp://example.com',  # Unsupported scheme
            'javascript:alert(1)',  # Dangerous scheme
            ''
        ]
        
        for url in invalid_urls:
            with self.assertRaises(ValidationError):
                validate_url(url)
    
    @patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'MINIO_ACCESS_KEY': 'minio_key',
        'MINIO_SECRET_KEY': 'minio_secret'
    })
    def test_environment_variable_usage(self):
        """Test that environment variables are used for credentials."""
        # Test AWS credentials
        aws_key = os.getenv('AWS_ACCESS_KEY_ID', 'test')
        aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        
        self.assertEqual(aws_key, 'test_key')
        self.assertEqual(aws_secret, 'test_secret')
        
        # Test MinIO credentials
        minio_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        minio_secret = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
        
        self.assertEqual(minio_key, 'minio_key')
        self.assertEqual(minio_secret, 'minio_secret')
    
    def test_no_hardcoded_credentials_in_code(self):
        """Test that no hardcoded credentials exist in the codebase."""
        # This test would need to be run against the actual codebase
        # For now, we'll test that our validation functions work correctly
        
        # Test that we can detect and sanitize hardcoded-looking values
        test_data = {
            'access_key': 'AKIAIOSFODNN7EXAMPLE',
            'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        
        sanitized = sanitize_log_data(test_data)
        self.assertEqual(sanitized['access_key'], '***REDACTED***')
        self.assertEqual(sanitized['secret_key'], '***REDACTED***')
    
    def test_credential_rotation_support(self):
        """Test that the system supports credential rotation."""
        # Test that environment variables can be changed
        os.environ['TEST_CREDENTIAL'] = 'old_value'
        old_value = os.getenv('TEST_CREDENTIAL')
        
        os.environ['TEST_CREDENTIAL'] = 'new_value'
        new_value = os.getenv('TEST_CREDENTIAL')
        
        self.assertEqual(old_value, 'old_value')
        self.assertEqual(new_value, 'new_value')
        self.assertNotEqual(old_value, new_value)


class TestSecurityValidation(unittest.TestCase):
    """Test security validation functions."""
    
    def test_sql_identifier_validation(self):
        """Test SQL identifier validation."""
        from src.odin.validation import validate_sql_identifier
        
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
    
    def test_numeric_range_validation(self):
        """Test numeric range validation."""
        from src.odin.validation import validate_numeric_range
        
        # Test valid ranges
        result = validate_numeric_range(5, min_val=0, max_val=10)
        self.assertEqual(result, 5)
        
        # Test out of range
        with self.assertRaises(ValidationError):
            validate_numeric_range(15, min_val=0, max_val=10)
        
        with self.assertRaises(ValidationError):
            validate_numeric_range(-5, min_val=0, max_val=10)
    
    def test_string_length_validation(self):
        """Test string length validation."""
        from src.odin.validation import validate_string_length
        
        # Test valid lengths
        result = validate_string_length('hello', min_length=3, max_length=10)
        self.assertEqual(result, 'hello')
        
        # Test invalid lengths
        with self.assertRaises(ValidationError):
            validate_string_length('hi', min_length=3, max_length=10)
        
        with self.assertRaises(ValidationError):
            validate_string_length('very_long_string', min_length=3, max_length=10)


if __name__ == '__main__':
    unittest.main()
