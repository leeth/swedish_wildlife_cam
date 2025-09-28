#!/usr/bin/env python3
"""
Hugin Stage 2 Workflow

This module handles Hugin's stage 2 processing after Munin stage 1:
2.1 - Menneske eller dyr detection
2.2 - Species detection (hvilket dyr)
2.3 - Dan cluster og data observations
2.4 - Berig med cluster navn for pretty reporting
"""

import argparse
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import sys

from .cluster_service import ClusterService
from .cluster_tagging import ClusterTaggingService
from .analytics_engine import AnalyticsEngine
from .data_models import GPSCluster


class HuginStage2Workflow:
    """Hugin Stage 2 workflow for image analysis and location clustering."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        
        # Initialize services
        db_path = Path(self.config.get('database', {}).get('path', 'hugin_post_s2.db'))
        self.cluster_service = ClusterService(db_path, self.logger)
        self.tagging_service = ClusterTaggingService(db_path, self.logger)
        self.analytics_engine = AnalyticsEngine(self.logger, self.cluster_service)
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            'database': {
                'path': 'hugin_post_s2.db'
            },
            'image_analysis': {
                'species_detection': True,
                'confidence_threshold': 0.5,
                'batch_size': 100
            },
            'location_clustering': {
                'enabled': True,
                'radius_meters': 5.0,
                'min_points': 1,
                'auto_cluster': True
            },
            'data_condensation': {
                'enabled': True,
                'time_window_minutes': 10,
                'aggregation_method': 'count',
                'include_species_breakdown': True
            },
            'output': {
                'include_cluster_names': True,
                'unknown_cluster_prefix': 'Unknown_Cluster_',
                'export_formats': ['json', 'csv', 'geojson'],
                'decouple_labeling': True
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
        logger = logging.getLogger('hugin_post_s2')
        
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
    
    def process_hugin_stage2_workflow(self, munin_results: Path, output_dir: Path) -> Dict[str, Any]:
        """Process complete Hugin Stage 2 workflow."""
        self.logger.info(f"Starting Hugin Stage 2 workflow: {munin_results}")
        
        results = {
            "workflow_start": datetime.now().isoformat(),
            "munin_results": str(munin_results),
            "output_dir": str(output_dir),
            "stages_completed": [],
            "errors": []
        }
        
        try:
            # Stage 2.1: Load Munin results
            self.logger.info("Stage 2.1: Loading Munin results")
            munin_data = self._load_munin_results(munin_results)
            results["stages_completed"].append("load_munin_results")
            results["munin_observations"] = len(munin_data)
            
            # Stage 2.1: Menneske eller dyr detection
            if self.config['stage_2_1']['enabled']:
                self.logger.info("Stage 2.1: Menneske eller dyr detection")
                human_animal_results = self._detect_human_or_animal(munin_data)
                results["stages_completed"].append("human_animal_detection")
                results["stage_2_1"] = human_animal_results
            
            # Stage 2.2: Species detection (hvilket dyr)
            if self.config['stage_2_2']['enabled']:
                self.logger.info("Stage 2.2: Species detection (hvilket dyr)")
                species_results = self._detect_species(munin_data)
                results["stages_completed"].append("species_detection")
                results["stage_2_2"] = species_results
            
            # Stage 2.3: Dan cluster og data observations
            if self.config['stage_2_3']['enabled']:
                self.logger.info("Stage 2.3: Dan cluster og data observations")
                cluster_results = self._create_clusters_and_observations(munin_data)
                results["stages_completed"].append("cluster_and_observations")
                results["stage_2_3"] = cluster_results
            
            # Stage 2.4: Berig med cluster navn for pretty reporting
            if self.config['stage_2_4']['enabled']:
                self.logger.info("Stage 2.4: Berig med cluster navn for pretty reporting")
                enrichment_results = self._enrich_with_cluster_names(munin_data)
                results["stages_completed"].append("cluster_name_enrichment")
                results["stage_2_4"] = enrichment_results
            
            # Generate final output
            self.logger.info("Generating final output")
            output_results = self._generate_final_output(munin_data, output_dir)
            results["stages_completed"].append("generate_output")
            results["output"] = output_results
            
            results["workflow_end"] = datetime.now().isoformat()
            results["success"] = True
            
            self.logger.info("✅ Hugin Stage 2 workflow completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Hugin Stage 2 workflow failed: {e}")
            results["errors"].append(str(e))
            results["success"] = False
        
        return results
    
    def _load_munin_results(self, munin_results: Path) -> List[Dict[str, Any]]:
        """Load Munin results from various formats."""
        if munin_results.suffix == '.json':
            with open(munin_results, 'r') as f:
                return json.load(f)
        elif munin_results.suffix == '.yaml':
            with open(munin_results, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('observations', [])
        elif munin_results.suffix == '.parquet':
            import polars as pl
            df = pl.read_parquet(munin_results)
            return df.to_dicts()
        else:
            raise ValueError(f"Unsupported Munin results format: {munin_results.suffix}")
    
    def _analyze_images_for_species(self, s2_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze images for species determination."""
        self.logger.info("Analyzing images for species determination")
        
        # This would integrate with Hugin's species detection
        # For now, return basic structure
        species_analysis = {
            "total_images": len(s2_data),
            "species_detected": [],
            "confidence_scores": [],
            "processing_time": 0
        }
        
        # Analyze each image
        for observation in s2_data:
            # This would call Hugin's species detection
            # For now, extract basic info
            if 'species' in observation:
                species_analysis["species_detected"].append(observation['species'])
            if 'confidence' in observation:
                species_analysis["confidence_scores"].append(observation['confidence'])
        
        return species_analysis
    
    def _cluster_locations(self, s2_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cluster locations based on GPS coordinates."""
        self.logger.info("Clustering locations based on GPS coordinates")
        
        # Filter data with GPS coordinates
        gps_data = [
            obs for obs in s2_data 
            if obs.get('gps_latitude') and obs.get('gps_longitude')
        ]
        
        if not gps_data:
            self.logger.warning("No GPS data found for clustering")
            return {"error": "No GPS data found"}
        
        # Process for clustering
        cluster_stats = self.cluster_service.process_observations_dataframe(
            self._data_to_dataframe(gps_data)
        )
        
        # Get cluster information
        clusters = self.cluster_service.manager.get_all_clusters()
        unknown_clusters = self.cluster_service.manager.get_unknown_clusters()
        
        return {
            "cluster_stats": cluster_stats,
            "total_clusters": len(clusters),
            "unknown_clusters": len(unknown_clusters),
            "named_clusters": len([c for c in clusters if c.is_named]),
            "gps_data_points": len(gps_data)
        }
    
    def _condense_data(self, s2_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Condense data with configurable time windows."""
        self.logger.info("Condensing data with time windows")
        
        time_window = self.config['data_condensation']['time_window_minutes']
        aggregation_method = self.config['data_condensation']['aggregation_method']
        
        # Group data by time windows
        condensed_data = {}
        
        for observation in s2_data:
            if 'timestamp' in observation:
                # Round timestamp to time window
                timestamp = datetime.fromisoformat(observation['timestamp'])
                window_start = timestamp.replace(
                    minute=(timestamp.minute // time_window) * time_window,
                    second=0,
                    microsecond=0
                )
                window_key = window_start.isoformat()
                
                if window_key not in condensed_data:
                    condensed_data[window_key] = {
                        'window_start': window_start.isoformat(),
                        'window_end': (window_start + timedelta(minutes=time_window)).isoformat(),
                        'observations': [],
                        'species_count': {},
                        'total_observations': 0
                    }
                
                condensed_data[window_key]['observations'].append(observation)
                condensed_data[window_key]['total_observations'] += 1
                
                # Count species
                species = observation.get('species', 'unknown')
                if species not in condensed_data[window_key]['species_count']:
                    condensed_data[window_key]['species_count'][species] = 0
                condensed_data[window_key]['species_count'][species] += 1
        
        return {
            "time_window_minutes": time_window,
            "aggregation_method": aggregation_method,
            "total_windows": len(condensed_data),
            "condensed_data": condensed_data
        }
    
    def _generate_output(self, s2_data: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
        """Generate output with cluster names (user-provided only)."""
        self.logger.info("Generating output with cluster information")
        
        output_dir.mkdir(exist_ok=True)
        exports = {}
        
        # Get cluster information
        clusters = self.cluster_service.manager.get_all_clusters()
        unknown_clusters = self.cluster_service.manager.get_unknown_clusters()
        
        # Generate cluster-aware output
        cluster_output = {
            "processing_timestamp": datetime.now().isoformat(),
            "total_observations": len(s2_data),
            "clusters": [],
            "unknown_clusters": [],
            "decoupled_labeling": self.config['output']['decouple_labeling']
        }
        
        # Add named clusters
        for cluster in clusters:
            if cluster.is_named:
                cluster_output["clusters"].append({
                    "cluster_id": cluster.cluster_id,
                    "name": cluster.name,
                    "center_latitude": cluster.center_latitude,
                    "center_longitude": cluster.center_longitude,
                    "point_count": cluster.point_count,
                    "description": cluster.description
                })
        
        # Add unknown clusters with generated names
        for i, unknown_cluster in enumerate(unknown_clusters):
            generated_name = f"{self.config['output']['unknown_cluster_prefix']}{i+1}"
            cluster_output["unknown_clusters"].append({
                "cluster_id": unknown_cluster.cluster_id,
                "generated_name": generated_name,
                "center_latitude": unknown_cluster.center_latitude,
                "center_longitude": unknown_cluster.center_longitude,
                "point_count": unknown_cluster.point_count,
                "first_seen": unknown_cluster.first_seen.isoformat(),
                "last_seen": unknown_cluster.last_seen.isoformat()
            })
        
        # Export JSON
        json_file = output_dir / "cluster_analysis.json"
        with open(json_file, 'w') as f:
            json.dump(cluster_output, f, indent=2, default=str)
        exports["cluster_analysis_json"] = str(json_file)
        
        # Export cluster boundaries
        if clusters:
            geojson_file = output_dir / "cluster_boundaries.geojson"
            self.cluster_service.export_cluster_boundaries_for_mapping(geojson_file, "geojson")
            exports["cluster_boundaries_geojson"] = str(geojson_file)
            
            kml_file = output_dir / "cluster_boundaries.kml"
            self.cluster_service.export_cluster_boundaries_for_mapping(kml_file, "kml")
            exports["cluster_boundaries_kml"] = str(kml_file)
        
        # Export condensed data
        condensed_data = self._condense_data(s2_data)
        if condensed_data and "condensed_data" in condensed_data:
            csv_file = output_dir / "condensed_data.csv"
            self._export_condensed_csv(condensed_data["condensed_data"], csv_file)
            exports["condensed_data_csv"] = str(csv_file)
        
        return exports
    
    def _data_to_dataframe(self, data: List[Dict[str, Any]]) -> Any:
        """Convert data to Polars DataFrame."""
        import polars as pl
        return pl.DataFrame(data)
    
    def _export_condensed_csv(self, condensed_data: Dict[str, Any], output_file: Path) -> None:
        """Export condensed data to CSV."""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            if condensed_data:
                # Get all unique species
                all_species = set()
                for window_data in condensed_data.values():
                    all_species.update(window_data['species_count'].keys())
                
                # Create CSV header
                fieldnames = ['window_start', 'window_end', 'total_observations'] + list(all_species)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write data
                for window_data in condensed_data.values():
                    row = {
                        'window_start': window_data['window_start'],
                        'window_end': window_data['window_end'],
                        'total_observations': window_data['total_observations']
                    }
                    row.update(window_data['species_count'])
                    writer.writerow(row)
    
    def request_unknown_clusters_for_labeling(self, limit: int = 50) -> Dict[str, Any]:
        """Request unknown clusters for user labeling (decoupled from processing)."""
        self.logger.info("Requesting unknown clusters for labeling")
        
        unknown_clusters = self.tagging_service.request_unknown_clusters(limit)
        
        # Add generated names for unknown clusters
        for i, cluster in enumerate(unknown_clusters['clusters']):
            cluster['generated_name'] = f"{self.config['output']['unknown_cluster_prefix']}{i+1}"
            cluster['labeling_required'] = True
        
        return unknown_clusters
    
    def submit_cluster_labels(self, cluster_labels: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Submit cluster labels (decoupled from processing)."""
        self.logger.info("Submitting cluster labels")
        
        results = self.tagging_service.submit_cluster_names(cluster_labels)
        
        return {
            "labeling_timestamp": datetime.now().isoformat(),
            "labels_submitted": len(cluster_labels),
            "successful_labels": len(results.get('successful_names', {})),
            "failed_labels": len(results.get('failed_names', {})),
            "results": results
        }


def main():
    """Main Post-S2 Workflow CLI entry point."""
    parser = argparse.ArgumentParser(description="Hugin Post-S2 Workflow")
    parser.add_argument("--config", type=Path, help="Configuration YAML file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process post-S2 workflow
    process_parser = subparsers.add_parser("process", help="Process post-S2 workflow")
    process_parser.add_argument("s2_results", type=Path, help="S2 results file")
    process_parser.add_argument("output_dir", type=Path, help="Output directory")
    
    # Request unknown clusters for labeling
    request_parser = subparsers.add_parser("request-labels", help="Request unknown clusters for labeling")
    request_parser.add_argument("--limit", type=int, default=50, help="Limit number of clusters")
    request_parser.add_argument("--output", "-o", type=Path, help="Output YAML file")
    
    # Submit cluster labels
    submit_parser = subparsers.add_parser("submit-labels", help="Submit cluster labels")
    submit_parser.add_argument("labels_file", type=Path, help="Labels YAML file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize post-S2 workflow
    workflow = PostS2Workflow(args.config)
    
    if args.verbose:
        workflow.logger.setLevel(logging.DEBUG)
    
    try:
        if args.command == "process":
            results = workflow.process_post_s2_workflow(args.s2_results, args.output_dir)
            
            if results["success"]:
                print("✅ Post-S2 workflow completed successfully")
                print(f"  S2 observations: {results.get('s2_observations', 0)}")
                print(f"  Steps: {', '.join(results['steps_completed'])}")
                if "clustering" in results:
                    clustering = results["clustering"]
                    print(f"  Clusters: {clustering.get('total_clusters', 0)} total, {clustering.get('unknown_clusters', 0)} unknown")
            else:
                print("❌ Post-S2 workflow failed")
                for error in results.get("errors", []):
                    print(f"  Error: {error}")
                sys.exit(1)
                
        elif args.command == "request-labels":
            unknown = workflow.request_unknown_clusters_for_labeling(args.limit)
            
            print(f"Found {unknown['filtered_count']} unknown clusters needing labels")
            
            if args.output:
                with open(args.output, 'w') as f:
                    yaml.dump(unknown, f, default_flow_style=False, indent=2)
                print(f"Saved to {args.output}")
            else:
                for cluster in unknown['clusters']:
                    print(f"  {cluster['cluster_id'][:8]} - {cluster['generated_name']} - {cluster['point_count']} points")
                    
        elif args.command == "submit-labels":
            with open(args.labels_file, 'r') as f:
                labels = yaml.safe_load(f)
            
            results = workflow.submit_cluster_labels(labels)
            
            print(f"✅ Submitted {results['labels_submitted']} cluster labels")
            print(f"  Successful: {results['successful_labels']}")
            print(f"  Failed: {results['failed_labels']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
