"""
Centralized logging configuration for wildlife detection pipeline.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class WildlifeLogger:
    """Centralized logger for wildlife detection pipeline."""
    
    def __init__(self, name: str, log_level: str = "INFO", log_file: Optional[Path] = None):
        """
        Initialize logger with consistent formatting.
        
        Args:
            name: Logger name (usually module name)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with optional context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with structured context."""
        if kwargs:
            context = json.dumps(kwargs, default=str, indent=None)
            full_message = f"{message} | Context: {context}"
        else:
            full_message = message
        
        self.logger.log(level, full_message)
    
    def log_stage_start(self, stage: str, **kwargs):
        """Log stage start with context."""
        self.info(f"🚀 Starting {stage}", stage=stage, timestamp=datetime.now().isoformat(), **kwargs)
    
    def log_stage_complete(self, stage: str, **kwargs):
        """Log stage completion with context."""
        self.info(f"✅ Completed {stage}", stage=stage, timestamp=datetime.now().isoformat(), **kwargs)
    
    def log_stage_error(self, stage: str, error: Exception, **kwargs):
        """Log stage error with context."""
        self.error(f"❌ Error in {stage}: {str(error)}", 
                  stage=stage, error_type=type(error).__name__, error_message=str(error), **kwargs)
    
    def log_detection_stats(self, total_detections: int, filtered_detections: int, 
                           dropped_detections: int, **kwargs):
        """Log detection statistics."""
        self.info(f"📊 Detection stats: {total_detections} total, {filtered_detections} kept, {dropped_detections} dropped",
                 total_detections=total_detections, filtered_detections=filtered_detections, 
                 dropped_detections=dropped_detections, **kwargs)
    
    def log_processing_progress(self, current: int, total: int, item_type: str = "items", **kwargs):
        """Log processing progress."""
        percentage = (current / total * 100) if total > 0 else 0
        self.info(f"🔄 Processing {current}/{total} {item_type} ({percentage:.1f}%)",
                 current=current, total=total, percentage=percentage, **kwargs)
    
    def log_video_processing(self, video_path: str, frames_extracted: int, 
                            detections_found: int, duration_seconds: float, **kwargs):
        """Log video processing results."""
        self.info(f"🎥 Video processed: {Path(video_path).name} - {frames_extracted} frames, {detections_found} detections, {duration_seconds:.1f}s",
                 video_path=video_path, frames_extracted=frames_extracted, 
                 detections_found=detections_found, duration_seconds=duration_seconds, **kwargs)
    
    def log_compression_stats(self, original_count: int, compressed_count: int, 
                             compression_ratio: float, **kwargs):
        """Log compression statistics."""
        self.info(f"🗜️ Compression: {original_count} → {compressed_count} observations ({compression_ratio:.1f}x reduction)",
                 original_count=original_count, compressed_count=compressed_count, 
                 compression_ratio=compression_ratio, **kwargs)


def get_logger(name: str, log_level: str = "INFO", log_file: Optional[Path] = None) -> WildlifeLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name
        log_level: Logging level
        log_file: Optional log file path
        
    Returns:
        Configured WildlifeLogger instance
    """
    return WildlifeLogger(name, log_level, log_file)


def setup_pipeline_logging(log_level: str = "INFO", log_dir: Optional[Path] = None) -> WildlifeLogger:
    """
    Setup logging for the entire pipeline.
    
    Args:
        log_level: Logging level
        log_dir: Directory for log files
        
    Returns:
        Main pipeline logger
    """
    if log_dir:
        log_file = log_dir / "wildlife_pipeline.log"
    else:
        log_file = None
    
    return get_logger("wildlife_pipeline", log_level, log_file)
