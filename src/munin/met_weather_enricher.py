"""
MET Norway Weather Enricher for Wildlife Observations

Uses MET Norway Locationforecast API (yr.no backend) for weather data.
Includes caching and rate limiting considerations.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
from pathlib import Path

from ..common.utils.gps_utils import calculate_distance_km, parse_cache_key

logger = logging.getLogger(__name__)

class METWeatherEnricher:
    """
    Weather enricher using MET Norway Locationforecast API.

    Features:
    - Caching: (lat,lon,hour) → forecast JSON on disk/S3 (TTL 2-3h)
    - Fallback to nearest time
    - Rate limiting and unique User-Agent
    - Europe/Stockholm timezone normalization
    """

    def __init__(self, cache_dir: str = "/tmp/weather_cache", 
                 ttl_hours: int = 72, proximity_km: float = 10.0):
        self.base_url = ("https://api.met.no/weatherapi/"
                         "locationforecast/2.0/compact")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours  # 72 hours cache for same location
        self.proximity_km = proximity_km  # 10km radius for proximity caching
        self.user_agent = ("WildlifePipeline/1.0 "
                           "(https://github.com/your-org/wildlife-pipeline)")

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
        """Generate cache key for (lat,lon) combination with 72h cache."""
        # Round coordinates to ~100m precision for location-based caching
        lat_rounded = round(lat, 3)  # ~100m precision
        lon_rounded = round(lon, 3)  # ~100m precision
        return f"{lat_rounded:.3f}_{lon_rounded:.3f}"

    def _find_proximity_cache(self, lat: float, lon: float) -> Optional[Tuple[str, Dict]]:
        """Find cached forecast within proximity radius (10km)."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)

                    # Check TTL first
                    cached_time = datetime.fromisoformat(cached_data['cached_at'])
                    if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                        continue  # Skip expired cache

                    # Extract coordinates from cache key
                    cache_key = cache_file.stem
                    try:
                        cached_lat, cached_lon = parse_cache_key(cache_key)

                        # Calculate distance using common GPS utils
                        distance_km = calculate_distance_km(lat, lon, cached_lat, cached_lon)

                        if distance_km <= self.proximity_km:
                            logger.info(f"Found proximity cache within {distance_km:.2f}km of {lat:.4f}, {lon:.4f}")
                            return cache_key, cached_data['forecast']

                    except ValueError:
                        # Skip invalid cache keys
                        continue

                except Exception as e:
                    logger.warning(f"Failed to check proximity cache {cache_file}: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"Failed to find proximity cache: {e}")
            return None

    def _get_cached_forecast(self, cache_key: str) -> Optional[Dict]:
        """Get cached forecast if still valid (72h TTL for same location)."""
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)

            # Check TTL (72 hours for same location)
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                cache_file.unlink()  # Remove expired cache
                logger.debug(f"Cache expired for {cache_key} (older than {self.ttl_hours}h)")
                return None

            logger.debug(f"Using cached forecast for {cache_key} (age: {datetime.now() - cached_time})")
            return cached_data['forecast']

        except Exception as e:
            logger.warning(f"Failed to read cache {cache_key}: {e}")
            return None

    def _cache_forecast(self, cache_key: str, forecast: Dict):
        """Cache forecast data for 72 hours (same location)."""
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'forecast': forecast,
                'ttl_hours': self.ttl_hours,
                'location': cache_key
            }

            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            logger.info(f"Cached forecast for {cache_key} (TTL: {self.ttl_hours}h)")

        except Exception as e:
            logger.warning(f"Failed to cache forecast {cache_key}: {e}")

    def _fetch_forecast(self, lat: float, lon: float) -> Dict:
        """Fetch forecast from MET Norway API."""
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

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch weather forecast: {e}")
            raise

    def _find_nearest_forecast(self, forecast: Dict, target_time: datetime) -> Optional[Dict]:
        """Find the nearest forecast time to target_time."""
        if 'properties' not in forecast or 'timeseries' not in forecast['properties']:
            return None

        timeseries = forecast['properties']['timeseries']

        # Convert target time to UTC (MET API uses UTC)
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

        # Extract weather data
        weather_data = {
            'weather_time': forecast_entry['time'],
            'temp_c': instant.get('air_temperature', None),
            'wind_ms': instant.get('wind_speed', None),
            'wind_dir_deg': instant.get('wind_from_direction', None),
            'precip_mm': instant.get('precipitation_amount', 0),
            'cloud_pc': instant.get('cloud_area_fraction', None),
            'pressure_hpa': instant.get('air_pressure_at_sea_level', None),
            'condition_code': self._get_condition_code(instant),
            'wind_dir_card': self._get_cardinal_direction(instant.get('wind_from_direction'))
        }

        return weather_data

    def _get_condition_code(self, instant: Dict) -> str:
        """Get weather condition code from forecast data."""
        # Simple condition mapping based on available data
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

    def enrich_observation(self, lat: float, lon: float, timestamp: datetime) -> Dict:
        """
        Enrich a single observation with weather data.

        Args:
            lat: Latitude
            lon: Longitude
            timestamp: Observation timestamp (will be normalized to Europe/Stockholm)

        Returns:
            Dictionary with weather data
        """
        try:
            # Normalize timestamp to Europe/Stockholm
            stockholm_tz = datetime.now().astimezone().tzinfo
            normalized_time = timestamp.astimezone(stockholm_tz)

            # Check proximity cache first (10km radius, 72h TTL)
            proximity_result = self._find_proximity_cache(lat, lon)

            if proximity_result:
                cache_key, cached_forecast = proximity_result
                logger.info(f"Using proximity cache for {lat:.4f}, {lon:.4f} (within {self.proximity_km}km)")
                forecast = cached_forecast
            else:
                # Check exact location cache
                cache_key = self._get_cache_key(lat, lon, normalized_time)
                cached_forecast = self._get_cached_forecast(cache_key)

                if cached_forecast:
                    logger.info(f"Using exact location cache for {lat:.4f}, {lon:.4f}")
                    forecast = cached_forecast
                else:
                    # Fetch from API (only if not cached within proximity)
                    logger.info(f"Fetching fresh forecast for {lat:.4f}, {lon:.4f} (not in proximity cache)")
                    forecast = self._fetch_forecast(lat, lon)
                    self._cache_forecast(cache_key, forecast)

            # Find nearest forecast time
            nearest_forecast = self._find_nearest_forecast(forecast, normalized_time)

            if not nearest_forecast:
                logger.warning(f"No forecast found for {lat:.4f}, {lon:.4f} at {normalized_time}")
                return {}

            # Extract weather data
            weather_data = self._extract_weather_data(nearest_forecast)

            logger.info(f"Weather enrichment successful for {lat:.4f}, {lon:.4f}")
            return weather_data

        except Exception as e:
            logger.error(f"Weather enrichment failed for {lat:.4f}, {lon:.4f}: {e}")
            return {}

    def enrich_observations(self, observations: List[Dict]) -> List[Dict]:
        """
        Enrich multiple observations with weather data.

        Args:
            observations: List of observation dictionaries with lat, lon, timestamp

        Returns:
            List of enriched observations
        """
        enriched_observations = []

        for obs in observations:
            try:
                lat = obs.get('lat')
                lon = obs.get('lon')
                timestamp = obs.get('timestamp')

                if not all([lat, lon, timestamp]):
                    logger.warning(f"Skipping observation with missing coordinates/timestamp: {obs}")
                    enriched_observations.append(obs)
                    continue

                # Parse timestamp if it's a string
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)

                # Enrich with weather data
                weather_data = self.enrich_observation(lat, lon, timestamp)

                # Add weather data to observation
                enriched_obs = obs.copy()
                enriched_obs.update(weather_data)
                enriched_observations.append(enriched_obs)

            except Exception as e:
                logger.error(f"Failed to enrich observation {obs}: {e}")
                enriched_observations.append(obs)

        return enriched_observations

    def cleanup_expired_cache(self):
        """Clean up expired cache files."""
        try:
            expired_files = []
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)

                    cached_time = datetime.fromisoformat(cached_data['cached_at'])
                    if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                        expired_files.append(cache_file)

                except Exception as e:
                    logger.warning(f"Failed to check cache file {cache_file}: {e}")
                    expired_files.append(cache_file)  # Remove corrupted files

            for cache_file in expired_files:
                cache_file.unlink()
                logger.debug(f"Removed expired cache: {cache_file.name}")

            logger.info(f"Cleaned up {len(expired_files)} expired cache files")

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics including proximity information."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            # Analyze cache coverage
            valid_caches = 0
            expired_caches = 0

            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)

                    cached_time = datetime.fromisoformat(cached_data['cached_at'])
                    if datetime.now() - cached_time <= timedelta(hours=self.ttl_hours):
                        valid_caches += 1
                    else:
                        expired_caches += 1

                except Exception:
                    expired_caches += 1

            return {
                'cache_dir': str(self.cache_dir),
                'total_files': len(cache_files),
                'valid_caches': valid_caches,
                'expired_caches': expired_caches,
                'total_size_bytes': total_size,
                'ttl_hours': self.ttl_hours,
                'proximity_km': self.proximity_km
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    def test_proximity_cache(self, test_lat: float, test_lon: float) -> Dict[str, Any]:
        """Test proximity cache functionality for a given location."""
        try:
            # Find proximity cache
            proximity_result = self._find_proximity_cache(test_lat, test_lon)

            if proximity_result:
                cache_key, cached_forecast = proximity_result
                cached_lat, cached_lon = parse_cache_key(cache_key)
                distance_km = calculate_distance_km(test_lat, test_lon, cached_lat, cached_lon)

                return {
                    'found': True,
                    'cache_key': cache_key,
                    'cached_location': f"{cached_lat:.4f}, {cached_lon:.4f}",
                    'distance_km': round(distance_km, 2),
                    'within_proximity': distance_km <= self.proximity_km
                }
            else:
                return {
                    'found': False,
                    'proximity_km': self.proximity_km,
                    'message': f"No cache found within {self.proximity_km}km radius"
                }

        except Exception as e:
            logger.error(f"Failed to test proximity cache: {e}")
            return {'error': str(e)}
