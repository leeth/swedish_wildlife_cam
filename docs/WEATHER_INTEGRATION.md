# Weather Data Integration for Munin

This document describes the weather data integration system for enriching positive wildlife observations with historical weather data using YR.no (Norwegian Meteorological Institute) API.

## Overview

The weather integration system enriches individual positive wildlife observations (those with animals detected) with historical weather data at their specific time and location. This targeted approach is more efficient and provides precise environmental context for wildlife monitoring data. This is particularly useful for:

- Correlating wildlife behavior with weather conditions at the exact time of observation
- Understanding how weather affects wildlife activity patterns
- Analyzing the impact of weather on camera trap effectiveness
- Providing precise environmental context for wildlife observations
- Enriching only meaningful observations (positive detections) rather than all data

## Architecture

### Components

1. **ObservationWeatherEnricher** - Main weather data enrichment class for individual observations
2. **Observation Weather CLI** - Command-line interface for weather operations
3. **Database Schema** - SQLite tables for weather data storage linked to observations
4. **Caching System** - API response caching for performance

### Data Flow

```
Positive Wildlife Observations → Weather Enricher → YR.no API → Weather Database
     ↓
Individual Observations + Weather Data (at specific time/location)
```

## Features

### Weather Data Collection

- **Temperature** - Air temperature in Celsius
- **Humidity** - Relative humidity percentage
- **Precipitation** - Precipitation amount in mm
- **Wind** - Wind speed, direction, and gusts
- **Pressure** - Atmospheric pressure
- **Visibility** - Visibility distance
- **Cloud Cover** - Cloud coverage percentage
- **UV Index** - Ultraviolet index
- **Dew Point** - Dew point temperature

### API Integration

- **YR.no API** - Free Norwegian Meteorological Institute API
- **No API Key Required** - Just proper User-Agent header
- **Historical Data** - Access to past weather observations
- **High Quality** - Reliable data for Nordic/European locations

## Installation

### Prerequisites

```bash
pip install requests sqlite3
```

### Database Setup

The weather integration automatically creates the required database tables:

- `yr_weather_observations` - Weather observation data
- `yr_weather_cache` - API response caching

## Usage

### Command Line Interface

#### Enrich a Single Observation

```bash
python scripts/enrich_observations_weather.py enrich-single \
  --observation-id obs_123 \
  --timestamp "2024-01-15T10:30:00Z" \
  --latitude 59.9139 \
  --longitude 10.7522
```

#### Enrich All Positive Observations

```bash
python scripts/enrich_observations_weather.py enrich-positive \
  --days-back 7
```

#### Show Weather Data for Observation

```bash
python scripts/enrich_observations_weather.py show-weather \
  --observation-id obs_123
```

#### Show Statistics

```bash
python scripts/enrich_observations_weather.py show-stats
```

#### Cleanup Cache

```bash
python scripts/enrich_observations_weather.py cleanup-cache
```

### Programmatic Usage

```python
from munin.observation_weather_enricher import ObservationWeatherEnricher
from datetime import datetime, timedelta

# Initialize weather enricher
weather_enricher = ObservationWeatherEnricher(Path("wildlife_pipeline.db"))

# Enrich a single positive observation
observation_data = {
    'observation_id': 'obs_123',
    'timestamp': datetime.now() - timedelta(hours=2),
    'latitude': 59.9139,
    'longitude': 10.7522,
    'camera_id': 'camera_001'
}

result = weather_enricher.enrich_single_observation(observation_data)
print(f"Enrichment result: {result['success']}")

# Enrich all positive observations from database
batch_result = weather_enricher.enrich_positive_observations_from_db(days_back=7)
print(f"Enriched {batch_result['successful_enrichments']} observations")

# Retrieve weather data for specific observation
weather_data = weather_enricher.get_weather_for_observation('obs_123')
if weather_data:
    print(f"Temperature: {weather_data['temperature']}°C")
    print(f"Humidity: {weather_data['humidity']}%")
```

## Configuration

### Weather Configuration File

The system uses `config/weather_config.yaml` for configuration:

```yaml
weather:
  provider: "yr_no"
  yr_no:
    user_agent: "Wildlife-Pipeline/1.0 (contact@wildlife-pipeline.org)"
    cache_duration_hours: 6
    timeout: 30
  enrichment:
    default_days_back: 7
    parameters:
      - "temperature"
      - "humidity"
      - "precipitation"
      - "wind_speed"
      - "wind_direction"
      - "pressure"
      - "visibility"
      - "cloud_cover"
      - "uv_index"
```

## Database Schema

### Weather Observations Table

```sql
CREATE TABLE yr_weather_observations (
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
);
```

### Weather Cache Table

```sql
CREATE TABLE yr_weather_cache (
    cache_key TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    date TEXT NOT NULL,
    response_data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

## API Rate Limits

### YR.no API

- **No rate limits** for reasonable usage
- **User-Agent required** - Must identify your application
- **Free access** - No API key required
- **Update frequency** - Data updated every 6 hours

### Best Practices

1. **Respectful usage** - Don't make excessive requests
2. **Proper User-Agent** - Always include identifying information
3. **Caching** - Use built-in caching to reduce API calls
4. **Error handling** - Handle API failures gracefully

## Error Handling

The system includes comprehensive error handling:

- **API failures** - Automatic retry with exponential backoff
- **Invalid coordinates** - Validation of GPS coordinates
- **Database errors** - Transaction rollback on failures
- **Cache management** - Automatic cleanup of expired entries

## Performance Considerations

### Caching

- **6-hour cache** - YR.no data updated every 6 hours
- **Automatic cleanup** - Expired cache entries removed
- **Memory efficient** - JSON storage for cache data

### Database Optimization

- **Indexes** - Optimized for common queries
- **Batch processing** - Process multiple clusters efficiently
- **Connection pooling** - Efficient database connections

## Monitoring

### Logging

The system provides detailed logging:

- **API requests** - Track API calls and responses
- **Cache hits** - Monitor cache effectiveness
- **Errors** - Detailed error logging with context
- **Performance** - Processing time tracking

### Statistics

Get weather data statistics:

```python
stats = weather_enricher.get_weather_statistics()
print(f"Total observations: {stats['total_observations']}")
print(f"Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
```

## Troubleshooting

### Common Issues

1. **API failures** - Check internet connection and YR.no status
2. **Invalid coordinates** - Ensure GPS coordinates are valid
3. **Database errors** - Check database file permissions
4. **Cache issues** - Clear cache if data seems stale

### Debug Mode

Enable verbose logging:

```bash
python scripts/enrich_weather.py --verbose enrich-cluster --cluster-id cluster_123
```

## Future Enhancements

### Planned Features

1. **Multiple providers** - Support for other weather APIs
2. **Weather alerts** - Severe weather notifications
3. **Historical trends** - Long-term weather pattern analysis
4. **Machine learning** - Weather-based wildlife behavior prediction

### Integration Opportunities

1. **Analytics engine** - Weather correlation analysis
2. **Reporting** - Weather impact reports
3. **Visualization** - Weather data charts and graphs
4. **API endpoints** - REST API for weather data access

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify GPS coordinates are valid
3. Ensure database file is accessible
4. Test with a simple cluster first

## License

This weather integration system is part of the Wildlife Pipeline project and follows the same licensing terms.
