#!/usr/bin/env python3
"""
Hugin Master CLI

Master command-line interface that binds all Hugin functionality:
- Wildlife pipeline processing
- GPS cluster management and tagging
- Analytics and reporting
- Data export and visualization
"""

import argparse
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys

# Import all Hugin modules
from .cluster_cli import ClusterCLI
from .cluster_service import ClusterService
from .cluster_tagging import ClusterTaggingService
from .analytics_engine import AnalyticsEngine
from .data_converter import convert_parquet_to_sqlite


class HuginMasterCLI:
    """Master CLI that orchestrates all Hugin functionality."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize services
        db_path = Path(self.config.get('database', {}).get('path', 'hugin.db'))
        self.cluster_service = ClusterService(db_path, self.logger)
        self.tagging_service = ClusterTaggingService(db_path, self.logger)
        self.analytics_engine = AnalyticsEngine(self.logger)
        
        # Initialize cluster CLI
        self.cluster_cli = ClusterCLI(config_path)
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'database': {
                'path': 'hugin.db',
                'clusters_path': 'clusters.db'
            },
            'pipeline': {
                'input_dir': 'data/input',
                'output_dir': 'data/output',
                'temp_dir': 'data/temp'
            },
            'clustering': {
                'radius_meters': 5.0,
                'min_points': 1,
                'auto_cluster': True
            },
            'analytics': {
                'include_clusters': True,
                'cluster_analysis': True,
                'export_formats': ['json', 'csv', 'geojson']
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                # Deep merge with defaults
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
        logger = logging.getLogger('hugin_master')
        
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
    
    def process_pipeline(self, input_data: Path, output_dir: Path, 
                        include_clustering: bool = True) -> Dict[str, Any]:
        """Process complete Hugin pipeline with clustering."""
        self.logger.info(f"Starting Hugin pipeline processing: {input_data}")
        
        results = {
            "pipeline_start": datetime.now().isoformat(),
            "input_data": str(input_data),
            "output_dir": str(output_dir),
            "steps_completed": [],
            "errors": []
        }
        
        try:
            # Step 1: Load and process observations
            self.logger.info("Step 1: Loading observations")
            observations = self._load_observations(input_data)
            results["steps_completed"].append("load_observations")
            results["observation_count"] = len(observations)
            
            # Step 2: GPS clustering (if enabled)
            if include_clustering and self.config['clustering']['auto_cluster']:
                self.logger.info("Step 2: GPS clustering")
                cluster_stats = self.cluster_service.process_observations_dataframe(
                    self._observations_to_dataframe(observations)
                )
                results["steps_completed"].append("gps_clustering")
                results["cluster_stats"] = cluster_stats
            
            # Step 3: Analytics with cluster data
            self.logger.info("Step 3: Analytics processing")
            analytics_results = self._run_analytics(observations, include_clustering)
            results["steps_completed"].append("analytics")
            results["analytics"] = analytics_results
            
            # Step 4: Export results
            self.logger.info("Step 4: Exporting results")
            export_results = self._export_results(analytics_results, output_dir)
            results["steps_completed"].append("export")
            results["exports"] = export_results
            
            results["pipeline_end"] = datetime.now().isoformat()
            results["success"] = True
            
            self.logger.info("✅ Hugin pipeline completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}")
            results["errors"].append(str(e))
            results["success"] = False
        
        return results
    
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
    
    def _run_analytics(self, observations: List[Dict], include_clusters: bool) -> Dict[str, Any]:
        """Run analytics with optional cluster data."""
        df = self._observations_to_dataframe(observations)
        
        # Basic analytics
        analytics_results = {
            "temporal_report": self.analytics_engine.generate_temporal_report(df),
            "gps_report": self.analytics_engine.generate_gps_report(df)
        }
        
        # Cluster-aware analytics
        if include_clusters:
            cluster_analytics = self._run_cluster_analytics(df)
            analytics_results["cluster_analytics"] = cluster_analytics
        
        return analytics_results
    
    def _run_cluster_analytics(self, df) -> Dict[str, Any]:
        """Run cluster-aware analytics."""
        # Get cluster statistics
        cluster_stats = self.cluster_service.get_cluster_analytics()
        
        # Get cluster boundaries for mapping
        cluster_boundaries = self.cluster_service.get_all_cluster_boundaries()
        
        # Analyze species by cluster
        species_by_cluster = self._analyze_species_by_cluster(df)
        
        # Analyze temporal patterns by cluster
        temporal_by_cluster = self._analyze_temporal_by_cluster(df)
        
        return {
            "cluster_statistics": cluster_stats,
            "cluster_boundaries": cluster_boundaries,
            "species_by_cluster": species_by_cluster,
            "temporal_by_cluster": temporal_by_cluster
        }
    
    def _analyze_species_by_cluster(self, df) -> Dict[str, Any]:
        """Analyze species distribution by cluster."""
        # This would require joining observations with cluster assignments
        # For now, return basic structure
        return {
            "method": "species_by_cluster",
            "description": "Species distribution analysis by GPS cluster",
            "clusters_analyzed": len(self.cluster_service.get_all_clusters())
        }
    
    def _analyze_temporal_by_cluster(self, df) -> Dict[str, Any]:
        """Analyze temporal patterns by cluster."""
        return {
            "method": "temporal_by_cluster",
            "description": "Temporal pattern analysis by GPS cluster",
            "clusters_analyzed": len(self.cluster_service.get_all_clusters())
        }
    
    def _export_results(self, analytics_results: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Export results in multiple formats."""
        output_dir.mkdir(exist_ok=True)
        exports = {}
        
        # Export analytics JSON
        analytics_file = output_dir / "analytics_report.json"
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
        
        return exports
    
    def run_cluster_workflow(self, workflow_config: Path) -> Dict[str, Any]:
        """Run cluster tagging workflow from configuration."""
        self.logger.info(f"Running cluster workflow: {workflow_config}")
        
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
            
            # Step 2: Process naming if provided
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
            
            # Step 4: Process merges if provided
            if 'merge_requests' in workflow:
                self.logger.info("Step 4: Processing merge requests")
                merge_results = self.tagging_service.merge_overlapping_clusters(
                    workflow['merge_requests']
                )
                results["steps_completed"].append("process_merges")
                results["results"]["merges"] = merge_results
            
            results["workflow_end"] = datetime.now().isoformat()
            results["success"] = True
            
            self.logger.info("✅ Cluster workflow completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {e}")
            results["errors"] = [str(e)]
            results["success"] = False
        
        return results
    
    def regenerate_analytics(self, input_data: Path, output_dir: Path) -> Dict[str, Any]:
        """Regenerate analytics report with current cluster data."""
        self.logger.info("Regenerating analytics with current cluster data")
        
        # Load observations
        observations = self._load_observations(input_data)
        
        # Run analytics with cluster data
        analytics_results = self._run_analytics(observations, include_clusters=True)
        
        # Export updated results
        export_results = self._export_results(analytics_results, output_dir)
        
        return {
            "regeneration_timestamp": datetime.now().isoformat(),
            "input_data": str(input_data),
            "output_dir": str(output_dir),
            "analytics": analytics_results,
            "exports": export_results,
            "success": True
        }


