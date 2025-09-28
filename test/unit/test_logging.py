"""
Unit tests for logging configuration and functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from src.wildlife_pipeline.logging_config import WildlifeLogger, get_logger, setup_pipeline_logging


class TestWildlifeLogger:
    """Test WildlifeLogger functionality."""
    
    def test_initialization(self):
        """Test logger initialization."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        assert logger.logger.name == "test_logger"
        assert logger.logger.level == 20  # INFO level
    
    def test_basic_logging(self):
        """Test basic logging functionality."""
        logger = WildlifeLogger("test_logger", "DEBUG")
        
        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.info("Test message")
            output = mock_stdout.getvalue()
            
            assert "Test message" in output
            assert "INFO" in output
    
    def test_logging_with_context(self):
        """Test logging with structured context."""
        logger = WildlifeLogger("test_logger", "DEBUG")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.info("Test message", param1="value1", param2=42)
            output = mock_stdout.getvalue()
            
            assert "Test message" in output
            assert "Context:" in output
            assert "param1" in output
            assert "value1" in output
            assert "param2" in output
            assert "42" in output
    
    def test_stage_logging_methods(self):
        """Test stage-specific logging methods."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.log_stage_start("test_stage", param="value")
            output = mock_stdout.getvalue()
            
            assert "🚀 Starting test_stage" in output
            assert "stage" in output
            assert "param" in output
    
    def test_detection_stats_logging(self):
        """Test detection statistics logging."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.log_detection_stats(100, 80, 20, filter_ratio=0.8)
            output = mock_stdout.getvalue()
            
            assert "📊 Detection stats" in output
            assert "100 total" in output
            assert "80 kept" in output
            assert "20 dropped" in output
    
    def test_video_processing_logging(self):
        """Test video processing logging."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.log_video_processing("test.mp4", 50, 10, 30.5)
            output = mock_stdout.getvalue()
            
            assert "🎥 Video processed" in output
            assert "test.mp4" in output
            assert "50 frames" in output
            assert "10 detections" in output
            assert "30.5s" in output
    
    def test_compression_stats_logging(self):
        """Test compression statistics logging."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.log_compression_stats(1000, 100, 10.0)
            output = mock_stdout.getvalue()
            
            assert "🗜️ Compression" in output
            assert "1000 → 100" in output
            assert "10.0x reduction" in output
    
    def test_processing_progress_logging(self):
        """Test processing progress logging."""
        logger = WildlifeLogger("test_logger", "INFO")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.log_processing_progress(25, 100, "images")
            output = mock_stdout.getvalue()
            
            assert "🔄 Processing" in output
            assert "25/100 images" in output
            assert "25.0%" in output
    
    def test_file_logging(self):
        """Test file logging functionality."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_file = Path(f.name)
        
        try:
            logger = WildlifeLogger("test_logger", "INFO", log_file)
            
            logger.info("Test file message")
            
            # Check if file was created and contains message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test file message" in content
            
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_error_logging(self):
        """Test error logging functionality."""
        logger = WildlifeLogger("test_logger", "ERROR")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            logger.error("Test error message", error_code=500)
            output = mock_stdout.getvalue()
            
            assert "ERROR" in output
            assert "Test error message" in output
            assert "error_code" in output
    
    def test_stage_error_logging(self):
        """Test stage error logging."""
        logger = WildlifeLogger("test_logger", "ERROR")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            error = ValueError("Test error")
            logger.log_stage_error("test_stage", error, param="value")
            output = mock_stdout.getvalue()
            
            assert "❌ Error in test_stage" in output
            assert "ValueError" in output
            assert "Test error" in output


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_basic(self):
        """Test basic get_logger functionality."""
        logger = get_logger("test_logger")
        
        assert isinstance(logger, WildlifeLogger)
        assert logger.logger.name == "test_logger"
    
    def test_get_logger_with_level(self):
        """Test get_logger with custom level."""
        logger = get_logger("test_logger", "DEBUG")
        
        assert logger.logger.level == 10  # DEBUG level
    
    def test_get_logger_with_file(self):
        """Test get_logger with log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_file = Path(f.name)
        
        try:
            logger = get_logger("test_logger", "INFO", log_file)
            
            assert isinstance(logger, WildlifeLogger)
            assert logger.logger.name == "test_logger"
            
        finally:
            if log_file.exists():
                log_file.unlink()


class TestSetupPipelineLogging:
    """Test setup_pipeline_logging function."""
    
    def test_setup_pipeline_logging_basic(self):
        """Test basic pipeline logging setup."""
        logger = setup_pipeline_logging("INFO")
        
        assert isinstance(logger, WildlifeLogger)
        assert logger.logger.name == "wildlife_pipeline"
        assert logger.logger.level == 20  # INFO level
    
    def test_setup_pipeline_logging_with_file(self):
        """Test pipeline logging setup with log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            logger = setup_pipeline_logging("DEBUG", log_dir)
            
            assert isinstance(logger, WildlifeLogger)
            assert logger.logger.name == "wildlife_pipeline"
            
            # Check if log file was created
            log_file = log_dir / "wildlife_pipeline.log"
            assert log_file.exists()


class TestLoggingIntegration:
    """Test logging integration with pipeline components."""
    
    def test_stages_logging_integration(self):
        """Test logging integration with stages module."""
        from src.wildlife_pipeline.stages import filter_bboxes
        from src.wildlife_pipeline.detector import Detection
        
        # Create test detections
        detections = [
            Detection(label='moose', confidence=0.9, bbox=[100, 100, 200, 200]),
            Detection(label='boar', confidence=0.3, bbox=[150, 150, 250, 250])
        ]
        
        # Capture logging output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            filtered, dropped = filter_bboxes(
                detections, 800, 600, 0.5, 0.01, 0.8, 0.2, 5.0, 20
            )
            output = mock_stdout.getvalue()
        
        # Check that logging occurred
        assert "🔍 Filtering" in output
        assert "📊 Detection stats" in output
        assert len(filtered) == 1
        assert dropped == 1
    
    def test_video_processor_logging_integration(self):
        """Test logging integration with video processor."""
        from src.wildlife_pipeline.video_processor import VideoProcessor
        from src.wildlife_pipeline.detector import BaseDetector
        
        # Mock detector
        class MockDetector(BaseDetector):
            def predict(self, image_path):
                return []
        
        processor = VideoProcessor(
            detector=MockDetector(),
            sample_interval_seconds=0.3,
            max_frames=10
        )
        
        # Test that logger is initialized
        assert hasattr(processor, 'logger') or hasattr(VideoProcessor, 'logger')
    
    def test_stage3_logging_integration(self):
        """Test logging integration with Stage 3 reporting."""
        from src.wildlife_pipeline.cloud.stage3_reporting import Stage3Reporter
        
        reporter = Stage3Reporter(
            compression_window_minutes=10,
            min_confidence=0.5,
            min_duration_seconds=5.0
        )
        
        # Test that logger is initialized
        assert hasattr(reporter, 'logger') or hasattr(Stage3Reporter, 'logger')


if __name__ == '__main__':
    pytest.main([__file__])
