#!/usr/bin/env python3
"""
Test script for YR.no weather integration

This script tests the weather enrichment functionality
with a simple GPS cluster.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from munin.yr_weather_enricher import YRWeatherEnricher
from hugin.gps_clustering import GPSClusterManager


def test_weather_integration():
    """Test the weather integration functionality."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting YR.no weather integration test...")
    
    # Initialize components
    db_path = Path("test_weather.db")
    weather_enricher = YRWeatherEnricher(db_path)
    cluster_manager = GPSClusterManager(db_path)
    
    try:
        # Create a test cluster (Oslo coordinates)
        logger.info("Creating test cluster...")
        test_assignment = cluster_manager.assign_gps_point(
            observation_id="test_obs_1",
            latitude=59.9139,  # Oslo
            longitude=10.7522
        )
        cluster_id = test_assignment.cluster_id
        logger.info(f"Created test cluster: {cluster_id}")
        
        # Enrich with weather data
        logger.info("Enriching cluster with weather data...")
        cluster_data = {
            'cluster_id': cluster_id,
            'start_date': datetime.now() - timedelta(days=1),
            'end_date': datetime.now()
        }
        
        result = weather_enricher.enrich_cluster_weather(cluster_data)
        logger.info(f"Weather enrichment result: {result}")
        
        # Retrieve weather data
        logger.info("Retrieving weather data...")
        weather_data = weather_enricher.get_weather_for_cluster(cluster_id)
        logger.info(f"Retrieved {len(weather_data)} weather observations")
        
        if weather_data:
            # Show sample data
            sample = weather_data[0]
            logger.info("Sample weather observation:")
            logger.info(f"  Timestamp: {sample['timestamp']}")
            logger.info(f"  Temperature: {sample['temperature']}°C")
            logger.info(f"  Humidity: {sample['humidity']}%")
            logger.info(f"  Wind Speed: {sample['wind_speed']} m/s")
            logger.info(f"  Precipitation: {sample['precipitation']} mm")
        
        # Get statistics
        logger.info("Getting weather statistics...")
        stats = weather_enricher.get_weather_statistics()
        logger.info(f"Weather statistics: {stats}")
        
        logger.info("Weather integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Weather integration test failed: {e}")
        return False
    
    finally:
        # Cleanup test database
        if db_path.exists():
            db_path.unlink()
            logger.info("Cleaned up test database")


if __name__ == "__main__":
    success = test_weather_integration()
    sys.exit(0 if success else 1)
