"""
Efficient Cluster Management Example

This example shows the most efficient solution for:
1. Large Parquet datasets with cluster_id
2. Small SQLite setup with cluster names
3. GPS locations and mean points for plotting
4. Fast reporting without reprocessing
"""

import json
import random
from datetime import datetime

import polars as pl

# Import our efficient cluster system
from hugin.efficient_cluster_lookup import EfficientClusterLookup, FastReportingEngine


def create_sample_data():
    """Create sample Parquet data with cluster_id and GPS coordinates."""
    print("📊 Creating sample Parquet data...")

    # Generate sample data
    data = []
    cluster_ids = [f"cluster_{i:03d}" for i in range(1, 21)]  # 20 clusters

    for i in range(1000):  # 1000 observations
        cluster_id = random.choice(cluster_ids)
        # Generate GPS coordinates around Sweden
        lat = 59.3 + random.uniform(-2, 2)  # Around Stockholm
        lon = 18.1 + random.uniform(-2, 2)

        data.append({
            'observation_id': f"obs_{i:04d}",
            'cluster_id': cluster_id,
            'latitude': lat,
            'longitude': lon,
            'species': random.choice(['moose', 'deer', 'fox', 'badger']),
            'confidence': random.uniform(0.7, 0.95),
            'timestamp': datetime.now().isoformat()
        })

    # Create DataFrame and save as Parquet
    df = pl.DataFrame(data)
    df.write_parquet('sample_data.parquet')
    print(f"✅ Created sample_data.parquet with {len(df)} observations")
    return df

def setup_cluster_names():
    """Setup cluster names in SQLite."""
    print("🏷️ Setting up cluster names...")

    lookup = EfficientClusterLookup('cluster_names.db')

    # Add some cluster names
    cluster_names = {
        'cluster_001': 'North Forest',
        'cluster_002': 'South Meadow',
        'cluster_003': 'East Lake',
        'cluster_004': 'West Hill',
        'cluster_005': 'Central Park',
        'cluster_006': 'River Valley',
        'cluster_007': 'Mountain View',
        'cluster_008': 'Forest Edge',
        'cluster_009': 'Wildlife Corridor',
        'cluster_010': 'Observation Point'
    }

    count = lookup.batch_add_cluster_names(cluster_names)
    print(f"✅ Added {count} cluster names")
    return lookup

def extract_gps_locations(lookup: EfficientClusterLookup):
    """Extract GPS locations from Parquet and store in SQLite."""
    print("📍 Extracting GPS locations...")

    # Load Parquet data
    df = pl.read_parquet('sample_data.parquet')

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

    print(f"✅ Extracted {total_locations} locations for {len(cluster_locations)} clusters")
    return total_locations

def demonstrate_fast_enrichment():
    """Demonstrate fast data enrichment without reprocessing."""
    print("⚡ Demonstrating fast enrichment...")

    # Load original data
    df = pl.read_parquet('sample_data.parquet')
    print(f"📊 Original data: {len(df)} rows")

    # Fast enrichment with cluster names
    lookup = EfficientClusterLookup('cluster_names.db')
    enriched_df = lookup.enrich_dataframe_with_names(df)

    print(f"📊 Enriched data: {len(enriched_df)} rows")
    print("📋 Sample enriched data:")
    print(enriched_df.head().to_pandas())

    return enriched_df

def demonstrate_plotting_data():
    """Demonstrate cluster mean points for plotting."""
    print("📍 Demonstrating plotting data...")

    lookup = EfficientClusterLookup('cluster_names.db')

    # Get all cluster means
    means = lookup.get_all_cluster_means()
    names = lookup.get_all_cluster_names()

    print("📍 Cluster Mean Points for Plotting:")
    for cluster_id, (lat, lon, count) in list(means.items())[:5]:  # Show first 5
        name = names.get(cluster_id, cluster_id)
        print(f"  {cluster_id} ({name}): {lat:.4f}, {lon:.4f} ({count} points)")

    # Export for plotting
    lookup.export_cluster_means_for_plotting('cluster_means.csv')
    print("✅ Exported cluster means to cluster_means.csv")

    return means

def demonstrate_fast_reporting():
    """Demonstrate fast reporting with cluster names."""
    print("📊 Demonstrating fast reporting...")

    engine = FastReportingEngine('cluster_names.db')

    # Generate cluster report
    stats = engine.generate_cluster_report('sample_data.parquet', 'enriched_report.csv')
    print(f"✅ Generated cluster report: {json.dumps(stats, indent=2)}")

    # Generate species analysis
    species_stats = engine.generate_species_by_cluster_report('sample_data.parquet', 'species_analysis.csv')
    print(f"✅ Generated species analysis: {json.dumps(species_stats, indent=2)}")

    return stats

def demonstrate_unknown_clusters():
    """Demonstrate finding unknown clusters."""
    print("❓ Demonstrating unknown clusters...")

    lookup = EfficientClusterLookup('cluster_names.db')
    df = pl.read_parquet('sample_data.parquet')

    unknown = lookup.get_unknown_clusters(df)
    print(f"❓ Found {len(unknown)} unknown clusters:")
    for cluster_id in unknown[:5]:  # Show first 5
        print(f"  - {cluster_id}")

    return unknown

def main():
    """Main demonstration function."""
    print("🚀 Efficient Cluster Management Demo")
    print("=" * 50)

    # 1. Create sample data
    create_sample_data()

    # 2. Setup cluster names
    lookup = setup_cluster_names()

    # 3. Extract GPS locations
    extract_gps_locations(lookup)

    # 4. Demonstrate fast enrichment
    demonstrate_fast_enrichment()

    # 5. Demonstrate plotting data
    demonstrate_plotting_data()

    # 6. Demonstrate fast reporting
    demonstrate_fast_reporting()

    # 7. Demonstrate unknown clusters
    demonstrate_unknown_clusters()

    # 8. Show final statistics
    final_stats = lookup.get_stats()
    print("\n📊 Final Statistics:")
    print(json.dumps(final_stats, indent=2))

    print("\n✅ Demo completed successfully!")
    print("📁 Generated files:")
    print("  - sample_data.parquet (original data)")
    print("  - cluster_names.db (SQLite with names and locations)")
    print("  - enriched_report.csv (enriched report)")
    print("  - species_analysis.csv (species analysis)")
    print("  - cluster_means.csv (mean points for plotting)")

if __name__ == "__main__":
    main()
