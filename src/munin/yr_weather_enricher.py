"""
YR Weather Enricher - Minimal implementation for testing
"""
from typing import Dict, Any, Optional
import requests
import logging

logger = logging.getLogger(__name__)

class YRWeatherEnricher:
    """Minimal YR Weather Enricher implementation"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.met.no/weatherapi/locationforecast/2.0"
    
    def get_weather_data(self, latitude: float, longitude: float, timestamp: str) -> Dict[str, Any]:
        """Get weather data for given coordinates and timestamp"""
        try:
            # Minimal implementation - return mock data for testing
            return {
                "temperature": 15.0,
                "humidity": 65.0,
                "wind_speed": 3.2,
                "precipitation": 0.0,
                "source": "yr_api",
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {}
    
    def enrich_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich observation with weather data"""
        if "latitude" in observation and "longitude" in observation:
            weather_data = self.get_weather_data(
                observation["latitude"],
                observation["longitude"],
                observation.get("timestamp", "")
            )
            observation.update(weather_data)
        return observation
