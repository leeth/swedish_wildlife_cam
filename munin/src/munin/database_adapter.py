"""
Database adapter abstraction for wildlife detection pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import sqlite3
import json
from contextlib import contextmanager


class DatabaseAdapter(ABC):
    """Abstract database adapter for database operations."""
    
    @abstractmethod
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        pass
    
    @abstractmethod
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        pass
    
    @abstractmethod
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> None:
        """Execute multiple operations in a transaction."""
        pass
    
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        pass
    
    @abstractmethod
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter implementation."""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main detections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    image_width INTEGER,
                    image_height INTEGER,
                    stage1_dropped INTEGER DEFAULT 0,
                    manual_review_count INTEGER DEFAULT 0,
                    observations_stage2 TEXT,
                    video_source TEXT,
                    frame_number INTEGER,
                    frame_timestamp REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Individual detection results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detection_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_x1 REAL,
                    bbox_y1 REAL,
                    bbox_x2 REAL,
                    bbox_y2 REAL,
                    FOREIGN KEY (detection_id) REFERENCES detections (id)
                )
            """)
            
            # Observations table for Parquet conversion
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    camera_id TEXT,
                    timestamp TEXT,
                    latitude REAL,
                    longitude REAL,
                    observation_any BOOLEAN,
                    observations TEXT,  -- JSON string
                    top_label TEXT,
                    top_confidence REAL,
                    needs_review BOOLEAN,
                    pipeline_version TEXT,
                    model_hashes TEXT,  -- JSON string
                    source_etag TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_camera_id ON detections(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_camera_id ON observations(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON observations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_observation_any ON observations(observation_any)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseError(f"Query execution failed: {e}")
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            raise DatabaseError(f"Update execution failed: {e}")
    
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> None:
        """Execute multiple operations in a transaction."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for operation in operations:
                    query = operation['query']
                    params = operation.get('params', ())
                    cursor.execute(query, params)
                
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Transaction execution failed: {e}")
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def insert_detection(self, detection_data: Dict[str, Any]) -> int:
        """Insert a detection record and return the detection ID."""
        query = """
            INSERT INTO detections (
                file_path, file_type, camera_id, timestamp, latitude, longitude,
                image_width, image_height, stage1_dropped, manual_review_count,
                observations_stage2, video_source, frame_number, frame_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            detection_data.get('file_path'),
            detection_data.get('file_type', 'image'),
            detection_data.get('camera_id'),
            detection_data.get('timestamp'),
            detection_data.get('latitude'),
            detection_data.get('longitude'),
            detection_data.get('image_width'),
            detection_data.get('image_height'),
            detection_data.get('stage1_dropped', 0),
            detection_data.get('manual_review_count', 0),
            detection_data.get('observations_stage2'),
            detection_data.get('video_source'),
            detection_data.get('frame_number'),
            detection_data.get('frame_timestamp')
        )
        
        # Execute insert and get ID
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            detection_id = cursor.lastrowid
            
            # Insert individual detection results
            for result in detection_data.get('detection_results', []):
                result_query = """
                    INSERT INTO detection_results (
                        detection_id, label, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                result_params = (
                    detection_id,
                    result.get('label'),
                    result.get('confidence'),
                    result.get('bbox', [None, None, None, None])[0],
                    result.get('bbox', [None, None, None, None])[1],
                    result.get('bbox', [None, None, None, None])[2],
                    result.get('bbox', [None, None, None, None])[3]
                )
                cursor.execute(result_query, result_params)
            
            conn.commit()
            return detection_id
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the database."""
        stats = {}
        
        # Total detections
        result = self.execute_query("SELECT COUNT(*) as count FROM detections")
        stats['total_detections'] = result[0]['count'] if result else 0
        
        # GPS detections
        result = self.execute_query("SELECT COUNT(*) as count FROM detections WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        stats['gps_detections'] = result[0]['count'] if result else 0
        
        # Species counts
        result = self.execute_query("""
            SELECT label, COUNT(*) as count 
            FROM detection_results 
            GROUP BY label 
            ORDER BY count DESC
        """)
        stats['species_counts'] = {row['label']: row['count'] for row in result}
        
        # Camera counts
        result = self.execute_query("""
            SELECT camera_id, COUNT(*) as count 
            FROM detections 
            GROUP BY camera_id 
            ORDER BY count DESC
        """)
        stats['camera_counts'] = {row['camera_id']: row['count'] for row in result}
        
        return stats


class DatabaseError(Exception):
    """Database operation error."""
    pass


def create_database_adapter(adapter_type: str, **kwargs) -> DatabaseAdapter:
    """Factory function to create database adapters."""
    if adapter_type == "sqlite":
        return SQLiteAdapter(**kwargs)
    else:
        raise ValueError(f"Unsupported database adapter type: {adapter_type}")
