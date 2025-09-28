"""
Efficient Cluster Lookup System

This module provides the most efficient solution for:
1. Large datasets with cluster_id
2. Small SQLite setup with cluster names
3. Reporting enrichment without reprocessing
4. Minimal overhead for large datasets
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)

@dataclass
class ClusterName:
    """Lightweight cluster name record."""
    cluster_id: str
    name: str
    created_at: datetime
    updated_at: datetime

@dataclass
class ClusterLocation:
    """GPS location for cluster."""
    cluster_id: str
    latitude: float
    longitude: float
    timestamp: datetime

@dataclass
class ClusterMean:
    """Mean GPS point for cluster plotting."""
    cluster_id: str
    mean_latitude: float
    mean_longitude: float
    point_count: int
    created_at: datetime

class EfficientClusterLookup:
    """
    Most efficient cluster lookup system for large datasets.

    Features:
    - Lightweight SQLite for cluster names only
    - In-memory lookup cache for performance
    - No reprocessing of data
    - Minimal overhead for large datasets
    - Fast reporting enrichment
    """

    def __init__(self, db_path: Union[str, Path] = "cluster_names.db"):
        self.db_path = Path(db_path)
        self._name_cache: Dict[str, str] = {}
        self._cache_loaded = False
        self._init_database()

    def _init_database(self):
        """Initialize lightweight SQLite database for cluster names and locations."""
        with sqlite3.connect(self.db_path) as conn:
            # Cluster names table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_names (
                    cluster_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cluster_id ON cluster_names(cluster_id)
            """)

            # Cluster locations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cluster_id) REFERENCES cluster_names(cluster_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cluster_locations_cluster_id ON cluster_locations(cluster_id)
            """)

            # Cluster mean points table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_means (
                    cluster_id TEXT PRIMARY KEY,
                    mean_latitude REAL NOT NULL,
                    mean_longitude REAL NOT NULL,
                    point_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cluster_id) REFERENCES cluster_names(cluster_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cluster_means_cluster_id ON cluster_means(cluster_id)
            """)

    def _load_cache(self):
        """Load cluster names into memory cache for fast lookup."""
        if self._cache_loaded:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT cluster_id, name FROM cluster_names")
            self._name_cache = dict(cursor.fetchall())

        self._cache_loaded = True
        logger.info(f"Loaded {len(self._name_cache)} cluster names into cache")

    def add_cluster_name(self, cluster_id: str, name: str) -> bool:
        """Add or update cluster name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cluster_names (cluster_id, name, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (cluster_id, name))

            # Update cache
            self._name_cache[cluster_id] = name
            return True
        except Exception as e:
            logger.error(f"Failed to add cluster name: {e}")
            return False

    def batch_add_cluster_names(self, names: Dict[str, str]) -> int:
        """Add multiple cluster names efficiently."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany("""
                    INSERT OR REPLACE INTO cluster_names (cluster_id, name, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, list(names.items()))

            # Update cache
            self._name_cache.update(names)
            return len(names)
        except Exception as e:
            logger.error(f"Failed to batch add cluster names: {e}")
            return 0

    def get_cluster_name(self, cluster_id: str) -> Optional[str]:
        """Get cluster name by ID (fast cache lookup)."""
        if not self._cache_loaded:
            self._load_cache()
        return self._name_cache.get(cluster_id)

    def get_all_cluster_names(self) -> Dict[str, str]:
        """Get all cluster names."""
        if not self._cache_loaded:
            self._load_cache()
        return self._name_cache.copy()

    def enrich_dataframe_with_names(self, df: pl.DataFrame, cluster_id_col: str = "cluster_id") -> pl.DataFrame:
        """
        Enrich DataFrame with cluster names without reprocessing.

        Args:
            df: DataFrame with cluster_id column
            cluster_id_col: Name of cluster_id column

        Returns:
            DataFrame with added 'cluster_name' column
        """
        if not self._cache_loaded:
            self._load_cache()

        # Create mapping for Polars
        cluster_names = pl.DataFrame({
            "cluster_id": list(self._name_cache.keys()),
            "cluster_name": list(self._name_cache.values())
        })

        # Join with cluster names
        enriched_df = df.join(
            cluster_names,
            on=cluster_id_col,
            how="left"
        )

        # Fill missing names with cluster_id
        enriched_df = enriched_df.with_columns(
            pl.when(pl.col("cluster_name").is_null())
            .then(pl.col(cluster_id_col))
            .otherwise(pl.col("cluster_name"))
            .alias("cluster_name")
        )

        return enriched_df

    def enrich_pandas_with_names(self, df: pd.DataFrame, cluster_id_col: str = "cluster_id") -> pd.DataFrame:
        """
        Enrich Pandas DataFrame with cluster names without reprocessing.

        Args:
            df: DataFrame with cluster_id column
            cluster_id_col: Name of cluster_id column

        Returns:
            DataFrame with added 'cluster_name' column
        """
        if not self._cache_loaded:
            self._load_cache()

        # Create mapping
        df = df.copy()
        df['cluster_name'] = df[cluster_id_col].map(self._name_cache)

        # Fill missing names with cluster_id
        df['cluster_name'] = df['cluster_name'].fillna(df[cluster_id_col])

        return df

    def enrich_dict_list_with_names(self, data: List[Dict[str, Any]], cluster_id_key: str = "cluster_id") -> List[Dict[str, Any]]:
        """
        Enrich list of dictionaries with cluster names without reprocessing.

        Args:
            data: List of dictionaries with cluster_id
            cluster_id_key: Key name for cluster_id

        Returns:
            List of dictionaries with added 'cluster_name' key
        """
        if not self._cache_loaded:
            self._load_cache()

        enriched_data = []
        for item in data:
            enriched_item = item.copy()
            cluster_id = item.get(cluster_id_key)
            enriched_item['cluster_name'] = self._name_cache.get(cluster_id, cluster_id)
            enriched_data.append(enriched_item)

        return enriched_data

    def get_unknown_clusters(self, data: Union[pl.DataFrame, pd.DataFrame, List[Dict]],
                           cluster_id_col: str = "cluster_id") -> List[str]:
        """
        Get list of unknown clusters (without names) from data.

        Args:
            data: DataFrame or list of dictionaries
            cluster_id_col: Name of cluster_id column/key

        Returns:
            List of unknown cluster IDs
        """
        if not self._cache_loaded:
            self._load_cache()

        if isinstance(data, pl.DataFrame):
            unique_clusters = data[cluster_id_col].unique().to_list()
        elif isinstance(data, pd.DataFrame):
            unique_clusters = data[cluster_id_col].unique().tolist()
        else:  # List of dicts
            unique_clusters = list({item.get(cluster_id_col) for item in data if item.get(cluster_id_col)})

        unknown_clusters = [cid for cid in unique_clusters if cid not in self._name_cache]
        return unknown_clusters

    def export_cluster_names(self, output_path: Union[str, Path]) -> bool:
        """Export cluster names to JSON file."""
        try:
            if not self._cache_loaded:
                self._load_cache()

            with open(output_path, 'w') as f:
                json.dump(self._name_cache, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export cluster names: {e}")
            return False

    def import_cluster_names(self, input_path: Union[str, Path]) -> int:
        """Import cluster names from JSON file."""
        try:
            with open(input_path) as f:
                names = json.load(f)

            return self.batch_add_cluster_names(names)
        except Exception as e:
            logger.error(f"Failed to import cluster names: {e}")
            return 0

    def add_cluster_locations(self, cluster_id: str, locations: List[tuple]) -> int:
        """Add GPS locations for a cluster."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert locations
                conn.executemany("""
                    INSERT INTO cluster_locations (cluster_id, latitude, longitude)
                    VALUES (?, ?, ?)
                """, [(cluster_id, lat, lon) for lat, lon in locations])

                # Calculate and store mean point
                mean_lat = sum(lat for lat, lon in locations) / len(locations)
                mean_lon = sum(lon for lat, lon in locations) / len(locations)

                conn.execute("""
                    INSERT OR REPLACE INTO cluster_means (cluster_id, mean_latitude, mean_longitude, point_count)
                    VALUES (?, ?, ?, ?)
                """, (cluster_id, mean_lat, mean_lon, len(locations)))

                return len(locations)
        except Exception as e:
            logger.error(f"Failed to add cluster locations: {e}")
            return 0

    def get_cluster_locations(self, cluster_id: str) -> List[tuple]:
        """Get GPS locations for a cluster."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT latitude, longitude FROM cluster_locations
                    WHERE cluster_id = ? ORDER BY timestamp
                """, (cluster_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get cluster locations: {e}")
            return []

    def get_cluster_mean(self, cluster_id: str) -> Optional[tuple]:
        """Get mean GPS point for a cluster."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT mean_latitude, mean_longitude, point_count FROM cluster_means
                    WHERE cluster_id = ?
                """, (cluster_id,))
                result = cursor.fetchone()
                return result if result else None
        except Exception as e:
            logger.error(f"Failed to get cluster mean: {e}")
            return None

    def get_all_cluster_means(self) -> Dict[str, tuple]:
        """Get all cluster mean points for plotting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT cluster_id, mean_latitude, mean_longitude, point_count
                    FROM cluster_means ORDER BY point_count DESC
                """)
                return {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Failed to get all cluster means: {e}")
            return {}

    def export_cluster_means_for_plotting(self, output_path: Union[str, Path]) -> bool:
        """Export cluster mean points for plotting (CSV format)."""
        try:
            means = self.get_all_cluster_means()
            names = self.get_all_cluster_names()

            with open(output_path, 'w') as f:
                f.write("cluster_id,cluster_name,latitude,longitude,point_count\n")
                for cluster_id, (lat, lon, count) in means.items():
                    name = names.get(cluster_id, cluster_id)
                    f.write(f"{cluster_id},{name},{lat},{lon},{count}\n")

            return True
        except Exception as e:
            logger.error(f"Failed to export cluster means: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about cluster names and locations."""
        if not self._cache_loaded:
            self._load_cache()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get location stats
                cursor = conn.execute("SELECT COUNT(*) FROM cluster_locations")
                total_locations = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM cluster_means")
                total_means = cursor.fetchone()[0]

                cursor = conn.execute("SELECT SUM(point_count) FROM cluster_means")
                total_points = cursor.fetchone()[0] or 0

                return {
                    "total_clusters": len(self._name_cache),
                    "named_clusters": len([name for name in self._name_cache.values() if name]),
                    "total_locations": total_locations,
                    "total_means": total_means,
                    "total_points": total_points,
                    "database_path": str(self.db_path),
                    "cache_loaded": self._cache_loaded
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_clusters": len(self._name_cache),
                "named_clusters": len([name for name in self._name_cache.values() if name]),
                "database_path": str(self.db_path),
                "cache_loaded": self._cache_loaded
            }


class EfficientReportingEnricher:
    """
    High-performance reporting enricher for large datasets.

    Features:
    - Minimal memory overhead
    - Fast lookup without reprocessing
    - Support for multiple data formats
    - Batch processing capabilities
    """

    def __init__(self, cluster_lookup: EfficientClusterLookup):
        self.cluster_lookup = cluster_lookup

    def enrich_report(self, data: Union[pl.DataFrame, pd.DataFrame, List[Dict]],
                     output_format: str = "polars") -> Union[pl.DataFrame, pd.DataFrame, List[Dict]]:
        """
        Enrich report data with cluster names.

        Args:
            data: Input data
            output_format: "polars", "pandas", or "dict"

        Returns:
            Enriched data with cluster names
        """
        if isinstance(data, pl.DataFrame):
            enriched = self.cluster_lookup.enrich_dataframe_with_names(data)
            return enriched if output_format == "polars" else enriched.to_pandas()

        elif isinstance(data, pd.DataFrame):
            enriched = self.cluster_lookup.enrich_pandas_with_names(data)
            return enriched if output_format == "pandas" else enriched

        else:  # List of dicts
            enriched = self.cluster_lookup.enrich_dict_list_with_names(data)
            return enriched

    def generate_cluster_summary(self, data: Union[pl.DataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """Generate cluster summary statistics."""
        df = data.to_pandas() if isinstance(data, pl.DataFrame) else data

        # Get cluster counts
        cluster_counts = df['cluster_id'].value_counts().to_dict()

        # Get named clusters
        named_clusters = df[df['cluster_name'] != df['cluster_id']]['cluster_id'].unique()

        return {
            "total_observations": len(df),
            "unique_clusters": len(cluster_counts),
            "named_clusters": len(named_clusters),
            "unnamed_clusters": len(cluster_counts) - len(named_clusters),
            "top_clusters": dict(list(cluster_counts.items())[:10])
        }


# Convenience functions for easy usage
def create_efficient_lookup(db_path: Union[str, Path] = "cluster_names.db") -> EfficientClusterLookup:
    """Create efficient cluster lookup instance."""
    return EfficientClusterLookup(db_path)

def enrich_data_fast(data: Union[pl.DataFrame, pd.DataFrame, List[Dict]],
                    db_path: Union[str, Path] = "cluster_names.db") -> Union[pl.DataFrame, pd.DataFrame, List[Dict]]:
    """Fast data enrichment with cluster names."""
    lookup = EfficientClusterLookup(db_path)

    if isinstance(data, pl.DataFrame):
        return lookup.enrich_dataframe_with_names(data)
    elif isinstance(data, pd.DataFrame):
        return lookup.enrich_pandas_with_names(data)
    else:
        return lookup.enrich_dict_list_with_names(data)

def get_unknown_clusters_fast(data: Union[pl.DataFrame, pd.DataFrame, List[Dict]],
                            db_path: Union[str, Path] = "cluster_names.db") -> List[str]:
    """Get unknown clusters from data."""
    lookup = EfficientClusterLookup(db_path)
    return lookup.get_unknown_clusters(data)
