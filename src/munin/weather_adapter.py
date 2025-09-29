"""
Weather Adapter for MET Norway Locationforecast API

Simple client for getting hourly weather data with caching and ETag support.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from pathlib import Path
import hashlib

from ..common.utils.gps_utils import calculate_distance_km, parse_cache_key

logger = logging.getLogger(__name__)

class METWeatherAdapter:
    """
    Weather adapter for MET Norway Locationforecast API.
    
    Features:
    - get_hourly(lat, lon, ts) → nearest hour from Locationforecast
    - User-Agent: 'wildlife-pipeline/0.1 (email)'
    - Disk/S3 cache per (lat,lon,yyyy-mm-ddThh) + ETag/Expires
    - Proximity caching with 10km radius
    """
    
    def __init__(self, cache_dir: str = "/tmp/weather_cache", proximity_km: float = 10.0):
        self.base_url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.proximity_km = proximity_km
        self.user_agent = "wildlife-pipeline/0.1 (asbjorn@example.com)"
        
        # Rate limiting: max 1 request per second
        self.last_request_time = 0
        self.min_request_interval = 1.0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, lat: float, lon: float, timestamp: datetime) -> str:
        """Generate cache key for (lat,lon,yyyy-mm-ddThh) combination."""
        # Round coordinates to ~100m precision
        lat_rounded = round(lat, 3)
        lon_rounded = round(lon, 3)
        
        # Round timestamp to nearest hour
        hour_timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        hour_str = hour_timestamp.strftime('%Y-%m-%dT%H')
        
        return f"{lat_rounded:.3f}_{lon_rounded:.3f}_{hour_str}"
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_cached_forecast(self, cache_key: str) -> Optional[Dict]:
        """Get cached forecast if still valid (check ETag/Expires)."""
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check ETag/Expires
            if 'expires' in cached_data:
                expires_time = datetime.fromisoformat(cached_data['expires'])
                if datetime.now() > expires_time:
                    logger.debug(f"Cache expired for {cache_key}")
                    cache_file.unlink()
                    return None
            
            logger.debug(f"Using cached forecast for {cache_key}")
            return cached_data['forecast']
        
        except Exception as e:
            logger.warning(f"Failed to read cache {cache_key}: {e}")
            return None
    
    def _cache_forecast(self, cache_key: str, forecast: Dict, etag: Optional[str] = None, expires: Optional[str] = None):
        """Cache forecast data with ETag/Expires metadata."""
        cache_file = self._get_cache_file(cache_key)
        
        try:
            cache_data = {
                'forecast': forecast,
                'cached_at': datetime.now().isoformat(),
                'etag': etag,
                'expires': expires
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            logger.info(f"Cached forecast for {cache_key} (ETag: {etag}, Expires: {expires})")
        
        except Exception as e:
            logger.warning(f"Failed to cache forecast {cache_key}: {e}")
    
    def _find_proximity_cache(self, lat: float, lon: float, timestamp: datetime) -> Optional[Tuple[str, Dict]]:
        """Find cached forecast within proximity radius."""
        try:
            # Round timestamp to nearest hour for proximity search
            hour_timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    # Check expires
                    if 'expires' in cached_data:
                        expires_time = datetime.fromisoformat(cached_data['expires'])
                        if datetime.now() > expires_time:
                            continue
                    
                    # Extract coordinates from cache key
                    cache_key = cache_file.stem
                    if '_' in cache_key:
                        try:
                            cached_lat, cached_lon = parse_cache_key(cache_key.split('_')[0] + '_' + cache_key.split('_')[1])
                            
                            # Calculate distance
                            distance_km = calculate_distance_km(lat, lon, cached_lat, cached_lon)
                            
                            if distance_km <= self.proximity_km:
                                logger.info(f"Found proximity cache within {distance_km:.2f}km of {lat:.4f}, {lon:.4f}")
                                return cache_key, cached_data['forecast']
                        
                        except ValueError:
                            continue
                
                except Exception as e:
                    logger.warning(f"Failed to check proximity cache {cache_file}: {e}")
                    continue
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to find proximity cache: {e}")
            return None
    
    def _fetch_forecast(self, lat: float, lon: float) -> Tuple[Dict, Optional[str], Optional[str]]:
        """Fetch forecast from MET Norway API with ETag support."""
        self._rate_limit()
        
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        
        params = {
            'lat': lat,
            'lon': lon
        }
        
        try:
            logger.info(f"Fetching weather forecast for {lat:.4f}, {lon:.4f}")
            response = requests.get(self.base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            # Extract ETag and Expires headers
            etag = response.headers.get('ETag')
            expires = response.headers.get('Expires')
            
            return response.json(), etag, expires
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch weather forecast: {e}")
            raise
    
    def _find_nearest_forecast(self, forecast: Dict, target_time: datetime) -> Optional[Dict]:
        """Find the nearest forecast time to target_time."""
        if 'properties' not in forecast or 'timeseries' not in forecast['properties']:
            return None
        
        timeseries = forecast['properties']['timeseries']
        
        # Convert target time to UTC
        target_utc = target_time.astimezone().utctimetuple()
        target_timestamp = time.mktime(target_utc)
        
        best_match = None
        min_diff = float('inf')
        
        for entry in timeseries:
            try:
                # Parse time from forecast entry
                forecast_time = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
                forecast_timestamp = forecast_time.timestamp()
                
                # Calculate time difference
                time_diff = abs(forecast_timestamp - target_timestamp)
                
                if time_diff < min_diff:
                    min_diff = time_diff
                    best_match = entry
            
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse forecast time: {e}")
                continue
        
        return best_match
    
    def _extract_weather_data(self, forecast_entry: Dict) -> Dict:
        """Extract weather data from forecast entry."""
        if 'data' not in forecast_entry or 'instant' not in forecast_entry['data']:
            return {}
        
        instant = forecast_entry['data']['instant']['details']
        
        # Extract weather data with met_source
        weather_data = {
            'weather_time': forecast_entry['time'],
            'weather_temp_c': instant.get('air_temperature', None),
            'weather_wind_ms': instant.get('wind_speed', None),
            'weather_wind_dir_deg': instant.get('wind_from_direction', None),
            'weather_precip_mm': instant.get('precipitation_amount', 0),
            'weather_cloud_pc': instant.get('cloud_area_fraction', None),
            'weather_pressure_hpa': instant.get('air_pressure_at_sea_level', None),
            'weather_condition_code': self._get_condition_code(instant),
            'weather_wind_dir_card': self._get_cardinal_direction(instant.get('wind_from_direction')),
            'met_source': 'locationforecast/2.0'
        }
        
        return weather_data
    
    def _get_condition_code(self, instant: Dict) -> str:
        """Get weather condition code from forecast data."""
        if instant.get('precipitation_amount', 0) > 0:
            return 'rain'
        elif instant.get('cloud_area_fraction', 0) > 0.8:
            return 'cloudy'
        elif instant.get('cloud_area_fraction', 0) > 0.3:
            return 'partly_cloudy'
        else:
            return 'clear'
    
    def _get_cardinal_direction(self, wind_dir_deg: Optional[float]) -> Optional[str]:
        """Convert wind direction degrees to cardinal direction."""
        if wind_dir_deg is None:
            return None
        
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = int((wind_dir_deg + 22.5) / 45) % 8
        return directions[index]
    
    def get_hourly(self, lat: float, lon: float, timestamp: datetime) -> Dict:
        """
        Get hourly weather data for given coordinates and timestamp.
        
        Args:
            lat: Latitude
            lon: Longitude
            timestamp: Target timestamp
        
        Returns:
            Dictionary with weather data including met_source
        """
        try:
            # Normalize timestamp to nearest hour
            hour_timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
            
            # Check proximity cache first
            proximity_result = self._find_proximity_cache(lat, lon, hour_timestamp)
            
            if proximity_result:
                cache_key, cached_forecast = proximity_result
                logger.info(f"Using proximity cache for {lat:.4f}, {lon:.4f}")
                forecast = cached_forecast
            else:
                # Check exact location cache
                cache_key = self._get_cache_key(lat, lon, hour_timestamp)
                cached_forecast = self._get_cached_forecast(cache_key)
                
                if cached_forecast:
                    logger.info(f"Using exact location cache for {lat:.4f}, {lon:.4f}")
                    forecast = cached_forecast
                else:
                    # Fetch from API
                    logger.info(f"Fetching fresh forecast for {lat:.4f}, {lon:.4f}")
                    forecast, etag, expires = self._fetch_forecast(lat, lon)
                    self._cache_forecast(cache_key, forecast, etag, expires)
            
            # Find nearest forecast time
            nearest_forecast = self._find_nearest_forecast(forecast, timestamp)
            
            if not nearest_forecast:
                logger.warning(f"No forecast found for {lat:.4f}, {lon:.4f} at {timestamp}")
                return {'met_source': 'locationforecast/2.0'}
            
            # Extract weather data
            weather_data = self._extract_weather_data(nearest_forecast)
            
            logger.info(f"Weather data retrieved for {lat:.4f}, {lon:.4f}")
            return weather_data
        
        except Exception as e:
            logger.error(f"Weather data retrieval failed for {lat:.4f}, {lon:.4f}: {e}")
            return {'met_source': 'locationforecast/2.0'}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            valid_caches = 0
            expired_caches = 0
            
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    
                    if 'expires' in cached_data:
                        expires_time = datetime.fromisoformat(cached_data['expires'])
                        if datetime.now() <= expires_time:
                            valid_caches += 1
                        else:
                            expired_caches += 1
                    else:
                        valid_caches += 1
                
                except Exception:
                    expired_caches += 1
            
            return {
                'cache_dir': str(self.cache_dir),
                'total_files': len(cache_files),
                'valid_caches': valid_caches,
                'expired_caches': expired_caches,
                'total_size_bytes': total_size,
                'proximity_km': self.proximity_km
            }
        
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
