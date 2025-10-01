"""
Database adapter for wildlife detection results.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict
import sqlite3


class DatabaseAdapter(ABC):
    """Abstract database adapter interface."""

    @abstractmethod
    def insert_detection(self, detection_data: Dict[str, Any]) -> int:
        """Insert a detection record and return the detection ID."""
        pass

    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the database."""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter implementation."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
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

            cursor.execute("""
                INSERT INTO detections
                (file_path, file_type, camera_id, timestamp, latitude, longitude,
                 image_width, image_height, stage1_dropped, manual_review_count,
                 observations_stage2, video_source, frame_number, frame_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detection_data.get('file_path'),
                detection_data.get('file_type'),
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
            conn.commit()
            return detection_id

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total detections
            cursor.execute("SELECT COUNT(*) FROM detections")
            total_detections = cursor.fetchone()[0]

            # Detections by camera
            cursor.execute("""
                SELECT camera_id, COUNT(*) as count
                FROM detections
                GROUP BY camera_id
            """)
            camera_stats = dict(cursor.fetchall())

            # Date range
            cursor.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
                FROM detections
            """)
            date_range = cursor.fetchone()

            return {
                "total_detections": total_detections,
                "camera_stats": camera_stats,
                "date_range": {
                    "earliest": date_range[0],
                    "latest": date_range[1]
                } if date_range[0] else None
            }
