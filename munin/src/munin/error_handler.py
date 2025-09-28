"""
Error handling and retry logic for wildlife detection pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict, Type, Union
import time
import functools
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Error context information."""
    error_type: str
    severity: ErrorSeverity
    message: str
    operation: str
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None


class PipelineError(Exception):
    """Base pipeline error."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context


class DatabaseError(PipelineError):
    """Database operation error."""
    pass


class StorageError(PipelineError):
    """Storage operation error."""
    pass


class NetworkError(PipelineError):
    """Network operation error."""
    pass


class ModelError(PipelineError):
    """Model operation error."""
    pass


class ValidationError(PipelineError):
    """Data validation error."""
    pass


class ErrorHandler(ABC):
    """Abstract error handler."""
    
    @abstractmethod
    def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Handle an error and return whether to retry."""
        pass
    
    @abstractmethod
    def should_retry(self, error: Exception, context: ErrorContext) -> bool:
        """Determine if an error should be retried."""
        pass


class DefaultErrorHandler(ErrorHandler):
    """Default error handler with retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, 
                 backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        
        # Error type to severity mapping
        self.error_severity_map = {
            ValidationError: ErrorSeverity.HIGH,
            DatabaseError: ErrorSeverity.HIGH,
            StorageError: ErrorSeverity.MEDIUM,
            NetworkError: ErrorSeverity.LOW,
            ModelError: ErrorSeverity.MEDIUM,
        }
        
        # Retryable error types
        self.retryable_errors = {
            NetworkError,
            StorageError,
            DatabaseError
        }
    
    def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Handle an error and return whether to retry."""
        # Log error
        self._log_error(error, context)
        
        # Check if should retry
        if self.should_retry(error, context):
            return True
        
        # Handle non-retryable errors
        self._handle_non_retryable_error(error, context)
        return False
    
    def should_retry(self, error: Exception, context: ErrorContext) -> bool:
        """Determine if an error should be retried."""
        # Check retry count
        if context.retry_count >= context.max_retries:
            return False
        
        # Check if error type is retryable
        error_type = type(error)
        if error_type not in self.retryable_errors:
            return False
        
        # Check severity
        severity = self.error_severity_map.get(error_type, ErrorSeverity.MEDIUM)
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        return True
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """Log error information."""
        print(f"Error in {context.operation}: {error}")
        print(f"  Type: {type(error).__name__}")
        print(f"  Severity: {context.severity.value}")
        print(f"  Retry: {context.retry_count}/{context.max_retries}")
        if context.metadata:
            print(f"  Metadata: {context.metadata}")
    
    def _handle_non_retryable_error(self, error: Exception, context: ErrorContext):
        """Handle non-retryable errors."""
        print(f"Non-retryable error in {context.operation}: {error}")
        # Could implement alerting, logging to external systems, etc.


def retry_on_error(max_retries: int = 3, retry_delay: float = 1.0, 
                   backoff_factor: float = 2.0, error_handler: Optional[ErrorHandler] = None):
    """Decorator for retrying functions on error."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or DefaultErrorHandler(max_retries, retry_delay, backoff_factor)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context = ErrorContext(
                        error_type=type(e).__name__,
                        severity=ErrorSeverity.MEDIUM,
                        message=str(e),
                        operation=func.__name__,
                        retry_count=attempt,
                        max_retries=max_retries,
                        metadata={'args': str(args), 'kwargs': str(kwargs)}
                    )
                    
                    if not handler.handle_error(e, context):
                        raise e
                    
                    # Wait before retry
                    if attempt < max_retries:
                        delay = retry_delay * (backoff_factor ** attempt)
                        time.sleep(delay)
            
            # Should not reach here
            raise Exception(f"Max retries exceeded for {func.__name__}")
        
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


def create_error_handler(handler_type: str = "default", **kwargs) -> ErrorHandler:
    """Factory function to create error handlers."""
    if handler_type == "default":
        return DefaultErrorHandler(**kwargs)
    else:
        raise ValueError(f"Unsupported error handler type: {handler_type}")


# Specific error handlers for different components
class DatabaseErrorHandler(DefaultErrorHandler):
    """Database-specific error handler."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.retryable_errors.add(DatabaseError)
        self.error_severity_map[DatabaseError] = ErrorSeverity.HIGH


class StorageErrorHandler(DefaultErrorHandler):
    """Storage-specific error handler."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.retryable_errors.add(StorageError)
        self.error_severity_map[StorageError] = ErrorSeverity.MEDIUM


class NetworkErrorHandler(DefaultErrorHandler):
    """Network-specific error handler."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.retryable_errors.add(NetworkError)
        self.error_severity_map[NetworkError] = ErrorSeverity.LOW
