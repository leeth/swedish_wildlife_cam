#!/usr/bin/env python3
"""
Weather Enrichment CLI Tool

This script provides a command-line interface for enriching
GPS clusters with YR.no weather data.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from munin.yr_weather_enricher import YRWeatherEnricher
from hugin.gps_clustering import GPSClusterManager


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def enrich_single_cluster(args):
    """Enrich a single cluster with weather data."""
    logger = logging.getLogger(__name__)
    
    # Initialize components
    weather_enricher = YRWeatherEnricher(Path(args.database))
    cluster_manager = GPSClusterManager(Path(args.database))
    
    # Get cluster information
    cluster = cluster_manager.get_cluster(args.cluster_id)
    if not cluster:
        logger.error(f"Cluster {args.cluster_id} not found")
        return 1
    
    logger.info(f"Enriching cluster {args.cluster_id} ({cluster.name or 'Unnamed'})")
    logger.info(f"Location: {cluster.center_latitude}, {cluster.center_longitude}")
    
    # Prepare enrichment data
    cluster_data = {
        'cluster_id': args.cluster_id,
        'start_date': args.start_date,
        'end_date': args.end_date
    }
    
    try:
        result = weather_enricher.enrich_cluster_weather(cluster_data)
        logger.info(f"Weather enrichment successful:")
        logger.info(f"  Observations: {result['observations_count']}")
        logger.info(f"  Stored: {result['stored_count']}")
        logger.info(f"  Provider: {result['provider']}")
        return 0
        
    except Exception as e:
        logger.error(f"Weather enrichment failed: {e}")
        return 1


def enrich_all_clusters(args):
    """Enrich all clusters with weather data."""
    logger = logging.getLogger(__name__)
    
    # Initialize components
    weather_enricher = YRWeatherEnricher(Path(args.database))
    
    logger.info(f"Enriching all clusters with weather data (last {args.days_back} days)")
    
    try:
        result = weather_enricher.enrich_all_clusters(days_back=args.days_back)
        
        logger.info(f"Enrichment completed:")
        logger.info(f"  Total clusters: {result['total_clusters']}")
        logger.info(f"  Successful: {result['successful_enrichments']}")
        logger.info(f"  Failed: {result['failed_enrichments']}")
        
        # Show cluster results
        for cluster_result in result['cluster_results']:
            if cluster_result['success']:
                logger.info(f"  ✓ {cluster_result['cluster_name']}: {cluster_result['observations_count']} observations")
            else:
                logger.error(f"  ✗ {cluster_result['cluster_name']}: {cluster_result['error']}")
        
        return 0 if result['failed_enrichments'] == 0 else 1
        
    except Exception as e:
        logger.error(f"All clusters enrichment failed: {e}")
        return 1


def show_weather_data(args):
    """Show weather data for a cluster."""
    logger = logging.getLogger(__name__)
    
    # Initialize components
    weather_enricher = YRWeatherEnricher(Path(args.database))
    
    logger.info(f"Retrieving weather data for cluster {args.cluster_id}")
    
    try:
        weather_data = weather_enricher.get_weather_for_cluster(
            cluster_id=args.cluster_id,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        logger.info(f"Found {len(weather_data)} weather observations")
        
        if weather_data and args.show_details:
            logger.info("Sample observations:")
            for i, obs in enumerate(weather_data[:5]):  # Show first 5
                logger.info(f"  {i+1}. {obs['timestamp']}: "
                          f"Temp={obs['temperature']}°C, "
                          f"Humidity={obs['humidity']}%, "
                          f"Wind={obs['wind_speed']}m/s, "
                          f"Precip={obs['precipitation']}mm")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to retrieve weather data: {e}")
        return 1


def show_statistics(args):
    """Show weather data statistics."""
    logger = logging.getLogger(__name__)
    
    # Initialize components
    weather_enricher = YRWeatherEnricher(Path(args.database))
    
    try:
        stats = weather_enricher.get_weather_statistics()
        
        logger.info("Weather Data Statistics:")
        logger.info(f"  Total observations: {stats['total_observations']}")
        
        if stats['date_range']:
            logger.info(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        if stats['cluster_stats']:
            logger.info("  Observations by cluster:")
            for cluster_id, count in stats['cluster_stats'].items():
                logger.info(f"    {cluster_id}: {count} observations")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to retrieve statistics: {e}")
        return 1


def cleanup_cache(args):
    """Clean up expired cache entries."""
    logger = logging.getLogger(__name__)
    
    # Initialize components
    weather_enricher = YRWeatherEnricher(Path(args.database))
    
    try:
        deleted_count = weather_enricher.cleanup_expired_cache()
        logger.info(f"Cleaned up {deleted_count} expired cache entries")
        return 0
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return 1


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Weather Enrichment CLI Tool for Munin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich a specific cluster
  python scripts/enrich_weather.py enrich-cluster --cluster-id cluster_123 --days-back 7
  
  # Enrich all clusters
  python scripts/enrich_weather.py enrich-all --days-back 3
  
  # Show weather data for a cluster
  python scripts/enrich_weather.py show-data --cluster-id cluster_123 --show-details
  
  # Show statistics
  python scripts/enrich_weather.py show-stats
  
  # Cleanup cache
  python scripts/enrich_weather.py cleanup-cache
        """
    )
    
    parser.add_argument(
        '--database', '-d',
        default='wildlife_pipeline.db',
        help='Database file path (default: wildlife_pipeline.db)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Enrich single cluster command
    enrich_parser = subparsers.add_parser('enrich-cluster', help='Enrich a single cluster')
    enrich_parser.add_argument('--cluster-id', required=True, help='Cluster ID to enrich')
    enrich_parser.add_argument('--days-back', type=int, default=7, help='Days to look back (default: 7)')
    enrich_parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    enrich_parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    
    # Enrich all clusters command
    enrich_all_parser = subparsers.add_parser('enrich-all', help='Enrich all clusters')
    enrich_all_parser.add_argument('--days-back', type=int, default=7, help='Days to look back (default: 7)')
    
    # Show weather data command
    show_parser = subparsers.add_parser('show-data', help='Show weather data for a cluster')
    show_parser.add_argument('--cluster-id', required=True, help='Cluster ID')
    show_parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    show_parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    show_parser.add_argument('--show-details', action='store_true', help='Show detailed observations')
    
    # Show statistics command
    subparsers.add_parser('show-stats', help='Show weather data statistics')
    
    # Cleanup cache command
    subparsers.add_parser('cleanup-cache', help='Clean up expired cache entries')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Parse dates if provided
    if hasattr(args, 'start_date') and args.start_date:
        args.start_date = datetime.fromisoformat(args.start_date)
    elif hasattr(args, 'start_date'):
        args.start_date = datetime.now() - timedelta(days=args.days_back)
    
    if hasattr(args, 'end_date') and args.end_date:
        args.end_date = datetime.fromisoformat(args.end_date)
    elif hasattr(args, 'end_date'):
        args.end_date = datetime.now()
    
    # Execute command
    if args.command == 'enrich-cluster':
        return enrich_single_cluster(args)
    elif args.command == 'enrich-all':
        return enrich_all_clusters(args)
    elif args.command == 'show-data':
        return show_weather_data(args)
    elif args.command == 'show-stats':
        return show_statistics(args)
    elif args.command == 'cleanup-cache':
        return cleanup_cache(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
