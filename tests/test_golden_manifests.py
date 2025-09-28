"""
Golden manifest tests for wildlife pipeline.

This module provides tests that validate the structure and content
of pipeline artifacts against known good examples (golden manifests).
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import pytest
import pandas as pd
import polars as pl

from src.wildlife_pipeline.data_contracts import (
    ManifestEntry, Stage2Entry, ObservationRecord, 
    CompressedObservation, PipelineConfig
)
from src.wildlife_pipeline.analytics_engine import AnalyticsEngine


class TestGoldenManifests:
    """Test golden manifest structures and validation."""
    
    @pytest.fixture
    def sample_manifest_entries(self) -> List[Dict[str, Any]]:
        """Sample manifest entries for testing."""
        return [
            {
                "source_path": "/data/camera1/IMG_001.jpg",
                "crop_path": "/data/crops/camera1_2025-09-07T10:30:00_0_moose_0.85.jpg",
                "camera_id": "camera1",
                "timestamp": "2025-09-07T10:30:00Z",
                "bbox": [100.0, 150.0, 300.0, 400.0],
                "det_score": 0.85,
                "stage1_model": "yolov8n_wildlife.pt",
                "config_hash": "abc123def456"
            },
            {
                "source_path": "/data/camera1/IMG_002.jpg", 
                "crop_path": "/data/crops/camera1_2025-09-07T10:35:00_1_boar_0.92.jpg",
                "camera_id": "camera1",
                "timestamp": "2025-09-07T10:35:00Z",
                "bbox": [200.0, 250.0, 450.0, 500.0],
                "det_score": 0.92,
                "stage1_model": "yolov8n_wildlife.pt",
                "config_hash": "abc123def456"
            }
        ]
    
    @pytest.fixture
    def sample_stage2_entries(self) -> List[Dict[str, Any]]:
        """Sample stage 2 entries for testing."""
        return [
            {
                "crop_path": "/data/crops/camera1_2025-09-07T10:30:00_0_moose_0.85.jpg",
                "label": "moose",
                "confidence": 0.88,
                "auto_ok": True,
                "stage2_model": "yolov8n_classifier.pt",
                "stage1_model": "yolov8n_wildlife.pt",
                "config_hash": "abc123def456",
                "processing_time_ms": 45.2
            },
            {
                "crop_path": "/data/crops/camera1_2025-09-07T10:35:00_1_boar_0.92.jpg",
                "label": "boar",
                "confidence": 0.95,
                "auto_ok": True,
                "stage2_model": "yolov8n_classifier.pt",
                "stage1_model": "yolov8n_wildlife.pt",
                "config_hash": "abc123def456",
                "processing_time_ms": 42.1
            }
        ]
    
    @pytest.fixture
    def sample_observation_records(self) -> List[Dict[str, Any]]:
        """Sample observation records for testing."""
        return [
            {
                "observation_id": "obs-001",
                "image_path": "/data/camera1/IMG_001.jpg",
                "camera_id": "camera1",
                "timestamp": "2025-09-07T10:30:00Z",
                "gps": {
                    "latitude": 59.3293,
                    "longitude": 18.0686,
                    "accuracy": 5.0,
                    "source": "exif"
                },
                "observations": [
                    {
                        "label": "moose",
                        "confidence": 0.88,
                        "bbox_x1": 100.0,
                        "bbox_y1": 150.0,
                        "bbox_x2": 300.0,
                        "bbox_y2": 400.0,
                        "stage1_model": "yolov8n_wildlife.pt",
                        "stage1_confidence": 0.85,
                        "stage2_model": "yolov8n_classifier.pt",
                        "stage2_confidence": 0.88
                    }
                ],
                "top_label": "moose",
                "top_confidence": 0.88,
                "needs_review": False,
                "pipeline_version": "0.1.0",
                "model_hashes": {
                    "stage1": "abc123def456",
                    "stage2": "def456ghi789"
                },
                "source_etag": "etag-001",
                "processing_metadata": {
                    "processing_time_ms": 45.2,
                    "gpu_used": True
                }
            }
        ]
    
    def test_manifest_entry_validation(self, sample_manifest_entries):
        """Test manifest entry validation against golden structure."""
        for entry_data in sample_manifest_entries:
            # Test Pydantic validation
            entry = ManifestEntry(**entry_data)
            
            # Validate required fields
            assert entry.source_path is not None
            assert entry.crop_path is not None
            assert entry.camera_id is not None
            assert entry.timestamp is not None
            assert len(entry.bbox) == 4
            assert 0 <= entry.det_score <= 1
            assert entry.stage1_model is not None
            assert entry.config_hash is not None
            
            # Validate bbox coordinates
            x1, y1, x2, y2 = entry.bbox
            assert x2 > x1
            assert y2 > y1
            assert all(coord >= 0 for coord in entry.bbox)
    
    def test_stage2_entry_validation(self, sample_stage2_entries):
        """Test stage 2 entry validation against golden structure."""
        for entry_data in sample_stage2_entries:
            # Test Pydantic validation
            entry = Stage2Entry(**entry_data)
            
            # Validate required fields
            assert entry.crop_path is not None
            assert entry.label is not None
            assert 0 <= entry.confidence <= 1
            assert isinstance(entry.auto_ok, bool)
            assert entry.stage2_model is not None
            assert entry.stage1_model is not None
            assert entry.config_hash is not None
    
    def test_observation_record_validation(self, sample_observation_records):
        """Test observation record validation against golden structure."""
        for record_data in sample_observation_records:
            # Test Pydantic validation
            record = ObservationRecord(**record_data)
            
            # Validate required fields
            assert record.observation_id is not None
            assert record.image_path is not None
            assert record.camera_id is not None
            assert record.timestamp is not None
            assert record.pipeline_version is not None
            assert record.model_hashes is not None
            
            # Validate GPS if present
            if record.gps:
                assert -90 <= record.gps.latitude <= 90
                assert -180 <= record.gps.longitude <= 180
            
            # Validate observations
            for obs in record.observations:
                assert obs.label is not None
                assert 0 <= obs.confidence <= 1
                assert obs.stage1_model is not None
                assert obs.stage2_model is not None
    
    def test_manifest_jsonl_structure(self, sample_manifest_entries):
        """Test manifest JSONL file structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Write sample entries
            for entry in sample_manifest_entries:
                f.write(json.dumps(entry) + '\n')
            f.flush()
            
            # Read and validate
            with open(f.name, 'r') as rf:
                lines = rf.readlines()
                assert len(lines) == len(sample_manifest_entries)
                
                for i, line in enumerate(lines):
                    entry_data = json.loads(line.strip())
                    entry = ManifestEntry(**entry_data)
                    assert entry.camera_id == sample_manifest_entries[i]["camera_id"]
    
    def test_parquet_schema_validation(self, sample_observation_records):
        """Test Parquet schema validation."""
        # Create DataFrame
        df = pd.DataFrame(sample_observation_records)
        
        # Validate schema
        required_columns = [
            'observation_id', 'image_path', 'camera_id', 'timestamp',
            'top_label', 'top_confidence', 'needs_review', 'pipeline_version'
        ]
        
        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"
        
        # Validate data types
        assert df['camera_id'].dtype == 'object'
        assert df['timestamp'].dtype == 'object'  # datetime
        assert df['top_confidence'].dtype in ['float64', 'float32']
        assert df['needs_review'].dtype == 'bool'
    
    def test_polars_schema_validation(self, sample_observation_records):
        """Test Polars schema validation."""
        # Create Polars DataFrame
        df = pl.DataFrame(sample_observation_records)
        
        # Validate schema
        required_columns = [
            'observation_id', 'image_path', 'camera_id', 'timestamp',
            'top_label', 'top_confidence', 'needs_review', 'pipeline_version'
        ]
        
        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"
        
        # Validate data types
        assert df['camera_id'].dtype == pl.Utf8
        assert df['timestamp'].dtype == pl.Utf8  # datetime
        assert df['top_confidence'].dtype in [pl.Float64, pl.Float32]
        assert df['needs_review'].dtype == pl.Boolean
    
    def test_analytics_engine_schema(self, sample_observation_records):
        """Test analytics engine schema handling."""
        engine = AnalyticsEngine()
        
        # Convert to Polars
        df = pl.DataFrame(sample_observation_records)
        
        # Test schema validation
        assert 'camera_id' in df.columns
        assert 'top_label' in df.columns
        assert 'timestamp' in df.columns
        
        # Test analytics operations
        species_counts = df.group_by("top_label").agg([
            pl.col("observation_id").count().alias("count")
        ])
        
        assert len(species_counts) > 0
        assert 'count' in species_counts.columns
    
    def test_pipeline_config_validation(self):
        """Test pipeline configuration validation."""
        config = PipelineConfig(
            stage1_confidence=0.3,
            min_relative_area=0.003,
            max_relative_area=0.8,
            min_aspect_ratio=0.2,
            max_aspect_ratio=5.0,
            edge_margin_px=12,
            crop_padding=0.15,
            stage2_confidence=0.5,
            compression_window_minutes=10,
            min_duration_seconds=5.0
        )
        
        # Validate configuration values
        assert 0 <= config.stage1_confidence <= 1
        assert 0 <= config.min_relative_area <= 1
        assert 0 <= config.max_relative_area <= 1
        assert config.max_relative_area > config.min_relative_area
        assert config.max_aspect_ratio > config.min_aspect_ratio
        assert config.edge_margin_px >= 0
        assert 0 <= config.crop_padding <= 1
        assert 0 <= config.stage2_confidence <= 1
        assert config.compression_window_minutes > 0
        assert config.min_duration_seconds >= 0
    
    def test_compressed_observation_validation(self):
        """Test compressed observation validation."""
        compressed = CompressedObservation(
            camera_id="camera1",
            species="moose",
            start_time=datetime(2025, 9, 7, 10, 30, 0),
            end_time=datetime(2025, 9, 7, 10, 40, 0),
            duration_seconds=600.0,
            max_confidence=0.95,
            avg_confidence=0.88,
            frame_count=20,
            timeline=[
                {"timestamp": "2025-09-07T10:30:00Z", "confidence": 0.85},
                {"timestamp": "2025-09-07T10:35:00Z", "confidence": 0.95},
                {"timestamp": "2025-09-07T10:40:00Z", "confidence": 0.88}
            ]
        )
        
        # Validate compressed observation
        assert compressed.camera_id is not None
        assert compressed.species is not None
        assert compressed.end_time > compressed.start_time
        assert compressed.duration_seconds > 0
        assert 0 <= compressed.max_confidence <= 1
        assert 0 <= compressed.avg_confidence <= 1
        assert compressed.frame_count > 0
        assert len(compressed.timeline) > 0
    
    def test_golden_manifest_consistency(self, sample_manifest_entries, sample_stage2_entries):
        """Test consistency between manifest and stage2 entries."""
        # Check that crop paths match
        manifest_crops = {entry["crop_path"] for entry in sample_manifest_entries}
        stage2_crops = {entry["crop_path"] for entry in sample_stage2_entries}
        
        # All stage2 entries should have corresponding manifest entries
        assert stage2_crops.issubset(manifest_crops)
        
        # Check model consistency
        for manifest_entry in sample_manifest_entries:
            for stage2_entry in sample_stage2_entries:
                if manifest_entry["crop_path"] == stage2_entry["crop_path"]:
                    assert manifest_entry["stage1_model"] == stage2_entry["stage1_model"]
                    assert manifest_entry["config_hash"] == stage2_entry["config_hash"]
    
    def test_data_contract_serialization(self, sample_observation_records):
        """Test data contract serialization and deserialization."""
        # Test JSON serialization
        for record_data in sample_observation_records:
            record = ObservationRecord(**record_data)
            
            # Serialize to JSON
            json_str = record.json()
            assert isinstance(json_str, str)
            
            # Deserialize from JSON
            parsed_record = ObservationRecord.parse_raw(json_str)
            assert parsed_record.observation_id == record.observation_id
            assert parsed_record.camera_id == record.camera_id
            assert parsed_record.top_label == record.top_label
    
    def test_validation_error_handling(self):
        """Test validation error handling for invalid data."""
        # Test invalid bbox
        with pytest.raises(ValueError):
            ManifestEntry(
                source_path="/data/test.jpg",
                crop_path="/data/crop.jpg",
                camera_id="camera1",
                timestamp=datetime.now(),
                bbox=[300.0, 150.0, 100.0, 400.0],  # Invalid: x2 < x1
                det_score=0.85,
                stage1_model="model.pt",
                config_hash="hash123"
            )
        
        # Test invalid confidence
        with pytest.raises(ValueError):
            Stage2Entry(
                crop_path="/data/crop.jpg",
                label="moose",
                confidence=1.5,  # Invalid: > 1
                auto_ok=True,
                stage2_model="model.pt",
                stage1_model="model.pt",
                config_hash="hash123"
            )
        
        # Test invalid GPS coordinates
        with pytest.raises(ValueError):
            from src.wildlife_pipeline.data_contracts import GPSCoordinates
            GPSCoordinates(
                latitude=95.0,  # Invalid: > 90
                longitude=0.0,
                source="test"
            )
