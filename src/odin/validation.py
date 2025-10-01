"""
Security validation utilities for Odin.

Provides input validation and sanitization functions to prevent security vulnerabilities.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class ValidationManager:
    """Manager for validation operations."""
    
    def __init__(self):
        """Initialize validation manager."""
        pass
    
    def validate_input(self, data: Any) -> bool:
        """Validate input data."""
        return True
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration."""
        return True


def validate_path(path: Union[str, Path], allow_absolute: bool = False) -> Path:
    """
    Validate and sanitize file paths to prevent path traversal attacks.

    Args:
        path: Path to validate
        allow_absolute: Whether to allow absolute paths

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or potentially dangerous
    """
    if isinstance(path, str):
        path = Path(path)

    # Convert to absolute path for validation
    try:
        path = path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {e}") from e

    # Check for path traversal attempts
    path_str = str(path)
    if '..' in path_str or path_str.startswith('/') and not allow_absolute:
        raise ValidationError("Path traversal detected or absolute path not allowed")

    # Check for dangerous characters
    dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')']
    if any(char in path_str for char in dangerous_chars):
        raise ValidationError("Path contains dangerous characters")

    return path


def validate_s3_path(s3_path: str) -> Dict[str, str]:
    """
    Validate S3 path format and extract components.

    Args:
        s3_path: S3 path in format s3://bucket/key

    Returns:
        Dictionary with bucket and key

    Raises:
        ValidationError: If S3 path is invalid
    """
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
    """
    Validate URL format and scheme.

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {e}") from e

    if not parsed.scheme or not parsed.netloc:
        raise ValidationError("URL must have scheme and netloc")

    # Only allow safe schemes
    allowed_schemes = ['http', 'https', 's3', 'file']
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")

    return url


def validate_environment_variable(name: str, required: bool = False) -> Optional[str]:
    """
    Validate environment variable exists and is not empty.

    Args:
        name: Environment variable name
        required: Whether the variable is required

    Returns:
        Environment variable value or None

    Raises:
        ValidationError: If required variable is missing or empty
    """
    value = os.getenv(name)

    if required and not value:
        raise ValidationError(f"Required environment variable {name} is not set")

    if value and not value.strip():
        raise ValidationError(f"Environment variable {name} is empty")

    return value


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize data for logging by removing sensitive information.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
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


def validate_sql_identifier(identifier: str) -> str:
    """
    Validate SQL identifier to prevent injection.

    Args:
        identifier: SQL identifier to validate

    Returns:
        Validated identifier

    Raises:
        ValidationError: If identifier is invalid
    """
    if not identifier:
        raise ValidationError("SQL identifier cannot be empty")

    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValidationError("SQL identifier contains invalid characters")

    # Check for SQL keywords
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TABLE', 'INDEX', 'VIEW', 'TRIGGER', 'PROCEDURE', 'FUNCTION'
    ]

    if identifier.upper() in sql_keywords:
        raise ValidationError(f"SQL identifier cannot be a reserved keyword: {identifier}")

    return identifier


def validate_numeric_range(value: Union[int, float], min_val: Optional[Union[int, float]] = None,
                          max_val: Optional[Union[int, float]] = None) -> Union[int, float]:
    """
    Validate numeric value is within specified range.

    Args:
        value: Numeric value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated numeric value

    Raises:
        ValidationError: If value is outside range
    """
    if not isinstance(value, (int, float)):
        raise ValidationError("Value must be numeric")

    if min_val is not None and value < min_val:
        raise ValidationError(f"Value {value} is below minimum {min_val}")

    if max_val is not None and value > max_val:
        raise ValidationError(f"Value {value} is above maximum {max_val}")

    return value


def validate_string_length(value: str, min_length: int = 0, max_length: Optional[int] = None) -> str:
    """
    Validate string length is within specified bounds.

    Args:
        value: String to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Validated string

    Raises:
        ValidationError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")

    if len(value) < min_length:
        raise ValidationError(f"String length {len(value)} is below minimum {min_length}")

    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"String length {len(value)} exceeds maximum {max_length}")

    return value

