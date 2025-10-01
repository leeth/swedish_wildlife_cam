#!/usr/bin/env python3
"""
Observation Weather Enricher for Munin

This module enriches individual positive wildlife observations with weather data
from YR.no at the specific time and location of the observation.

Key features:
- Only enriches positive observations (with animals detected)
- Uses exact timestamp and GPS coordinates from observation
- Efficient single-observation weather lookup
- Integrates with existing observation database
"""

# Removed unused import logging
import requests
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..common.core.base import BaseProcessor
from ..common.exceptions import ValidationError
from ..common.utils.logging_utils import get_logger


@dataclass
class WeatherObservation:
    """Weather observation for a specific time and location."""
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
    dew_point: Optional[float] = None
    wind_gust: Optional[float] = None


class ObservationWeatherEnricher(BaseProcessor):
    """Weather enricher for individual wildlife observations."""

    def __init__(self, db_path: Path, user_agent: str = "Wildlife-Pipeline/1.0", **kwargs):
        super().__init__(**kwargs)
        self.db_path = db_path
        self.logger = get_logger(self.__class__.__name__)
        self.user_agent = user_agent

        # YR.no API configuration
        self.base_url = "https://api.met.no/weatherapi"
        self.location_forecast_url = "/locationforecast/2.0/complete"

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with weather tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Weather observations table (linked to individual observations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_weather (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL,
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
                    dew_point REAL,
                    wind_gust REAL,
                    created_at TEXT NOT NULL,
                    UNIQUE(observation_id)
                )
            """)

            # Weather cache table for API responses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_weather_cache (
                    cache_key TEXT PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    date TEXT NOT NULL,
                    response_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_weather_observation ON observation_weather(observation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_weather_timestamp ON observation_weather(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_weather_coords ON observation_weather(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_cache_key ON observation_weather_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_cache_expires ON observation_weather_cache(expires_at)")

            conn.commit()

    def process(self, input_data: Any) -> Any:
        """Process weather enrichment request.

        Args:
            input_data: Observation data or list of observations

        Returns:
            Weather enrichment results
        """
        if isinstance(input_data, dict):
            return self.enrich_single_observation(input_data)
        elif isinstance(input_data, list):
            return self.enrich_observations_batch(input_data)
        else:
            raise ValidationError("Input data must be observation dictionary or list of observations")

    def enrich_single_observation(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single positive observation with weather data.

        Args:
            observation_data: Dictionary containing observation information
                - observation_id: Unique observation ID
                - timestamp: Observation timestamp
                - latitude: GPS latitude
                - longitude: GPS longitude
                - (optional) camera_id: Camera identifier

        Returns:
            Weather enrichment results
        """
        observation_id = observation_data.get('observation_id')
        timestamp = observation_data.get('timestamp')
        latitude = observation_data.get('latitude')
        longitude = observation_data.get('longitude')

        if not all([observation_id, timestamp, latitude, longitude]):
            raise ValidationError("observation_id, timestamp, latitude, and longitude are required")

        # Convert timestamp if it's a string
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # with ProcessingTimer(self.logger, f"Weather enrichment for observation {observation_id}"):
        try:
            # Check if already enriched
            existing_weather = self._get_weather_for_observation(observation_id)
            if existing_weather:
                self.logger.info(f"Observation {observation_id} already has weather data")
                return {
                    "success": True,
                    "observation_id": observation_id,
                    "already_enriched": True,
                    "weather_data": existing_weather
                }

            # Fetch weather data from YR.no
            weather_data = self._fetch_weather_for_observation(
                latitude, longitude, timestamp
            )

            if not weather_data:
                self.logger.warning(f"No weather data found for observation {observation_id}")
                return {
                    "success": False,
                    "observation_id": observation_id,
                    "error": "No weather data available"
                }

            # Store weather data
            self._store_weather_for_observation(observation_id, weather_data)

            return {
                "success": True,
                "observation_id": observation_id,
                "weather_data": {
                    "timestamp": weather_data.timestamp.isoformat(),
                    "temperature": weather_data.temperature,
                    "humidity": weather_data.humidity,
                    "precipitation": weather_data.precipitation,
                    "wind_speed": weather_data.wind_speed,
                    "wind_direction": weather_data.wind_direction,
                    "pressure": weather_data.pressure,
                    "visibility": weather_data.visibility,
                    "cloud_cover": weather_data.cloud_cover,
                    "uv_index": weather_data.uv_index,
                    "dew_point": weather_data.dew_point,
                    "wind_gust": weather_data.wind_gust
                }
            }

        except Exception as e:
            self.logger.error(f"Weather enrichment failed for observation {observation_id}: {e}")
            return {
                "success": False,
                "observation_id": observation_id,
                "error": str(e)
            }

    def enrich_observations_batch(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enrich a batch of positive observations with weather data.

        Args:
            observations: List of observation dictionaries

        Returns:
            Batch enrichment results
        """
        results = {
            "total_observations": len(observations),
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "already_enriched": 0,
            "results": []
        }

        for obs in observations:
            try:
                result = self.enrich_single_observation(obs)
                results["results"].append(result)

                if result["success"]:
                    if result.get("already_enriched"):
                        results["already_enriched"] += 1
                    else:
                        results["successful_enrichments"] += 1
                else:
                    results["failed_enrichments"] += 1

            except Exception as e:
                self.logger.error(f"Failed to enrich observation {obs.get('observation_id', 'unknown')}: {e}")
                results["failed_enrichments"] += 1
                results["results"].append({
                    "success": False,
                    "observation_id": obs.get('observation_id', 'unknown'),
                    "error": str(e)
                })

        return results

    def enrich_positive_observations_from_db(self, days_back: int = 7) -> Dict[str, Any]:
        """Enrich all positive observations from the database.

        Args:
            days_back: Number of days to look back for observations

        Returns:
            Enrichment results
        """
        # Get positive observations from database
        positive_observations = self._get_positive_observations_from_db(days_back)

        if not positive_observations:
            self.logger.info("No positive observations found in database")
            return {
                "total_observations": 0,
                "successful_enrichments": 0,
                "failed_enrichments": 0,
                "already_enriched": 0
            }

        self.logger.info(f"Found {len(positive_observations)} positive observations to enrich")

        # Enrich in batches
        batch_size = 10
        results = {
            "total_observations": len(positive_observations),
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "already_enriched": 0,
            "results": []
        }

        for i in range(0, len(positive_observations), batch_size):
            batch = positive_observations[i:i + batch_size]
            batch_result = self.enrich_observations_batch(batch)

            results["successful_enrichments"] += batch_result["successful_enrichments"]
            results["failed_enrichments"] += batch_result["failed_enrichments"]
            results["already_enriched"] += batch_result["already_enriched"]
            results["results"].extend(batch_result["results"])

            # Small delay between batches to be respectful to API
            if i + batch_size < len(positive_observations):
                import time
                time.sleep(1)

        return results

    def _get_positive_observations_from_db(self, days_back: int) -> List[Dict[str, Any]]:
        """Get positive observations from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query for positive observations with GPS data
            # This assumes you have an observations table with the structure from your pipeline
            cursor.execute("""
                SELECT
                    observation_id,
                    timestamp,
                    latitude,
                    longitude,
                    camera_id,
                    top_label,
                    top_confidence
                FROM observations
                WHERE observation_any = 1
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
                AND timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            """.format(days_back))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def _get_weather_for_observation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        """Get existing weather data for an observation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM observation_weather
                WHERE observation_id = ?
            """, (observation_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def _fetch_weather_for_observation(self, latitude: float, longitude: float,
                                     timestamp: datetime) -> Optional[WeatherObservation]:
        """Fetch weather data for a specific observation."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(latitude, longitude, timestamp.date())
            cached_data = self._get_cached_weather(cache_key)
            if cached_data:
                return self._parse_cached_weather(cached_data, latitude, longitude, timestamp)

            # Fetch from YR.no API
            url = f"{self.base_url}{self.location_forecast_url}"
            params = {
                'lat': latitude,
                'lon': longitude
            }

            headers = {
                'User-Agent': self.user_agent
            }

            self.logger.info(f"Fetching weather data for {latitude}, {longitude} at {timestamp}")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            weather_obs = self._parse_yr_data_for_observation(data, latitude, longitude, timestamp)

            # Cache the response
            self._cache_weather_data(cache_key, latitude, longitude, timestamp.date(), data)

            return weather_obs

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch weather data: {e}")
            return None

    def _parse_yr_data_for_observation(self, data: Dict[str, Any], latitude: float,
                                     longitude: float, target_timestamp: datetime) -> Optional[WeatherObservation]:
        """Parse YR.no data to find the closest weather observation to the target timestamp."""
        try:
            timeseries = data.get('properties', {}).get('timeseries', [])

            # Find the closest timestamp to our target
            closest_obs = None
            min_time_diff = float('inf')

            for item in timeseries:
                timestamp_str = item.get('time')
                if not timestamp_str:
                    continue

                obs_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_diff = abs((obs_timestamp - target_timestamp).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_obs = item

            if not closest_obs:
                return None

            # Parse the closest observation
            details = closest_obs.get('data', {}).get('instant', {}).get('details', {})

            return WeatherObservation(
                timestamp=target_timestamp,  # Use original timestamp
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
                dew_point=details.get('dew_point_temperature'),
                wind_gust=details.get('wind_speed_of_gust')
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse YR.no data: {e}")
            return None

    def _parse_cached_weather(self, cached_data: Dict[str, Any], latitude: float,
                            longitude: float, target_timestamp: datetime) -> Optional[WeatherObservation]:
        """Parse cached weather data to find the closest observation."""
        try:
            import json
            timeseries = json.loads(cached_data)

            # Find the closest timestamp in cached data
            closest_obs = None
            min_time_diff = float('inf')

            for item in timeseries:
                timestamp_str = item.get('time')
                if not timestamp_str:
                    continue

                obs_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_diff = abs((obs_timestamp - target_timestamp).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_obs = item

            if not closest_obs:
                return None

            # Parse the closest observation
            details = closest_obs.get('data', {}).get('instant', {}).get('details', {})

            return WeatherObservation(
                timestamp=target_timestamp,
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
                dew_point=details.get('dew_point_temperature'),
                wind_gust=details.get('wind_speed_of_gust')
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse cached weather data: {e}")
            return None

    def _generate_cache_key(self, latitude: float, longitude: float, date: datetime.date) -> str:
        """Generate cache key for weather request."""
        return f"obs_weather_{latitude}_{longitude}_{date}"

    def _get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT response_data FROM observation_weather_cache
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))

            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row[0])

        return None

    def _cache_weather_data(self, cache_key: str, latitude: float, longitude: float,
                          date: datetime.date, data: Dict[str, Any]):
        """Cache weather data."""
        expires_at = datetime.now() + timedelta(hours=6)  # Cache for 6 hours

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            import json
            data_json = json.dumps(data)

            cursor.execute("""
                INSERT OR REPLACE INTO observation_weather_cache
                (cache_key, latitude, longitude, date, response_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                latitude,
                longitude,
                date.isoformat(),
                data_json,
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))

            conn.commit()

    def _store_weather_for_observation(self, observation_id: str, weather_data: WeatherObservation):
        """Store weather data for an observation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO observation_weather
                (observation_id, timestamp, latitude, longitude,
                 temperature, humidity, precipitation, wind_speed, wind_direction,
                 pressure, visibility, cloud_cover, uv_index, dew_point, wind_gust, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                observation_id,
                weather_data.timestamp.isoformat(),
                weather_data.latitude,
                weather_data.longitude,
                weather_data.temperature,
                weather_data.humidity,
                weather_data.precipitation,
                weather_data.wind_speed,
                weather_data.wind_direction,
                weather_data.pressure,
                weather_data.visibility,
                weather_data.cloud_cover,
                weather_data.uv_index,
                weather_data.dew_point,
                weather_data.wind_gust,
                datetime.now().isoformat()
            ))

            conn.commit()

    def get_weather_for_observation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        """Get weather data for a specific observation."""
        return self._get_weather_for_observation(observation_id)

    def get_weather_statistics(self) -> Dict[str, Any]:
        """Get weather enrichment statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total weather observations
            cursor.execute("SELECT COUNT(*) FROM observation_weather")
            total_observations = cursor.fetchone()[0]

            # Date range
            cursor.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
                FROM observation_weather
            """)
            date_range = cursor.fetchone()

            # Observations by camera (if available)
            cursor.execute("""
                SELECT COUNT(*) FROM observation_weather ow
                JOIN observations o ON ow.observation_id = o.observation_id
                WHERE o.camera_id IS NOT NULL
            """)
            with_camera = cursor.fetchone()[0]

            return {
                "total_weather_observations": total_observations,
                "date_range": {
                    "earliest": date_range[0],
                    "latest": date_range[1]
                } if date_range[0] else None,
                "observations_with_camera": with_camera
            }

    def cleanup_expired_cache(self):
        """Clean up expired weather cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM observation_weather_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} expired weather cache entries")

            return deleted_count
