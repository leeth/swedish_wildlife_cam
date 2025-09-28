"""
Fast Cluster CLI for Large Datasets

This CLI provides the most efficient solution for:
1. Large datasets with cluster_id
2. Fast enrichment without reprocessing
3. Minimal memory overhead
4. High-performance operations
"""

import click
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging
from .efficient_cluster_lookup import EfficientClusterLookup, EfficientReportingEnricher
from .fast_reporting import FastReportingEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Fast Cluster CLI for large datasets."""
    pass

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
@click.option('--format', default='csv', type=click.Choice(['csv', 'parquet', 'json']), help='Output format')
def enrich(data_path: str, output_path: str, cluster_db: str, format: str):
    """Enrich data with cluster names (fast, no reprocessing)."""
    try:
        engine = FastReportingEngine(cluster_db)
        stats = engine.generate_cluster_report(data_path, output_path, format)
        
        click.echo(f"✅ Enriched data: {output_path}")
        click.echo(f"📊 Statistics: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def species_analysis(data_path: str, output_path: str, cluster_db: str):
    """Generate species analysis by cluster."""
    try:
        engine = FastReportingEngine(cluster_db)
        stats = engine.generate_species_by_cluster_report(data_path, output_path)
        
        click.echo(f"✅ Species analysis: {output_path}")
        click.echo(f"📊 Statistics: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def temporal_analysis(data_path: str, output_path: str, cluster_db: str):
    """Generate temporal analysis by cluster."""
    try:
        engine = FastReportingEngine(cluster_db)
        stats = engine.generate_temporal_analysis(data_path, output_path)
        
        click.echo(f"✅ Temporal analysis: {output_path}")
        click.echo(f"📊 Statistics: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def activity_analysis(data_path: str, output_path: str, cluster_db: str):
    """Generate cluster activity patterns."""
    try:
        engine = FastReportingEngine(cluster_db)
        stats = engine.generate_cluster_activity_report(data_path, output_path)
        
        click.echo(f"✅ Activity analysis: {output_path}")
        click.echo(f"📊 Statistics: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
@click.option('--pattern', default='*.csv', help='File pattern to process')
def batch_enrich(input_dir: str, output_dir: str, cluster_db: str, pattern: str):
    """Batch enrich multiple files with cluster names."""
    try:
        engine = FastReportingEngine(cluster_db)
        results = engine.batch_enrich_files(input_dir, output_dir, pattern)
        
        click.echo(f"✅ Batch enriched files in: {output_dir}")
        click.echo(f"📊 Results: {json.dumps(results, indent=2)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
@click.option('--limit', default=20, help='Maximum number of unknown clusters to show')
def unknown_clusters(data_path: str, cluster_db: str, limit: int):
    """Show unknown clusters in data."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        
        # Load data to get cluster IDs
        data_path = Path(data_path)
        if data_path.suffix == '.parquet':
            import polars as pl
            df = pl.read_parquet(data_path)
            cluster_ids = df['cluster_id'].unique().to_list()
        elif data_path.suffix == '.csv':
            import polars as pl
            df = pl.read_csv(data_path)
            cluster_ids = df['cluster_id'].unique().to_list()
        else:
            click.echo(f"❌ Unsupported format: {data_path.suffix}")
            raise click.Abort()
        
        # Get unknown clusters
        unknown = lookup.get_unknown_clusters(df)
        
        click.echo(f"📊 Found {len(unknown)} unknown clusters (showing first {limit}):")
        for i, cluster_id in enumerate(unknown[:limit]):
            click.echo(f"  {i+1}. {cluster_id}")
        
        if len(unknown) > limit:
            click.echo(f"  ... and {len(unknown) - limit} more")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('cluster_id')
