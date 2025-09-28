# Hugin 🐦‍⬛

*"Hugin brings thoughts to mind"*

**Hugin** is the Thought Bringer of Odin's Ravens - responsible for analyzing, interpreting, and generating insights from wildlife detection data collected by Munin.

## The Thought Bringer

In Norse mythology, Hugin (Thought) was one of Odin's ravens who brought back thoughts and insights from the world. Our Hugin does the same for wildlife analysis:

- **Pattern Recognition**: Identifies behavioral patterns and movement trends
- **Temporal Analysis**: Compresses observations to avoid duplicate logging
- **Spatial Intelligence**: Analyzes GPS data for habitat usage patterns
- **Reporting**: Generates comprehensive reports and analytics
- **Insights**: Provides actionable intelligence from the collected data

## Quickstart

### Installation

```bash
# Install Hugin from main project
cd src/hugin/
pip install -e .

# Or install from source
git clone https://github.com/leeth/swedish_wildlife_cam.git
cd swedish_wildlife_cam/src/hugin
pip install -e .
```

### Basic Usage

```bash
# Stage 3: Reporting and compression
hugin-stage3 --profile local --manifest ./results/stage1/manifest.jsonl --predictions ./results/stage2/predictions.jsonl --output ./results

# Analytics and insights
hugin-analytics --input ./results/final.parquet --output ./analytics

# Generate reports
hugin-report --input ./results/final.parquet --output ./reports

# Interactive dashboard
hugin-dashboard --data ./results/final.parquet --port 8080
```

### Cloud Usage (AWS)

```bash
# Stage 3: Reporting with cloud data
hugin-stage3 --profile cloud --manifest s3://bucket/results/stage1/manifest.jsonl --predictions s3://bucket/results/stage2/predictions.jsonl --output s3://bucket/results

# Analytics with cloud storage
hugin-analytics --input s3://bucket/results/final.parquet --output s3://bucket/analytics

# Generate cloud reports
hugin-report --input s3://bucket/results/final.parquet --output s3://bucket/reports
```

## Features

### Analytics Engine
- **High-Performance**: Polars-based analytics for large datasets
- **Species Reports**: Comprehensive wildlife detection summaries
- **Camera Analysis**: Performance metrics and activity patterns
- **Temporal Analysis**: Time-based behavior insights
- **Spatial Intelligence**: GPS-based habitat analysis

### Visualization
- **Interactive Dashboards**: Streamlit and Dash-based interfaces
- **Time Series**: Behavioral pattern visualization
- **Spatial Maps**: GPS-based habitat mapping
- **Species Distribution**: Detection frequency analysis

### Reporting
- **Compression**: Eliminates duplicate observations
- **Insights**: Behavioral pattern recognition
- **Trends**: Long-term wildlife population analysis
- **Alerts**: Anomaly detection and notifications

## Architecture

### Hugin Pipeline Stages

**Stage 3: Reporting & Compression**
- Observation compression (10-minute windows)
- Duplicate detection elimination
- Timeline generation
- Quality assessment

**Analytics Engine**
- Species detection analysis
- Camera performance metrics
- Temporal pattern recognition
- Spatial habitat analysis

**Insights Generation**
- Behavioral pattern identification
- Population trend analysis
- Anomaly detection
- Predictive modeling

### High-Performance Analytics

Hugin uses Polars for lightning-fast data processing:

- **Memory Efficient**: Handles datasets with millions of records
- **Parallel Processing**: Multi-threaded analytics
- **Vectorized Operations**: Optimized mathematical operations
- **Lazy Evaluation**: Efficient query optimization

## Configuration

### Local Profile (`conf/profiles/local.yaml`)
```yaml
storage:
  adapter: "local"
  base_path: "file://./data"

analytics:
  engine: "polars"
  cache_size: "1GB"
  parallel_workers: 4

visualization:
  backend: "streamlit"
  port: 8080
  theme: "dark"
```

### Cloud Profile (`conf/profiles/cloud.yaml`)
```yaml
storage:
  adapter: "s3"
  base_path: "s3://wildlife-analytics-bucket"

analytics:
  engine: "polars"
  cache_size: "4GB"
  parallel_workers: 8

visualization:
  backend: "dash"
  port: 8080
  theme: "light"
```

## Output Formats

### Analytics Reports
```python
{
    "species_summary": {
        "total_observations": int,
        "unique_species": int,
        "species_counts": dict,
        "confidence_stats": dict
    },
    "camera_analysis": {
        "camera_metrics": list,
        "activity_patterns": dict,
        "performance_stats": dict
    },
    "temporal_analysis": {
        "hourly_patterns": dict,
        "daily_patterns": dict,
        "seasonal_trends": dict
    },
    "spatial_analysis": {
        "habitat_usage": dict,
        "movement_patterns": dict,
        "territory_analysis": dict
    }
}
```

### Compressed Observations
```python
{
    "camera_id": str,
    "species": str,
    "start_time": datetime,
    "end_time": datetime,
    "duration_seconds": float,
    "max_confidence": float,
    "avg_confidence": float,
    "frame_count": int,
    "timeline": list
}
```

## Visualization

### Interactive Dashboards

Hugin provides multiple visualization options:

- **Streamlit**: Quick prototyping and exploration
- **Dash**: Production-ready interactive dashboards
- **Plotly**: Advanced statistical visualizations
- **Bokeh**: Real-time data streaming

### Chart Types

- **Time Series**: Behavioral patterns over time
- **Heatmaps**: Spatial distribution of detections
- **Scatter Plots**: Confidence vs. time analysis
- **Bar Charts**: Species frequency analysis
- **Maps**: GPS-based habitat visualization

## Development

### Testing
```bash
# Run all tests
pytest test/unit/ -v

# Run analytics tests
pytest test/unit/test_analytics.py -v

# Run visualization tests
pytest test/unit/test_visualization.py -v
```

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Install visualization dependencies
pip install -r requirements-viz.txt

# Run linting
ruff check src/hugin/ test/unit/
black src/hugin/ test/unit/
```

## Documentation

- **[Hugin Guide](docs/HUGIN_GUIDE.md)**: Complete usage documentation
- **[Analytics API](docs/ANALYTICS_API.md)**: Analytics engine documentation
- **[Visualization Guide](docs/VISUALIZATION_GUIDE.md)**: Dashboard creation guide
- **[API Reference](docs/API_REFERENCE.md)**: Complete API documentation

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/leeth/swedish_wildlife_cam/issues)
- **Discussions**: [GitHub Discussions](https://github.com/leeth/swedish_wildlife_cam/discussions)
- **Documentation**: [Project Documentation](docs/)

---

*"Hugin brings thoughts to mind"* - Let Hugin be your thought bringer for wildlife insights! 🐦‍⬛
