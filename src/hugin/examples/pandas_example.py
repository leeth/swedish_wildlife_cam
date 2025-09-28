"""
Kort Pandas Eksempel - Hent Data fra Parquet og SQLite

Dette eksempel viser hvordan du henter data fra:
1. Parquet fil med store datasæt
2. SQLite database med cluster names og GPS locations
3. Kombiner data for analysis
"""

import sqlite3

import pandas as pd


def load_parquet_data(parquet_path: str) -> pd.DataFrame:
    """Hent data fra Parquet fil."""
    print(f"📊 Loading Parquet data from: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    print(f"✅ Loaded {len(df)} rows from Parquet")
    return df

def load_cluster_names(db_path: str) -> pd.DataFrame:
    """Hent cluster names fra SQLite."""
    print(f"🏷️ Loading cluster names from: {db_path}")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM cluster_names", conn)
    print(f"✅ Loaded {len(df)} cluster names")
    return df

def load_cluster_locations(db_path: str) -> pd.DataFrame:
    """Hent GPS locations fra SQLite."""
    print(f"📍 Loading GPS locations from: {db_path}")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM cluster_locations", conn)
    print(f"✅ Loaded {len(df)} GPS locations")
    return df

def load_cluster_means(db_path: str) -> pd.DataFrame:
    """Hent mean points fra SQLite."""
    print(f"📍 Loading mean points from: {db_path}")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM cluster_means", conn)
    print(f"✅ Loaded {len(df)} mean points")
    return df

def combine_data(parquet_df: pd.DataFrame, names_df: pd.DataFrame,
                 _locations_df: pd.DataFrame, means_df: pd.DataFrame) -> pd.DataFrame:
    """Kombiner data fra alle kilder."""
    print("🔗 Combining data from all sources...")

    # 1. Enrich Parquet data med cluster names
    enriched_df = parquet_df.merge(
        names_df[['cluster_id', 'name']],
        on='cluster_id',
        how='left'
    )

    # Fill missing names with cluster_id
    enriched_df['name'] = enriched_df['name'].fillna(enriched_df['cluster_id'])

    # 2. Add mean points for each cluster
    enriched_df = enriched_df.merge(
        means_df[['cluster_id', 'mean_latitude', 'mean_longitude', 'point_count']],
        on='cluster_id',
        how='left'
    )

    print(f"✅ Combined data: {len(enriched_df)} rows")
    return enriched_df

def analyze_data(df: pd.DataFrame):
    """Analyser kombineret data."""
    print("\n📊 Data Analysis:")
    print("=" * 50)

    # Basic stats
    print(f"Total observations: {len(df)}")
    print(f"Unique clusters: {df['cluster_id'].nunique()}")
    print(f"Named clusters: {df[df['name'] != df['cluster_id']]['cluster_id'].nunique()}")

    # Species analysis
    print("\nSpecies distribution:")
    species_counts = df['species'].value_counts()
    print(species_counts)

    # Cluster analysis
    print("\nTop clusters by observations:")
    cluster_counts = df['cluster_id'].value_counts().head(10)
    for cluster_id, count in cluster_counts.items():
        name = df[df['cluster_id'] == cluster_id]['name'].iloc[0]
        print(f"  {cluster_id} ({name}): {count} observations")

    # GPS analysis
    print("\nGPS coordinates range:")
    print(f"  Latitude: {df['latitude'].min():.4f} to {df['latitude'].max():.4f}")
    print(f"  Longitude: {df['longitude'].min():.4f} to {df['longitude'].max():.4f}")

def export_results(df: pd.DataFrame, output_path: str):
    """Export kombineret data."""
    print(f"\n💾 Exporting results to: {output_path}")
    df.to_csv(output_path, index=False)
    print(f"✅ Exported {len(df)} rows to CSV")

def main():
    """Hovedfunktion der demonstrerer data hentning."""
    print("🚀 Pandas Eksempel - Hent Data fra Parquet og SQLite")
    print("=" * 60)

    # File paths
    parquet_path = "sample_data.parquet"
    db_path = "cluster_names.db"
    output_path = "combined_data.csv"

    try:
        # 1. Hent data fra Parquet
        parquet_df = load_parquet_data(parquet_path)
        print(f"Parquet columns: {list(parquet_df.columns)}")
        print(f"Sample data:\n{parquet_df.head()}")

        # 2. Hent cluster names fra SQLite
        names_df = load_cluster_names(db_path)
        print(f"Cluster names:\n{names_df}")

        # 3. Hent GPS locations fra SQLite
        locations_df = load_cluster_locations(db_path)
        print(f"GPS locations: {len(locations_df)} points")

        # 4. Hent mean points fra SQLite
        means_df = load_cluster_means(db_path)
        print(f"Mean points:\n{means_df}")

        # 5. Kombiner data
        combined_df = combine_data(parquet_df, names_df, locations_df, means_df)

        # 6. Analyser data
        analyze_data(combined_df)

        # 7. Export results
        export_results(combined_df, output_path)

        print("\n✅ Eksempel fuldført!")
        print(f"📁 Output fil: {output_path}")

    except FileNotFoundError as e:
        print(f"❌ Fil ikke fundet: {e}")
        print("💡 Kør først: python -m hugin.examples.efficient_cluster_example")
    except Exception as e:
        print(f"❌ Fejl: {e}")

if __name__ == "__main__":
    main()