def main():
    """Main Hugin Master CLI entry point."""
    parser = argparse.ArgumentParser(description="Hugin Master CLI - Wildlife Pipeline Management")
    parser.add_argument("--config", type=Path, help="Configuration YAML file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Run complete Hugin pipeline")
    pipeline_parser.add_argument("input_data", type=Path, help="Input observations file")
    pipeline_parser.add_argument("output_dir", type=Path, help="Output directory")
    pipeline_parser.add_argument("--no-clustering", action="store_true", help="Skip GPS clustering")
    
    # Cluster workflow command
    workflow_parser = subparsers.add_parser("workflow", help="Run cluster tagging workflow")
    workflow_parser.add_argument("workflow_config", type=Path, help="Workflow YAML configuration")
    
    # Regenerate analytics command
    regenerate_parser = subparsers.add_parser("regenerate", help="Regenerate analytics with current clusters")
    regenerate_parser.add_argument("input_data", type=Path, help="Input observations file")
    regenerate_parser.add_argument("output_dir", type=Path, help="Output directory")
    
    # Cluster management (delegate to cluster CLI)
    cluster_parser = subparsers.add_parser("cluster", help="Cluster management commands")
    cluster_parser.add_argument("cluster_args", nargs=argparse.REMAINDER, help="Cluster CLI arguments")
    
    # Analytics command
    analytics_parser = subparsers.add_parser("analytics", help="Analytics and reporting")
    analytics_parser.add_argument("input_data", type=Path, help="Input observations file")
    analytics_parser.add_argument("--output", "-o", type=Path, help="Output file")
    analytics_parser.add_argument("--format", choices=["json", "csv", "geojson"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize master CLI
    master_cli = HuginMasterCLI(args.config)
    
    if args.verbose:
        master_cli.logger.setLevel(logging.DEBUG)
    
    try:
        if args.command == "pipeline":
            results = master_cli.process_pipeline(
                args.input_data, 
                args.output_dir, 
                include_clustering=not args.no_clustering
            )
            
            if results["success"]:
                print("✅ Pipeline completed successfully")
                print(f"  Observations: {results.get('observation_count', 0)}")
                print(f"  Steps: {', '.join(results['steps_completed'])}")
                if "cluster_stats" in results:
                    stats = results["cluster_stats"]
                    print(f"  Clusters: {stats.get('new_clusters', 0)} new, {stats.get('clustered', 0)} assigned")
            else:
                print("❌ Pipeline failed")
                for error in results.get("errors", []):
                    print(f"  Error: {error}")
                sys.exit(1)
                
        elif args.command == "workflow":
            results = master_cli.run_cluster_workflow(args.workflow_config)
            
            if results["success"]:
                print("✅ Workflow completed successfully")
                print(f"  Steps: {', '.join(results['steps_completed'])}")
            else:
                print("❌ Workflow failed")
                for error in results.get("errors", []):
                    print(f"  Error: {error}")
                sys.exit(1)
                
        elif args.command == "regenerate":
            results = master_cli.regenerate_analytics(args.input_data, args.output_dir)
            
            print("✅ Analytics regenerated successfully")
            print(f"  Output: {args.output_dir}")
            if "exports" in results:
                for export_type, export_path in results["exports"].items():
                    print(f"  {export_type}: {export_path}")
                    
        elif args.command == "cluster":
            # Delegate to cluster CLI
            import sys
            sys.argv = ["hugin_cli.py", "cluster"] + args.cluster_args
            from .cluster_cli import main as cluster_main
            cluster_main()
            
        elif args.command == "analytics":
            observations = master_cli._load_observations(args.input_data)
            analytics_results = master_cli._run_analytics(observations, include_clusters=True)
            
            if args.output:
                if args.format == "json":
                    with open(args.output, 'w') as f:
                        json.dump(analytics_results, f, indent=2, default=str)
                elif args.format == "csv":
                    # Convert to CSV (simplified)
                    import pandas as pd
                    # This would need proper CSV conversion logic
                    print("CSV export not fully implemented")
                elif args.format == "geojson":
                    # Export cluster boundaries as GeoJSON
                    if "cluster_analytics" in analytics_results:
                        boundaries = analytics_results["cluster_analytics"]["cluster_boundaries"]
                        master_cli.cluster_service.export_cluster_boundaries_for_mapping(args.output, "geojson")
                
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
