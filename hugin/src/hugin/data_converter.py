#!/usr/bin/env python3
"""
Convert Parquet files to SQLite database for analysis.

This tool converts the Parquet output from the wildlife detection pipeline
into a SQLite database for easier querying and analysis.
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import json


def create_observations_table(cursor: sqlite3.Cursor) -> None:
    """Create the observations table with proper schema."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            camera_id TEXT,
            timestamp TEXT,
            latitude REAL,
            longitude REAL,
            observation_any BOOLEAN,
            observations TEXT,  -- JSON string
            top_label TEXT,
            top_confidence REAL,
            needs_review BOOLEAN,
            pipeline_version TEXT,
            model_hashes TEXT,  -- JSON string
            source_etag TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_id ON observations(camera_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON observations(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_observation_any ON observations(observation_any)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_needs_review ON observations(needs_review)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_top_label ON observations(top_label)")


def convert_parquet_to_sqlite(
    input_path: str,
    output_path: str,
    table_name: str = "observations",
    batch_size: int = 1000
) -> None:
    """
    Convert Parquet file to SQLite database.
    
    Args:
        input_path: Path to input Parquet file
        output_path: Path to output SQLite database
        table_name: Name of the table to create
        batch_size: Number of rows to process at once
    """
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    # Check if input file exists
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Converting {input_path} to {output_path}")
    print(f"Table name: {table_name}")
    print(f"Batch size: {batch_size}")
    
    # Read Parquet file
    print("Reading Parquet file...")
    df = pd.read_parquet(input_path)
    print(f"Loaded {len(df)} rows")
    
    # Connect to SQLite database
    conn = sqlite3.connect(output_path)
    cursor = conn.cursor()
    
    try:
        # Create table
        create_observations_table(cursor)
        
        # Process data in batches
        total_rows = len(df)
        processed_rows = 0
        
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]
            
            # Prepare data for insertion
            batch_data = []
            for _, row in batch_df.iterrows():
                # Convert JSON fields to strings, handling numpy arrays
                observations = row.get('observations', [])
                try:
                    # Check if observations is valid and not empty
                    if pd.notna(observations) and observations is not None:
                        # Convert numpy arrays to lists for JSON serialization
                        if hasattr(observations, 'tolist'):
                            observations = observations.tolist()
                        # Handle nested numpy arrays in observations
                        def convert_numpy(obj):
                            if hasattr(obj, 'tolist'):
                                return obj.tolist()
                            elif isinstance(obj, list):
                                return [convert_numpy(item) for item in obj]
                            elif isinstance(obj, dict):
                                return {key: convert_numpy(value) for key, value in obj.items()}
                            else:
                                return obj
                        observations = convert_numpy(observations)
                        observations_json = json.dumps(observations)
                    else:
                        observations_json = None
                except (ValueError, TypeError):
                    # Handle edge cases with numpy arrays
                    observations_json = None
                
                model_hashes = row.get('model_hashes', {})
                if pd.notna(model_hashes) and model_hashes is not None:
                    if hasattr(model_hashes, 'tolist'):
                        model_hashes = model_hashes.tolist()
                    model_hashes_json = json.dumps(model_hashes)
                else:
                    model_hashes_json = None
                
                batch_data.append((
                    row.get('image_path'),
                    row.get('camera_id'),
                    row.get('timestamp'),
                    row.get('latitude'),
                    row.get('longitude'),
                    row.get('observation_any'),
                    observations_json,
                    row.get('top_label'),
                    row.get('top_confidence'),
                    row.get('needs_review'),
                    row.get('pipeline_version'),
                    model_hashes_json,
                    row.get('source_etag')
                ))
            
            # Insert batch
            cursor.executemany("""
                INSERT INTO observations (
                    image_path, camera_id, timestamp, latitude, longitude,
                    observation_any, observations, top_label, top_confidence,
                    needs_review, pipeline_version, model_hashes, source_etag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            
            processed_rows += len(batch_data)
            print(f"Processed {processed_rows}/{total_rows} rows ({processed_rows/total_rows*100:.1f}%)")
        
        # Commit changes
        conn.commit()
        print(f"Successfully converted {processed_rows} rows to SQLite database")
        
        # Print summary statistics
        cursor.execute("SELECT COUNT(*) FROM observations")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM observations WHERE observation_any = 1")
        wildlife_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM observations WHERE needs_review = 1")
        review_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT camera_id) FROM observations")
        camera_count = cursor.fetchone()[0]
        
        print("\nDatabase Summary:")
        print(f"  Total observations: {total_count}")
        print(f"  Wildlife detections: {wildlife_count}")
        print(f"  Needs review: {review_count}")
        print(f"  Unique cameras: {camera_count}")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def query_database(db_path: str, query: str) -> None:
    """
    Execute a query on the SQLite database and print results.
    
    Args:
        db_path: Path to SQLite database
        query: SQL query to execute
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Print results
            print(f"\nQuery: {query}")
            print(f"Results: {len(results)} rows\n")
            
            # Print header
            print(" | ".join(f"{col:15}" for col in column_names))
            print("-" * (len(column_names) * 18))
            
            # Print rows
            for row in results:
                print(" | ".join(f"{str(val):15}" for val in row))
        else:
            print("No results found")
            
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        conn.close()


def main():
    """Main function for the CLI."""
    parser = argparse.ArgumentParser(
        description="Convert Parquet files to SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert Parquet to SQLite
  python -m src.wildlife_pipeline.tools.parquet_to_sqlite \\
    --input ./results/final.parquet \\
    --output ./results/wildlife.db \\
    --table observations

  # Query the database
  python -m src.wildlife_pipeline.tools.parquet_to_sqlite \\
    --input ./results/final.parquet \\
    --output ./results/wildlife.db \\
    --query "SELECT camera_id, COUNT(*) FROM observations GROUP BY camera_id"

  # Convert with custom batch size
  python -m src.wildlife_pipeline.tools.parquet_to_sqlite \\
    --input ./results/final.parquet \\
    --output ./results/wildlife.db \\
    --batch-size 5000
        """
    )
    
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input Parquet file"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output SQLite database"
    )
    
    parser.add_argument(
        "--table",
        default="observations",
        help="Name of the table to create (default: observations)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of rows to process at once (default: 1000)"
    )
    
    parser.add_argument(
        "--query",
        help="SQL query to execute after conversion"
    )
    
    args = parser.parse_args()
    
    try:
        # Convert Parquet to SQLite
        convert_parquet_to_sqlite(
            input_path=args.input,
            output_path=args.output,
            table_name=args.table,
            batch_size=args.batch_size
        )
        
        # Execute query if provided
        if args.query:
            query_database(args.output, args.query)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
