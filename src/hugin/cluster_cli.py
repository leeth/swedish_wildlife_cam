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
import json
import logging
from typing import Any, Dict, List, Optional

import yaml

from .cluster_service import ClusterService
from .data_models import UnknownCluster

logger = logging.getLogger(__name__)

class ClusterCLI:
    """Command-line interface for cluster management."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize CLI with optional config."""
        self.config = self._load_config(config_path) if config_path else {}
        self.service = ClusterService(self.config.get('db_path', 'clusters.db'))
        self.logger = logger

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}

    def process_observations(self, input_path: str, output_path: str,
                            radius_meters: float = 5.0) -> bool:
        """Process observations and create clusters."""
        try:
            # Load observations
            if input_path.endswith('.json'):
                with open(input_path) as f:
                    observations = json.load(f)
            elif input_path.endswith('.yaml'):
                with open(input_path) as f:
                    data = yaml.safe_load(f)
                    observations = data.get('observations', [])
            else:
                self.logger.error(f"Unsupported input format: {input_path}")
                return False

            # Process observations
            result = self.service.process_observations(observations, radius_meters)

            if result['success']:
                # Save results
                with open(output_path, 'w') as f:
                    json.dump(result, f, indent=2, default=str)

                self.logger.info(f"✅ Created {result['clusters_created']} clusters")
                return True
            else:
                self.logger.error(f"❌ Processing failed: {result.get('error')}")
                return False

        except Exception as e:
            self.logger.error(f"Error processing observations: {e}")
            return False

    def request_unknown_clusters(self, limit: int = 20) -> List[UnknownCluster]:
        """Request unknown clusters for naming."""
        try:
            unknown = self.service.get_unknown_clusters(limit)

            if unknown:
                print(f"❓ Found {len(unknown)} unknown clusters:")
                for i, cluster in enumerate(unknown, 1):
                    print(f"  {i}. {cluster.cluster_id} - {cluster.point_count} points")
                    print(f"     Center: {cluster.center_latitude:.4f}, {cluster.center_longitude:.4f}")
            else:
                print("✅ All clusters are named!")

            return unknown

        except Exception as e:
            self.logger.error(f"Error requesting unknown clusters: {e}")
            return []

    def submit_cluster_names(self, names_file: str) -> int:
        """Submit cluster names from YAML file."""
        try:
            with open(names_file) as f:
                data = yaml.safe_load(f)

            names = data.get('cluster_names', {})
            if not names:
                self.logger.error("No cluster_names found in YAML file")
                return 0

            count = self.service.batch_name_clusters(names)
            print(f"✅ Named {count} clusters")
            return count

        except Exception as e:
            self.logger.error(f"Error submitting cluster names: {e}")
            return 0

    def export_boundaries(self, output_path: str, format: str = "geojson") -> bool:
        """Export cluster boundaries for mapping."""
        try:
            boundaries = self.service.get_all_cluster_boundaries()

            if format == "geojson":
                geojson = {
                    "type": "FeatureCollection",
                    "features": []
                }

                for boundary in boundaries:
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "cluster_id": boundary["cluster_id"],
                            "area_square_meters": boundary["area_square_meters"],
                            "perimeter_meters": boundary["perimeter_meters"]
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [boundary["convex_hull_points"]]
                        }
                    }
                    geojson["features"].append(feature)

                with open(output_path, 'w') as f:
                    json.dump(geojson, f, indent=2)

            elif format == "kml":
                # Simple KML export
                kml = '<?xml version="1.0" encoding="UTF-8"?>\n'
                kml += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
                kml += '<Document>\n'

                for boundary in boundaries:
                    kml += '  <Placemark>\n'
                    kml += f'    <name>Cluster {boundary["cluster_id"]}</name>\n'
                    kml += '    <Polygon>\n'
                    kml += '      <outerBoundaryIs>\n'
                    kml += '        <LinearRing>\n'
                    kml += '          <coordinates>\n'
                    for lat, lon in boundary["convex_hull_points"]:
                        kml += f'            {lon},{lat},0\n'
                    kml += '          </coordinates>\n'
                    kml += '        </LinearRing>\n'
                    kml += '      </outerBoundaryIs>\n'
                    kml += '    </Polygon>\n'
                    kml += '  </Placemark>\n'

                kml += '</Document>\n'
                kml += '</kml>\n'

                with open(output_path, 'w') as f:
                    f.write(kml)

            else:
                self.logger.error(f"Unsupported export format: {format}")
                return False

            print(f"✅ Exported {len(boundaries)} cluster boundaries to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting boundaries: {e}")
            return False

    def show_analytics(self) -> None:
        """Show cluster analytics."""
        try:
            analytics = self.service.get_cluster_analytics()

            print("📊 Cluster Analytics:")
            print(f"  Total clusters: {analytics.get('total_clusters', 0)}")
            print(f"  Named clusters: {analytics.get('named_clusters', 0)}")
            print(f"  Unnamed clusters: {analytics.get('unnamed_clusters', 0)}")
            print(f"  Total points: {analytics.get('total_points', 0)}")
            print(f"  Average points per cluster: {analytics.get('average_points_per_cluster', 0):.1f}")

        except Exception as e:
            self.logger.error(f"Error showing analytics: {e}")

    def export_data(self, output_path: str, format: str = "csv") -> bool:
        """Export cluster data."""
        try:
            success = self.service.export_cluster_data(output_path, format)
            if success:
                print(f"✅ Exported cluster data to {output_path}")
            else:
                print("❌ Failed to export cluster data")
            return success

        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GPS Cluster Management CLI")
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--db-path', help='Database path')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Process observations
    process_parser = subparsers.add_parser('process', help='Process observations')
    process_parser.add_argument('input', help='Input observations file')
    process_parser.add_argument('output', help='Output results file')
    process_parser.add_argument('--radius', type=float, default=5.0, help='Cluster radius in meters')

    # Request unknown clusters
    unknown_parser = subparsers.add_parser('request-unknown', help='Request unknown clusters')
    unknown_parser.add_argument('--limit', type=int, default=20, help='Maximum number of clusters to show')

    # Submit cluster names
    submit_parser = subparsers.add_parser('submit-names', help='Submit cluster names')
    submit_parser.add_argument('names_file', help='YAML file with cluster names')

    # Export boundaries
    export_parser = subparsers.add_parser('export-boundaries', help='Export cluster boundaries')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument('--format', choices=['geojson', 'kml'], default='geojson', help='Export format')

    # Show analytics
    subparsers.add_parser('analytics', help='Show cluster analytics')

    # Export data
    data_parser = subparsers.add_parser('export-data', help='Export cluster data')
    data_parser.add_argument('output', help='Output file path')
    data_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Export format')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = ClusterCLI(args.config)

    # Execute command
    if args.command == 'process':
        cli.process_observations(args.input, args.output, args.radius)
    elif args.command == 'request-unknown':
        cli.request_unknown_clusters(args.limit)
    elif args.command == 'submit-names':
        cli.submit_cluster_names(args.names_file)
    elif args.command == 'export-boundaries':
        cli.export_boundaries(args.output, args.format)
    elif args.command == 'analytics':
        cli.show_analytics()
    elif args.command == 'export-data':
        cli.export_data(args.output, args.format)


if __name__ == '__main__':
    main()
