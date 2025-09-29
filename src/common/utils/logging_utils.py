"""
Logging utility functions.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
import time


def setup_logging(level: str = "INFO", 
                 log_file: Optional[Union[str, Path]] = None,
                 format_string: Optional[str] = None) -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level
        log_file: Optional log file path
        format_string: Custom format string
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[]
    )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter(format_string)
    console_handler.setFormatter(console_formatter)
    logging.getLogger().addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_processing_start(logger: logging.Logger, 
                        operation: str,
                        input_path: Optional[Union[str, Path]] = None) -> None:
    """Log the start of a processing operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        input_path: Optional input file path
    """
    message = f"Starting {operation}"
    if input_path:
        message += f" on {input_path}"
    logger.info(message)


def log_processing_end(logger: logging.Logger,
                      operation: str,
                      duration: float,
                      success: bool = True,
                      output_path: Optional[Union[str, Path]] = None) -> None:
    """Log the end of a processing operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Processing duration in seconds
        success: Whether the operation was successful
        output_path: Optional output file path
    """
    status = "completed" if success else "failed"
    message = f"{operation} {status} in {duration:.2f}s"
    if output_path:
        message += f" -> {output_path}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)


class ProcessingTimer:
    """Context manager for timing processing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        """Initialize the timer.
        
        Args:
            logger: Logger instance
            operation: Name of the operation
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None
        
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        log_processing_start(self.logger, self.operation)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results."""
        if self.start_time:
            duration = time.time() - self.start_time
            success = exc_type is None
            log_processing_end(self.logger, self.operation, duration, success)
