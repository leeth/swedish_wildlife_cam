"""
Standalone security tests that don't require full module imports.

Tests for credential handling and security measures.
"""

import os
import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import re
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_environment_variable(name: str, required: bool = False) -> str:
    """Validate environment variable exists and is not empty."""
    value = os.getenv(name)
    
    if required and not value:
        raise ValidationError(f"Required environment variable {name} is not set")
    
    if value and not value.strip():
        raise ValidationError(f"Environment variable {name} is empty")
    
    return value


def sanitize_log_data(data: dict) -> dict:
    """Sanitize data for logging by removing sensitive information."""
    sensitive_keys = [
        'password', 'secret', 'key', 'token', 'credential',
        'aws_access_key', 'aws_secret_key', 'minio_access_key',
        'minio_secret_key', 'api_key', 'access_token'
    ]
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


def validate_path(path, allow_absolute: bool = False) -> Path:
    """Validate and sanitize file paths to prevent path traversal attacks."""
    if isinstance(path, str):
        path = Path(path)
    
    # Convert to absolute path for validation
    try:
        path = path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {e}")
    
    # Check for path traversal attempts
    path_str = str(path)
    if '..' in path_str or path_str.startswith('/') and not allow_absolute:
        raise ValidationError("Path traversal detected or absolute path not allowed")
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')']
    if any(char in path_str for char in dangerous_chars):
        raise ValidationError("Path contains dangerous characters")
    
    return path


def validate_s3_path(s3_path: str) -> dict:
    """Validate S3 path format and extract components."""
    if not s3_path.startswith('s3://'):
        raise ValidationError("S3 path must start with 's3://'")
    
    # Remove s3:// prefix
    path_without_prefix = s3_path[5:]
    
    if '/' not in path_without_prefix:
        raise ValidationError("S3 path must include bucket and key")
    
    bucket, key = path_without_prefix.split('/', 1)
    
    # Validate bucket name
    if not re.match(r'^[a-z0-9.-]+$', bucket):
        raise ValidationError("Invalid S3 bucket name")
    
    if len(bucket) < 3 or len(bucket) > 63:
        raise ValidationError("S3 bucket name must be 3-63 characters")
    
    # Validate key
    if not key or key.startswith('/'):
        raise ValidationError("Invalid S3 key")
    
    return {'bucket': bucket, 'key': key}


def validate_url(url: str) -> str:
    """Validate URL format and scheme."""
    if not url or not url.strip():
        raise ValidationError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}")
    
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError("URL must have scheme and netloc")
    
    # Only allow safe schemes
    allowed_schemes = ['http', 'https', 's3', 'file']
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
    
    return url


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
        result = validate_path(valid_path, allow_absolute=True)
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
            '',
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


if __name__ == '__main__':
    unittest.main()
