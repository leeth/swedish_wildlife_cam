#!/usr/bin/env python3
"""
Hugin GPS Cluster Management

Specialized Hugin script for GPS cluster management and tagging workflow.
This script focuses specifically on GPS clustering functionality and integrates
with the broader Hugin ecosystem for wildlife camera data analysis.

Features:
- GPS proximity clustering (5m radius)
- Cluster tagging and naming workflow
- Overlap detection and merging
- Analytics integration with cluster data
- YAML-based workflow management
"""

import argparse
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys

from .cluster_service import ClusterService
from .cluster_tagging import ClusterTaggingService
from .cluster_cli import ClusterCLI
from .analytics_engine import AnalyticsEngine


class HuginGPSClusterManagement:
    """Hugin GPS Cluster Management - Specialized cluster management for Hugin."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize services
        db_path = Path(self.config.get('database', {}).get('path', 'hugin_clusters.db'))
        self.cluster_service = ClusterService(db_path, self.logger)
        self.tagging_service = ClusterTaggingService(db_path, self.logger)
        self.analytics_engine = AnalyticsEngine(self.logger)
        
        # Initialize cluster CLI for delegation
        self.cluster_cli = ClusterCLI(config_path)
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'database': {
                'path': 'hugin_clusters.db'
            },
            'clustering': {
                'radius_meters': 5.0,
                'min_points': 1,
                'auto_cluster': True
            },
            'analytics': {
                'include_clusters': True,
                'cluster_analysis': True
            },
            'workflow': {
                'auto_detect_overlaps': True,
                'overlap_threshold': 10.0,
                'auto_merge_similar': False
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                self._deep_merge(default_config, user_config)
        
        return default_config
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('hugin_gps_cluster')
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            self.config['logging']['format']
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, self.config['logging']['level']))
        
        return logger
    
    def process_observations_with_clustering(self, input_data: Path, 
                                           output_dir: Path) -> Dict[str, Any]:
        """Process observations and create GPS clusters."""
        self.logger.info(f"Processing observations with GPS clustering: {input_data}")
        
        # Load observations
        observations = self._load_observations(input_data)
        
        # Process for clustering
        cluster_stats = self.cluster_service.process_observations_dataframe(
            self._observations_to_dataframe(observations)
        )
        
        # Generate cluster-aware analytics
        analytics_results = self._generate_cluster_analytics(observations)
        
        # Export results
        export_results = self._export_cluster_results(analytics_results, output_dir)
        
        return {
            "processing_timestamp": datetime.now().isoformat(),
            "input_data": str(input_data),
            "output_dir": str(output_dir),
            "cluster_stats": cluster_stats,
            "analytics": analytics_results,
            "exports": export_results,
            "success": True
        }
    
    def _load_observations(self, input_data: Path) -> List[Dict[str, Any]]:
        """Load observations from various formats."""
        if input_data.suffix == '.json':
            with open(input_data, 'r') as f:
                return json.load(f)
        elif input_data.suffix == '.yaml':
            with open(input_data, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('observations', [])
        elif input_data.suffix == '.parquet':
            import polars as pl
            df = pl.read_parquet(input_data)
            return df.to_dicts()
        else:
            raise ValueError(f"Unsupported input format: {input_data.suffix}")
    
    def _observations_to_dataframe(self, observations: List[Dict]) -> Any:
        """Convert observations to Polars DataFrame."""
        import polars as pl
        return pl.DataFrame(observations)
    
    def _generate_cluster_analytics(self, observations: List[Dict]) -> Dict[str, Any]:
        """Generate analytics with cluster data integration."""
        df = self._observations_to_dataframe(observations)
        
        # Basic analytics
        analytics = {
            "temporal_report": self.analytics_engine.generate_temporal_report(df),
            "gps_report": self.analytics_engine.generate_gps_report(df)
        }
        
        # Cluster-specific analytics
        cluster_analytics = {
            "cluster_statistics": self.cluster_service.get_cluster_analytics(),
            "cluster_boundaries": self.cluster_service.get_all_cluster_boundaries(),
            "species_by_cluster": self._analyze_species_by_cluster(df),
            "temporal_by_cluster": self._analyze_temporal_by_cluster(df),
            "cluster_activity_patterns": self._analyze_cluster_activity_patterns(df)
        }
        
        analytics["cluster_analytics"] = cluster_analytics
        return analytics
    
    def _analyze_species_by_cluster(self, df) -> Dict[str, Any]:
        """Analyze species distribution by GPS cluster."""
        # Get all clusters
        clusters = self.cluster_service.manager.get_all_clusters()
        
        species_analysis = {}
        for cluster in clusters:
            # Get assignments for this cluster
            assignments = self.cluster_service.manager.get_cluster_assignments(cluster.cluster_id)
            
            if assignments:
                # Analyze species in this cluster
                cluster_species = {}
                for assignment in assignments:
                    # This would need to be connected to observation data
                    # For now, return basic structure
                    pass
                
                species_analysis[cluster.cluster_id] = {
                    "cluster_name": cluster.name,
                    "point_count": cluster.point_count,
                    "species_diversity": 0,  # Would calculate from actual data
                    "dominant_species": "unknown"  # Would determine from data
                }
        
        return {
            "method": "species_by_cluster",
            "description": "Species distribution analysis by GPS cluster",
            "clusters_analyzed": len(clusters),
            "species_by_cluster": species_analysis
        }
    
    def _analyze_temporal_by_cluster(self, df) -> Dict[str, Any]:
        """Analyze temporal patterns by cluster."""
        clusters = self.cluster_service.manager.get_all_clusters()
        
        temporal_analysis = {}
        for cluster in clusters:
            assignments = self.cluster_service.manager.get_cluster_assignments(cluster.cluster_id)
            
            if assignments:
                # Analyze temporal patterns
                timestamps = [a.assigned_at for a in assignments]
                temporal_analysis[cluster.cluster_id] = {
                    "cluster_name": cluster.name,
                    "first_activity": min(timestamps).isoformat() if timestamps else None,
                    "last_activity": max(timestamps).isoformat() if timestamps else None,
                    "activity_duration_days": 0,  # Would calculate
                    "peak_activity_hour": 0  # Would calculate
                }
        
        return {
            "method": "temporal_by_cluster",
            "description": "Temporal pattern analysis by GPS cluster",
            "clusters_analyzed": len(clusters),
            "temporal_by_cluster": temporal_analysis
        }
    
    def _analyze_cluster_activity_patterns(self, df) -> Dict[str, Any]:
        """Analyze activity patterns across clusters."""
        return {
            "method": "cluster_activity_patterns",
            "description": "Activity pattern analysis across GPS clusters",
            "total_clusters": len(self.cluster_service.manager.get_all_clusters()),
            "named_clusters": len(self.cluster_service.manager.get_named_clusters()),
            "unknown_clusters": len(self.cluster_service.manager.get_unknown_clusters())
        }
    
    def _export_cluster_results(self, analytics_results: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Export cluster-aware results."""
        output_dir.mkdir(exist_ok=True)
        exports = {}
        
        # Export analytics JSON
        analytics_file = output_dir / "cluster_analytics.json"
        with open(analytics_file, 'w') as f:
            json.dump(analytics_results, f, indent=2, default=str)
        exports["analytics_json"] = str(analytics_file)
        
        # Export cluster boundaries
        if "cluster_analytics" in analytics_results:
            cluster_boundaries = analytics_results["cluster_analytics"]["cluster_boundaries"]
            
            # GeoJSON export
            geojson_file = output_dir / "cluster_boundaries.geojson"
            self.cluster_service.export_cluster_boundaries_for_mapping(geojson_file, "geojson")
            exports["cluster_geojson"] = str(geojson_file)
            
            # KML export
            kml_file = output_dir / "cluster_boundaries.kml"
            self.cluster_service.export_cluster_boundaries_for_mapping(kml_file, "kml")
            exports["cluster_kml"] = str(kml_file)
            
            # CSV export for cluster statistics
            csv_file = output_dir / "cluster_statistics.csv"
            self._export_cluster_csv(cluster_boundaries, csv_file)
            exports["cluster_csv"] = str(csv_file)
        
        return exports
    
    def _export_cluster_csv(self, cluster_boundaries: List[Dict], output_file: Path) -> None:
        """Export cluster data to CSV."""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            if cluster_boundaries:
                writer = csv.DictWriter(f, fieldnames=cluster_boundaries[0].keys())
                writer.writeheader()
                writer.writerows(cluster_boundaries)
    
    def run_tagging_workflow(self, workflow_config: Path) -> Dict[str, Any]:
        """Run cluster tagging workflow."""
        self.logger.info(f"Running cluster tagging workflow: {workflow_config}")
        
        with open(workflow_config, 'r') as f:
            workflow = yaml.safe_load(f)
        
        results = {
            "workflow_start": datetime.now().isoformat(),
            "workflow_config": str(workflow_config),
            "steps_completed": [],
            "results": {}
        }
        
        try:
            # Step 1: Request unknown clusters
            if workflow.get('request_unknown', {}).get('enabled', False):
                self.logger.info("Step 1: Requesting unknown clusters")
                unknown_request = self.tagging_service.request_unknown_clusters(
                    limit=workflow['request_unknown'].get('limit', 50),
                    min_points=workflow['request_unknown'].get('min_points', 1)
                )
                results["steps_completed"].append("request_unknown")
                results["results"]["unknown_clusters"] = unknown_request
            
            # Step 2: Process naming
            if 'cluster_names' in workflow:
                self.logger.info("Step 2: Processing cluster names")
                naming_results = self.tagging_service.submit_cluster_names(workflow['cluster_names'])
                results["steps_completed"].append("process_names")
                results["results"]["naming"] = naming_results
            
            # Step 3: Detect overlaps
            if workflow.get('detect_overlaps', {}).get('enabled', False):
                self.logger.info("Step 3: Detecting overlaps")
                overlaps = self.tagging_service.detect_overlaps(
                    workflow['detect_overlaps'].get('threshold', 10.0)
                )
                results["steps_completed"].append("detect_overlaps")
                results["results"]["overlaps"] = overlaps
            
            # Step 4: Process merges
            if 'merge_requests' in workflow:
                self.logger.info("Step 4: Processing merge requests")
                merge_results = self.tagging_service.merge_overlapping_clusters(
                    workflow['merge_requests']
                )
                results["steps_completed"].append("process_merges")
                results["results"]["merges"] = merge_results
            
            results["workflow_end"] = datetime.now().isoformat()
            results["success"] = True
            
            self.logger.info("✅ Cluster tagging workflow completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {e}")
            results["errors"] = [str(e)]
            results["success"] = False
        
        return results
    
    def regenerate_analytics_with_clusters(self, input_data: Path, output_dir: Path) -> Dict[str, Any]:
        """Regenerate analytics with current cluster data."""
        self.logger.info("Regenerating analytics with current cluster data")
        
        # Load observations
        observations = self._load_observations(input_data)
        
        # Generate cluster-aware analytics
        analytics_results = self._generate_cluster_analytics(observations)
        
        # Export updated results
        export_results = self._export_cluster_results(analytics_results, output_dir)
        
        return {
            "regeneration_timestamp": datetime.now().isoformat(),
            "input_data": str(input_data),
            "output_dir": str(output_dir),
            "analytics": analytics_results,
            "exports": export_results,
            "success": True
        }


