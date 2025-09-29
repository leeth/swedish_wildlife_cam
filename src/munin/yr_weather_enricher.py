#!/usr/bin/env python3
"""
YR.no Weather Data Enricher for Munin

This module enriches wildlife observations with historical weather data
from the Norwegian Meteorological Institute (YR.no) using GPS cluster coordinates.

YR.no provides:
- Free access to weather data
- Historical observations
- High-quality data for Nordic/European locations
- No API key required (just proper User-Agent)
- Good coverage for wildlife monitoring in Norway/Europe
"""

import logging
import requests
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..common.core.base import BaseProcessor
from ..common.exceptions import ProcessingError, ValidationError
from ..common.utils.logging_utils import get_logger, ProcessingTimer


@dataclass
class YRWeatherObservation:
    """YR.no weather observation data point."""
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


class YRWeatherEnricher(BaseProcessor):
    """YR.no weather data enricher for wildlife observations."""

    def __init__(self, db_path: Path, user_agent: str = "Wildlife-Pipeline/1.0", **kwargs):
        super().__init__(**kwargs)
        self.db_path = db_path
        self.logger = get_logger(self.__class__.__name__)
        self.user_agent = user_agent
        
        # YR.no API configuration
        self.base_url = "https://api.met.no/weatherapi"
        self.location_forecast_url = "/locationforecast/2.0/complete"
        self.historical_url = "/locationforecast/2.0/historical"
        
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with weather tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Weather observations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS yr_weather_observations (
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
                    dew_point REAL,
                    wind_gust REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (cluster_id) REFERENCES gps_clusters (cluster_id)
                )
            """)

            # Weather cache table for API responses
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS yr_weather_cache (
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yr_weather_cluster ON yr_weather_observations(cluster_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yr_weather_timestamp ON yr_weather_observations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yr_weather_coords ON yr_weather_observations(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yr_cache_key ON yr_weather_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yr_cache_expires ON yr_weather_cache(expires_at)")

            conn.commit()

    def process(self, input_data: Any) -> Any:
        """Process weather enrichment request.
        
        Args:
            input_data: Weather request or GPS cluster data
            
        Returns:
            Weather enrichment results
        """
        if isinstance(input_data, dict) and 'cluster_id' in input_data:
            return self.enrich_cluster_weather(input_data)
        else:
            raise ValidationError("Input data must be cluster dictionary with cluster_id")

    def enrich_cluster_weather(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich GPS cluster with YR.no weather data.
        
        Args:
            cluster_data: Dictionary containing cluster information
            
        Returns:
            Weather enrichment results
        """
        cluster_id = cluster_data.get('cluster_id')
        start_date = cluster_data.get('start_date')
        end_date = cluster_data.get('end_date')
        
        if not cluster_id:
            raise ValidationError("cluster_id is required")
            
        # Get cluster information
        cluster = self._get_cluster_info(cluster_id)
        if not cluster:
            raise ProcessingError(f"Cluster {cluster_id} not found")
            
        # Set default date range if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()
            
        return self._enrich_weather_data(
            cluster_id=cluster_id,
            latitude=cluster['center_latitude'],
            longitude=cluster['center_longitude'],
            start_date=start_date,
            end_date=end_date
        )

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

    def _enrich_weather_data(self, cluster_id: str, latitude: float, longitude: float, 
                           start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Enrich weather data for given coordinates and time range."""
        with ProcessingTimer(self.logger, "YR.no weather enrichment"):
            try:
                # Check cache first
                cached_data = self._get_cached_weather(latitude, longitude, start_date, end_date)
                if cached_data:
                    self.logger.info(f"Using cached YR.no weather data for {latitude}, {longitude}")
                    return cached_data
                
                # Fetch weather data from YR.no API
                weather_data = self._fetch_yr_weather_data(latitude, longitude, start_date, end_date)
                
                # Store in database
                stored_count = self._store_weather_data(weather_data, cluster_id)
                
                # Cache the response
                self._cache_weather_data(latitude, longitude, start_date, end_date, weather_data)
                
                return {
                    "success": True,
                    "observations_count": len(weather_data),
                    "stored_count": stored_count,
                    "provider": "yr_no",
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "cluster_id": cluster_id
                }
                
            except Exception as e:
                self.logger.error(f"YR.no weather enrichment failed: {e}")
                raise ProcessingError(f"YR.no weather enrichment failed: {e}")

    def _get_cached_weather(self, latitude: float, longitude: float, 
                          start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Check for cached weather data."""
        cache_key = self._generate_cache_key(latitude, longitude, start_date, end_date)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT response_data FROM yr_weather_cache
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                import json
                return json.loads(row[0])
        
        return None

    def _cache_weather_data(self, latitude: float, longitude: float, start_date: datetime, 
                          end_date: datetime, weather_data: List[YRWeatherObservation]):
        """Cache weather data for future use."""
        cache_key = self._generate_cache_key(latitude, longitude, start_date, end_date)
        expires_at = datetime.now() + timedelta(hours=6)  # Cache for 6 hours (YR.no updates frequently)
        
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
                    "dew_point": obs.dew_point,
                    "wind_gust": obs.wind_gust
                }
                for obs in weather_data
            ])
            
            cursor.execute("""
                INSERT OR REPLACE INTO yr_weather_cache
                (cache_key, latitude, longitude, date, response_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                latitude,
                longitude,
                start_date.date().isoformat(),
                data_json,
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))
            
            conn.commit()

    def _generate_cache_key(self, latitude: float, longitude: float, 
                          start_date: datetime, end_date: datetime) -> str:
        """Generate cache key for weather request."""
        return f"yr_{latitude}_{longitude}_{start_date.date()}_{end_date.date()}"

    def _fetch_yr_weather_data(self, latitude: float, longitude: float, 
                              start_date: datetime, end_date: datetime) -> List[YRWeatherObservation]:
        """Fetch weather data from YR.no API."""
        try:
            # YR.no Location Forecast API
            url = f"{self.base_url}{self.location_forecast_url}"
            params = {
                'lat': latitude,
                'lon': longitude
            }
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            self.logger.info(f"Fetching YR.no weather data for {latitude}, {longitude}")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_yr_data(data, latitude, longitude, start_date, end_date)
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch YR.no data: {e}")
            return []

    def _parse_yr_data(self, data: Dict[str, Any], latitude: float, longitude: float,
                      start_date: datetime, end_date: datetime) -> List[YRWeatherObservation]:
        """Parse YR.no weather data."""
        observations = []
        
        try:
            timeseries = data.get('properties', {}).get('timeseries', [])
            
            for item in timeseries:
                timestamp_str = item.get('time')
                if not timestamp_str:
                    continue
                    
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Filter by date range
                if timestamp < start_date or timestamp > end_date:
                    continue
                
                details = item.get('data', {}).get('instant', {}).get('details', {})
                
                obs = YRWeatherObservation(
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
                    dew_point=details.get('dew_point_temperature'),
                    wind_gust=details.get('wind_speed_of_gust')
                )
                
                observations.append(obs)
                
        except Exception as e:
            self.logger.warning(f"Failed to parse YR.no data: {e}")
        
        return observations

    def _store_weather_data(self, weather_data: List[YRWeatherObservation], cluster_id: str) -> int:
        """Store weather observations in database."""
        if not weather_data:
            return 0
        
        stored_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for obs in weather_data:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO yr_weather_observations
                        (observation_id, cluster_id, timestamp, latitude, longitude,
                         temperature, humidity, precipitation, wind_speed, wind_direction,
                         pressure, visibility, cloud_cover, uv_index, dew_point, wind_gust, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"yr_weather_{obs.timestamp.isoformat()}_{obs.latitude}_{obs.longitude}",
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
                        obs.dew_point,
                        obs.wind_gust,
                        datetime.now().isoformat()
                    ))
                    
                    stored_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to store YR.no weather observation: {e}")
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
                SELECT * FROM yr_weather_observations
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
            cursor.execute("SELECT COUNT(*) FROM yr_weather_observations")
            total_observations = cursor.fetchone()[0]
            
            # Observations by cluster
            cursor.execute("""
                SELECT cluster_id, COUNT(*) as count
                FROM yr_weather_observations
                GROUP BY cluster_id
            """)
            cluster_stats = dict(cursor.fetchall())
            
            # Date range
            cursor.execute("""
                SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
                FROM yr_weather_observations
            """)
            date_range = cursor.fetchone()
            
            return {
                "total_observations": total_observations,
                "cluster_stats": cluster_stats,
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
                DELETE FROM yr_weather_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} expired YR.no cache entries")
            
            return deleted_count

    def enrich_all_clusters(self, days_back: int = 7) -> Dict[str, Any]:
        """Enrich all GPS clusters with weather data.
        
        Args:
            days_back: Number of days to look back for weather data
            
        Returns:
            Enrichment results for all clusters
        """
        # Get all clusters
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cluster_id, center_latitude, center_longitude, name
                FROM gps_clusters
                ORDER BY created_at
            """)
            
            clusters = [dict(row) for row in cursor.fetchall()]
        
        results = {
            "total_clusters": len(clusters),
            "successful_enrichments": 0,
            "failed_enrichments": 0,
            "cluster_results": []
        }
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for cluster in clusters:
            try:
                cluster_data = {
                    'cluster_id': cluster['cluster_id'],
                    'start_date': start_date,
                    'end_date': end_date
                }
                
                result = self.enrich_cluster_weather(cluster_data)
                results["successful_enrichments"] += 1
                results["cluster_results"].append({
                    "cluster_id": cluster['cluster_id'],
                    "cluster_name": cluster['name'],
                    "success": True,
                    "observations_count": result.get("observations_count", 0)
                })
                
            except Exception as e:
                self.logger.error(f"Failed to enrich cluster {cluster['cluster_id']}: {e}")
                results["failed_enrichments"] += 1
                results["cluster_results"].append({
                    "cluster_id": cluster['cluster_id'],
                    "cluster_name": cluster['name'],
                    "success": False,
                    "error": str(e)
                })
        
        return results