@click.argument('name')
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def add_name(cluster_id: str, name: str, cluster_db: str):
    """Add cluster name."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        success = lookup.add_cluster_name(cluster_id, name)
        
        if success:
            click.echo(f"✅ Added name '{name}' for cluster {cluster_id}")
        else:
            click.echo(f"❌ Failed to add name for cluster {cluster_id}")
            raise click.Abort()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('names_file', type=click.Path(exists=True))
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def batch_add_names(names_file: str, cluster_db: str):
    """Add multiple cluster names from JSON file."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        
        with open(names_file, 'r') as f:
            names = json.load(f)
        
        count = lookup.batch_add_cluster_names(names)
        click.echo(f"✅ Added {count} cluster names")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def stats(cluster_db: str):
    """Show cluster names statistics."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        stats = lookup.get_stats()
        
        click.echo("📊 Cluster Names Statistics:")
        click.echo(json.dumps(stats, indent=2))
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('output_file', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def export_names(output_file: str, cluster_db: str):
    """Export cluster names to JSON file."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        success = lookup.export_cluster_names(output_file)
        
        if success:
            click.echo(f"✅ Exported cluster names to: {output_file}")
        else:
            click.echo(f"❌ Failed to export cluster names")
            raise click.Abort()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def import_names(input_file: str, cluster_db: str):
    """Import cluster names from JSON file."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        count = lookup.import_cluster_names(input_file)
        
        click.echo(f"✅ Imported {count} cluster names")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def extract_locations(data_path: str, cluster_db: str):
    """Extract GPS locations from Parquet data and store in SQLite."""
    try:
        import polars as pl
        
        # Load Parquet data
        df = pl.read_parquet(data_path)
        
        # Check if required columns exist
        if 'cluster_id' not in df.columns or 'latitude' not in df.columns or 'longitude' not in df.columns:
            click.echo("❌ Missing required columns: cluster_id, latitude, longitude")
            raise click.Abort()
        
        lookup = EfficientClusterLookup(cluster_db)
        
        # Group by cluster_id and extract locations
        cluster_locations = {}
        for row in df.iter_rows(named=True):
            cluster_id = row['cluster_id']
            if cluster_id not in cluster_locations:
                cluster_locations[cluster_id] = []
            cluster_locations[cluster_id].append((row['latitude'], row['longitude']))
        
        # Add locations to database
        total_locations = 0
        for cluster_id, locations in cluster_locations.items():
            count = lookup.add_cluster_locations(cluster_id, locations)
            total_locations += count
        
        click.echo(f"✅ Extracted {total_locations} locations for {len(cluster_locations)} clusters")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('cluster_id')
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def get_locations(cluster_id: str, cluster_db: str):
    """Get GPS locations for a cluster."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        locations = lookup.get_cluster_locations(cluster_id)
        
        click.echo(f"📍 Locations for cluster {cluster_id}:")
        for i, (lat, lon) in enumerate(locations):
            click.echo(f"  {i+1}. {lat}, {lon}")
        
        click.echo(f"Total: {len(locations)} locations")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('cluster_id')
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def get_mean(cluster_id: str, cluster_db: str):
    """Get mean GPS point for a cluster."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        mean = lookup.get_cluster_mean(cluster_id)
        
        if mean:
            lat, lon, count = mean
            click.echo(f"📍 Mean point for cluster {cluster_id}:")
            click.echo(f"  Latitude: {lat}")
            click.echo(f"  Longitude: {lon}")
            click.echo(f"  Point count: {count}")
        else:
            click.echo(f"❌ No mean point found for cluster {cluster_id}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.argument('output_path', type=click.Path())
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def export_means(output_path: str, cluster_db: str):
    """Export all cluster mean points for plotting."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        success = lookup.export_cluster_means_for_plotting(output_path)
        
        if success:
            click.echo(f"✅ Exported cluster means to: {output_path}")
        else:
            click.echo(f"❌ Failed to export cluster means")
            raise click.Abort()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

@cli.command()
@click.option('--cluster-db', default='cluster_names.db', help='Cluster names database path')
def list_means(cluster_db: str):
    """List all cluster mean points."""
    try:
        lookup = EfficientClusterLookup(cluster_db)
        means = lookup.get_all_cluster_means()
        names = lookup.get_all_cluster_names()
        
        click.echo("📍 Cluster Mean Points:")
        for cluster_id, (lat, lon, count) in means.items():
            name = names.get(cluster_id, cluster_id)
            click.echo(f"  {cluster_id} ({name}): {lat}, {lon} ({count} points)")
        
        click.echo(f"Total: {len(means)} clusters")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.Abort()

if __name__ == '__main__':
    cli()
