"""
Unit tests for Parquet to SQLite conversion tool.
"""

import pytest
import tempfile
import sqlite3
import pandas as pd
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.wildlife_pipeline.tools.parquet_to_sqlite import (
    convert_parquet_to_sqlite, query_database, create_observations_table
)


class TestParquetToSQLite:
    """Test Parquet to SQLite conversion."""
    
    def test_create_observations_table(self):
        """Test table creation."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table
            create_observations_table(cursor)
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'")
            result = cursor.fetchone()
            assert result is not None
            
            # Check if indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = cursor.fetchall()
            assert len(indexes) >= 5  # Should have at least 5 indexes
            
            conn.close()
            
        finally:
            Path(db_path).unlink()
    
    def test_convert_parquet_to_sqlite(self):
        """Test Parquet to SQLite conversion."""
        # Create test data
        test_data = {
            'image_path': ['image1.jpg', 'image2.jpg', 'image3.jpg'],
            'camera_id': ['camera1', 'camera2', 'camera1'],
            'timestamp': ['2025-09-07T10:30:00', '2025-09-07T11:00:00', '2025-09-07T12:00:00'],
            'latitude': [59.3293, 59.3293, 59.3293],
            'longitude': [18.0686, 18.0686, 18.0686],
            'observation_any': [True, False, True],
            'observations': [
                [{'label': 'moose', 'confidence': 0.9, 'bbox': [100, 100, 200, 200]}],
                [],
                [{'label': 'boar', 'confidence': 0.8, 'bbox': [150, 150, 250, 250]}]
            ],
            'top_label': ['moose', None, 'boar'],
            'top_confidence': [0.9, None, 0.8],
            'needs_review': [False, False, True],
            'pipeline_version': ['1.0.0', '1.0.0', '1.0.0'],
            'model_hashes': [{'stage1': 'abc123', 'stage2': 'def456'}, {'stage1': 'abc123', 'stage2': 'def456'}, {'stage1': 'abc123', 'stage2': 'def456'}],
            'source_etag': ['etag1', 'etag2', 'etag3']
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create Parquet file
            df = pd.DataFrame(test_data)
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite
            convert_parquet_to_sqlite(parquet_path, sqlite_path)
            
            # Verify SQLite database
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM observations")
            count = cursor.fetchone()[0]
            assert count == 3
            
            # Check specific data
            cursor.execute("SELECT image_path, camera_id, observation_any FROM observations WHERE image_path = 'image1.jpg'")
            result = cursor.fetchone()
            assert result == ('image1.jpg', 'camera1', True)
            
            # Check JSON fields
            cursor.execute("SELECT observations FROM observations WHERE image_path = 'image1.jpg'")
            observations_json = cursor.fetchone()[0]
            observations = json.loads(observations_json)
            assert len(observations) == 1
            assert observations[0]['label'] == 'moose'
            assert observations[0]['confidence'] == 0.9
            
            conn.close()
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()
    
    def test_convert_parquet_to_sqlite_with_batch_size(self):
        """Test conversion with custom batch size."""
        # Create larger test dataset
        test_data = {
            'image_path': [f'image{i}.jpg' for i in range(2500)],
            'camera_id': [f'camera{i % 5}' for i in range(2500)],
            'timestamp': ['2025-09-07T10:30:00'] * 2500,
            'latitude': [59.3293] * 2500,
            'longitude': [18.0686] * 2500,
            'observation_any': [i % 2 == 0 for i in range(2500)],
            'observations': [[] for _ in range(2500)],
            'top_label': [None] * 2500,
            'top_confidence': [None] * 2500,
            'needs_review': [False] * 2500,
            'pipeline_version': ['1.0.0'] * 2500,
            'model_hashes': [{'stage1': 'abc123', 'stage2': 'def456'}] * 2500,
            'source_etag': [f'etag{i}' for i in range(2500)]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create Parquet file
            df = pd.DataFrame(test_data)
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite with small batch size
            convert_parquet_to_sqlite(parquet_path, sqlite_path, batch_size=500)
            
            # Verify SQLite database
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM observations")
            count = cursor.fetchone()[0]
            assert count == 2500
            
            # Check batch processing worked
            cursor.execute("SELECT COUNT(DISTINCT camera_id) FROM observations")
            camera_count = cursor.fetchone()[0]
            assert camera_count == 5
            
            conn.close()
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()
    
    def test_convert_parquet_to_sqlite_missing_file(self):
        """Test conversion with missing input file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            with pytest.raises(FileNotFoundError):
                convert_parquet_to_sqlite("nonexistent.parquet", sqlite_path)
                
        finally:
            Path(sqlite_path).unlink()
    
    def test_convert_parquet_to_sqlite_empty_dataframe(self):
        """Test conversion with empty DataFrame."""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create empty Parquet file
            df = pd.DataFrame()
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite
            convert_parquet_to_sqlite(parquet_path, sqlite_path)
            
            # Verify SQLite database
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM observations")
            count = cursor.fetchone()[0]
            assert count == 0
            
            conn.close()
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()
    
    def test_convert_parquet_to_sqlite_with_nulls(self):
        """Test conversion with null values."""
        test_data = {
            'image_path': ['image1.jpg', 'image2.jpg'],
            'camera_id': ['camera1', None],
            'timestamp': ['2025-09-07T10:30:00', None],
            'latitude': [59.3293, None],
            'longitude': [18.0686, None],
            'observation_any': [True, False],
            'observations': [
                [{'label': 'moose', 'confidence': 0.9}],
                None
            ],
            'top_label': ['moose', None],
            'top_confidence': [0.9, None],
            'needs_review': [False, True],
            'pipeline_version': ['1.0.0', '1.0.0'],
            'model_hashes': [{'stage1': 'abc123'}, None],
            'source_etag': ['etag1', None]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create Parquet file
            df = pd.DataFrame(test_data)
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite
            convert_parquet_to_sqlite(parquet_path, sqlite_path)
            
            # Verify SQLite database
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM observations")
            count = cursor.fetchone()[0]
            assert count == 2
            
            # Check null handling
            cursor.execute("SELECT camera_id, timestamp, latitude FROM observations WHERE image_path = 'image2.jpg'")
            result = cursor.fetchone()
            assert result == (None, None, None)
            
            conn.close()
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()


class TestQueryDatabase:
    """Test database querying functionality."""
    
    def test_query_database(self):
        """Test querying the database."""
        # Create test data
        test_data = {
            'image_path': ['image1.jpg', 'image2.jpg', 'image3.jpg'],
            'camera_id': ['camera1', 'camera2', 'camera1'],
            'timestamp': ['2025-09-07T10:30:00', '2025-09-07T11:00:00', '2025-09-07T12:00:00'],
            'latitude': [59.3293, 59.3293, 59.3293],
            'longitude': [18.0686, 18.0686, 18.0686],
            'observation_any': [True, False, True],
            'observations': [
                [{'label': 'moose', 'confidence': 0.9}],
                [],
                [{'label': 'boar', 'confidence': 0.8}]
            ],
            'top_label': ['moose', None, 'boar'],
            'top_confidence': [0.9, None, 0.8],
            'needs_review': [False, False, True],
            'pipeline_version': ['1.0.0', '1.0.0', '1.0.0'],
            'model_hashes': [{'stage1': 'abc123'}] * 3,
            'source_etag': ['etag1', 'etag2', 'etag3']
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create Parquet file
            df = pd.DataFrame(test_data)
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite
            convert_parquet_to_sqlite(parquet_path, sqlite_path)
            
            # Test queries
            queries = [
                "SELECT COUNT(*) FROM observations",
                "SELECT camera_id, COUNT(*) FROM observations GROUP BY camera_id",
                "SELECT * FROM observations WHERE observation_any = 1",
                "SELECT * FROM observations WHERE needs_review = 1"
            ]
            
            for query in queries:
                # Should not raise exception
                query_database(sqlite_path, query)
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()
    
    def test_query_database_invalid_query(self):
        """Test querying with invalid SQL."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create empty database
            conn = sqlite3.connect(sqlite_path)
            conn.close()
            
            # Test invalid query
            query_database(sqlite_path, "INVALID SQL QUERY")
            
        finally:
            Path(sqlite_path).unlink()
    
    def test_query_database_missing_database(self):
        """Test querying with missing database."""
        with pytest.raises(Exception):  # SQLite will create the database, so we expect a different error
            query_database("nonexistent.db", "SELECT * FROM observations")


class TestParquetToSQLiteIntegration:
    """Test integration between Parquet and SQLite conversion."""
    
    def test_full_conversion_workflow(self):
        """Test complete conversion workflow."""
        # Create comprehensive test data
        test_data = {
            'image_path': [f'camera{i//10}/image{j}.jpg' for i in range(100) for j in range(10)],
            'camera_id': [f'camera{i//10}' for i in range(100) for j in range(10)],
            'timestamp': [f'2025-09-07T{10+i//10:02d}:{30+j:02d}:00' for i in range(100) for j in range(10)],
            'latitude': [59.3293 + (i % 10) * 0.001 for i in range(100) for j in range(10)],
            'longitude': [18.0686 + (i % 10) * 0.001 for i in range(100) for j in range(10)],
            'observation_any': [(i + j) % 3 == 0 for i in range(100) for j in range(10)],
            'observations': [
                [{'label': 'moose', 'confidence': 0.9, 'bbox': [100, 100, 200, 200]}] if (i + j) % 3 == 0 else []
                for i in range(100) for j in range(10)
            ],
            'top_label': ['moose' if (i + j) % 3 == 0 else None for i in range(100) for j in range(10)],
            'top_confidence': [0.9 if (i + j) % 3 == 0 else None for i in range(100) for j in range(10)],
            'needs_review': [(i + j) % 5 == 0 for i in range(100) for j in range(10)],
            'pipeline_version': ['1.0.0'] * 1000,
            'model_hashes': [{'stage1': 'abc123', 'stage2': 'def456'}] * 1000,
            'source_etag': [f'etag{i}_{j}' for i in range(100) for j in range(10)]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as parquet_file:
            parquet_path = parquet_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as sqlite_file:
            sqlite_path = sqlite_file.name
        
        try:
            # Create Parquet file
            df = pd.DataFrame(test_data)
            df.to_parquet(parquet_path, index=False)
            
            # Convert to SQLite
            convert_parquet_to_sqlite(parquet_path, sqlite_path, batch_size=100)
            
            # Verify database
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Check total count
            cursor.execute("SELECT COUNT(*) FROM observations")
            total_count = cursor.fetchone()[0]
            assert total_count == 1000
            
            # Check wildlife detections
            cursor.execute("SELECT COUNT(*) FROM observations WHERE observation_any = 1")
            wildlife_count = cursor.fetchone()[0]
            assert wildlife_count > 0
            
            # Check cameras
            cursor.execute("SELECT COUNT(DISTINCT camera_id) FROM observations")
            camera_count = cursor.fetchone()[0]
            assert camera_count == 10
            
            # Check review count
            cursor.execute("SELECT COUNT(*) FROM observations WHERE needs_review = 1")
            review_count = cursor.fetchone()[0]
            assert review_count > 0
            
            # Test complex query
            cursor.execute("""
                SELECT camera_id, 
                       COUNT(*) as total_images,
                       SUM(CASE WHEN observation_any = 1 THEN 1 ELSE 0 END) as wildlife_detections,
                       SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) as needs_review
                FROM observations 
                GROUP BY camera_id 
                ORDER BY camera_id
            """)
            results = cursor.fetchall()
            assert len(results) == 10
            
            conn.close()
            
        finally:
            Path(parquet_path).unlink()
            Path(sqlite_path).unlink()


if __name__ == '__main__':
    pytest.main([__file__])
