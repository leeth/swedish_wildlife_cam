#!/usr/bin/env python3
"""
Observation Weather Enrichment CLI Tool

This script provides a command-line interface for enriching
positive wildlife observations with YR.no weather data.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.munin.observation_weather_enricher import ObservationWeatherEnricher


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def enrich_single_observation(args):
    """Enrich a single observation with weather data."""
    logger = logging.getLogger(__name__)
    
    # Initialize weather enricher
    weather_enricher = ObservationWeatherEnricher(Path(args.database))
    
    # Prepare observation data
    observation_data = {
        'observation_id': args.observation_id,
        'timestamp': args.timestamp,
        'latitude': args.latitude,
        'longitude': args.longitude
    }
    
    if args.camera_id:
        observation_data['camera_id'] = args.camera_id
    
    logger.info(f"Enriching observation {args.observation_id} with weather data")
    logger.info(f"Location: {args.latitude}, {args.longitude}")
    logger.info(f"Timestamp: {args.timestamp}")
    
    try:
        result = weather_enricher.enrich_single_observation(observation_data)
        
        if result['success']:
            if result.get('already_enriched'):
                logger.info("Observation already has weather data")
            else:
                logger.info("Weather enrichment successful:")
                weather_data = result.get('weather_data', {})
                logger.info(f"  Temperature: {weather_data.get('temperature')}°C")
                logger.info(f"  Humidity: {weather_data.get('humidity')}%")
                logger.info(f"  Wind Speed: {weather_data.get('wind_speed')} m/s")
                logger.info(f"  Precipitation: {weather_data.get('precipitation')} mm")
        else:
            logger.error(f"Weather enrichment failed: {result.get('error')}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Weather enrichment failed: {e}")
        return 1


def enrich_positive_observations(args):
    """Enrich all positive observations from the database."""
    logger = logging.getLogger(__name__)
    
    # Initialize weather enricher
    weather_enricher = ObservationWeatherEnricher(Path(args.database))
    
    logger.info(f"Enriching all positive observations from the last {args.days_back} days")
    
    try:
        result = weather_enricher.enrich_positive_observations_from_db(days_back=args.days_back)
        
        logger.info(f"Enrichment completed:")
        logger.info(f"  Total observations: {result['total_observations']}")
        logger.info(f"  Successful: {result['successful_enrichments']}")
        logger.info(f"  Already enriched: {result['already_enriched']}")
        logger.info(f"  Failed: {result['failed_enrichments']}")
        
        # Show some sample results
        if result['results']:
            logger.info("Sample results:")
            for i, res in enumerate(result['results'][:5]):  # Show first 5
                if res['success']:
                    logger.info(f"  ✓ {res['observation_id']}: Weather data added")
                else:
                    logger.error(f"  ✗ {res['observation_id']}: {res.get('error', 'Unknown error')}")
        
        return 0 if result['failed_enrichments'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Positive observations enrichment failed: {e}")
        return 1


def show_weather_data(args):
    """Show weather data for an observation."""
    logger = logging.getLogger(__name__)
    
    # Initialize weather enricher
    weather_enricher = ObservationWeatherEnricher(Path(args.database))
    
    logger.info(f"Retrieving weather data for observation {args.observation_id}")
    
    try:
        weather_data = weather_enricher.get_weather_for_observation(args.observation_id)
        
        if weather_data:
            logger.info("Weather data found:")
            logger.info(f"  Timestamp: {weather_data['timestamp']}")
            logger.info(f"  Temperature: {weather_data['temperature']}°C")
            logger.info(f"  Humidity: {weather_data['humidity']}%")
            logger.info(f"  Wind Speed: {weather_data['wind_speed']} m/s")
            logger.info(f"  Wind Direction: {weather_data['wind_direction']}°")
            logger.info(f"  Precipitation: {weather_data['precipitation']} mm")
            logger.info(f"  Pressure: {weather_data['pressure']} hPa")
            logger.info(f"  Visibility: {weather_data['visibility']} m")
            logger.info(f"  Cloud Cover: {weather_data['cloud_cover']}%")
            logger.info(f"  UV Index: {weather_data['uv_index']}")
            logger.info(f"  Dew Point: {weather_data['dew_point']}°C")
            logger.info(f"  Wind Gust: {weather_data['wind_gust']} m/s")
        else:
            logger.info("No weather data found for this observation")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to retrieve weather data: {e}")
        return 1


def show_statistics(args):
    """Show weather enrichment statistics."""
    logger = logging.getLogger(__name__)
    
    # Initialize weather enricher
    weather_enricher = ObservationWeatherEnricher(Path(args.database))
    
    try:
        stats = weather_enricher.get_weather_statistics()
        
        logger.info("Weather Enrichment Statistics:")
        logger.info(f"  Total weather observations: {stats['total_weather_observations']}")
        
        if stats['date_range']:
            logger.info(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        logger.info(f"  Observations with camera data: {stats['observations_with_camera']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to retrieve statistics: {e}")
        return 1


def cleanup_cache(args):
    """Clean up expired cache entries."""
    logger = logging.getLogger(__name__)
    
    # Initialize weather enricher
    weather_enricher = ObservationWeatherEnricher(Path(args.database))
    
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
        description="Observation Weather Enrichment CLI Tool for Munin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich a single observation
  python scripts/enrich_observations_weather.py enrich-single \\
    --observation-id obs_123 \\
    --timestamp "2024-01-15T10:30:00Z" \\
    --latitude 59.9139 \\
    --longitude 10.7522
  
  # Enrich all positive observations from database
  python scripts/enrich_observations_weather.py enrich-positive --days-back 7
  
  # Show weather data for an observation
  python scripts/enrich_observations_weather.py show-weather --observation-id obs_123
  
  # Show statistics
  python scripts/enrich_observations_weather.py show-stats
  
  # Cleanup cache
  python scripts/enrich_observations_weather.py cleanup-cache
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
    
    # Enrich single observation command
    enrich_single_parser = subparsers.add_parser('enrich-single', help='Enrich a single observation')
    enrich_single_parser.add_argument('--observation-id', required=True, help='Observation ID')
    enrich_single_parser.add_argument('--timestamp', required=True, help='Observation timestamp (ISO format)')
    enrich_single_parser.add_argument('--latitude', type=float, required=True, help='GPS latitude')
    enrich_single_parser.add_argument('--longitude', type=float, required=True, help='GPS longitude')
    enrich_single_parser.add_argument('--camera-id', help='Camera ID (optional)')
    
    # Enrich positive observations command
    enrich_positive_parser = subparsers.add_parser('enrich-positive', help='Enrich all positive observations from database')
    enrich_positive_parser.add_argument('--days-back', type=int, default=7, help='Days to look back (default: 7)')
    
    # Show weather data command
    show_parser = subparsers.add_parser('show-weather', help='Show weather data for an observation')
    show_parser.add_argument('--observation-id', required=True, help='Observation ID')
    
    # Show statistics command
    subparsers.add_parser('show-stats', help='Show weather enrichment statistics')
    
    # Cleanup cache command
    subparsers.add_parser('cleanup-cache', help='Clean up expired cache entries')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Execute command
    if args.command == 'enrich-single':
        return enrich_single_observation(args)
    elif args.command == 'enrich-positive':
        return enrich_positive_observations(args)
    elif args.command == 'show-weather':
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
