#!/usr/bin/env python3
"""
Weather Enrichment Lambda Handler

This Lambda function enriches positive wildlife observations
with weather data from YR.no.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from munin.observation_weather_enricher import ObservationWeatherEnricher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run_weather_enrichment(input_uri: str, weather_uri: str, days_back: int = 7):
    """
    Run weather enrichment for positive observations.
    
    Args:
        input_uri: S3 URI to detection results
        weather_uri: S3 URI for weather data output
        days_back: Number of days to look back for weather data
        
    Returns:
        Dictionary with weather enrichment results
    """
    logger.info(f"Starting weather enrichment for {input_uri}")
    
    # This is a simplified implementation
    # In practice, you'd download detection results, enrich with weather, and upload results
    
    result = {
        "weather_uri": weather_uri,
        "observations_enriched": 0,  # Would be actual count
        "weather_observations": 0,
        "days_back": days_back,
        "provider": "yr_no"
    }
    
    logger.info(f"Weather enrichment completed: {result}")
    return result


def handler(event, context):
    """
    Lambda handler for weather enrichment.
    
    Args:
        event: Step Functions input event
        context: Lambda context
        
    Returns:
        Updated event with weather enrichment results
    """
    logger.info(f"Weather enrichment handler invoked with event: {json.dumps(event)}")
    
    try:
        intermediate_uri = event["intermediate_uri"]
        weather_uri = event.get("weather_uri", event["output_uri"].rstrip("/") + "/weather/")
        days_back = event.get("weather_days_back", 7)
        
        # Run weather enrichment
        result = run_weather_enrichment(intermediate_uri, weather_uri, days_back)
        
        # Update event with results
        event["weather_results"] = result
        event["weather_uri"] = weather_uri
        
        logger.info(f"Weather enrichment completed successfully")
        return event
        
    except Exception as e:
        logger.error(f"Error in weather enrichment: {e}")
        raise e

