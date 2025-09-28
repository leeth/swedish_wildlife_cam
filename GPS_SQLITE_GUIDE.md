# GPS and SQLite Database Guide

This guide explains the new GPS coordinate extraction and SQLite database functionality in the wildlife detection pipeline.

## 🗺️ GPS Coordinate Extraction

The pipeline now automatically extracts GPS coordinates from EXIF data in images and videos.

### Features

- **Automatic GPS extraction** from EXIF metadata
- **Support for multiple GPS formats** (PIL and exifread)
- **Coordinate validation** to ensure valid latitude/longitude values
- **Fallback handling** for images without GPS data

### GPS Data Sources

The system looks for GPS data in these EXIF fields:
- `GPSInfo` (PIL format)
- `GPS` (exifread format)
- `GPSLatitude` and `GPSLongitude` with reference directions

### Coordinate Conversion

GPS coordinates are automatically converted from Degrees/Minutes/Seconds (DMS) to decimal degrees:
- **Latitude**: -90° to +90°
- **Longitude**: -180° to +180°

## 🗄️ SQLite Database

The pipeline now supports SQLite database output in addition to CSV/Parquet formats.

### Database Schema

#### `detections` table
- `id`: Primary key
- `file_path`: Path to image/video file
- `file_type`: 'image' or 'video_frame'
- `camera_id`: Camera identifier
- `timestamp`: ISO format timestamp
- `latitude`: GPS latitude (decimal degrees)
- `longitude`: GPS longitude (decimal degrees)
- `image_width`: Image width in pixels
- `image_height`: Image height in pixels
- `stage1_dropped`: Number of detections dropped in Stage 1
- `manual_review_count`: Number of detections sent for manual review
- `observations_stage2`: JSON string of Stage 2 classification results
- `video_source`: Source video file (for video frames)
- `frame_number`: Frame number (for video frames)
- `frame_timestamp`: Frame timestamp (for video frames)

#### `detection_results` table
- `id`: Primary key
- `detection_id`: Foreign key to detections table
- `label`: Species label
- `confidence`: Detection confidence score
- `bbox_x1`, `bbox_y1`, `bbox_x2`, `bbox_y2`: Bounding box coordinates
- `stage`: Detection stage (1 for Stage 1, 2 for Stage 2)

### Database Indexes

For optimal performance, the following indexes are created:
- `idx_detections_camera`: Camera ID lookups
- `idx_detections_timestamp`: Time-based queries
- `idx_detections_gps`: GPS coordinate queries
- `idx_results_detection`: Detection result lookups
- `idx_results_label`: Species-based queries

## 🚀 Usage

### Command Line Options

```bash
# Use SQLite database output
python src/wildlife_pipeline/run_pipeline.py \
    --input /path/to/images \
    --output results.db \
    --write sqlite \
    --model megadetector

# Use CSV output (default)
python src/wildlife_pipeline/run_pipeline.py \
    --input /path/to/images \
    --output results.csv \
    --write csv \
    --model megadetector
```

### Database Queries

The `WildlifeDatabase` class provides several query methods:

```python
from src.wildlife_pipeline.database import WildlifeDatabase

db = WildlifeDatabase("results.db")

# Get all detections for a camera
camera_detections = db.get_detections_by_camera("camera_1")

# Get all detections for a species
moose_detections = db.get_detections_by_species("moose")

# Get all detections with GPS coordinates
gps_detections = db.get_detections_with_gps()

# Get summary statistics
stats = db.get_summary_stats()
print(f"Total detections: {stats['total_detections']}")
print(f"Detections with GPS: {stats['gps_detections']}")
print(f"Species detected: {stats['species_counts']}")

# Export to CSV
db.export_to_csv("export.csv")
```

## 📊 Output Examples

### SQLite Database Summary

```
Database summary:
  Total detections: 150
  Detections with GPS: 120
  Species detected: ['moose', 'boar', 'roedeer', 'fox', 'badger']
  Cameras: ['camera_1', 'camera_2', 'camera_3']
```

### GPS Coordinate Examples

- **Stockholm**: 59.3293°N, 18.0686°E
- **Copenhagen**: 55.6761°N, 12.5683°E
- **Helsinki**: 60.1699°N, 24.9384°E

## 🔧 Technical Details

### GPS Extraction Process

1. **EXIF Reading**: Extract EXIF data using PIL and exifread
2. **GPS Field Detection**: Look for GPSInfo or GPS fields
3. **Coordinate Parsing**: Parse DMS format coordinates
4. **Conversion**: Convert to decimal degrees
5. **Validation**: Ensure coordinates are within valid ranges

### Database Performance

- **Indexed queries** for fast lookups by camera, timestamp, and GPS
- **Efficient storage** with normalized schema
- **JSON support** for complex Stage 2 results
- **Foreign key constraints** for data integrity

### Error Handling

- **Missing GPS data**: Gracefully handled with NULL values
- **Invalid coordinates**: Filtered out during validation
- **Corrupted EXIF**: Fallback to file modification time
- **Database errors**: Transaction rollback on failures

## 🧪 Testing

Run the test script to verify functionality:

```bash
# Test GPS extraction and SQLite database
python scripts/test_gps_sqlite.py
```

Expected output:
```
Testing GPS extraction and SQLite database functionality...
Testing GPS coordinate extraction...
  GPS extraction successful: 59.3292, 18.0686
  Empty EXIF handled correctly

Testing SQLite database functionality...
Created database: /tmp/test_wildlife.db
Inserted detection ID: 1
Inserted detection ID: 2

Database queries:
Total detections: 2
Detections with GPS: 2
Species detected: {'boar': 1, 'moose': 1, 'roedeer': 1}
Cameras: {'camera_1': 1, 'camera_2': 1}

✅ All tests completed successfully!
```

## 🔄 Migration from CSV

If you have existing CSV data, you can import it into SQLite:

```python
import pandas as pd
from src.wildlife_pipeline.database import WildlifeDatabase

# Read existing CSV
df = pd.read_csv("existing_results.csv")

# Create new database
db = WildlifeDatabase("new_results.db")

# Convert and insert data
for _, row in df.iterrows():
    detection_data = {
        'file_path': row['file_path'],
        'file_type': 'image',
        'camera_id': row['camera_id'],
        'timestamp': row['timestamp'],
        'latitude': row.get('latitude'),
        'longitude': row.get('longitude'),
        'detection_results': []  # Convert from existing format
    }
    db.insert_detection(detection_data)
```

## 🎯 Benefits

### GPS Integration
- **Spatial analysis** of wildlife detections
- **Camera trap mapping** and coverage analysis
- **Habitat correlation** with detection patterns
- **Migration tracking** across camera locations

### SQLite Database
- **Structured queries** for complex analysis
- **Efficient storage** with indexes
- **Data integrity** with foreign key constraints
- **Flexible export** to CSV, JSON, or other formats
- **Scalable** for large datasets

### Stage 2 Integration
- **GPS coordinates** included in Stage 2 classification results
- **Spatial context** for species identification
- **Location-based** confidence scoring
- **Geographic distribution** analysis of species
