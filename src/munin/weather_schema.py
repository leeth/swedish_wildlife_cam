"""
Weather Data Schema for Wildlife Observations

Defines the weather data structure with nested weather_* keys for better organization.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WeatherData:
    """Weather data structure for wildlife observations."""
    
    weather_time: str
    temp_c: Optional[float] = None
    wind_ms: Optional[float] = None
    wind_dir_deg: Optional[float] = None
    precip_mm: Optional[float] = None
    cloud_pc: Optional[float] = None
    pressure_hpa: Optional[float] = None
    condition_code: Optional[str] = None
    wind_dir_card: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with nested weather structure."""
        return {
            'weather_time': self.weather_time,
            'weather_temp_c': self.temp_c,
            'weather_wind_ms': self.wind_ms,
            'weather_wind_dir_deg': self.wind_dir_deg,
            'weather_precip_mm': self.precip_mm,
            'weather_cloud_pc': self.cloud_pc,
            'weather_pressure_hpa': self.pressure_hpa,
            'weather_condition_code': self.condition_code,
            'weather_wind_dir_card': self.wind_dir_card
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeatherData':
        """Create WeatherData from dictionary."""
        return cls(
            weather_time=data.get('weather_time', ''),
            temp_c=data.get('weather_temp_c'),
            wind_ms=data.get('weather_wind_ms'),
            wind_dir_deg=data.get('weather_wind_dir_deg'),
            precip_mm=data.get('weather_precip_mm'),
            cloud_pc=data.get('weather_cloud_pc'),
            pressure_hpa=data.get('weather_pressure_hpa'),
            condition_code=data.get('weather_condition_code'),
            wind_dir_card=data.get('weather_wind_dir_card')
        )

def create_weather_struct() -> Dict[str, Any]:
    """Create PyArrow/Parquet schema for weather data."""
    return {
        'weather_time': 'string',
        'weather_temp_c': 'float64',
        'weather_wind_ms': 'float64', 
        'weather_wind_dir_deg': 'float64',
        'weather_precip_mm': 'float64',
        'weather_cloud_pc': 'float64',
        'weather_pressure_hpa': 'float64',
        'weather_condition_code': 'string',
        'weather_wind_dir_card': 'string'
    }

def enrich_observation_with_weather(observation: Dict[str, Any], weather_data: WeatherData) -> Dict[str, Any]:
    """Enrich observation with weather data using nested structure."""
    enriched = observation.copy()
    enriched.update(weather_data.to_dict())
    return enriched
