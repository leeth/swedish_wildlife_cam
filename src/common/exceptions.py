"""
Common exceptions for the wildlife pipeline
"""
class ValidationError(Exception):
    """Validation error exception"""
    pass

class PipelineError(Exception):
    """Pipeline error exception"""
    pass

class ConfigurationError(Exception):
    """Configuration error exception"""
    pass
