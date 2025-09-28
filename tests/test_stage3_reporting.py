"""
Unit tests for Stage 3 reporting and compression.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.wildlife_pipeline.cloud.stage3_reporting import Stage3Reporter, CompressedObservation
from src.wildlife_pipeline.cloud.interfaces import Stage2Entry, ManifestEntry


class TestStage3Reporter:
    """Test Stage 3 reporter functionality."""
    
    def test_initialization(self):
        """Test Stage3Reporter initialization."""
        reporter = Stage3Reporter(
            compression_window_minutes=10,
            min_confidence=0.5,
            min_duration_seconds=5.0
        )
        
        assert reporter.compression_window == timedelta(minutes=10)
        assert reporter.min_confidence == 0.5
        assert reporter.min_duration_seconds == 5.0
    
    def test_group_observations_by_camera_species(self):
        """Test grouping observations by camera and species."""
        reporter = Stage3Reporter()
        
        # Create test data
        stage2_entries = [
            Stage2Entry(
                crop_path="camera1_frame_000001.jpg",
                label="moose",
                confidence=0.9,
                auto_ok=True,
                stage2_model="yolo_classifier",
                stage1_model="megadetector",
                config_hash="abc123"
            ),
            Stage2Entry(
                crop_path="camera1_frame_000002.jpg", 
                label="moose",
                confidence=0.8,
                auto_ok=True,
                stage2_model="yolo_classifier",
                stage1_model="megadetector",
                config_hash="abc123"
            ),
            Stage2Entry(
                crop_path="camera2_frame_000001.jpg",
                label="boar", 
                confidence=0.7,
                auto_ok=True,
                stage2_model="yolo_classifier",
                stage1_model="megadetector",
                config_hash="abc123"
            )
        ]
        
        manifest_entries = [
            ManifestEntry(
                source_path="camera1/video.mp4",
                crop_path="camera1_frame_000001.jpg",
                camera_id="camera1",
                timestamp="2025-09-07T10:30:00",
                bbox=[100, 100, 200, 200],
                det_score=0.9,
                stage1_model="megadetector",
                config_hash="abc123"
            ),
            ManifestEntry(
                source_path="camera1/video.mp4",
                crop_path="camera1_frame_000002.jpg",
                camera_id="camera1", 
                timestamp="2025-09-07T10:30:30",
                bbox=[150, 150, 250, 250],
                det_score=0.8,
                stage1_model="megadetector",
                config_hash="abc123"
            ),
            ManifestEntry(
                source_path="camera2/video.mp4",
                crop_path="camera2_frame_000001.jpg",
                camera_id="camera2",
                timestamp="2025-09-07T11:00:00", 
                bbox=[200, 200, 300, 300],
                det_score=0.7,
                stage1_model="megadetector",
                config_hash="abc123"
            )
        ]
        
        grouped = reporter._group_observations_by_camera_species(
            stage2_entries, manifest_entries
        )
        
        # Check grouping
        assert len(grouped) == 2  # Two camera-species combinations
        assert ('camera1', 'moose') in grouped
        assert ('camera2', 'boar') in grouped
        
        # Check camera1 moose observations
        camera1_moose = grouped[('camera1', 'moose')]
        assert len(camera1_moose) == 2
        assert camera1_moose[0]['confidence'] == 0.9
        assert camera1_moose[1]['confidence'] == 0.8
        
        # Check camera2 boar observations  
        camera2_boar = grouped[('camera2', 'boar')]
        assert len(camera2_boar) == 1
        assert camera2_boar[0]['confidence'] == 0.7
    
    def test_compress_observations_for_species(self):
        """Test compression of observations for a specific species."""
        reporter = Stage3Reporter(compression_window_minutes=10)
        
        # Create test observations within compression window
        observations = [
            {
                'timestamp': datetime(2025, 9, 7, 10, 30, 0),
                'confidence': 0.9,
                'crop_path': 'camera1_frame_000001.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 1
            },
            {
                'timestamp': datetime(2025, 9, 7, 10, 30, 30),
                'confidence': 0.8,
                'crop_path': 'camera1_frame_000002.jpg',
                'source_path': 'camera1/video.mp4', 
                'is_video': True,
                'frame_number': 2
            },
            {
                'timestamp': datetime(2025, 9, 7, 10, 35, 0),
                'confidence': 0.85,
                'crop_path': 'camera1_frame_000003.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 3
            }
        ]
        
        compressed = reporter._compress_observations_for_species(
            'camera1', 'moose', observations
        )
        
        # Should be compressed into one observation
        assert len(compressed) == 1
        
        obs = compressed[0]
        assert obs.camera_id == 'camera1'
        assert obs.species == 'moose'
        assert obs.frame_count == 3
        assert obs.max_confidence == 0.9
        assert obs.source_video == 'camera1/video.mp4'
        assert obs.duration_seconds == 300  # 5 minutes
    
    def test_compress_observations_separate_windows(self):
        """Test compression with observations in separate time windows."""
        reporter = Stage3Reporter(compression_window_minutes=10)
        
        # Create test observations in separate windows
        observations = [
            {
                'timestamp': datetime(2025, 9, 7, 10, 30, 0),
                'confidence': 0.9,
                'crop_path': 'camera1_frame_000001.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 1
            },
            {
                'timestamp': datetime(2025, 9, 7, 10, 35, 0),
                'confidence': 0.8,
                'crop_path': 'camera1_frame_000002.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 2
            },
            # This one is outside the 10-minute window (15 minutes later)
            {
                'timestamp': datetime(2025, 9, 7, 10, 50, 0),
                'confidence': 0.85,
                'crop_path': 'camera1_frame_000003.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 3
            }
        ]
        
        compressed = reporter._compress_observations_for_species(
            'camera1', 'moose', observations
        )
        
        # Should be compressed into one observation (third frame filtered out due to short duration)
        assert len(compressed) == 1
        
        # First observation (first two frames)
        obs1 = compressed[0]
        assert obs1.frame_count == 2
        assert obs1.duration_seconds == 300  # 5 minutes
    
    def test_minimum_duration_filtering(self):
        """Test filtering of observations below minimum duration."""
        reporter = Stage3Reporter(min_duration_seconds=10.0)
        
        # Create short observation
        observations = [
            {
                'timestamp': datetime(2025, 9, 7, 10, 30, 0),
                'confidence': 0.9,
                'crop_path': 'camera1_frame_000001.jpg',
                'source_path': 'camera1/video.mp4',
                'is_video': True,
                'frame_number': 1
            }
        ]
        
        compressed = reporter._compress_observations_for_species(
            'camera1', 'moose', observations
        )
        
        # Should be filtered out due to short duration
        assert len(compressed) == 0
    
    def test_minimum_confidence_filtering(self):
        """Test filtering of observations below minimum confidence."""
        reporter = Stage3Reporter(min_confidence=0.8)
        
        # Create test data with low confidence
        stage2_entries = [
            Stage2Entry(
                crop_path="camera1_frame_000001.jpg",
                label="moose",
                confidence=0.5,  # Below threshold
                auto_ok=False,
                stage2_model="yolo_classifier",
                stage1_model="megadetector",
                config_hash="abc123"
            )
        ]
        
        manifest_entries = [
            ManifestEntry(
                source_path="camera1/video.mp4",
                crop_path="camera1_frame_000001.jpg",
                camera_id="camera1",
                timestamp="2025-09-07T10:30:00",
                bbox=[100, 100, 200, 200],
                det_score=0.5,
                stage1_model="megadetector",
                config_hash="abc123"
            )
        ]
        
        grouped = reporter._group_observations_by_camera_species(
            stage2_entries, manifest_entries
        )
        
        # Should be filtered out due to low confidence
        assert len(grouped) == 0
    
    def test_generate_report(self):
        """Test report generation."""
        reporter = Stage3Reporter()
        
        # Create test compressed observations
        observations = [
            CompressedObservation(
                camera_id="camera1",
                species="moose",
                start_time=datetime(2025, 9, 7, 10, 30, 0),
                end_time=datetime(2025, 9, 7, 10, 35, 0),
                duration_seconds=300,
                max_confidence=0.9,
                avg_confidence=0.85,
                frame_count=3,
                detection_timeline=[],
                source_video="camera1/video.mp4"
            ),
            CompressedObservation(
                camera_id="camera2",
                species="boar",
                start_time=datetime(2025, 9, 7, 11, 0, 0),
                end_time=datetime(2025, 9, 7, 11, 2, 0),
                duration_seconds=120,
                max_confidence=0.8,
                avg_confidence=0.75,
                frame_count=2,
                detection_timeline=[],
                source_video="camera2/video.mp4"
            )
        ]
        
        report = reporter.generate_report(observations)
        
        assert report['total_observations'] == 2
        assert 'moose' in report['species_summary']
        assert 'boar' in report['species_summary']
        assert 'camera1' in report['camera_summary']
        assert 'camera2' in report['camera_summary']
        assert report['video_observations'] == 2
        assert report['image_observations'] == 0
    
    def test_save_compressed_observations(self):
        """Test saving compressed observations to file."""
        reporter = Stage3Reporter()
        
        observations = [
            CompressedObservation(
                camera_id="camera1",
                species="moose",
                start_time=datetime(2025, 9, 7, 10, 30, 0),
                end_time=datetime(2025, 9, 7, 10, 35, 0),
                duration_seconds=300,
                max_confidence=0.9,
                avg_confidence=0.85,
                frame_count=3,
                detection_timeline=[],
                source_video="camera1/video.mp4"
            )
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            reporter.save_compressed_observations(observations, output_path)
            
            # Check file was created
            assert output_path.exists()
            
            # Check content
            import json
            with open(output_path) as f:
                data = json.load(f)
            
            assert len(data) == 1
            assert data[0]['camera_id'] == 'camera1'
            assert data[0]['species'] == 'moose'
            assert data[0]['duration_seconds'] == 300
            
        finally:
            if output_path.exists():
                output_path.unlink()


class TestCompressedObservation:
    """Test CompressedObservation dataclass."""
    
    def test_compressed_observation_creation(self):
        """Test creating a CompressedObservation."""
        obs = CompressedObservation(
            camera_id="camera1",
            species="moose",
            start_time=datetime(2025, 9, 7, 10, 30, 0),
            end_time=datetime(2025, 9, 7, 10, 35, 0),
            duration_seconds=300,
            max_confidence=0.9,
            avg_confidence=0.85,
            frame_count=3,
            detection_timeline=[],
            source_video="camera1/video.mp4",
            needs_review=False
        )
        
        assert obs.camera_id == "camera1"
        assert obs.species == "moose"
        assert obs.duration_seconds == 300
        assert obs.max_confidence == 0.9
        assert obs.avg_confidence == 0.85
        assert obs.frame_count == 3
        assert obs.source_video == "camera1/video.mp4"
        assert obs.needs_review == False


if __name__ == '__main__':
    pytest.main([__file__])
