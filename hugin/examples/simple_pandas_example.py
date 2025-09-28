"""
Simpelt Pandas Eksempel - Hent Data fra Parquet og SQLite

Kort eksempel der viser hvordan du henter data fra begge kilder.
"""

import pandas as pd
import sqlite3

def main():
    """Simpelt eksempel - hent data fra Parquet og SQLite."""
    
    # 1. Hent store datasæt fra Parquet
    print("📊 Henter data fra Parquet...")
    df = pd.read_parquet('data.parquet')
    print(f"✅ Parquet: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # 2. Hent cluster names fra SQLite
    print("\n🏷️ Henter cluster names fra SQLite...")
    with sqlite3.connect('cluster_names.db') as conn:
        names_df = pd.read_sql_query("SELECT * FROM cluster_names", conn)
    print(f"✅ SQLite names: {len(names_df)} clusters")
    
    # 3. Hent GPS locations fra SQLite
    print("\n📍 Henter GPS locations fra SQLite...")
    with sqlite3.connect('cluster_names.db') as conn:
        locations_df = pd.read_sql_query("SELECT * FROM cluster_locations", conn)
    print(f"✅ SQLite locations: {len(locations_df)} GPS points")
    
    # 4. Hent mean points fra SQLite
    print("\n📍 Henter mean points fra SQLite...")
    with sqlite3.connect('cluster_names.db') as conn:
        means_df = pd.read_sql_query("SELECT * FROM cluster_means", conn)
    print(f"✅ SQLite means: {len(means_df)} mean points")
    
    # 5. Kombiner data
    print("\n🔗 Kombinerer data...")
    
    # Enrich Parquet med cluster names
    enriched_df = df.merge(
        names_df[['cluster_id', 'name']], 
        on='cluster_id', 
        how='left'
    )
    
    # Add mean points
    enriched_df = enriched_df.merge(
        means_df[['cluster_id', 'mean_latitude', 'mean_longitude', 'point_count']],
        on='cluster_id',
        how='left'
    )
    
    print(f"✅ Kombineret: {len(enriched_df)} rows")
    
    # 6. Vis resultat
    print("\n📊 Resultat:")
    print(enriched_df.head())
    
    # 7. Export
    enriched_df.to_csv('combined_data.csv', index=False)
    print("\n💾 Eksporteret til: combined_data.csv")
    
    print("\n✅ Færdig!")

if __name__ == "__main__":
    main()
