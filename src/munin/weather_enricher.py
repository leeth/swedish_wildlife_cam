#!/usr/bin/env python3
"""
Weather Data Enricher for Munin

This module enriches wildlife observations with historical weather data
using GPS cluster coordinates. It supports multiple weather APIs and
provides a unified interface for weather data retrieval.

Supported APIs:
- AccuWeather (comprehensive historical data)
- YR.no (free, Nordic focus)
- Visual Crossing (balanced option)
- OpenWeatherMap (alternative)
"""

# Removed unused import logging
import requests
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from ..common.core.base import BaseProcessor
from ..common.exceptions import ProcessingError, ValidationError
from ..common.utils.logging_utils import get_logger, ProcessingTimer


class WeatherProvider(Enum):
    """Supported weather data providers."""
    ACCUWEATHER = "accuweather"
    YR_NO = "yr_no"
    VISUAL_CROSSING = "visual_crossing"
    OPENWEATHERMAP = "openweathermap"


@dataclass
class WeatherObservation:
    """Weather observation data point."""
    timestamp: datetime
    latitude: float
    longitude: float
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    pressure: Optional[float] = None
    visibility: Optional[float] = None
    cloud_cover: Optional[float] = None
    uv_index: Optional[float] = None
    provider: Optional[str] = None
    location_key: Optional[str] = None


@dataclass
class WeatherRequest:
    """Weather data request parameters."""
    latitude: float
    longitude: float
    start_date: datetime
    end_date: datetime
    provider: WeatherProvider = WeatherProvider.ACCUWEATHER
    include_hourly: bool = True
    include_daily: bool = True


