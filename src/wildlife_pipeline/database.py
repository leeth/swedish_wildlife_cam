"""
SQLite database module for wildlife detection results.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class WildlifeDatabase:
    """SQLite database for storing wildlife detection results."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
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
                    bbox_x1 REAL NOT NULL,
                    bbox_y1 REAL NOT NULL,
                    bbox_x2 REAL NOT NULL,
                    bbox_y2 REAL NOT NULL,
                    stage INTEGER NOT NULL,  -- 1 for stage1, 2 for stage2
                    FOREIGN KEY (detection_id) REFERENCES detections (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_camera ON detections(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_gps ON detections(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_detection ON detection_results(detection_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_label ON detection_results(label)")
            
            conn.commit()
    
    def insert_detection(self, detection_data: Dict[str, Any]) -> int:
        """Insert a detection record and return the detection ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert main detection record
            cursor.execute("""
                INSERT INTO detections (
                    file_path, file_type, camera_id, timestamp, latitude, longitude,
                    image_width, image_height, stage1_dropped, manual_review_count,
                    observations_stage2, video_source, frame_number, frame_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
            ))
            
            detection_id = cursor.lastrowid
            
            # Insert individual detection results
            for result in detection_data.get('detection_results', []):
                cursor.execute("""
                    INSERT INTO detection_results (
                        detection_id, label, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2, stage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    detection_id,
                    result.get('label'),
                    result.get('confidence'),
                    result.get('bbox', {}).get('x1', 0),
                    result.get('bbox', {}).get('y1', 0),
                    result.get('bbox', {}).get('x2', 0),
                    result.get('bbox', {}).get('y2', 0),
                    result.get('stage', 1)
                ))
            
            conn.commit()
            return detection_id
    
    def get_detections_by_camera(self, camera_id: str) -> List[Dict[str, Any]]:
        """Get all detections for a specific camera."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.*, 
                       GROUP_CONCAT(
                           json_object(
                               'label', dr.label,
                               'confidence', dr.confidence,
                               'bbox', json_object('x1', dr.bbox_x1, 'y1', dr.bbox_y1, 'x2', dr.bbox_x2, 'y2', dr.bbox_y2),
                               'stage', dr.stage
                           )
                       ) as detection_results
                FROM detections d
                LEFT JOIN detection_results dr ON d.id = dr.detection_id
                WHERE d.camera_id = ?
                GROUP BY d.id
                ORDER BY d.timestamp
            """, (camera_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_detections_by_species(self, species: str) -> List[Dict[str, Any]]:
        """Get all detections for a specific species."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.*, 
                       GROUP_CONCAT(
                           json_object(
                               'label', dr.label,
                               'confidence', dr.confidence,
                               'bbox', json_object('x1', dr.bbox_x1, 'y1', dr.bbox_y1, 'x2', dr.bbox_x2, 'y2', dr.bbox_y2),
                               'stage', dr.stage
                           )
                       ) as detection_results
                FROM detections d
                JOIN detection_results dr ON d.id = dr.detection_id
                WHERE dr.label = ?
                GROUP BY d.id
                ORDER BY d.timestamp
            """, (species,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_detections_with_gps(self) -> List[Dict[str, Any]]:
        """Get all detections that have GPS coordinates."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.*, 
                       GROUP_CONCAT(
                           json_object(
                               'label', dr.label,
                               'confidence', dr.confidence,
                               'bbox', json_object('x1', dr.bbox_x1, 'y1', dr.bbox_y1, 'x2', dr.bbox_x2, 'y2', dr.bbox_y2),
                               'stage', dr.stage
                           )
                       ) as detection_results
                FROM detections d
                LEFT JOIN detection_results dr ON d.id = dr.detection_id
                WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
                GROUP BY d.id
                ORDER BY d.timestamp
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total detections
            cursor.execute("SELECT COUNT(*) FROM detections")
            total_detections = cursor.fetchone()[0]
            
            # Detections with GPS
            cursor.execute("SELECT COUNT(*) FROM detections WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
            gps_detections = cursor.fetchone()[0]
            
            # Species counts
            cursor.execute("""
                SELECT label, COUNT(*) as count 
                FROM detection_results 
                GROUP BY label 
                ORDER BY count DESC
            """)
            species_counts = dict(cursor.fetchall())
            
            # Camera counts
            cursor.execute("""
                SELECT camera_id, COUNT(*) as count 
                FROM detections 
                GROUP BY camera_id 
                ORDER BY count DESC
            """)
            camera_counts = dict(cursor.fetchall())
            
            return {
                'total_detections': total_detections,
                'gps_detections': gps_detections,
                'species_counts': species_counts,
                'camera_counts': camera_counts
            }
    
    def export_to_csv(self, output_path: Path):
        """Export all detections to CSV format."""
        import pandas as pd
        
        with sqlite3.connect(self.db_path) as conn:
            # Get all detections with their results
            df = pd.read_sql_query("""
                SELECT d.*, 
                       dr.label as detection_label,
                       dr.confidence as detection_confidence,
                       dr.bbox_x1, dr.bbox_y1, dr.bbox_x2, dr.bbox_y2,
                       dr.stage as detection_stage
                FROM detections d
                LEFT JOIN detection_results dr ON d.id = dr.detection_id
                ORDER BY d.timestamp, d.id
            """, conn)
            
            df.to_csv(output_path, index=False)
    
    def close(self):
        """Close database connection (not needed for sqlite3 context manager)."""
        pass
