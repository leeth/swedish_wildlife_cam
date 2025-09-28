"""
Fast Reporting System for Large Datasets

This module provides the most efficient reporting solution for:
1. Large datasets with cluster_id
2. Fast enrichment without reprocessing
3. Minimal memory overhead
4. High-performance analytics
"""

import logging
from pathlib import Path
from typing import Any, Dict, Union

import polars as pl

from .efficient_cluster_lookup import EfficientClusterLookup, EfficientReportingEnricher

logger = logging.getLogger(__name__)

class FastReportingEngine:
    """
    High-performance reporting engine for large datasets.

    Features:
    - Minimal memory overhead
    - Fast cluster name lookup
    - No data reprocessing
    - Efficient analytics
    - Support for multiple output formats
    """

    def __init__(self, cluster_db_path: Union[str, Path] = "cluster_names.db"):
        self.cluster_lookup = EfficientClusterLookup(cluster_db_path)
        self.enricher = EfficientReportingEnricher(self.cluster_lookup)

    def generate_cluster_report(self, data_path: Union[str, Path],
                              output_path: Union[str, Path],
                              format: str = "csv") -> Dict[str, Any]:
        """
        Generate cluster report from large dataset.

        Args:
            data_path: Path to data file (CSV, Parquet, JSON)
            output_path: Output path for report
            format: Output format (csv, parquet, json)

        Returns:
            Report statistics
        """
        data_path = Path(data_path)

        # Load data efficiently
        if data_path.suffix == '.parquet':
            df = pl.read_parquet(data_path)
        elif data_path.suffix == '.csv':
            df = pl.read_csv(data_path)
        elif data_path.suffix == '.json':
            df = pl.read_json(data_path)
        else:
            raise ValueError(f"Unsupported format: {data_path.suffix}")

        # Enrich with cluster names (fast lookup)
        enriched_df = self.cluster_lookup.enrich_dataframe_with_names(df)

        # Generate analytics
        stats = self.enricher.generate_cluster_summary(enriched_df)

        # Save enriched data
        output_path = Path(output_path)
        if format == "csv":
            enriched_df.write_csv(output_path)
        elif format == "parquet":
            enriched_df.write_parquet(output_path)
        elif format == "json":
            enriched_df.write_json(output_path)
        else:
            raise ValueError(f"Unsupported output format: {format}")

        logger.info(f"Generated cluster report: {output_path}")
        return stats

    def generate_species_by_cluster_report(self, data_path: Union[str, Path],
                                         output_path: Union[str, Path]) -> Dict[str, Any]:
        """Generate species analysis by cluster."""
        data_path = Path(data_path)

        # Load data
        if data_path.suffix == '.parquet':
            df = pl.read_parquet(data_path)
        elif data_path.suffix == '.csv':
            df = pl.read_csv(data_path)
        else:
            raise ValueError(f"Unsupported format: {data_path.suffix}")

        # Enrich with cluster names
        enriched_df = self.cluster_lookup.enrich_dataframe_with_names(df)

        # Analyze species by cluster
        species_analysis = (
            enriched_df
            .group_by(["cluster_id", "cluster_name", "species"])
            .agg([
                pl.count().alias("count"),
                pl.col("confidence").mean().alias("avg_confidence"),
                pl.col("timestamp").min().alias("first_seen"),
                pl.col("timestamp").max().alias("last_seen")
            ])
            .sort("count", descending=True)
        )

        # Save results
        output_path = Path(output_path)
        species_analysis.write_csv(output_path)

        # Generate summary
        summary = {
            "total_clusters": species_analysis["cluster_id"].n_unique(),
            "total_species": species_analysis["species"].n_unique(),
            "top_species": species_analysis.head(10).to_dicts()
        }

        logger.info(f"Generated species by cluster report: {output_path}")
        return summary

    def generate_temporal_analysis(self, data_path: Union[str, Path],
                                 output_path: Union[str, Path]) -> Dict[str, Any]:
        """Generate temporal analysis by cluster."""
        data_path = Path(data_path)

        # Load data
        if data_path.suffix == '.parquet':
            df = pl.read_parquet(data_path)
        elif data_path.suffix == '.csv':
            df = pl.read_csv(data_path)
        else:
            raise ValueError(f"Unsupported format: {data_path.suffix}")

        # Enrich with cluster names
        enriched_df = self.cluster_lookup.enrich_dataframe_with_names(df)

        # Convert timestamp to datetime if needed
        if "timestamp" in enriched_df.columns:
            enriched_df = enriched_df.with_columns(
                pl.col("timestamp").str.to_datetime().alias("datetime")
            )

        # Temporal analysis
        temporal_analysis = (
            enriched_df
            .with_columns([
                pl.col("datetime").dt.date().alias("date"),
                pl.col("datetime").dt.hour().alias("hour")
            ])
            .group_by(["cluster_id", "cluster_name", "date", "hour"])
            .agg([
                pl.count().alias("observations"),
                pl.col("species").n_unique().alias("unique_species")
            ])
            .sort(["cluster_id", "date", "hour"])
        )

        # Save results
        output_path = Path(output_path)
        temporal_analysis.write_csv(output_path)

        # Generate summary
        summary = {
            "date_range": {
                "start": temporal_analysis["date"].min(),
                "end": temporal_analysis["date"].max()
            },
            "total_observations": temporal_analysis["observations"].sum(),
            "clusters_analyzed": temporal_analysis["cluster_id"].n_unique()
        }

        logger.info(f"Generated temporal analysis: {output_path}")
        return summary

    def generate_cluster_activity_report(self, data_path: Union[str, Path],
                                       output_path: Union[str, Path]) -> Dict[str, Any]:
        """Generate cluster activity patterns."""
        data_path = Path(data_path)

        # Load data
        if data_path.suffix == '.parquet':
            df = pl.read_parquet(data_path)
        elif data_path.suffix == '.csv':
            df = pl.read_csv(data_path)
        else:
            raise ValueError(f"Unsupported format: {data_path.suffix}")

        # Enrich with cluster names
        enriched_df = self.cluster_lookup.enrich_dataframe_with_names(df)

        # Activity analysis
        activity_analysis = (
            enriched_df
            .with_columns([
                pl.col("timestamp").str.to_datetime().alias("datetime"),
                pl.col("datetime").dt.hour().alias("hour"),
                pl.col("datetime").dt.weekday().alias("weekday")
            ])
            .group_by(["cluster_id", "cluster_name"])
            .agg([
                pl.count().alias("total_observations"),
                pl.col("hour").mode().alias("peak_hour"),
                pl.col("weekday").mode().alias("peak_weekday"),
                pl.col("species").n_unique().alias("unique_species"),
                pl.col("datetime").min().alias("first_activity"),
                pl.col("datetime").max().alias("last_activity")
            ])
            .sort("total_observations", descending=True)
        )

        # Save results
        output_path = Path(output_path)
        activity_analysis.write_csv(output_path)

        # Generate summary
        summary = {
            "total_clusters": activity_analysis["cluster_id"].n_unique(),
            "total_observations": activity_analysis["total_observations"].sum(),
            "most_active_cluster": activity_analysis.head(1).to_dicts()[0] if len(activity_analysis) > 0 else None
        }

        logger.info(f"Generated cluster activity report: {output_path}")
        return summary

    def batch_enrich_files(self, input_dir: Union[str, Path],
                          output_dir: Union[str, Path],
                          pattern: str = "*.csv") -> Dict[str, Any]:
        """Batch enrich multiple files with cluster names."""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        results = {}

        for file_path in input_dir.glob(pattern):
            try:
                # Load data
                if file_path.suffix == '.parquet':
                    df = pl.read_parquet(file_path)
                elif file_path.suffix == '.csv':
                    df = pl.read_csv(file_path)
                else:
                    continue

                # Enrich with cluster names
                enriched_df = self.cluster_lookup.enrich_dataframe_with_names(df)

                # Save enriched data
                output_file = output_dir / f"enriched_{file_path.name}"
                enriched_df.write_csv(output_file)

                results[str(file_path)] = {
                    "status": "success",
                    "output_file": str(output_file),
                    "rows": len(enriched_df)
                }

            except Exception as e:
                results[str(file_path)] = {
                    "status": "error",
                    "error": str(e)
                }

        logger.info(f"Batch enriched {len(results)} files")
        return results


# Convenience functions
def fast_enrich_report(data_path: Union[str, Path],
                      output_path: Union[str, Path],
                      cluster_db_path: Union[str, Path] = "cluster_names.db") -> Dict[str, Any]:
    """Fast report enrichment with cluster names."""
    engine = FastReportingEngine(cluster_db_path)
    return engine.generate_cluster_report(data_path, output_path)

def fast_species_analysis(data_path: Union[str, Path],
                        output_path: Union[str, Path],
                        cluster_db_path: Union[str, Path] = "cluster_names.db") -> Dict[str, Any]:
    """Fast species analysis by cluster."""
    engine = FastReportingEngine(cluster_db_path)
    return engine.generate_species_by_cluster_report(data_path, output_path)

def fast_temporal_analysis(data_path: Union[str, Path],
                         output_path: Union[str, Path],
                         cluster_db_path: Union[str, Path] = "cluster_names.db") -> Dict[str, Any]:
    """Fast temporal analysis by cluster."""
    engine = FastReportingEngine(cluster_db_path)
    return engine.generate_temporal_analysis(data_path, output_path)