def main():
    """Main Hugin GPS Cluster Management CLI entry point."""
    parser = argparse.ArgumentParser(description="Hugin GPS Cluster Management")
    parser.add_argument("--config", type=Path, help="Configuration YAML file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process observations with clustering
    process_parser = subparsers.add_parser("process", help="Process observations with GPS clustering")
    process_parser.add_argument("input_data", type=Path, help="Input observations file")
    process_parser.add_argument("output_dir", type=Path, help="Output directory")
    
    # Run tagging workflow
    workflow_parser = subparsers.add_parser("workflow", help="Run cluster tagging workflow")
    workflow_parser.add_argument("workflow_config", type=Path, help="Workflow YAML configuration")
    
    # Regenerate analytics
    regenerate_parser = subparsers.add_parser("regenerate", help="Regenerate analytics with current clusters")
    regenerate_parser.add_argument("input_data", type=Path, help="Input observations file")
    regenerate_parser.add_argument("output_dir", type=Path, help="Output directory")
    
    # Cluster management (delegate to cluster CLI)
    cluster_parser = subparsers.add_parser("cluster", help="Cluster management commands")
    cluster_parser.add_argument("cluster_args", nargs=argparse.REMAINDER, help="Cluster CLI arguments")
    
    # Analytics with clusters
    analytics_parser = subparsers.add_parser("analytics", help="Generate cluster-aware analytics")
    analytics_parser.add_argument("input_data", type=Path, help="Input observations file")
    analytics_parser.add_argument("--output", "-o", type=Path, help="Output file")
    analytics_parser.add_argument("--format", choices=["json", "csv", "geojson"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize GPS cluster management
    gps_cluster_mgmt = HuginGPSClusterManagement(args.config)
    
    if args.verbose:
        gps_cluster_mgmt.logger.setLevel(logging.DEBUG)
    
    try:
        if args.command == "process":
            results = gps_cluster_mgmt.process_observations_with_clustering(
                args.input_data, 
                args.output_dir
            )
            
            if results["success"]:
                print("✅ GPS clustering completed successfully")
                print(f"  Observations: {len(gps_cluster_mgmt._load_observations(args.input_data))}")
                if "cluster_stats" in results:
                    stats = results["cluster_stats"]
                    print(f"  Clusters: {stats.get('new_clusters', 0)} new, {stats.get('clustered', 0)} assigned")
                print(f"  Output: {args.output_dir}")
            else:
                print("❌ GPS clustering failed")
                sys.exit(1)
                
        elif args.command == "workflow":
            results = gps_cluster_mgmt.run_tagging_workflow(args.workflow_config)
            
            if results["success"]:
                print("✅ Workflow completed successfully")
                print(f"  Steps: {', '.join(results['steps_completed'])}")
            else:
                print("❌ Workflow failed")
                for error in results.get("errors", []):
                    print(f"  Error: {error}")
                sys.exit(1)
                
        elif args.command == "regenerate":
            results = gps_cluster_mgmt.regenerate_analytics_with_clusters(args.input_data, args.output_dir)
            
            print("✅ Analytics regenerated with cluster data")
            print(f"  Output: {args.output_dir}")
            if "exports" in results:
                for export_type, export_path in results["exports"].items():
                    print(f"  {export_type}: {export_path}")
                    
        elif args.command == "cluster":
            # Delegate to cluster CLI
            sys.argv = ["hugin_gps_cluster_management.py", "cluster"] + args.cluster_args
            from .cluster_cli import main as cluster_main
            cluster_main()
            
        elif args.command == "analytics":
            observations = gps_cluster_mgmt._load_observations(args.input_data)
            analytics_results = gps_cluster_mgmt._generate_cluster_analytics(observations)
            
            if args.output:
                if args.format == "json":
                    with open(args.output, 'w') as f:
                        json.dump(analytics_results, f, indent=2, default=str)
                elif args.format == "geojson":
                    # Export cluster boundaries as GeoJSON
                    if "cluster_analytics" in analytics_results:
                        gps_cluster_mgmt.cluster_service.export_cluster_boundaries_for_mapping(args.output, "geojson")
                
                print(f"✅ Analytics exported to {args.output}")
            else:
                print(json.dumps(analytics_results, indent=2, default=str))
                
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
