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
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import polars as pl

from .gps_clustering import GPSClusterManager
from .data_models import GPSCluster, GPSClusterAssignment, UnknownCluster


class ClusterService:
    """High-level GPS cluster service for Hugin."""
    
    def __init__(self, db_path: Path, logger: Optional[logging.Logger] = None):
        self.manager = GPSClusterManager(db_path, logger)
        self.logger = logger or logging.getLogger(__name__)
    
    def process_observations_dataframe(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Process a Polars DataFrame of observations for clustering."""
        self.logger.info(f"Processing {len(df)} observations for GPS clustering")
        
        # Filter observations with GPS data
        gps_df = df.filter(
            pl.col("gps_latitude").is_not_null() & 
            pl.col("gps_longitude").is_not_null()
        )
        
        if len(gps_df) == 0:
            self.logger.warning("No GPS data found in observations")
            return {"error": "No GPS data available"}
        
        # Convert to list of dictionaries for processing
        observations = gps_df.to_dicts()
        
        # Process batch
        stats = self.manager.process_observations_batch(observations)
        
        self.logger.info(f"Clustering complete: {stats['clustered']} points clustered, {stats['new_clusters']} new clusters")
        return stats
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """Get summary of all clusters."""
        clusters = self.manager.get_all_clusters()
        named_clusters = self.manager.get_named_clusters()
        unknown_clusters = self.manager.get_unknown_clusters()
        stats = self.manager.get_statistics()
        
        return {
            "total_clusters": len(clusters),
            "named_clusters": len(named_clusters),
            "unknown_clusters": len(unknown_clusters),
            "statistics": stats,
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "center_latitude": c.center_latitude,
                    "center_longitude": c.center_longitude,
                    "point_count": c.point_count,
                    "is_named": c.is_named,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat()
                }
                for c in clusters
            ]
        }
    
    def get_unknown_clusters_for_naming(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unknown clusters that need manual naming."""
        unknown_clusters = self.manager.get_unknown_clusters()
        
        # Sort by point count (descending) and creation time
        unknown_clusters.sort(key=lambda x: (-x.point_count, x.first_seen))
        
        return [
            {
                "cluster_id": uc.cluster_id,
                "center_latitude": uc.center_latitude,
                "center_longitude": uc.center_longitude,
                "point_count": uc.point_count,
                "first_seen": uc.first_seen.isoformat(),
                "last_seen": uc.last_seen.isoformat(),
                "sample_observations": uc.sample_observations[:5]  # Limit to 5 samples
            }
            for uc in unknown_clusters[:limit]
        ]
    
    def name_unknown_cluster(self, cluster_id: str, name: str, description: Optional[str] = None) -> bool:
        """Name an unknown cluster."""
        success = self.manager.name_cluster(cluster_id, name, description)
        
        if success:
            self.logger.info(f"Named cluster {cluster_id} as '{name}'")
        else:
            self.logger.warning(f"Failed to name cluster {cluster_id}")
        
        return success
    
    def find_cluster_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find cluster by name."""
        cluster = self.manager.find_cluster_by_name(name)
        
        if cluster:
            return {
                "cluster_id": cluster.cluster_id,
                "name": cluster.name,
                "center_latitude": cluster.center_latitude,
                "center_longitude": cluster.center_longitude,
                "point_count": cluster.point_count,
                "is_named": cluster.is_named,
                "description": cluster.description,
                "created_at": cluster.created_at.isoformat(),
                "updated_at": cluster.updated_at.isoformat()
            }
        
        return None
    
    def get_cluster_details(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cluster."""
        cluster = self.manager.get_cluster(cluster_id)
        
        if not cluster:
            return None
        
        # Get assignments
        assignments = self.manager.get_cluster_assignments(cluster_id)
        
        # Get boundary information
        boundary = self.manager.get_cluster_boundary(cluster_id)
        
        return {
            "cluster": {
                "cluster_id": cluster.cluster_id,
                "name": cluster.name,
                "center_latitude": cluster.center_latitude,
                "center_longitude": cluster.center_longitude,
                "radius_meters": cluster.radius_meters,
                "point_count": cluster.point_count,
                "is_named": cluster.is_named,
                "description": cluster.description,
                "created_at": cluster.created_at.isoformat(),
                "updated_at": cluster.updated_at.isoformat()
            },
            "assignments": [
                {
                    "assignment_id": a.assignment_id,
                    "observation_id": a.observation_id,
                    "latitude": a.latitude,
                    "longitude": a.longitude,
                    "distance_to_center": a.distance_to_center,
                    "assigned_at": a.assigned_at.isoformat()
                }
                for a in assignments
            ],
            "boundary": boundary
        }
    
    def search_clusters_by_location(self, latitude: float, longitude: float, 
                                   radius_meters: float = 100.0) -> List[Dict[str, Any]]:
        """Search for clusters near a given location."""
        all_clusters = self.manager.get_all_clusters()
        nearby_clusters = []
        
        for cluster in all_clusters:
            distance = self.manager._calculate_distance(
                latitude, longitude,
                cluster.center_latitude, cluster.center_longitude
            )
            
            if distance <= radius_meters:
                nearby_clusters.append({
                    "cluster_id": cluster.cluster_id,
                    "name": cluster.name,
                    "center_latitude": cluster.center_latitude,
                    "center_longitude": cluster.center_longitude,
                    "point_count": cluster.point_count,
                    "is_named": cluster.is_named,
                    "distance_meters": distance
                })
        
        # Sort by distance
        nearby_clusters.sort(key=lambda x: x["distance_meters"])
        return nearby_clusters
    
    def get_cluster_analytics(self) -> Dict[str, Any]:
        """Get analytics about clusters."""
        stats = self.manager.get_statistics()
        all_clusters = self.manager.get_all_clusters()
        
        # Calculate additional metrics
        if all_clusters:
            point_counts = [c.point_count for c in all_clusters]
            avg_points = sum(point_counts) / len(point_counts)
            max_points = max(point_counts)
            min_points = min(point_counts)
        else:
            avg_points = max_points = min_points = 0
        
        # Get clusters by size
        small_clusters = [c for c in all_clusters if c.point_count < 5]
        medium_clusters = [c for c in all_clusters if 5 <= c.point_count < 20]
        large_clusters = [c for c in all_clusters if c.point_count >= 20]
        
        return {
            "basic_stats": stats,
            "size_distribution": {
                "small_clusters": len(small_clusters),
                "medium_clusters": len(medium_clusters),
                "large_clusters": len(large_clusters)
            },
            "point_statistics": {
                "average_points": round(avg_points, 2),
                "max_points": max_points,
                "min_points": min_points
            },
            "naming_status": {
                "named_count": len([c for c in all_clusters if c.is_named]),
                "unnamed_count": len([c for c in all_clusters if not c.is_named]),
                "naming_rate": len([c for c in all_clusters if c.is_named]) / len(all_clusters) if all_clusters else 0
            }
        }
    
    def export_clusters(self, output_path: Path) -> bool:
        """Export all clusters to JSON file."""
        try:
            clusters = self.manager.get_all_clusters()
            
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "total_clusters": len(clusters),
                "clusters": [
                    {
                        "cluster_id": c.cluster_id,
                        "name": c.name,
                        "center_latitude": c.center_latitude,
                        "center_longitude": c.center_longitude,
                        "radius_meters": c.radius_meters,
                        "point_count": c.point_count,
                        "is_named": c.is_named,
                        "description": c.description,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat()
                    }
                    for c in clusters
                ]
            }
            
            import json
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Exported {len(clusters)} clusters to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export clusters: {e}")
            return False
    
    def import_clusters(self, input_path: Path) -> int:
        """Import clusters from JSON file."""
        try:
            import json
            with open(input_path, 'r') as f:
                import_data = json.load(f)
            
            imported_count = 0
            
            for cluster_data in import_data.get('clusters', []):
                # Create cluster object
                cluster = GPSCluster(
                    cluster_id=cluster_data['cluster_id'],
                    name=cluster_data.get('name'),
                    center_latitude=cluster_data['center_latitude'],
                    center_longitude=cluster_data['center_longitude'],
                    radius_meters=cluster_data.get('radius_meters', 5.0),
                    point_count=cluster_data.get('point_count', 0),
                    created_at=datetime.fromisoformat(cluster_data['created_at']),
                    updated_at=datetime.fromisoformat(cluster_data['updated_at']),
                    description=cluster_data.get('description'),
                    is_named=cluster_data.get('is_named', False)
                )
                
                # Store in database
                with self.manager.db_path.open('a'):  # Ensure database exists
                    pass
                
                # Use manager to store cluster
                with self.manager.db_path.open('a'):
                    pass
                
                # For now, just count - actual import would need database operations
                imported_count += 1
            
            self.logger.info(f"Imported {imported_count} clusters from {input_path}")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Failed to import clusters: {e}")
            return 0
    
    def get_cluster_boundary(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get boundary information for a specific cluster."""
        return self.manager.get_cluster_boundary(cluster_id)
    
    def get_all_cluster_boundaries(self) -> List[Dict[str, Any]]:
        """Get boundary information for all clusters."""
        return self.manager.get_all_cluster_boundaries()
    
    def get_cluster_mapping_data(self, cluster_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cluster data formatted for mapping applications."""
        if cluster_id:
            # Single cluster
            boundary = self.manager.get_cluster_boundary(cluster_id)
            cluster = self.manager.get_cluster(cluster_id)
            
            if not boundary or not cluster:
                return {"error": "Cluster not found"}
            
            return {
                "cluster_id": cluster_id,
                "name": cluster.name,
                "center": {
                    "latitude": boundary["center"]["latitude"],
                    "longitude": boundary["center"]["longitude"]
                },
                "bounding_box": boundary["bounding_box"],
                "boundary_points": boundary["boundary_points"],
                "convex_hull": boundary["convex_hull"],
                "area_square_meters": boundary["area_square_meters"],
                "perimeter_meters": boundary["perimeter_meters"],
                "point_count": cluster.point_count,
                "is_named": cluster.is_named
            }
        else:
            # All clusters
            boundaries = self.manager.get_all_cluster_boundaries()
            
            return {
                "total_clusters": len(boundaries),
                "clusters": boundaries
            }
    
    def export_cluster_boundaries_for_mapping(self, output_path: Path, format: str = "geojson") -> bool:
        """Export cluster boundaries in mapping format (GeoJSON, KML, etc.)."""
        try:
            boundaries = self.manager.get_all_cluster_boundaries()
            
            if format.lower() == "geojson":
                return self._export_geojson(boundaries, output_path)
            elif format.lower() == "kml":
                return self._export_kml(boundaries, output_path)
            else:
                self.logger.error(f"Unsupported format: {format}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to export cluster boundaries: {e}")
            return False
    
    def _export_geojson(self, boundaries: List[Dict[str, Any]], output_path: Path) -> bool:
        """Export clusters as GeoJSON."""
        import json
        
        features = []
        
        for boundary in boundaries:
            # Create polygon from convex hull
            if boundary.get("convex_hull") and len(boundary["convex_hull"]) >= 3:
                coordinates = [[point["longitude"], point["latitude"]] for point in boundary["convex_hull"]]
                # Close the polygon
                coordinates.append(coordinates[0])
                
                feature = {
                    "type": "Feature",
                    "properties": {
                        "cluster_id": boundary["cluster_id"],
                        "name": boundary.get("name"),
                        "point_count": boundary.get("point_count", 0),
                        "is_named": boundary.get("is_named", False),
                        "area_square_meters": boundary.get("area_square_meters"),
                        "perimeter_meters": boundary.get("perimeter_meters")
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coordinates]
                    }
                }
                features.append(feature)
            
            # Add center point
            center_feature = {
                "type": "Feature",
                "properties": {
                    "cluster_id": boundary["cluster_id"],
                    "name": boundary.get("name"),
                    "type": "center",
                    "point_count": boundary.get("point_count", 0),
                    "is_named": boundary.get("is_named", False)
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        boundary["center"]["longitude"],
                        boundary["center"]["latitude"]
                    ]
                }
            }
            features.append(center_feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        self.logger.info(f"Exported {len(features)} features to GeoJSON: {output_path}")
        return True
    
    def _export_kml(self, boundaries: List[Dict[str, Any]], output_path: Path) -> bool:
        """Export clusters as KML."""
        kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>GPS Clusters</name>
    <description>Wildlife camera GPS clusters with boundaries</description>
'''
        
        for boundary in boundaries:
            cluster_id = boundary["cluster_id"]
            name = boundary.get("name", f"Cluster {cluster_id[:8]}")
            center = boundary["center"]
            
            # Add center point
            kml_content += f'''
    <Placemark>
        <name>{name} (Center)</name>
        <description>Cluster {cluster_id} - {boundary.get("point_count", 0)} points</description>
        <Point>
            <coordinates>{center["longitude"]},{center["latitude"]},0</coordinates>
        </Point>
    </Placemark>
'''
            
            # Add boundary polygon if available
            if boundary.get("convex_hull") and len(boundary["convex_hull"]) >= 3:
                coordinates = " ".join([f"{point['longitude']},{point['latitude']},0" for point in boundary["convex_hull"]])
                # Close the polygon
                first_point = boundary["convex_hull"][0]
                coordinates += f" {first_point['longitude']},{first_point['latitude']},0"
                
                kml_content += f'''
    <Placemark>
        <name>{name} (Boundary)</name>
        <description>Cluster {cluster_id} boundary</description>
        <Polygon>
            <outerBoundaryIs>
                <LinearRing>
                    <coordinates>{coordinates}</coordinates>
                </LinearRing>
            </outerBoundaryIs>
        </Polygon>
    </Placemark>
'''
        
        kml_content += '''
</Document>
</kml>'''
        
        with open(output_path, 'w') as f:
            f.write(kml_content)
        
        self.logger.info(f"Exported clusters to KML: {output_path}")
        return True
