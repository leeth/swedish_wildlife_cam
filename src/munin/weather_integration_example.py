#!/usr/bin/env python3
"""
Weather Integration Example for Munin

This script demonstrates how to integrate YR.no weather data
with GPS clusters in the wildlife pipeline.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from yr_weather_enricher import YRWeatherEnricher
from hugin.gps_clustering import GPSClusterManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate weather integration."""
    
    # Initialize components
    db_path = Path("wildlife_pipeline.db")
    weather_enricher = YRWeatherEnricher(db_path)
    cluster_manager = GPSClusterManager(db_path)
    
    logger.info("Starting weather integration example...")
    
    # Example 1: Enrich a specific cluster with weather data
    logger.info("Example 1: Enriching specific cluster with weather data")
    
    # Get the first cluster (or create a test one)
    clusters = cluster_manager.get_all_clusters()
    if not clusters:
        logger.info("No clusters found. Creating a test cluster...")
        # Create a test cluster for demonstration
        test_assignment = cluster_manager.assign_gps_point(
            observation_id="test_obs_1",
            latitude=59.9139,  # Oslo coordinates
            longitude=10.7522
        )
        cluster_id = test_assignment.cluster_id
    else:
        cluster_id = clusters[0].cluster_id
        logger.info(f"Using existing cluster: {cluster_id}")
    
    # Enrich with weather data for the last 7 days
    cluster_data = {
        'cluster_id': cluster_id,
        'start_date': datetime.now() - timedelta(days=7),
        'end_date': datetime.now()
    }
    
    try:
        result = weather_enricher.enrich_cluster_weather(cluster_data)
        logger.info(f"Weather enrichment result: {result}")
    except Exception as e:
        logger.error(f"Weather enrichment failed: {e}")
    
    # Example 2: Get weather data for a cluster
    logger.info("Example 2: Retrieving weather data for cluster")
    
    weather_data = weather_enricher.get_weather_for_cluster(
        cluster_id=cluster_id,
        start_date=datetime.now() - timedelta(days=3),
        end_date=datetime.now()
    )
    
    logger.info(f"Retrieved {len(weather_data)} weather observations")
    
    if weather_data:
        # Show sample weather data
        sample = weather_data[0]
        logger.info(f"Sample weather observation:")
        logger.info(f"  Timestamp: {sample['timestamp']}")
        logger.info(f"  Temperature: {sample['temperature']}°C")
        logger.info(f"  Humidity: {sample['humidity']}%")
        logger.info(f"  Wind Speed: {sample['wind_speed']} m/s")
        logger.info(f"  Precipitation: {sample['precipitation']} mm")
    
    # Example 3: Enrich all clusters with weather data
    logger.info("Example 3: Enriching all clusters with weather data")
    
    try:
        all_results = weather_enricher.enrich_all_clusters(days_back=3)
        logger.info(f"All clusters enrichment results: {all_results}")
    except Exception as e:
        logger.error(f"All clusters enrichment failed: {e}")
    
    # Example 4: Get weather statistics
    logger.info("Example 4: Weather data statistics")
    
    stats = weather_enricher.get_weather_statistics()
    logger.info(f"Weather statistics: {stats}")
    
    # Example 5: Cleanup expired cache
    logger.info("Example 5: Cleaning up expired cache")
    
    deleted_count = weather_enricher.cleanup_expired_cache()
    logger.info(f"Cleaned up {deleted_count} expired cache entries")
    
    logger.info("Weather integration example completed!")


if __name__ == "__main__":
    main()
