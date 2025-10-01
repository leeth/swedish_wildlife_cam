#!/usr/bin/env python3
"""
Test script for observation-based weather enrichment

This script tests the weather enrichment functionality
for individual positive wildlife observations.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from munin.observation_weather_enricher import ObservationWeatherEnricher


def test_observation_weather_enrichment():
    """Test the observation-based weather enrichment functionality."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting observation-based weather enrichment test...")
    
    # Initialize weather enricher
    db_path = Path("test_observation_weather.db")
    weather_enricher = ObservationWeatherEnricher(db_path)
    
    try:
        # Test 1: Enrich a single observation
        logger.info("Test 1: Enriching single observation...")
        
        observation_data = {
            'observation_id': 'test_obs_1',
            'timestamp': datetime.now() - timedelta(hours=2),
            'latitude': 59.9139,  # Oslo
            'longitude': 10.7522,
            'camera_id': 'camera_001'
        }
        
        result = weather_enricher.enrich_single_observation(observation_data)
        logger.info(f"Single observation enrichment result: {result}")
        
        if result['success']:
            weather_data = result.get('weather_data', {})
            logger.info("Weather data retrieved:")
            logger.info(f"  Temperature: {weather_data.get('temperature')}°C")
            logger.info(f"  Humidity: {weather_data.get('humidity')}%")
            logger.info(f"  Wind Speed: {weather_data.get('wind_speed')} m/s")
        
        # Test 2: Enrich a batch of observations
        logger.info("Test 2: Enriching batch of observations...")
        
        batch_observations = [
            {
                'observation_id': 'test_obs_2',
                'timestamp': datetime.now() - timedelta(hours=4),
                'latitude': 59.9139,
                'longitude': 10.7522,
                'camera_id': 'camera_001'
            },
            {
                'observation_id': 'test_obs_3',
                'timestamp': datetime.now() - timedelta(hours=6),
                'latitude': 59.9139,
                'longitude': 10.7522,
                'camera_id': 'camera_002'
            }
        ]
        
        batch_result = weather_enricher.enrich_observations_batch(batch_observations)
        logger.info(f"Batch enrichment result: {batch_result}")
        
        # Test 3: Retrieve weather data for an observation
        logger.info("Test 3: Retrieving weather data for observation...")
        
        weather_data = weather_enricher.get_weather_for_observation('test_obs_1')
        if weather_data:
            logger.info("Retrieved weather data:")
            logger.info(f"  Observation ID: {weather_data['observation_id']}")
            logger.info(f"  Temperature: {weather_data['temperature']}°C")
            logger.info(f"  Humidity: {weather_data['humidity']}%")
            logger.info(f"  Wind Speed: {weather_data['wind_speed']} m/s")
        
        # Test 4: Get statistics
        logger.info("Test 4: Getting weather statistics...")
        
        stats = weather_enricher.get_weather_statistics()
        logger.info(f"Weather statistics: {stats}")
        
        # Test 5: Test duplicate enrichment (should not re-fetch)
        logger.info("Test 5: Testing duplicate enrichment...")
        
        duplicate_result = weather_enricher.enrich_single_observation(observation_data)
        logger.info(f"Duplicate enrichment result: {duplicate_result}")
        
        logger.info("Observation-based weather enrichment test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Observation weather enrichment test failed: {e}")
        return False
    
    finally:
        # Cleanup test database
        if db_path.exists():
            db_path.unlink()
            logger.info("Cleaned up test database")


if __name__ == "__main__":
    success = test_observation_weather_enrichment()
    sys.exit(0 if success else 1)
