"""
Analytics Engine with Polars for high-performance data processing.

This module provides:
- Polars-based data processing for large datasets
- Efficient aggregation and reporting
- Memory-efficient operations
- Integration with existing pandas workflows
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
import logging

try:
    import polars as pl
    import pandas as pd
    import numpy as np
    from polars import col, lit, when
except ImportError as e:
    print(f"Missing dependencies for analytics engine: {e}")
    print("Install with: pip install polars pandas numpy")
    exit(1)

from .data_contracts import ObservationRecord, CompressedObservation, CameraInfo
from .logging_config import get_logger

logger = get_logger("wildlife_pipeline.analytics_engine")


class AnalyticsEngine:
    """High-performance analytics engine using Polars."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".wildlife_cache" / "analytics"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        
        # Configure Polars for optimal performance
        pl.Config.set_streaming_chunk_size(8192)
        pl.Config.set_fmt_str_lengths(100)
        
        self.logger.info("🚀 Analytics engine initialized with Polars")
    
    def load_observations_from_parquet(self, parquet_path: Union[str, Path]) -> pl.DataFrame:
        """Load observations from Parquet file using Polars."""
        parquet_path = Path(parquet_path)
        
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
        
        self.logger.info(f"📊 Loading observations from: {parquet_path}")
        
        try:
            # Load with streaming for large files
            df = pl.scan_parquet(str(parquet_path)).collect()
            
            self.logger.info(f"✅ Loaded {len(df)} observations")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error loading Parquet file: {e}")
            raise
    
    def load_observations_from_pandas(self, df: pd.DataFrame) -> pl.DataFrame:
        """Convert pandas DataFrame to Polars DataFrame."""
        self.logger.info(f"🔄 Converting pandas DataFrame to Polars ({len(df)} rows)")
        
        try:
            # Convert pandas to polars
            pl_df = pl.from_pandas(df)
            self.logger.info("✅ Conversion completed")
            return pl_df
            
        except Exception as e:
            self.logger.error(f"❌ Error converting to Polars: {e}")
            raise
    
    def generate_species_report(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive species detection report."""
        self.logger.info("📈 Generating species report")
        
        start_time = time.time()
        
        # Species detection counts
        species_counts = (
            df.group_by("top_label")
            .agg([
                col("observation_id").count().alias("total_detections"),
                col("top_confidence").mean().alias("avg_confidence"),
                col("top_confidence").max().alias("max_confidence"),
                col("top_confidence").min().alias("min_confidence"),
                col("needs_review").sum().alias("needs_review_count"),
            ])
            .sort("total_detections", descending=True)
        )
        
        # Camera activity
        camera_activity = (
            df.group_by("camera_id")
            .agg([
                col("observation_id").count().alias("total_observations"),
                col("timestamp").min().alias("first_observation"),
                col("timestamp").max().alias("last_observation"),
                col("top_label").n_unique().alias("unique_species"),
            ])
            .sort("total_observations", descending=True)
        )
        
        # Temporal analysis
        temporal_analysis = (
            df.with_columns([
                col("timestamp").dt.hour().alias("hour"),
                col("timestamp").dt.date().alias("date"),
                col("timestamp").dt.weekday().alias("weekday"),
            ])
            .group_by(["date", "top_label"])
            .agg([
                col("observation_id").count().alias("daily_count"),
                col("top_confidence").mean().alias("avg_confidence"),
            ])
            .sort("date", descending=True)
        )
        
        # GPS analysis (if available)
        gps_analysis = None
        if "gps_latitude" in df.columns and "gps_longitude" in df.columns:
            gps_analysis = (
                df.filter(col("gps_latitude").is_not_null() & col("gps_longitude").is_not_null())
                .group_by("top_label")
                .agg([
                    col("gps_latitude").mean().alias("avg_latitude"),
                    col("gps_longitude").mean().alias("avg_longitude"),
                    col("gps_latitude").std().alias("lat_std"),
                    col("gps_longitude").std().alias("lon_std"),
                ])
            )
        
        processing_time = time.time() - start_time
        
        report = {
            "summary": {
                "total_observations": len(df),
                "unique_species": df["top_label"].n_unique(),
                "unique_cameras": df["camera_id"].n_unique(),
                "date_range": {
                    "start": df["timestamp"].min(),
                    "end": df["timestamp"].max(),
                },
                "processing_time_seconds": processing_time,
            },
            "species_counts": species_counts.to_dicts(),
            "camera_activity": camera_activity.to_dicts(),
            "temporal_analysis": temporal_analysis.to_dicts(),
            "gps_analysis": gps_analysis.to_dicts() if gps_analysis is not None else None,
        }
        
        self.logger.info(f"✅ Species report generated in {processing_time:.2f}s")
        return report
    
    def generate_camera_report(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate camera-specific analytics report."""
        self.logger.info("📷 Generating camera report")
        
        start_time = time.time()
        
        # Camera performance metrics
        camera_metrics = (
            df.group_by("camera_id")
            .agg([
                col("observation_id").count().alias("total_observations"),
                col("top_label").n_unique().alias("species_diversity"),
                col("top_confidence").mean().alias("avg_confidence"),
                col("needs_review").sum().alias("review_required"),
                col("timestamp").min().alias("first_observation"),
                col("timestamp").max().alias("last_observation"),
                (col("timestamp").max() - col("timestamp").min()).alias("active_duration"),
            ])
            .with_columns([
                (col("review_required") / col("total_observations")).alias("review_rate"),
            ])
            .sort("total_observations", descending=True)
        )
        
        # Species distribution per camera
        species_per_camera = (
            df.group_by(["camera_id", "top_label"])
            .agg([
                col("observation_id").count().alias("count"),
                col("top_confidence").mean().alias("avg_confidence"),
            ])
            .sort(["camera_id", "count"], descending=[False, True])
        )
        
        # Temporal patterns per camera
        temporal_patterns = (
            df.with_columns([
                col("timestamp").dt.hour().alias("hour"),
                col("timestamp").dt.weekday().alias("weekday"),
            ])
            .group_by(["camera_id", "hour"])
            .agg([
                col("observation_id").count().alias("hourly_count"),
            ])
            .sort(["camera_id", "hour"])
        )
        
        processing_time = time.time() - start_time
        
        report = {
            "camera_metrics": camera_metrics.to_dicts(),
            "species_per_camera": species_per_camera.to_dicts(),
            "temporal_patterns": temporal_patterns.to_dicts(),
            "processing_time_seconds": processing_time,
        }
        
        self.logger.info(f"✅ Camera report generated in {processing_time:.2f}s")
        return report
    
    def generate_temporal_report(self, df: pl.DataFrame, 
                               time_window: str = "1h") -> Dict[str, Any]:
        """Generate temporal analysis report."""
        self.logger.info(f"⏰ Generating temporal report (window: {time_window})")
        
        start_time = time.time()
        
        # Time-based aggregations
        temporal_df = (
            df.with_columns([
                col("timestamp").dt.truncate(time_window).alias("time_window"),
                col("timestamp").dt.hour().alias("hour"),
                col("timestamp").dt.weekday().alias("weekday"),
                col("timestamp").dt.date().alias("date"),
            ])
        )
        
        # Activity by time window
        activity_by_window = (
            temporal_df
            .group_by("time_window")
            .agg([
                col("observation_id").count().alias("total_observations"),
                col("top_label").n_unique().alias("unique_species"),
                col("camera_id").n_unique().alias("active_cameras"),
                col("top_confidence").mean().alias("avg_confidence"),
            ])
            .sort("time_window")
        )
        
        # Hourly patterns
        hourly_patterns = (
            temporal_df
            .group_by("hour")
            .agg([
                col("observation_id").count().alias("total_observations"),
                col("top_label").n_unique().alias("unique_species"),
                col("camera_id").n_unique().alias("active_cameras"),
            ])
            .sort("hour")
        )
        
        # Weekly patterns
        weekly_patterns = (
            temporal_df
            .group_by("weekday")
            .agg([
                col("observation_id").count().alias("total_observations"),
                col("top_label").n_unique().alias("unique_species"),
                col("camera_id").n_unique().alias("active_cameras"),
            ])
            .sort("weekday")
        )
        
        processing_time = time.time() - start_time
        
        report = {
            "activity_by_window": activity_by_window.to_dicts(),
            "hourly_patterns": hourly_patterns.to_dicts(),
            "weekly_patterns": weekly_patterns.to_dicts(),
            "processing_time_seconds": processing_time,
        }
        
        self.logger.info(f"✅ Temporal report generated in {processing_time:.2f}s")
        return report
    
    def generate_gps_report(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate GPS-based spatial analysis report."""
        self.logger.info("🗺️  Generating GPS spatial report")
        
        # Check if GPS data is available
        gps_columns = ["gps_latitude", "gps_longitude"]
        if not all(col in df.columns for col in gps_columns):
            self.logger.warning("⚠️  GPS columns not found in data")
            return {"error": "GPS data not available"}
        
        start_time = time.time()
        
        # Filter records with GPS data
        gps_df = df.filter(
            col("gps_latitude").is_not_null() & 
            col("gps_longitude").is_not_null()
        )
        
        if len(gps_df) == 0:
            self.logger.warning("⚠️  No GPS data found")
            return {"error": "No GPS data available"}
        
        # Spatial aggregations
        spatial_analysis = (
            gps_df
            .group_by("top_label")
            .agg([
                col("gps_latitude").mean().alias("avg_latitude"),
                col("gps_longitude").mean().alias("avg_longitude"),
                col("gps_latitude").std().alias("lat_std"),
                col("gps_longitude").std().alias("lon_std"),
                col("observation_id").count().alias("count"),
            ])
            .sort("count", descending=True)
        )
        
        # Camera locations
        camera_locations = (
            gps_df
            .group_by("camera_id")
            .agg([
                col("gps_latitude").mean().alias("avg_latitude"),
                col("gps_longitude").mean().alias("avg_longitude"),
                col("gps_latitude").std().alias("lat_std"),
                col("gps_longitude").std().alias("lon_std"),
                col("observation_id").count().alias("observation_count"),
            ])
            .sort("observation_count", descending=True)
        )
        
        # Spatial clustering (simplified)
        spatial_clusters = (
            gps_df
            .with_columns([
                (col("gps_latitude") * 100).round().alias("lat_cluster"),
                (col("gps_longitude") * 100).round().alias("lon_cluster"),
            ])
            .group_by(["lat_cluster", "lon_cluster"])
            .agg([
                col("observation_id").count().alias("cluster_size"),
                col("top_label").n_unique().alias("species_diversity"),
                col("camera_id").n_unique().alias("camera_count"),
            ])
            .sort("cluster_size", descending=True)
        )
        
        processing_time = time.time() - start_time
        
        report = {
            "spatial_analysis": spatial_analysis.to_dicts(),
            "camera_locations": camera_locations.to_dicts(),
            "spatial_clusters": spatial_clusters.to_dicts(),
            "gps_coverage": {
                "total_with_gps": len(gps_df),
                "total_observations": len(df),
                "gps_percentage": len(gps_df) / len(df) * 100,
            },
            "processing_time_seconds": processing_time,
        }
        
        self.logger.info(f"✅ GPS report generated in {processing_time:.2f}s")
        return report
    
    def export_to_parquet(self, df: pl.DataFrame, output_path: Union[str, Path]) -> None:
        """Export Polars DataFrame to Parquet with optimization."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"💾 Exporting to Parquet: {output_path}")
        
        try:
            # Write with compression and optimization
            df.write_parquet(
                str(output_path),
                compression="snappy",
                use_pyarrow=True,
            )
            
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            self.logger.info(f"✅ Export completed: {file_size:.2f} MB")
            
        except Exception as e:
            self.logger.error(f"❌ Export failed: {e}")
            raise
    
    def export_to_csv(self, df: pl.DataFrame, output_path: Union[str, Path]) -> None:
        """Export Polars DataFrame to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"💾 Exporting to CSV: {output_path}")
        
        try:
            df.write_csv(str(output_path))
            self.logger.info("✅ CSV export completed")
            
        except Exception as e:
            self.logger.error(f"❌ CSV export failed: {e}")
            raise
    
    def benchmark_performance(self, df: pl.DataFrame, 
                            operations: List[str] = None) -> Dict[str, float]:
        """Benchmark Polars performance vs pandas."""
        if operations is None:
            operations = [
                "group_by_species",
                "temporal_aggregation", 
                "gps_analysis",
                "export_parquet",
            ]
        
        results = {}
        
        for op in operations:
            start_time = time.time()
            
            if op == "group_by_species":
                _ = df.group_by("top_label").agg([
                    col("observation_id").count(),
                    col("top_confidence").mean(),
                ])
            elif op == "temporal_aggregation":
                _ = df.with_columns([
                    col("timestamp").dt.hour().alias("hour"),
                ]).group_by("hour").agg([
                    col("observation_id").count(),
                ])
            elif op == "gps_analysis" and "gps_latitude" in df.columns:
                _ = df.filter(
                    col("gps_latitude").is_not_null()
                ).group_by("top_label").agg([
                    col("gps_latitude").mean(),
                ])
            elif op == "export_parquet":
                temp_path = self.cache_dir / "temp_benchmark.parquet"
                df.write_parquet(str(temp_path))
                temp_path.unlink()  # Clean up
            
            elapsed = time.time() - start_time
            results[op] = elapsed
            
            self.logger.info(f"⏱️  {op}: {elapsed:.3f}s")
        
        return results


def main():
    """Test the analytics engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analytics Engine")
    parser.add_argument("parquet_path", help="Path to Parquet file")
    parser.add_argument("--output-dir", default="./analytics_output", help="Output directory")
    parser.add_argument("--report-type", choices=["species", "camera", "temporal", "gps", "all"], 
                       default="all", help="Type of report to generate")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmark")
    
    args = parser.parse_args()
    
    # Initialize analytics engine
    engine = AnalyticsEngine()
    
    # Load data
    df = engine.load_observations_from_parquet(args.parquet_path)
    
    # Generate reports
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.report_type in ["species", "all"]:
        report = engine.generate_species_report(df)
        with open(output_dir / "species_report.json", "w") as f:
            import json
            json.dump(report, f, indent=2, default=str)
        print("✅ Species report generated")
    
    if args.report_type in ["camera", "all"]:
        report = engine.generate_camera_report(df)
        with open(output_dir / "camera_report.json", "w") as f:
            import json
            json.dump(report, f, indent=2, default=str)
        print("✅ Camera report generated")
    
    if args.report_type in ["temporal", "all"]:
        report = engine.generate_temporal_report(df)
        with open(output_dir / "temporal_report.json", "w") as f:
            import json
            json.dump(report, f, indent=2, default=str)
        print("✅ Temporal report generated")
    
    if args.report_type in ["gps", "all"]:
        report = engine.generate_gps_report(df)
        with open(output_dir / "gps_report.json", "w") as f:
            import json
            json.dump(report, f, indent=2, default=str)
        print("✅ GPS report generated")
    
    # Run benchmark if requested
    if args.benchmark:
        results = engine.benchmark_performance(df)
        print(f"\n📊 Performance Benchmark:")
        for op, time_taken in results.items():
            print(f"  {op}: {time_taken:.3f}s")


if __name__ == "__main__":
    main()
