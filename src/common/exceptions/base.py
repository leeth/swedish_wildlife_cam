"""
Base exceptions for the wildlife pipeline.
"""


class WildlifePipelineError(Exception):
    """Base exception for all wildlife pipeline errors."""

    def __init__(self, message: str, error_code: str = None):
        """Initialize the exception.

        Args:
            message: Error message
            error_code: Optional error code for categorization
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(WildlifePipelineError):
    """Raised when there's a configuration error."""
    pass


class ProcessingError(WildlifePipelineError):
    """Raised when processing fails."""
    pass


class ValidationError(WildlifePipelineError):
    """Raised when validation fails."""
    pass
