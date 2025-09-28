"""
Centralized logging configuration for the wildlife pipeline.
Provides log4j-equivalent functionality with structured logging.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

import yaml


class LoggingManager:
    """Centralized logging manager for the wildlife pipeline."""

    _initialized = False
    _config_path: Optional[Path] = None

    @classmethod
    def setup_logging(cls, config_path: Optional[Path] = None,
                     log_level: str = "INFO",
                     log_dir: str = "./logs") -> None:
        """
        Initialize centralized logging configuration.

        Args:
            config_path: Path to logging configuration YAML file
            log_level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
        """
        if cls._initialized:
            return

        # Set default config path if not provided
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "conf" / "logging.yaml"

        cls._config_path = config_path

        # Ensure log directories exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        (log_path / "app").mkdir(exist_ok=True)
        (log_path / "debug").mkdir(exist_ok=True)
        (log_path / "error").mkdir(exist_ok=True)
        (log_path / "audit").mkdir(exist_ok=True)

        # Load logging configuration
        if config_path.exists():
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Update log file paths to be relative to project root
            for _handler_name, handler_config in config.get('handlers', {}).items():
                if 'filename' in handler_config:
                    handler_config['filename'] = str(log_path / handler_config['filename'].replace('logs/', ''))

            logging.config.dictConfig(config)
        else:
            # Fallback to basic configuration
            logging.basicConfig(
                level=getattr(logging, log_level.upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler(log_path / "app" / "application.log")
                ]
            )

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.

        Args:
            name: Logger name (typically module name)

        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.setup_logging()

        return logging.getLogger(name)

    @classmethod
    def get_audit_logger(cls) -> logging.Logger:
        """Get the audit logger for security and compliance logging."""
        return cls.get_logger("audit")

    @classmethod
    def get_security_logger(cls) -> logging.Logger:
        """Get the security logger for security-related events."""
        return cls.get_logger("security")

    @classmethod
    def get_infrastructure_logger(cls) -> logging.Logger:
        """Get the infrastructure logger for infrastructure events."""
        return cls.get_logger("infrastructure")


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return LoggingManager.get_logger(name)


def get_audit_logger() -> logging.Logger:
    """Get the audit logger."""
    return LoggingManager.get_audit_logger()


def get_security_logger() -> logging.Logger:
    """Get the security logger."""
    return LoggingManager.get_security_logger()


def get_infrastructure_logger() -> logging.Logger:
    """Get the infrastructure logger."""
    return LoggingManager.get_infrastructure_logger()


class StructuredLogger:
    """Structured logger for consistent log formatting."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_operation(self, operation: str, **kwargs) -> None:
        """Log an operation with structured data."""
        self.logger.info(f"Operation: {operation}", extra={"operation": operation, **kwargs})

    def log_error(self, error: Exception, context: str = "", **kwargs) -> None:
        """Log an error with context."""
        self.logger.error(f"Error in {context}: {str(error)}",
                         extra={"error": str(error), "context": context, **kwargs},
                         exc_info=True)

    def log_security_event(self, event: str, **kwargs) -> None:
        """Log a security event."""
        security_logger = get_security_logger()
        security_logger.warning(f"Security event: {event}", extra={"event": event, **kwargs})

    def log_audit_event(self, action: str, user: str = "system", **kwargs) -> None:
        """Log an audit event."""
        audit_logger = get_audit_logger()
        audit_logger.info(f"Audit: {action} by {user}",
                         extra={"action": action, "user": user, **kwargs})


# Initialize logging on module import
LoggingManager.setup_logging()

