#!/usr/bin/env python3
"""
GPS Cluster CLI for Hugin

Command-line interface for GPS cluster management with YAML configuration support.
Provides functionality to:
- Process observations for clustering
- Manage cluster naming
- Export cluster boundaries for mapping
- Handle unknown clusters
"""

import argparse
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .cluster_service import ClusterService
from .cluster_tagging import ClusterTaggingService
from .data_models import GPSCluster


class ClusterCLI:
    """Command-line interface for GPS cluster management."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize cluster service
        db_path = Path(self.config.get('database', {}).get('path', 'clusters.db'))
        self.cluster_service = ClusterService(db_path, self.logger)
        self.tagging_service = ClusterTaggingService(db_path, self.logger)
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'database': {
                'path': 'clusters.db'
            },
            'clustering': {
                'radius_meters': 5.0,
                'min_points': 1
            },
            'export': {
                'formats': ['geojson', 'kml', 'json'],
                'output_dir': 'exports'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(user_config)
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('cluster_cli')
        
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
    
    def process_observations(self, input_file: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """Process observations file for clustering."""
        self.logger.info(f"Processing observations from {input_file}")
        
        # Load observations
        if input_file.suffix == '.json':
            with open(input_file, 'r') as f:
                observations = json.load(f)
        elif input_file.suffix == '.yaml':
            with open(input_file, 'r') as f:
                observations = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file format: {input_file.suffix}")
        
        # Process observations
        stats = self.cluster_service.process_observations_dataframe(
            self._observations_to_dataframe(observations)
        )
        
        # Save results if output file specified
        if output_file:
            results = {
                'processing_stats': stats,
                'timestamp': datetime.now().isoformat(),
                'input_file': str(input_file)
            }
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Results saved to {output_file}")
        
        return stats
    
    def _observations_to_dataframe(self, observations: List[Dict]) -> Any:
        """Convert observations to Polars DataFrame."""
        import polars as pl
        
        return pl.DataFrame(observations)
    
    def list_clusters(self, named_only: bool = False) -> List[Dict[str, Any]]:
        """List all clusters."""
        if named_only:
            clusters = self.cluster_service.manager.get_named_clusters()
        else:
            clusters = self.cluster_service.manager.get_all_clusters()
        
        return [
            {
                'cluster_id': c.cluster_id,
                'name': c.name,
                'center_latitude': c.center_latitude,
                'center_longitude': c.center_longitude,
                'point_count': c.point_count,
                'is_named': c.is_named,
                'created_at': c.created_at.isoformat()
            }
            for c in clusters
        ]
    
    def get_unknown_clusters(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unknown clusters that need naming."""
        return self.cluster_service.get_unknown_clusters_for_naming(limit)
    
    def name_cluster(self, cluster_id: str, name: str, description: Optional[str] = None) -> bool:
        """Name an unknown cluster."""
        success = self.cluster_service.name_unknown_cluster(cluster_id, name, description)
        
        if success:
            self.logger.info(f"Named cluster {cluster_id} as '{name}'")
        else:
            self.logger.error(f"Failed to name cluster {cluster_id}")
        
        return success
    
    def get_cluster_details(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cluster."""
        return self.cluster_service.get_cluster_details(cluster_id)
    
    def get_cluster_boundary(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster boundary information."""
        return self.cluster_service.get_cluster_boundary(cluster_id)
    
    def export_clusters(self, output_dir: Path, formats: List[str] = None) -> Dict[str, bool]:
        """Export clusters in various formats."""
        if formats is None:
            formats = self.config['export']['formats']
        
        output_dir.mkdir(exist_ok=True)
        results = {}
        
        for format_type in formats:
            output_file = output_dir / f"clusters.{format_type}"
            
            if format_type in ['geojson', 'kml']:
                success = self.cluster_service.export_cluster_boundaries_for_mapping(
                    output_file, format_type
                )
            else:
                # JSON export
                clusters = self.cluster_service.get_all_cluster_boundaries()
                with open(output_file, 'w') as f:
                    json.dump(clusters, f, indent=2)
                success = True
            
            results[format_type] = success
            
            if success:
                self.logger.info(f"Exported clusters to {output_file}")
            else:
                self.logger.error(f"Failed to export {format_type}")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cluster statistics."""
        return self.cluster_service.get_cluster_analytics()
    
    def search_clusters(self, latitude: float, longitude: float, radius_meters: float = 100.0) -> List[Dict[str, Any]]:
        """Search for clusters near a location."""
        return self.cluster_service.search_clusters_by_location(latitude, longitude, radius_meters)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GPS Cluster Management CLI")
    parser.add_argument("--config", type=Path, help="Configuration YAML file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process observations command
    process_parser = subparsers.add_parser("process", help="Process observations for clustering")
    process_parser.add_argument("input_file", type=Path, help="Input observations file (JSON/YAML)")
    process_parser.add_argument("--output", "-o", type=Path, help="Output results file")
    
    # List clusters command
    list_parser = subparsers.add_parser("list", help="List clusters")
    list_parser.add_argument("--named-only", action="store_true", help="Show only named clusters")
    
    # Unknown clusters command
    unknown_parser = subparsers.add_parser("unknown", help="Show unknown clusters")
    unknown_parser.add_argument("--limit", type=int, default=50, help="Limit number of results")
    
    # Name cluster command
    name_parser = subparsers.add_parser("name", help="Name an unknown cluster")
    name_parser.add_argument("cluster_id", help="Cluster ID to name")
    name_parser.add_argument("name", help="Name for the cluster")
    name_parser.add_argument("--description", help="Cluster description")
    
    # Cluster details command
    details_parser = subparsers.add_parser("details", help="Get cluster details")
    details_parser.add_argument("cluster_id", help="Cluster ID")
    
    # Cluster boundary command
    boundary_parser = subparsers.add_parser("boundary", help="Get cluster boundary")
    boundary_parser.add_argument("cluster_id", help="Cluster ID")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export clusters")
    export_parser.add_argument("output_dir", type=Path, help="Output directory")
    export_parser.add_argument("--formats", nargs="+", choices=["geojson", "kml", "json"], 
                              help="Export formats")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show cluster statistics")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search clusters near location")
    search_parser.add_argument("latitude", type=float, help="Latitude")
    search_parser.add_argument("longitude", type=float, help="Longitude")
    search_parser.add_argument("--radius", type=float, default=100.0, help="Search radius in meters")
    
    # Tagging workflow commands
    request_parser = subparsers.add_parser("request-unknown", help="Request unknown clusters for naming")
    request_parser.add_argument("--limit", type=int, default=50, help="Limit number of clusters")
    request_parser.add_argument("--min-points", type=int, default=1, help="Minimum points per cluster")
    request_parser.add_argument("--output", "-o", type=Path, help="Output YAML file")
    
    submit_parser = subparsers.add_parser("submit-names", help="Submit cluster names")
    submit_parser.add_argument("yaml_file", type=Path, help="YAML file with cluster names")
    
    overlaps_parser = subparsers.add_parser("detect-overlaps", help="Detect overlapping clusters")
    overlaps_parser.add_argument("--threshold", type=float, default=10.0, help="Overlap threshold in meters")
    
    merge_parser = subparsers.add_parser("merge-clusters", help="Merge overlapping clusters")
    merge_parser.add_argument("yaml_file", type=Path, help="YAML file with merge requests")
    
    template_parser = subparsers.add_parser("create-template", help="Create tagging template")
    template_parser.add_argument("output_file", type=Path, help="Output YAML template file")
    
    changes_parser = subparsers.add_parser("changes", help="Get changes since last check")
    changes_parser.add_argument("--since", type=str, help="Since timestamp (ISO format)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = ClusterCLI(args.config)
    
    if args.verbose:
        cli.logger.setLevel(logging.DEBUG)
    
    # Execute command
    try:
        if args.command == "process":
            stats = cli.process_observations(args.input_file, args.output)
            print(f"Processed {stats.get('processed', 0)} observations")
            print(f"Created {stats.get('new_clusters', 0)} new clusters")
            
        elif args.command == "list":
            clusters = cli.list_clusters(args.named_only)
            print(f"Found {len(clusters)} clusters:")
            for cluster in clusters:
                status = "Named" if cluster['is_named'] else "Unknown"
                print(f"  {cluster['cluster_id'][:8]} - {cluster['name'] or 'Unnamed'} ({status}) - {cluster['point_count']} points")
                
        elif args.command == "unknown":
            unknown = cli.get_unknown_clusters(args.limit)
            print(f"Found {len(unknown)} unknown clusters:")
            for cluster in unknown:
                print(f"  {cluster['cluster_id'][:8]} - {cluster['point_count']} points at ({cluster['center_latitude']:.6f}, {cluster['center_longitude']:.6f})")
                
        elif args.command == "name":
            success = cli.name_cluster(args.cluster_id, args.name, args.description)
            if success:
                print(f"✅ Named cluster {args.cluster_id} as '{args.name}'")
            else:
                print(f"❌ Failed to name cluster {args.cluster_id}")
                
        elif args.command == "details":
            details = cli.get_cluster_details(args.cluster_id)
            if details:
                print(json.dumps(details, indent=2))
            else:
                print(f"Cluster {args.cluster_id} not found")
                
        elif args.command == "boundary":
            boundary = cli.get_cluster_boundary(args.cluster_id)
            if boundary:
                print(json.dumps(boundary, indent=2))
            else:
                print(f"Boundary for cluster {args.cluster_id} not found")
                
        elif args.command == "export":
            results = cli.export_clusters(args.output_dir, args.formats)
            for format_type, success in results.items():
                status = "✅" if success else "❌"
                print(f"{status} {format_type.upper()}: {args.output_dir}/clusters.{format_type}")
                
        elif args.command == "stats":
            stats = cli.get_statistics()
            print("📊 Cluster Statistics:")
            print(f"  Total clusters: {stats['basic_stats']['total_clusters']}")
            print(f"  Named clusters: {stats['basic_stats']['named_clusters']}")
            print(f"  Unknown clusters: {stats['basic_stats']['unknown_clusters']}")
            print(f"  Total assignments: {stats['basic_stats']['total_assignments']}")
            print(f"  Average points per cluster: {stats['point_statistics']['average_points']}")
            print(f"  Naming rate: {stats['naming_status']['naming_rate']:.1%}")
            
        elif args.command == "search":
            clusters = cli.search_clusters(args.latitude, args.longitude, args.radius)
            print(f"Found {len(clusters)} clusters within {args.radius}m:")
            for cluster in clusters:
                print(f"  {cluster['cluster_id'][:8]} - {cluster['name'] or 'Unnamed'} - {cluster['distance_meters']:.1f}m away")
                
        elif args.command == "request-unknown":
            unknown = cli.tagging_service.request_unknown_clusters(args.limit, args.min_points)
            print(f"Found {unknown['filtered_count']} unknown clusters (filtered from {unknown['total_unknown']} total)")
            
            if args.output:
                with open(args.output, 'w') as f:
                    yaml.dump(unknown, f, default_flow_style=False, indent=2)
                print(f"Saved to {args.output}")
            else:
                for cluster in unknown['clusters']:
                    print(f"  {cluster['cluster_id'][:8]} - {cluster['point_count']} points at ({cluster['center_latitude']:.6f}, {cluster['center_longitude']:.6f})")
                    
        elif args.command == "submit-names":
            results = cli.tagging_service.process_tagging_yaml(args.yaml_file)
            if "error" in results:
                print(f"❌ Error: {results['error']}")
            else:
                print(f"✅ Processed {results['changes_applied']} changes from {args.yaml_file}")
                if "results" in results:
                    if "naming" in results["results"]:
                        naming = results["results"]["naming"]
                        print(f"  Named: {len(naming.get('successful_names', {}))}")
                        print(f"  Failed: {len(naming.get('failed_names', {}))}")
                    if "merging" in results["results"]:
                        merging = results["results"]["merging"]
                        print(f"  Merged: {len(merging.get('successful_merges', {}))}")
                        print(f"  Failed: {len(merging.get('failed_merges', {}))}")
                        
        elif args.command == "detect-overlaps":
            overlaps = cli.tagging_service.detect_overlaps(args.threshold)
            print(f"Found {overlaps['overlapping_groups_count']} overlapping groups with {overlaps['total_overlapping_clusters']} total clusters")
            
            for group in overlaps['overlapping_groups']:
                print(f"  Group {group['group_id']}: {len(group['clusters'])} clusters (distance: {group['overlap_distance']:.1f}m)")
                for cluster in group['clusters']:
                    print(f"    {cluster['cluster_id'][:8]} - {cluster['name'] or 'Unnamed'} - {cluster['point_count']} points")
                    
        elif args.command == "merge-clusters":
            results = cli.tagging_service.process_tagging_yaml(args.yaml_file)
            if "error" in results:
                print(f"❌ Error: {results['error']}")
            else:
                print(f"✅ Processed merge requests from {args.yaml_file}")
                if "results" in results and "merging" in results["results"]:
                    merging = results["results"]["merging"]
                    print(f"  Successful merges: {len(merging.get('successful_merges', {}))}")
                    print(f"  Failed merges: {len(merging.get('failed_merges', {}))}")
                    
        elif args.command == "create-template":
            success = cli.tagging_service.create_tagging_yaml_template(args.output_file)
            if success:
                print(f"✅ Created tagging template at {args.output_file}")
            else:
                print(f"❌ Failed to create template")
                
        elif args.command == "changes":
            since_timestamp = None
            if args.since:
                since_timestamp = datetime.fromisoformat(args.since)
            
            changes = cli.tagging_service.get_changes_since(since_timestamp)
            print(f"Changes since {changes.get('since', 'beginning')}:")
            print(f"  Newly named clusters: {changes.get('newly_named_count', 0)}")
            print(f"  Overlapping groups: {changes.get('overlapping_clusters', {}).get('overlapping_groups_count', 0)}")
            
            if changes.get('clusters'):
                print("  Recently named clusters:")
                for cluster in changes['clusters']:
                    print(f"    {cluster['cluster_id'][:8]} - {cluster['name']} - {cluster['point_count']} points")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
