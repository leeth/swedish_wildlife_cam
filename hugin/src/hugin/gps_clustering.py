#!/usr/bin/env python3
"""
GPS Proximity Clustering for Wildlife Pipeline

This module implements GPS proximity clustering with 5m radius (10m diameter)
for grouping nearby wildlife camera locations. It provides:

- Proximity clustering algorithm using Haversine distance
- Cluster management with naming and lookup
- Unknown cluster detection for manual naming
- Database integration for cluster persistence
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import math
import logging

from .data_models import GPSCluster, GPSClusterAssignment, UnknownCluster, GPSCoordinates, ClusterBoundary


@dataclass
class GPSPoint:
    """GPS point for clustering."""
    observation_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    camera_id: Optional[str] = None


class GPSClusterManager:
    """GPS proximity cluster manager with 5m radius clustering."""
    
    def __init__(self, db_path: Path, logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self.cluster_radius_meters = 5.0  # 5m radius = 10m diameter
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with cluster tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # GPS clusters table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gps_clusters (
                    cluster_id TEXT PRIMARY KEY,
                    name TEXT,
                    center_latitude REAL NOT NULL,
                    center_longitude REAL NOT NULL,
                    radius_meters REAL DEFAULT 5.0,
                    point_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    description TEXT,
                    is_named BOOLEAN DEFAULT 0
                )
            """)
            
            # GPS cluster assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gps_cluster_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    cluster_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    distance_to_center REAL NOT NULL,
                    assigned_at TEXT NOT NULL,
                    FOREIGN KEY (cluster_id) REFERENCES gps_clusters (cluster_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clusters_coords ON gps_clusters(center_latitude, center_longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clusters_named ON gps_clusters(is_named)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_cluster ON gps_cluster_assignments(cluster_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_observation ON gps_cluster_assignments(observation_id)")
            
            conn.commit()
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters using Haversine formula."""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371000  # Earth radius in meters
        
        return c * r
    
    def _find_nearby_cluster(self, latitude: float, longitude: float) -> Optional[GPSCluster]:
        """Find existing cluster within radius of given coordinates."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all clusters
            cursor.execute("SELECT * FROM gps_clusters")
            clusters = cursor.fetchall()
            
            for cluster_row in clusters:
                cluster = GPSCluster(**dict(cluster_row))
                distance = self._calculate_distance(
                    latitude, longitude,
                    cluster.center_latitude, cluster.center_longitude
                )
                
                if distance <= self.cluster_radius_meters:
                    return cluster
        
        return None
    
    def _create_new_cluster(self, latitude: float, longitude: float) -> GPSCluster:
        """Create a new cluster with given coordinates as center."""
        cluster = GPSCluster(
            center_latitude=latitude,
            center_longitude=longitude,
            radius_meters=self.cluster_radius_meters,
            point_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO gps_clusters 
                (cluster_id, name, center_latitude, center_longitude, radius_meters, 
                 point_count, created_at, updated_at, description, is_named)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cluster.cluster_id,
                cluster.name,
                cluster.center_latitude,
                cluster.center_longitude,
                cluster.radius_meters,
                cluster.point_count,
                cluster.created_at.isoformat(),
                cluster.updated_at.isoformat(),
                cluster.description,
                cluster.is_named
            ))
            
            conn.commit()
        
        self.logger.info(f"Created new GPS cluster {cluster.cluster_id} at ({latitude:.6f}, {longitude:.6f})")
        return cluster
    
    def _update_cluster_center(self, cluster: GPSCluster, new_points: List[GPSPoint]):
        """Update cluster center based on all assigned points."""
        if not new_points:
            return cluster
        
        # Calculate new center as centroid of all points
        total_lat = sum(point.latitude for point in new_points)
        total_lon = sum(point.longitude for point in new_points)
        count = len(new_points)
        
        new_center_lat = total_lat / count
        new_center_lon = total_lon / count
        
        # Update cluster
        cluster.center_latitude = new_center_lat
        cluster.center_longitude = new_center_lon
        cluster.point_count = count
        cluster.updated_at = datetime.now()
        
        # Update in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE gps_clusters 
                SET center_latitude = ?, center_longitude = ?, point_count = ?, updated_at = ?
                WHERE cluster_id = ?
            """, (
                cluster.center_latitude,
                cluster.center_longitude,
                cluster.point_count,
                cluster.updated_at.isoformat(),
                cluster.cluster_id
            ))
            
            conn.commit()
        
        return cluster
    
    def assign_gps_point(self, observation_id: str, latitude: float, longitude: float, 
                        camera_id: Optional[str] = None, timestamp: Optional[datetime] = None) -> GPSClusterAssignment:
        """Assign a GPS point to a cluster (existing or new)."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Find nearby cluster
        cluster = self._find_nearby_cluster(latitude, longitude)
        
        if cluster is None:
            # Create new cluster
            cluster = self._create_new_cluster(latitude, longitude)
        
        # Calculate distance to cluster center
        distance = self._calculate_distance(
            latitude, longitude,
            cluster.center_latitude, cluster.center_longitude
        )
        
        # Create assignment
        assignment = GPSClusterAssignment(
            cluster_id=cluster.cluster_id,
            observation_id=observation_id,
            latitude=latitude,
            longitude=longitude,
            distance_to_center=distance,
            assigned_at=datetime.now()
        )
        
        # Store assignment
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO gps_cluster_assignments 
                (assignment_id, cluster_id, observation_id, latitude, longitude, distance_to_center, assigned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.assignment_id,
                assignment.cluster_id,
                assignment.observation_id,
                assignment.latitude,
                assignment.longitude,
                assignment.distance_to_center,
                assignment.assigned_at.isoformat()
            ))
            
            conn.commit()
        
        # Update cluster center and point count
        all_points = self._get_cluster_points(cluster.cluster_id)
        self._update_cluster_center(cluster, all_points)
        
        self.logger.debug(f"Assigned observation {observation_id} to cluster {cluster.cluster_id}")
        return assignment
    
    def _get_cluster_points(self, cluster_id: str) -> List[GPSPoint]:
        """Get all GPS points assigned to a cluster."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT observation_id, latitude, longitude, assigned_at
                FROM gps_cluster_assignments 
                WHERE cluster_id = ?
                ORDER BY assigned_at
            """, (cluster_id,))
            
            points = []
            for row in cursor.fetchall():
                points.append(GPSPoint(
                    observation_id=row['observation_id'],
                    latitude=row['latitude'],
                    longitude=row['longitude'],
                    timestamp=datetime.fromisoformat(row['assigned_at'])
                ))
            
            return points
    
    def get_cluster(self, cluster_id: str) -> Optional[GPSCluster]:
        """Get cluster by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM gps_clusters WHERE cluster_id = ?", (cluster_id,))
            row = cursor.fetchone()
            
            if row:
                return GPSCluster(**dict(row))
        
        return None
    
    def get_all_clusters(self) -> List[GPSCluster]:
        """Get all clusters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM gps_clusters ORDER BY created_at")
            rows = cursor.fetchall()
            
            return [GPSCluster(**dict(row)) for row in rows]
    
    def get_named_clusters(self) -> List[GPSCluster]:
        """Get all named clusters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM gps_clusters WHERE is_named = 1 ORDER BY name")
            rows = cursor.fetchall()
            
            return [GPSCluster(**dict(row)) for row in rows]
    
    def get_unknown_clusters(self) -> List[UnknownCluster]:
        """Get all unknown clusters that need manual naming."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM gps_clusters 
                WHERE is_named = 0 
                ORDER BY point_count DESC, created_at
            """)
            rows = cursor.fetchall()
            
            unknown_clusters = []
            for row in rows:
                cluster = GPSCluster(**dict(row))
                
                # Get sample observations
                cursor.execute("""
                    SELECT observation_id FROM gps_cluster_assignments 
                    WHERE cluster_id = ? 
                    ORDER BY assigned_at 
                    LIMIT 5
                """, (cluster.cluster_id,))
                
                sample_observations = [row['observation_id'] for row in cursor.fetchall()]
                
                # Get first and last seen timestamps
                cursor.execute("""
                    SELECT MIN(assigned_at) as first_seen, MAX(assigned_at) as last_seen
                    FROM gps_cluster_assignments 
                    WHERE cluster_id = ?
                """, (cluster.cluster_id,))
                
                time_row = cursor.fetchone()
                first_seen = datetime.fromisoformat(time_row['first_seen']) if time_row['first_seen'] else cluster.created_at
                last_seen = datetime.fromisoformat(time_row['last_seen']) if time_row['last_seen'] else cluster.updated_at
                
                unknown_cluster = UnknownCluster(
                    cluster_id=cluster.cluster_id,
                    center_latitude=cluster.center_latitude,
                    center_longitude=cluster.center_longitude,
                    point_count=cluster.point_count,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    sample_observations=sample_observations
                )
                
                unknown_clusters.append(unknown_cluster)
            
            return unknown_clusters
    
    def name_cluster(self, cluster_id: str, name: str, description: Optional[str] = None) -> bool:
        """Name an unknown cluster."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE gps_clusters 
                SET name = ?, description = ?, is_named = 1, updated_at = ?
                WHERE cluster_id = ?
            """, (
                name,
                description,
                datetime.now().isoformat(),
                cluster_id
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                self.logger.info(f"Named cluster {cluster_id} as '{name}'")
                return True
        
        return False
    
    def find_cluster_by_name(self, name: str) -> Optional[GPSCluster]:
        """Find cluster by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM gps_clusters WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                return GPSCluster(**dict(row))
        
        return None
    
    def get_cluster_assignments(self, cluster_id: str) -> List[GPSClusterAssignment]:
        """Get all assignments for a cluster."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM gps_cluster_assignments 
                WHERE cluster_id = ? 
                ORDER BY assigned_at
            """, (cluster_id,))
            
            rows = cursor.fetchall()
            return [GPSClusterAssignment(**dict(row)) for row in rows]
    
    def get_statistics(self) -> Dict[str, any]:
        """Get clustering statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total clusters
            cursor.execute("SELECT COUNT(*) FROM gps_clusters")
            total_clusters = cursor.fetchone()[0]
            
            # Named clusters
            cursor.execute("SELECT COUNT(*) FROM gps_clusters WHERE is_named = 1")
            named_clusters = cursor.fetchone()[0]
            
            # Unknown clusters
            cursor.execute("SELECT COUNT(*) FROM gps_clusters WHERE is_named = 0")
            unknown_clusters = cursor.fetchone()[0]
            
            # Total assignments
            cursor.execute("SELECT COUNT(*) FROM gps_cluster_assignments")
            total_assignments = cursor.fetchone()[0]
            
            # Average points per cluster
            cursor.execute("SELECT AVG(point_count) FROM gps_clusters")
            avg_points = cursor.fetchone()[0] or 0
            
            return {
                "total_clusters": total_clusters,
                "named_clusters": named_clusters,
                "unknown_clusters": unknown_clusters,
                "total_assignments": total_assignments,
                "avg_points_per_cluster": round(avg_points, 2),
                "naming_rate": named_clusters / total_clusters if total_clusters > 0 else 0
            }
    
    def process_observations_batch(self, observations: List[Dict]) -> Dict[str, int]:
        """Process a batch of observations for clustering."""
        stats = {"processed": 0, "clustered": 0, "new_clusters": 0, "errors": 0}
        
        for obs in observations:
            try:
                # Extract GPS data
                gps_lat = obs.get('gps_latitude')
                gps_lon = obs.get('gps_longitude')
                observation_id = obs.get('observation_id')
                
                if not all([gps_lat, gps_lon, observation_id]):
                    continue
                
                # Check if already assigned
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM gps_cluster_assignments 
                        WHERE observation_id = ?
                    """, (observation_id,))
                    
                    if cursor.fetchone()[0] > 0:
                        continue  # Already assigned
                
                # Assign to cluster
                assignment = self.assign_gps_point(
                    observation_id=observation_id,
                    latitude=gps_lat,
                    longitude=gps_lon,
                    camera_id=obs.get('camera_id'),
                    timestamp=obs.get('timestamp')
                )
                
                stats["processed"] += 1
                stats["clustered"] += 1
                
                # Check if this created a new cluster
                cluster = self.get_cluster(assignment.cluster_id)
                if cluster and cluster.point_count == 1:
                    stats["new_clusters"] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing observation {obs.get('observation_id', 'unknown')}: {e}")
                stats["errors"] += 1
        
        return stats
    
    def calculate_cluster_boundary(self, cluster_id: str) -> Optional[ClusterBoundary]:
        """Calculate boundary information for a cluster."""
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return None
        
        # Get all points in cluster
        points = self._get_cluster_points(cluster_id)
        if not points:
            return None
        
        # Calculate bounding box
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        # Calculate boundary points (extreme points)
        boundary_points = []
        
        # Find extreme points in each direction
        for point in points:
            if (point.latitude == min_lat or point.latitude == max_lat or 
                point.longitude == min_lon or point.longitude == max_lon):
                boundary_points.append((point.latitude, point.longitude))
        
        # Calculate convex hull
        convex_hull_points = self._calculate_convex_hull(points)
        
        # Calculate area and perimeter
        area = self._calculate_polygon_area(convex_hull_points)
        perimeter = self._calculate_polygon_perimeter(convex_hull_points)
        
        return ClusterBoundary(
            cluster_id=cluster_id,
            min_latitude=min_lat,
            max_latitude=max_lat,
            min_longitude=min_lon,
            max_longitude=max_lon,
            center_latitude=cluster.center_latitude,
            center_longitude=cluster.center_longitude,
            boundary_points=boundary_points,
            convex_hull_points=convex_hull_points,
            area_square_meters=area,
            perimeter_meters=perimeter
        )
    
    def _calculate_convex_hull(self, points: List[GPSPoint]) -> List[Tuple[float, float]]:
        """Calculate convex hull of GPS points using Graham scan algorithm."""
        if len(points) < 3:
            # For less than 3 points, return all points
            return [(p.latitude, p.longitude) for p in points]
        
        # Convert to (lat, lon) tuples
        point_list = [(p.latitude, p.longitude) for p in points]
        
        # Find bottom-most point (or leftmost in case of tie)
        start = min(point_list, key=lambda p: (p[0], p[1]))
        
        # Sort points by polar angle with respect to start point
        def polar_angle(p):
            return math.atan2(p[0] - start[0], p[1] - start[1])
        
        sorted_points = sorted(point_list, key=polar_angle)
        
        # Graham scan
        hull = []
        for point in sorted_points:
            while len(hull) > 1 and self._cross_product(hull[-2], hull[-1], point) <= 0:
                hull.pop()
            hull.append(point)
        
        return hull
    
    def _cross_product(self, o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Calculate cross product for convex hull algorithm."""
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    
    def _calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate approximate area of polygon using shoelace formula."""
        if len(points) < 3:
            return 0.0
        
        # Shoelace formula for polygon area
        n = len(points)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        area = abs(area) / 2.0
        
        # Convert from lat/lon degrees to square meters (approximate)
        # This is a rough approximation - for more accuracy, use proper projection
        lat_center = sum(p[0] for p in points) / len(points)
        meters_per_degree_lat = 111320  # Approximate meters per degree latitude
        meters_per_degree_lon = 111320 * math.cos(math.radians(lat_center))
        
        return area * meters_per_degree_lat * meters_per_degree_lon
    
    def _calculate_polygon_perimeter(self, points: List[Tuple[float, float]]) -> float:
        """Calculate approximate perimeter of polygon."""
        if len(points) < 2:
            return 0.0
        
        perimeter = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            distance = self._calculate_distance(
                points[i][0], points[i][1],
                points[j][0], points[j][1]
            )
            perimeter += distance
        
        return perimeter
    
    def get_cluster_boundary(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster boundary information for mapping."""
        boundary = self.calculate_cluster_boundary(cluster_id)
        if not boundary:
            return None
        
        return {
            "cluster_id": boundary.cluster_id,
            "bounding_box": {
                "min_latitude": boundary.min_latitude,
                "max_latitude": boundary.max_latitude,
                "min_longitude": boundary.min_longitude,
                "max_longitude": boundary.max_longitude
            },
            "center": {
                "latitude": boundary.center_latitude,
                "longitude": boundary.center_longitude
            },
            "boundary_points": [
                {"latitude": lat, "longitude": lon} 
                for lat, lon in boundary.boundary_points
            ],
            "convex_hull": [
                {"latitude": lat, "longitude": lon} 
                for lat, lon in boundary.convex_hull_points
            ],
            "area_square_meters": boundary.area_square_meters,
            "perimeter_meters": boundary.perimeter_meters
        }
    
    def get_all_cluster_boundaries(self) -> List[Dict[str, Any]]:
        """Get boundary information for all clusters."""
        clusters = self.get_all_clusters()
        boundaries = []
        
        for cluster in clusters:
            boundary_info = self.get_cluster_boundary(cluster.cluster_id)
            if boundary_info:
                # Add cluster metadata
                boundary_info.update({
                    "name": cluster.name,
                    "point_count": cluster.point_count,
                    "is_named": cluster.is_named,
                    "created_at": cluster.created_at.isoformat(),
                    "updated_at": cluster.updated_at.isoformat()
                })
                boundaries.append(boundary_info)
        
        return boundaries
    
    def detect_overlapping_clusters(self, overlap_threshold_meters: float = 10.0) -> List[Dict[str, Any]]:
        """Detect clusters that overlap within threshold distance."""
        clusters = self.get_all_clusters()
        overlapping_groups = []
        processed = set()
        
        for i, cluster1 in enumerate(clusters):
            if cluster1.cluster_id in processed:
                continue
                
            overlapping = [cluster1]
            processed.add(cluster1.cluster_id)
            
            for j, cluster2 in enumerate(clusters[i+1:], i+1):
                if cluster2.cluster_id in processed:
                    continue
                    
                distance = self._calculate_distance(
                    cluster1.center_latitude, cluster1.center_longitude,
                    cluster2.center_latitude, cluster2.center_longitude
                )
                
                if distance <= overlap_threshold_meters:
                    overlapping.append(cluster2)
                    processed.add(cluster2.cluster_id)
            
            if len(overlapping) > 1:
                overlapping_groups.append({
                    "group_id": f"overlap_{len(overlapping_groups)}",
                    "clusters": [
                        {
                            "cluster_id": c.cluster_id,
                            "name": c.name,
                            "center_latitude": c.center_latitude,
                            "center_longitude": c.center_longitude,
                            "point_count": c.point_count,
                            "is_named": c.is_named
                        }
                        for c in overlapping
                    ],
                    "overlap_distance": min([
                        self._calculate_distance(
                            overlapping[0].center_latitude, overlapping[0].center_longitude,
                            c.center_latitude, c.center_longitude
                        )
                        for c in overlapping[1:]
                    ])
                })
        
        return overlapping_groups
    
    def merge_clusters(self, cluster_ids: List[str], new_name: str, 
                      new_description: Optional[str] = None) -> Optional[str]:
        """Merge multiple clusters into a single cluster."""
        if len(cluster_ids) < 2:
            return None
        
        # Get all clusters to merge
        clusters_to_merge = []
        for cluster_id in cluster_ids:
            cluster = self.get_cluster(cluster_id)
            if cluster:
                clusters_to_merge.append(cluster)
        
        if len(clusters_to_merge) < 2:
            return None
        
        # Calculate new center as centroid of all points
        all_assignments = []
        for cluster in clusters_to_merge:
            assignments = self.get_cluster_assignments(cluster.cluster_id)
            all_assignments.extend(assignments)
        
        if not all_assignments:
            return None
        
        # Calculate new center
        total_lat = sum(a.latitude for a in all_assignments)
        total_lon = sum(a.longitude for a in all_assignments)
        count = len(all_assignments)
        
        new_center_lat = total_lat / count
        new_center_lon = total_lon / count
        
        # Create new merged cluster
        merged_cluster = GPSCluster(
            center_latitude=new_center_lat,
            center_longitude=new_center_lon,
            radius_meters=self.cluster_radius_meters,
            point_count=count,
            name=new_name,
            description=new_description,
            is_named=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store merged cluster
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO gps_clusters 
                (cluster_id, name, center_latitude, center_longitude, radius_meters, 
                 point_count, created_at, updated_at, description, is_named)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                merged_cluster.cluster_id,
                merged_cluster.name,
                merged_cluster.center_latitude,
                merged_cluster.center_longitude,
                merged_cluster.radius_meters,
                merged_cluster.point_count,
                merged_cluster.created_at.isoformat(),
                merged_cluster.updated_at.isoformat(),
                merged_cluster.description,
                merged_cluster.is_named
            ))
            
            # Update assignments to point to new cluster
            cursor.execute("""
                UPDATE gps_cluster_assignments 
                SET cluster_id = ?
                WHERE cluster_id IN ({})
            """.format(','.join('?' * len(cluster_ids))), 
            [merged_cluster.cluster_id] + cluster_ids)
            
            # Delete old clusters
            cursor.execute("""
                DELETE FROM gps_clusters 
                WHERE cluster_id IN ({})
            """.format(','.join('?' * len(cluster_ids))), cluster_ids)
            
            conn.commit()
        
        self.logger.info(f"Merged {len(cluster_ids)} clusters into {merged_cluster.cluster_id}")
        return merged_cluster.cluster_id
    
    def batch_name_clusters(self, cluster_names: Dict[str, str], 
                          descriptions: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """Batch name multiple clusters."""
        results = {}
        
        for cluster_id, name in cluster_names.items():
            description = descriptions.get(cluster_id) if descriptions else None
            success = self.name_cluster(cluster_id, name, description)
            results[cluster_id] = success
        
        return results
    
    def get_naming_changes_since(self, since_timestamp: datetime) -> Dict[str, Any]:
        """Get clusters that have been named since a timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM gps_clusters 
                WHERE is_named = 1 AND updated_at > ?
                ORDER BY updated_at DESC
            """, (since_timestamp.isoformat(),))
            
            rows = cursor.fetchall()
            
            changes = {
                "timestamp": datetime.now().isoformat(),
                "since": since_timestamp.isoformat(),
                "newly_named_count": len(rows),
                "clusters": [
                    {
                        "cluster_id": row['cluster_id'],
                        "name": row['name'],
                        "description": row['description'],
                        "point_count": row['point_count'],
                        "updated_at": row['updated_at']
                    }
                    for row in rows
                ]
            }
            
            return changes