class WeatherEnricher(BaseProcessor):
    """Weather data enricher for wildlife observations."""

    def __init__(self, db_path: Path, api_keys: Dict[str, str] = None, **kwargs):
        super().__init__(**kwargs)
        self.db_path = db_path
        self.logger = get_logger(self.__class__.__name__)
        self.api_keys = api_keys or {}

        # API endpoints and configurations
        self.api_configs = {
            WeatherProvider.ACCUWEATHER: {
                'base_url': 'http://dataservice.accuweather.com',
                'location_url': '/locations/v1/cities/geoposition/search',
                'historical_url': '/currentconditions/v1/{location_key}/historical/24h',
                'daily_url': '/forecasts/v1/daily/{location_key}',
                'requires_location_key': True
            },
            WeatherProvider.YR_NO: {
                'base_url': 'https://api.met.no/weatherapi',
                'location_url': '/locationforecast/2.0/complete',
                'historical_url': '/locationforecast/2.0/historical',
                'requires_location_key': False
            },
            WeatherProvider.VISUAL_CROSSING: {
                'base_url': 'https://weather.visualcrossing.com',
                'historical_url': '/VisualCrossingWebServices/rest/services/timeline',
                'requires_location_key': False
            },
            WeatherProvider.OPENWEATHERMAP: {
                'base_url': 'https://api.openweathermap.org/data/2.5',
                'historical_url': '/onecall/timemachine',
                'requires_location_key': False
            }
        }

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with weather tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Weather observations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_observations (
                    observation_id TEXT PRIMARY KEY,
                    cluster_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    temperature REAL,
                    humidity REAL,
                    precipitation REAL,
                    wind_speed REAL,
                    wind_direction REAL,
                    pressure REAL,
                    visibility REAL,
                    cloud_cover REAL,
                    uv_index REAL,
                    provider TEXT NOT NULL,
                    location_key TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (cluster_id) REFERENCES gps_clusters (cluster_id)
                )
            """)

            # Weather cache table for API responses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    date TEXT NOT NULL,
                    response_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_cluster ON weather_observations(cluster_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_timestamp ON weather_observations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_coords ON weather_observations(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON weather_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON weather_cache(expires_at)")

            conn.commit()

    def process(self, input_data: Any) -> Any:
        """Process weather enrichment request.

        Args:
            input_data: Weather request or GPS cluster data

        Returns:
            Weather enrichment results
        """
        if isinstance(input_data, WeatherRequest):
            return self.enrich_weather_data(input_data)
        elif isinstance(input_data, dict) and 'cluster_id' in input_data:
            return self.enrich_cluster_weather(input_data)
        else:
            raise ValidationError("Input data must be WeatherRequest or cluster dictionary")

    def enrich_cluster_weather(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich GPS cluster with weather data.

        Args:
            cluster_data: Dictionary containing cluster information

        Returns:
            Weather enrichment results
        """
        cluster_id = cluster_data.get('cluster_id')
        start_date = cluster_data.get('start_date')
        end_date = cluster_data.get('end_date')
        provider = WeatherProvider(cluster_data.get('provider', 'accuweather'))

        if not cluster_id:
            raise ValidationError("cluster_id is required")

        # Get cluster information
        cluster = self._get_cluster_info(cluster_id)
        if not cluster:
            raise ProcessingError(f"Cluster {cluster_id} not found")

        # Create weather request
        weather_request = WeatherRequest(
            latitude=cluster['center_latitude'],
            longitude=cluster['center_longitude'],
            start_date=start_date or datetime.now() - timedelta(days=7),
            end_date=end_date or datetime.now(),
            provider=provider
        )

        return self.enrich_weather_data(weather_request, cluster_id)

    def enrich_weather_data(self, request: WeatherRequest, cluster_id: Optional[str] = None) -> Dict[str, Any]:
        """Enrich weather data for given coordinates and time range.

        Args:
            request: Weather data request
            cluster_id: Optional cluster ID for association

        Returns:
            Weather enrichment results
        """
        with ProcessingTimer(self.logger, "Weather enrichment"):
            try:
                # Check cache first
                cached_data = self._get_cached_weather(request)
                if cached_data:
                    self.logger.info(f"Using cached weather data for {request.latitude}, {request.longitude}")
                    return cached_data

                # Fetch weather data from API
                weather_data = self._fetch_weather_data(request)

                # Store in database
                stored_count = self._store_weather_data(weather_data, cluster_id)

                # Cache the response
                self._cache_weather_data(request, weather_data)

                return {
                    "success": True,
                    "observations_count": len(weather_data),
                    "stored_count": stored_count,
                    "provider": request.provider.value,
                    "coordinates": {
                        "latitude": request.latitude,
                        "longitude": request.longitude
                    },
                    "date_range": {
                        "start": request.start_date.isoformat(),
                        "end": request.end_date.isoformat()
                    }
                }

            except Exception as e:
                self.logger.error(f"Weather enrichment failed: {e}")
                raise ProcessingError(f"Weather enrichment failed: {e}")

    def _get_cluster_info(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster information from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT cluster_id, center_latitude, center_longitude, name
                FROM gps_clusters
                WHERE cluster_id = ?
            """, (cluster_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def _get_cached_weather(self, request: WeatherRequest) -> Optional[Dict[str, Any]]:
        """Check for cached weather data."""
        cache_key = self._generate_cache_key(request)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT response_data FROM weather_cache
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))

            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row[0])

        return None

    def _cache_weather_data(self, request: WeatherRequest, weather_data: List[WeatherObservation]):
        """Cache weather data for future use."""
        cache_key = self._generate_cache_key(request)
        expires_at = datetime.now() + timedelta(hours=24)  # Cache for 24 hours

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Convert weather data to JSON
            import json
            data_json = json.dumps([
                {
                    "timestamp": obs.timestamp.isoformat(),
                    "latitude": obs.latitude,
                    "longitude": obs.longitude,
                    "temperature": obs.temperature,
                    "humidity": obs.humidity,
                    "precipitation": obs.precipitation,
                    "wind_speed": obs.wind_speed,
                    "wind_direction": obs.wind_direction,
                    "pressure": obs.pressure,
                    "visibility": obs.visibility,
                    "cloud_cover": obs.cloud_cover,
                    "uv_index": obs.uv_index,
                    "provider": obs.provider,
                    "location_key": obs.location_key
                }
                for obs in weather_data
            ])

            cursor.execute("""
                INSERT OR REPLACE INTO weather_cache
                (cache_key, provider, latitude, longitude, date, response_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                request.provider.value,
                request.latitude,
                request.longitude,
                request.start_date.date().isoformat(),
                data_json,
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))

            conn.commit()

    def _generate_cache_key(self, request: WeatherRequest) -> str:
        """Generate cache key for weather request."""
        return f"{request.provider.value}_{request.latitude}_{request.longitude}_{request.start_date.date()}_{request.end_date.date()}"

    def _fetch_weather_data(self, request: WeatherRequest) -> List[WeatherObservation]:
        """Fetch weather data from the specified provider."""
        provider = request.provider
        config = self.api_configs[provider]

        if provider == WeatherProvider.ACCUWEATHER:
            return self._fetch_accuweather_data(request, config)
        elif provider == WeatherProvider.YR_NO:
            return self._fetch_yr_data(request, config)
        elif provider == WeatherProvider.VISUAL_CROSSING:
            return self._fetch_visual_crossing_data(request, config)
        elif provider == WeatherProvider.OPENWEATHERMAP:
            return self._fetch_openweathermap_data(request, config)
        else:
            raise ValidationError(f"Unsupported weather provider: {provider}")

    def _fetch_accuweather_data(self, request: WeatherRequest, config: Dict[str, str]) -> List[WeatherObservation]:
        """Fetch weather data from AccuWeather API."""
        api_key = self.api_keys.get('accuweather')
        if not api_key:
            raise ProcessingError("AccuWeather API key not provided")

        # Get location key
        location_key = self._get_accuweather_location_key(
            request.latitude, request.longitude, api_key, config
        )

        if not location_key:
            raise ProcessingError("Could not obtain AccuWeather location key")

        # Fetch historical data
        weather_data = []
        current_date = request.start_date

        while current_date <= request.end_date:
            try:
                url = f"{config['base_url']}{config['historical_url'].format(location_key=location_key)}"
                params = {
                    'apikey': api_key,
                    'details': 'true'
                }

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                for item in data:
                    obs = self._parse_accuweather_observation(item, request.latitude, request.longitude, location_key)
                    if obs:
                        weather_data.append(obs)

                current_date += timedelta(days=1)

            except requests.RequestException as e:
                self.logger.warning(f"Failed to fetch AccuWeather data for {current_date}: {e}")
                current_date += timedelta(days=1)
                continue

        return weather_data

    def _get_accuweather_location_key(self, latitude: float, longitude: float, api_key: str, config: Dict[str, str]) -> Optional[str]:
        """Get AccuWeather location key for coordinates."""
        try:
            url = f"{config['base_url']}{config['location_url']}"
            params = {
                'apikey': api_key,
                'q': f"{latitude},{longitude}"
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get('Key')

        except requests.RequestException as e:
            self.logger.error(f"Failed to get AccuWeather location key: {e}")
            return None

    def _parse_accuweather_observation(self, data: Dict[str, Any], latitude: float, longitude: float, location_key: str) -> Optional[WeatherObservation]:
        """Parse AccuWeather observation data."""
        try:
            timestamp_str = data.get('LocalObservationDateTime')
            if not timestamp_str:
                return None

            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            return WeatherObservation(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                temperature=data.get('Temperature', {}).get('Metric', {}).get('Value'),
                humidity=data.get('RelativeHumidity'),
                precipitation=data.get('PrecipitationSummary', {}).get('PastHour', {}).get('Metric', {}).get('Value'),
                wind_speed=data.get('Wind', {}).get('Speed', {}).get('Metric', {}).get('Value'),
                wind_direction=data.get('Wind', {}).get('Direction', {}).get('Degrees'),
                pressure=data.get('Pressure', {}).get('Metric', {}).get('Value'),
                visibility=data.get('Visibility', {}).get('Metric', {}).get('Value'),
                cloud_cover=data.get('CloudCover'),
                uv_index=data.get('UVIndex'),
                provider='accuweather',
                location_key=location_key
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse AccuWeather observation: {e}")
            return None

    def _fetch_yr_data(self, request: WeatherRequest, config: Dict[str, str]) -> List[WeatherObservation]:
        """Fetch weather data from YR.no API."""
        try:
            url = f"{config['base_url']}{config['historical_url']}"
            params = {
                'lat': request.latitude,
                'lon': request.longitude,
                'start': request.start_date.isoformat(),
                'end': request.end_date.isoformat()
            }

            headers = {
                'User-Agent': 'Wildlife-Pipeline/1.0 (contact@example.com)'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            return self._parse_yr_data(data, request.latitude, request.longitude)

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch YR.no data: {e}")
            return []

    def _parse_yr_data(self, data: Dict[str, Any], latitude: float, longitude: float) -> List[WeatherObservation]:
        """Parse YR.no weather data."""
        observations = []

        try:
            timeseries = data.get('properties', {}).get('timeseries', [])

            for item in timeseries:
                timestamp_str = item.get('time')
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                details = item.get('data', {}).get('instant', {}).get('details', {})

                obs = WeatherObservation(
                    timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                    temperature=details.get('air_temperature'),
                    humidity=details.get('relative_humidity'),
                    precipitation=details.get('precipitation_amount'),
                    wind_speed=details.get('wind_speed'),
                    wind_direction=details.get('wind_from_direction'),
                    pressure=details.get('air_pressure_at_sea_level'),
                    visibility=details.get('visibility'),
                    cloud_cover=details.get('cloud_area_fraction'),
                    uv_index=details.get('ultraviolet_index_clear_sky'),
                    provider='yr_no'
                )

                observations.append(obs)

        except Exception as e:
            self.logger.warning(f"Failed to parse YR.no data: {e}")

        return observations

    def _fetch_visual_crossing_data(self, request: WeatherRequest, config: Dict[str, str]) -> List[WeatherObservation]:
        """Fetch weather data from Visual Crossing API."""
        api_key = self.api_keys.get('visual_crossing')
        if not api_key:
            raise ProcessingError("Visual Crossing API key not provided")

        try:
            url = f"{config['base_url']}{config['historical_url']}/{request.latitude},{request.longitude}/{request.start_date.date()}/{request.end_date.date()}"
            params = {
                'key': api_key,
                'include': 'hours',
                'elements': 'datetime,temp,humidity,precip,windspeed,winddir,pressure,visibility,cloudcover,uvindex'
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return self._parse_visual_crossing_data(data, request.latitude, request.longitude)

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch Visual Crossing data: {e}")
            return []

    def _parse_visual_crossing_data(self, data: Dict[str, Any], latitude: float, longitude: float) -> List[WeatherObservation]:
        """Parse Visual Crossing weather data."""
        observations = []

        try:
            days = data.get('days', [])

            for day in days:
                date_str = day.get('datetime')
                if not date_str:
                    continue

                hours = day.get('hours', [])

                for hour in hours:
                    timestamp_str = f"{date_str}T{hour.get('datetime')}"
                    timestamp = datetime.fromisoformat(timestamp_str)

                    obs = WeatherObservation(
                        timestamp=timestamp,
                        latitude=latitude,
                        longitude=longitude,
                        temperature=hour.get('temp'),
                        humidity=hour.get('humidity'),
                        precipitation=hour.get('precip'),
                        wind_speed=hour.get('windspeed'),
                        wind_direction=hour.get('winddir'),
                        pressure=hour.get('pressure'),
                        visibility=hour.get('visibility'),
                        cloud_cover=hour.get('cloudcover'),
                        uv_index=hour.get('uvindex'),
                        provider='visual_crossing'
                    )

                    observations.append(obs)

        except Exception as e:
            self.logger.warning(f"Failed to parse Visual Crossing data: {e}")

        return observations

    def _fetch_openweathermap_data(self, request: WeatherRequest, config: Dict[str, str]) -> List[WeatherObservation]:
        """Fetch weather data from OpenWeatherMap API."""
        api_key = self.api_keys.get('openweathermap')
        if not api_key:
            raise ProcessingError("OpenWeatherMap API key not provided")

        observations = []
        current_date = request.start_date

        while current_date <= request.end_date:
            try:
                # OpenWeatherMap One Call API 3.0
                url = f"{config['base_url']}{config['historical_url']}"
                params = {
                    'lat': request.latitude,
                    'lon': request.longitude,
                    'dt': int(current_date.timestamp()),
                    'appid': api_key,
                    'units': 'metric'
                }

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                obs = self._parse_openweathermap_data(data, request.latitude, request.longitude)
                if obs:
                    observations.append(obs)

                current_date += timedelta(days=1)

            except requests.RequestException as e:
                self.logger.warning(f"Failed to fetch OpenWeatherMap data for {current_date}: {e}")
                current_date += timedelta(days=1)
                continue

        return observations

    def _parse_openweathermap_data(self, data: Dict[str, Any], latitude: float, longitude: float) -> Optional[WeatherObservation]:
        """Parse OpenWeatherMap weather data."""
        try:
            current = data.get('current', {})
            timestamp = datetime.fromtimestamp(current.get('dt', 0))

            return WeatherObservation(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                temperature=current.get('temp'),
                humidity=current.get('humidity'),
                precipitation=current.get('rain', {}).get('1h', 0),
                wind_speed=current.get('wind_speed'),
                wind_direction=current.get('wind_deg'),
                pressure=current.get('pressure'),
                visibility=current.get('visibility'),
                cloud_cover=current.get('clouds'),
                uv_index=current.get('uvi'),
                provider='openweathermap'
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse OpenWeatherMap data: {e}")
            return None

    def _store_weather_data(self, weather_data: List[WeatherObservation], cluster_id: Optional[str] = None) -> int:
        """Store weather observations in database."""
        if not weather_data:
            return 0

        stored_count = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for obs in weather_data:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO weather_observations
                        (observation_id, cluster_id, timestamp, latitude, longitude,
                         temperature, humidity, precipitation, wind_speed, wind_direction,
                         pressure, visibility, cloud_cover, uv_index, provider, location_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"weather_{obs.timestamp.isoformat()}_{obs.latitude}_{obs.longitude}",
                        cluster_id,
                        obs.timestamp.isoformat(),
                        obs.latitude,
                        obs.longitude,
                        obs.temperature,
                        obs.humidity,
                        obs.precipitation,
                        obs.wind_speed,
                        obs.wind_direction,
                        obs.pressure,
                        obs.visibility,
                        obs.cloud_cover,
                        obs.uv_index,
                        obs.provider,
                        obs.location_key,
                        datetime.now().isoformat()
                    ))

                    stored_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to store weather observation: {e}")
                    continue

            conn.commit()

        return stored_count

    def get_weather_for_cluster(self, cluster_id: str, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get weather data for a specific cluster."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT * FROM weather_observations
                WHERE cluster_id = ?
            """
            params = [cluster_id]

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_weather_statistics(self) -> Dict[str, Any]:
        """Get weather data statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total weather observations
            cursor.execute("SELECT COUNT(*) FROM weather_observations")
            total_observations = cursor.fetchone()[0]

            # Observations by provider
            cursor.execute("""
                SELECT provider, COUNT(*) as count
                FROM weather_observations
                GROUP BY provider
            """)
            provider_stats = dict(cursor.fetchall())

            # Date range
            cursor.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
                FROM weather_observations
            """)
            date_range = cursor.fetchone()

            return {
                "total_observations": total_observations,
                "provider_stats": provider_stats,
                "date_range": {
                    "earliest": date_range[0],
                    "latest": date_range[1]
                } if date_range[0] else None
            }

    def cleanup_expired_cache(self):
        """Clean up expired weather cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM weather_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} expired cache entries")

            return deleted_count
