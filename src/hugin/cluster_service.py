#!/usr/bin/env python3
"""
GPS Cluster Service for Hugin

This service provides high-level cluster management functionality:
- Automatic clustering of GPS observations
- Cluster naming and lookup
- Unknown cluster detection
- Integration with Hugin analytics
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import polars as pl

from .data_models import UnknownCluster
from .gps_clustering import GPSClusterManager

logger = logging.getLogger(__name__)

class ClusterService:
    """High-level cluster management service."""

    def __init__(self, db_path: str = "clusters.db"):
        """Initialize cluster service."""
        self.manager = GPSClusterManager(db_path)
        self.logger = logger

    def process_observations(self, observations: List[Dict[str, Any]],
                           radius_meters: float = 5.0) -> Dict[str, Any]:
        """
        Process observations and create clusters.

        Args:
            observations: List of observation dictionaries
            radius_meters: Cluster radius in meters

        Returns:
            Processing results
        """
        try:
            # Convert observations to GPS points
            gps_points = []
            for obs in observations:
                if 'latitude' in obs and 'longitude' in obs:
                    gps_points.append({
                        'latitude': obs['latitude'],
                        'longitude': obs['longitude'],
                        'observation_id': obs.get('observation_id', ''),
                        'timestamp': obs.get('timestamp', datetime.now())
                    })

            if not gps_points:
                return {"success": False, "error": "No valid GPS points found"}

            # Perform clustering
            clusters = self.manager.create_clusters(gps_points, radius_meters)

            return {
                "success": True,
                "clusters_created": len(clusters),
                "total_points": len(gps_points),
                "clusters": [cluster.dict() for cluster in clusters]
            }

        except Exception as e:
            self.logger.error(f"Error processing observations: {e}")
            return {"success": False, "error": str(e)}

    def get_cluster_analytics(self) -> Dict[str, Any]:
        """Get cluster analytics."""
        try:
            clusters = self.manager.get_all_clusters()

            analytics = {
                "total_clusters": len(clusters),
                "named_clusters": len([c for c in clusters if c.name]),
                "unnamed_clusters": len([c for c in clusters if not c.name]),
                "total_points": sum(c.point_count for c in clusters),
                "average_points_per_cluster": sum(c.point_count for c in clusters) / len(clusters) if clusters else 0
            }

            return analytics

        except Exception as e:
            self.logger.error(f"Error getting cluster analytics: {e}")
            return {"error": str(e)}

    def get_unknown_clusters(self, limit: int = 20) -> List[UnknownCluster]:
        """Get unknown clusters that need naming."""
        try:
            clusters = self.manager.get_all_clusters()
            unknown = [c for c in clusters if not c.name][:limit]

            unknown_clusters = []
            for cluster in unknown:
                assignments = self.manager.get_cluster_assignments(cluster.cluster_id)
                sample_observations = assignments[:5]  # First 5 observations

                unknown_clusters.append(UnknownCluster(
                    cluster_id=cluster.cluster_id,
                    center_latitude=cluster.center_latitude,
                    center_longitude=cluster.center_longitude,
                    point_count=cluster.point_count,
                    first_seen=cluster.created_at,
                    last_seen=cluster.updated_at,
                    sample_observations=sample_observations
                ))

            return unknown_clusters

        except Exception as e:
            self.logger.error(f"Error getting unknown clusters: {e}")
            return []

    def name_cluster(self, cluster_id: str, name: str) -> bool:
        """Name a cluster."""
        try:
            return self.manager.name_cluster(cluster_id, name)
        except Exception as e:
            self.logger.error(f"Error naming cluster {cluster_id}: {e}")
            return False

    def batch_name_clusters(self, names: Dict[str, str]) -> int:
        """Name multiple clusters."""
        try:
            return self.manager.batch_name_clusters(names)
        except Exception as e:
            self.logger.error(f"Error batch naming clusters: {e}")
            return 0

    def get_cluster_boundaries(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster boundary information."""
        try:
            boundary = self.manager.get_cluster_boundary(cluster_id)
            return boundary.dict() if boundary else None
        except Exception as e:
            self.logger.error(f"Error getting cluster boundary: {e}")
            return None

    def get_all_cluster_boundaries(self) -> List[Dict[str, Any]]:
        """Get all cluster boundaries."""
        try:
            boundaries = self.manager.get_all_cluster_boundaries()
            return [b.dict() for b in boundaries]
        except Exception as e:
            self.logger.error(f"Error getting all cluster boundaries: {e}")
            return []

    def export_cluster_data(self, output_path: str, format: str = "csv") -> bool:
        """Export cluster data."""
        try:
            clusters = self.manager.get_all_clusters()

            if format == "csv":
                df = pl.DataFrame([c.dict() for c in clusters])
                df.write_csv(output_path)
            elif format == "json":
                import json
                with open(output_path, 'w') as f:
                    json.dump([c.dict() for c in clusters], f, indent=2, default=str)
            else:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error exporting cluster data: {e}")
            return False
