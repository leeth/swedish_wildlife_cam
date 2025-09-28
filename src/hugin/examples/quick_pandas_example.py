"""
Kort Pandas Eksempel - Hent Data fra Parquet og SQLite

Dette er det korteste eksempel der viser hvordan du henter data fra begge kilder.
"""

import sqlite3

import pandas as pd

# 1. Hent store datasæt fra Parquet
df = pd.read_parquet('data.parquet')
print(f"📊 Parquet: {len(df)} rows")

# 2. Hent cluster names fra SQLite
with sqlite3.connect('cluster_names.db') as conn:
    names_df = pd.read_sql_query("SELECT * FROM cluster_names", conn)
print(f"🏷️ Names: {len(names_df)} clusters")

# 3. Hent GPS locations fra SQLite
with sqlite3.connect('cluster_names.db') as conn:
    locations_df = pd.read_sql_query("SELECT * FROM cluster_locations", conn)
print(f"📍 Locations: {len(locations_df)} GPS points")

# 4. Hent mean points fra SQLite
with sqlite3.connect('cluster_names.db') as conn:
    means_df = pd.read_sql_query("SELECT * FROM cluster_means", conn)
print(f"📍 Means: {len(means_df)} mean points")

# 5. Kombiner data
enriched_df = df.merge(names_df[['cluster_id', 'name']], on='cluster_id', how='left')
enriched_df = enriched_df.merge(means_df[['cluster_id', 'mean_latitude', 'mean_longitude', 'point_count']], on='cluster_id', how='left')

print(f"✅ Kombineret: {len(enriched_df)} rows")
print(enriched_df.head())

# 6. Export
enriched_df.to_csv('combined_data.csv', index=False)
print("💾 Eksporteret til: combined_data.csv")
