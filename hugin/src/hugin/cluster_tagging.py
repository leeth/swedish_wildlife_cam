#!/usr/bin/env python3
"""
Cluster Tagging Service for Hugin

This service provides cluster tagging workflow functionality:
- Request unknown clusters for naming
- Batch naming with change detection
- Overlap detection and merging
- Tagging workflow management
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from .cluster_service import ClusterService
from .gps_clustering import GPSClusterManager


class ClusterTaggingService:
    """Service for managing cluster tagging workflow."""
    
    def __init__(self, db_path: Path, logger: Optional[logging.Logger] = None):
        self.cluster_service = ClusterService(db_path, logger)
        self.manager = self.cluster_service.manager
        self.logger = logger or logging.getLogger(__name__)
        self._last_check_timestamp = None
    
    def request_unknown_clusters(self, limit: int = 50, 
                                min_points: int = 1) -> Dict[str, Any]:
        """Request unknown clusters that need naming."""
        unknown_clusters = self.manager.get_unknown_clusters()
        
        # Filter by minimum points
        filtered_clusters = [
            uc for uc in unknown_clusters 
            if uc.point_count >= min_points
        ]
        
        # Sort by point count (descending) and first seen
        filtered_clusters.sort(key=lambda x: (-x.point_count, x.first_seen))
        
        return {
            "request_id": f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "total_unknown": len(unknown_clusters),
            "filtered_count": len(filtered_clusters),
            "limit": limit,
            "min_points": min_points,
            "clusters": [
                {
                    "cluster_id": uc.cluster_id,
                    "center_latitude": uc.center_latitude,
                    "center_longitude": uc.center_longitude,
                    "point_count": uc.point_count,
                    "first_seen": uc.first_seen.isoformat(),
                    "last_seen": uc.last_seen.isoformat(),
                    "sample_observations": uc.sample_observations[:5]
                }
                for uc in filtered_clusters[:limit]
            ]
        }
    
    def submit_cluster_names(self, cluster_names: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Submit cluster names and detect changes."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "submitted_count": len(cluster_names),
            "successful_names": {},
            "failed_names": {},
            "changes_detected": []
        }
        
        # Extract names and descriptions
        names = {k: v.get('name') for k, v in cluster_names.items()}
        descriptions = {k: v.get('description') for k, v in cluster_names.items() if v.get('description')}
        
        # Batch name clusters
        naming_results = self.manager.batch_name_clusters(names, descriptions)
        
        # Process results
        for cluster_id, success in naming_results.items():
            if success:
                results["successful_names"][cluster_id] = cluster_names[cluster_id]
                results["changes_detected"].append({
                    "cluster_id": cluster_id,
                    "action": "named",
                    "name": names[cluster_id],
                    "description": descriptions.get(cluster_id)
                })
            else:
                results["failed_names"][cluster_id] = cluster_names[cluster_id]
        
        # Update last check timestamp
        self._last_check_timestamp = datetime.now()
        
        self.logger.info(f"Named {len(results['successful_names'])} clusters, {len(results['failed_names'])} failed")
        return results
    
    def detect_overlaps(self, overlap_threshold_meters: float = 10.0) -> Dict[str, Any]:
        """Detect overlapping clusters that might need merging."""
        overlapping_groups = self.manager.detect_overlapping_clusters(overlap_threshold_meters)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overlap_threshold_meters": overlap_threshold_meters,
            "overlapping_groups_count": len(overlapping_groups),
            "total_overlapping_clusters": sum(len(group["clusters"]) for group in overlapping_groups),
            "overlapping_groups": overlapping_groups
        }
    
    def merge_overlapping_clusters(self, merge_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge overlapping clusters with new names."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "merge_requests_count": len(merge_requests),
            "successful_merges": {},
            "failed_merges": {},
            "changes_detected": []
        }
        
        for merge_request in merge_requests:
            cluster_ids = merge_request.get("cluster_ids", [])
            new_name = merge_request.get("new_name")
            new_description = merge_request.get("new_description")
            
            if len(cluster_ids) < 2 or not new_name:
                results["failed_merges"][str(cluster_ids)] = "Invalid merge request"
                continue
            
            # Perform merge
            merged_cluster_id = self.manager.merge_clusters(cluster_ids, new_name, new_description)
            
            if merged_cluster_id:
                results["successful_merges"][str(cluster_ids)] = {
                    "merged_cluster_id": merged_cluster_id,
                    "new_name": new_name,
                    "new_description": new_description
                }
                results["changes_detected"].append({
                    "action": "merged",
                    "original_clusters": cluster_ids,
                    "merged_cluster_id": merged_cluster_id,
                    "new_name": new_name
                })
            else:
                results["failed_merges"][str(cluster_ids)] = "Merge failed"
        
        self.logger.info(f"Merged {len(results['successful_merges'])} cluster groups, {len(results['failed_merges'])} failed")
        return results
    
    def get_changes_since(self, since_timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Get all changes since a timestamp."""
        if since_timestamp is None:
            since_timestamp = self._last_check_timestamp or datetime.now() - timedelta(days=1)
        
        changes = self.manager.get_naming_changes_since(since_timestamp)
        
        # Add overlap detection
        overlaps = self.detect_overlaps()
        changes["overlapping_clusters"] = overlaps
        
        return changes
    
    def export_tagging_workflow(self, output_path: Path) -> bool:
        """Export current tagging workflow state."""
        try:
            # Get current state
            unknown_clusters = self.request_unknown_clusters(limit=1000)
            overlaps = self.detect_overlaps()
            stats = self.cluster_service.get_cluster_analytics()
            
            workflow_state = {
                "export_timestamp": datetime.now().isoformat(),
                "workflow_state": {
                    "unknown_clusters": unknown_clusters,
                    "overlapping_clusters": overlaps,
                    "statistics": stats
                },
                "workflow_metadata": {
                    "total_clusters": stats["basic_stats"]["total_clusters"],
                    "named_clusters": stats["basic_stats"]["named_clusters"],
                    "unknown_clusters": stats["basic_stats"]["unknown_clusters"],
                    "naming_rate": stats["naming_status"]["naming_rate"]
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(workflow_state, f, indent=2)
            
            self.logger.info(f"Exported tagging workflow to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export workflow: {e}")
            return False
    
    def import_tagging_workflow(self, input_path: Path) -> Dict[str, Any]:
        """Import and apply tagging workflow from file."""
        try:
            with open(input_path, 'r') as f:
                workflow_data = json.load(f)
            
            results = {
                "import_timestamp": datetime.now().isoformat(),
                "imported_changes": 0,
                "applied_names": {},
                "applied_merges": {},
                "errors": []
            }
            
            # Apply cluster names if provided
            if "cluster_names" in workflow_data:
                cluster_names = workflow_data["cluster_names"]
                naming_results = self.submit_cluster_names(cluster_names)
                results["applied_names"] = naming_results["successful_names"]
                results["imported_changes"] += len(naming_results["successful_names"])
            
            # Apply merges if provided
            if "merge_requests" in workflow_data:
                merge_requests = workflow_data["merge_requests"]
                merge_results = self.merge_overlapping_clusters(merge_requests)
                results["applied_merges"] = merge_results["successful_merges"]
                results["imported_changes"] += len(merge_results["successful_merges"])
            
            self.logger.info(f"Imported workflow with {results['imported_changes']} changes")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to import workflow: {e}")
            return {"error": str(e)}
    
    def create_tagging_yaml_template(self, output_path: Path) -> bool:
        """Create a YAML template for cluster tagging."""
        try:
            # Get unknown clusters for template
            unknown_request = self.request_unknown_clusters(limit=10)
            
            template = {
                "tagging_workflow": {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "description": "Cluster tagging workflow template"
                },
                "unknown_clusters": {
                    "request_id": unknown_request["request_id"],
                    "clusters": [
                        {
                            "cluster_id": cluster["cluster_id"],
                            "suggested_name": "",  # To be filled by user
                            "description": "",    # To be filled by user
                            "notes": ""           # Optional notes
                        }
                        for cluster in unknown_request["clusters"]
                    ]
                },
                "merge_requests": {
                    "description": "Clusters that overlap and should be merged",
                    "merges": []  # To be filled if overlaps are detected
                }
            }
            
            with open(output_path, 'w') as f:
                yaml.dump(template, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Created tagging template at {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create template: {e}")
            return False
    
    def process_tagging_yaml(self, yaml_path: Path) -> Dict[str, Any]:
        """Process a YAML file with cluster tagging data."""
        try:
            with open(yaml_path, 'r') as f:
                tagging_data = yaml.safe_load(f)
            
            results = {
                "processed_timestamp": datetime.now().isoformat(),
                "yaml_file": str(yaml_path),
                "changes_applied": 0,
                "results": {}
            }
            
            # Process cluster names
            if "unknown_clusters" in tagging_data and "clusters" in tagging_data["unknown_clusters"]:
                cluster_names = {}
                for cluster in tagging_data["unknown_clusters"]["clusters"]:
                    cluster_id = cluster.get("cluster_id")
                    name = cluster.get("suggested_name")
                    description = cluster.get("description")
                    
                    if cluster_id and name:
                        cluster_names[cluster_id] = {
                            "name": name,
                            "description": description or ""
                        }
                
                if cluster_names:
                    naming_results = self.submit_cluster_names(cluster_names)
                    results["results"]["naming"] = naming_results
                    results["changes_applied"] += len(naming_results["successful_names"])
            
            # Process merge requests
            if "merge_requests" in tagging_data and "merges" in tagging_data["merge_requests"]:
                merge_requests = []
                for merge in tagging_data["merge_requests"]["merges"]:
                    if "cluster_ids" in merge and "new_name" in merge:
                        merge_requests.append(merge)
                
                if merge_requests:
                    merge_results = self.merge_overlapping_clusters(merge_requests)
                    results["results"]["merging"] = merge_results
                    results["changes_applied"] += len(merge_results["successful_merges"])
            
            self.logger.info(f"Processed YAML with {results['changes_applied']} changes")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to process YAML: {e}")
            return {"error": str(e)}
