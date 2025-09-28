# Location Classification Tools Guide

This guide explains how to use the location classification tools for organizing wildlife camera images by location.

## 🎯 Overview

The location classification system helps you:
- **Classify images by location** using GPS coordinates
- **Identify unknown locations** that need manual labeling
- **Move images to cloud storage** with organized folder structure
- **Share location labels** via Git repository
- **Sync location data** across team members

## 🏗️ Architecture

### Components

1. **LocationClassifier** - Core classification engine
2. **InteractiveLocationLabeler** - Manual labeling interface
3. **LocationSync** - Git synchronization tool

### Database Schema

```sql
-- Known locations
CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius_meters REAL DEFAULT 10.0,
    description TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- Image location mappings
CREATE TABLE image_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    sd_card TEXT NOT NULL,
    location_id TEXT,
    latitude REAL,
    longitude REAL,
    distance_meters REAL,
    needs_review BOOLEAN DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (location_id) REFERENCES locations (id)
);

-- SD card mappings
CREATE TABLE sd_card_mappings (
    sd_card TEXT PRIMARY KEY,
    description TEXT,
    first_seen TEXT,
    last_seen TEXT,
    image_count INTEGER DEFAULT 0
);
```

## 🚀 Quick Start

### 1. Classify Images

```bash
# Classify images from a directory
python -m src.wildlife_pipeline.tools.location_classifier classify \
    /path/to/images \
    --sd-card SD001 \
    --recursive

# Show classification statistics
python -m src.wildlife_pipeline.tools.location_classifier stats
```

### 2. Label Unknown Locations

```bash
# Interactive mode for labeling
python -m src.wildlife_pipeline.tools.location_labeler --interactive

# Create location from specific image
python -m src.wildlife_pipeline.tools.location_labeler create \
    /path/to/image.jpg \
    --name "Camera Site A" \
    --description "Main wildlife crossing"
```

### 3. Move Images to Cloud

```bash
# Move classified images to cloud storage
python -m src.wildlife_pipeline.tools.location_classifier move \
    /path/to/images \
    s3://my-bucket/wildlife-images/ \
    --dry-run  # Preview what will be moved
```

### 4. Sync with Git

```bash
# Full sync with remote repository
python -m src.wildlife_pipeline.tools.location_sync sync \
    --repo /path/to/git/repo \
    --merge-strategy skip_existing
```

## 📋 Detailed Usage

### Location Classifier

The `location_classifier` tool handles the core classification workflow:

```bash
# Basic classification
location_classifier classify /path/to/images --sd-card SD001

# Options:
--db PATH              # SQLite database path (default: ./location_classifier.db)
--storage TYPE         # Storage adapter (local, s3, gcs)
--recursive           # Process subdirectories
```

**Classification Process:**
1. Extracts GPS coordinates from EXIF data
2. Finds nearby known locations (within 10m radius)
3. Marks unknown locations for review
4. Stores results in SQLite database

### Interactive Location Labeler

The `location_labeler` tool provides an interactive interface for manual labeling:

```bash
# Interactive mode
location_labeler --interactive

# Show unknown locations
location_labeler show --limit 20

# Create location from image
location_labeler create /path/to/image.jpg --name "Site A"

# Show location on map
location_labeler map /path/to/image.jpg
```

**Interactive Features:**
- View unknown locations with GPS coordinates
- Create new location labels
- Open locations in web browser maps
- Export/import location data
- Batch processing capabilities

### Location Sync Tool

The `location_sync` tool manages Git synchronization:

```bash
# Export current labels
location_sync export --repo /path/to/repo

# Import labels from Git
location_sync pull --repo /path/to/repo

# Full sync (export + commit + push + pull + import)
location_sync sync --repo /path/to/repo

# Show status
location_sync status --repo /path/to/repo
```

**Sync Workflow:**
1. Export current location labels to JSON
2. Commit and push changes to Git
3. Pull latest changes from remote
4. Import new location labels
5. Handle merge conflicts

## 🗂️ Folder Structure

### Input Structure
```
/path/to/images/
  SD001/
    IMG_0001.JPG
    IMG_0002.JPG
  SD002/
    IMG_0003.JPG
    IMG_0004.JPG
```

### Cloud Storage Structure
```
s3://my-bucket/wildlife-images/
  SD001/
    stockholm_central/
      IMG_0001.JPG
      IMG_0002.JPG
    unknown/
      IMG_0003.JPG
  SD002/
    stockholm_north/
      IMG_0004.JPG
```

### Git Repository Structure
```
location_labels/
  locations_20250101_120000.json
  locations_20250102_140000.json
  README.md
```

## 🔧 Configuration

### Database Configuration

The SQLite database stores all location and image data:

```python
# Custom database path
classifier = LocationClassifier(Path("./custom_locations.db"))
```

### Storage Configuration

Configure cloud storage adapters:

```python
# S3 storage
storage_adapter = create_storage_adapter("s3", 
    base_path="s3://my-bucket/wildlife-images",
    region="eu-north-1")

# GCS storage  
storage_adapter = create_storage_adapter("gcs",
    base_path="gs://my-bucket/wildlife-images")
```

### Git Configuration

Set up Git repository for location sharing:

```bash
# Initialize repository
git init /path/to/location-repo
cd /path/to/location-repo

# Create labels directory
mkdir location_labels
echo "# Location Labels" > location_labels/README.md

# Initial commit
git add location_labels/
git commit -m "Initial location labels"
git remote add origin https://github.com/user/location-labels.git
git push -u origin main
```

## 📊 Workflow Examples

### Example 1: New Camera Deployment

```bash
# 1. Classify images from new SD card
location_classifier classify /path/to/new-images --sd-card SD003

# 2. Review unknown locations
location_labeler show --limit 10

# 3. Create location labels for unknown sites
location_labeler create /path/to/image1.jpg --name "Camera Site C"
location_labeler create /path/to/image2.jpg --name "Camera Site D"

# 4. Move images to cloud storage
location_classifier move /path/to/new-images s3://bucket/wildlife/

# 5. Sync labels with team
location_sync sync --repo /path/to/location-repo
```

### Example 2: Team Collaboration

```bash
# 1. Pull latest location labels from team
location_sync pull --repo /path/to/location-repo

# 2. Classify new images with updated labels
location_classifier classify /path/to/images --sd-card SD004

# 3. Add new locations found
location_labeler --interactive

# 4. Export and sync changes
location_sync sync --repo /path/to/location-repo
```

### Example 3: Batch Processing

```bash
# 1. Process multiple SD cards
for sd_card in SD001 SD002 SD003; do
    location_classifier classify /path/to/$sd_card --sd-card $sd_card
done

# 2. Review all unknown locations
location_labeler show --limit 50

# 3. Batch create locations from JSON file
location_labeler import locations_to_create.json

# 4. Move all images to cloud
location_classifier move /path/to/all-images s3://bucket/wildlife/
```

## 🛠️ Advanced Features

### Custom Location Radius

```python
# Create location with custom radius
location = Location(
    id="custom_site",
    name="Custom Site",
    latitude=59.3293,
    longitude=18.0686,
    radius_meters=25.0  # 25 meter radius
)
```

### Merge Strategies

```bash
# Skip existing locations (default)
location_sync sync --merge-strategy skip_existing

# Update existing locations
location_sync sync --merge-strategy update_existing

# Create new locations with modified IDs
location_sync sync --merge-strategy create_new
```

### Batch Operations

```python
# Batch create locations
locations_data = [
    {"image_path": "/path/to/img1.jpg", "name": "Site A", "description": "..."},
    {"image_path": "/path/to/img2.jpg", "name": "Site B", "description": "..."}
]

labeler = InteractiveLocationLabeler(db_path)
labeler.batch_create_locations(locations_data)
```

## 🔍 Troubleshooting

### Common Issues

**GPS Data Not Found:**
```bash
# Check if images have GPS data
exiftool /path/to/image.jpg | grep GPS
```

**Database Locked:**
```bash
# Check for other processes using database
lsof location_classifier.db
```

**Git Conflicts:**
```bash
# Resolve conflicts manually
location_sync resolve --repo /path/to/repo
```

### Debug Mode

```bash
# Enable verbose logging
export PYTHONPATH=/path/to/wildlife_pipeline
python -m src.wildlife_pipeline.tools.location_classifier classify /path/to/images --sd-card SD001 -v
```

## 📈 Performance Tips

1. **Batch Processing**: Process multiple SD cards in batches
2. **Database Indexing**: Ensure proper indexes on GPS coordinates
3. **Cloud Storage**: Use appropriate storage classes for archived images
4. **Git Optimization**: Use shallow clones for large repositories

## 🔒 Security Considerations

1. **GPS Privacy**: Consider removing GPS data from public images
2. **Database Access**: Secure SQLite database files
3. **Git Repository**: Use private repositories for sensitive location data
4. **Cloud Storage**: Configure appropriate access controls

## 📚 API Reference

### LocationClassifier

```python
classifier = LocationClassifier(db_path, storage_adapter)

# Classify image
image_location = classifier.classify_image(image_path, sd_card)

# Find nearby location
location = classifier.find_nearby_location(lat, lon, max_distance=10.0)

# Get statistics
stats = classifier.get_statistics()
```

### InteractiveLocationLabeler

```python
labeler = InteractiveLocationLabeler(db_path)

# Show unknown locations
unknown = labeler.show_unknown_locations(limit=20)

# Create location
location_id = labeler.create_location_interactive(image_path)

# Show on map
labeler.show_location_map(image_path)
```

### LocationSync

```python
sync_tool = LocationSync(db_path, git_repo_path)

# Export labels
export_file = sync_tool.export_labels()

# Sync with remote
sync_tool.sync_with_remote(merge_strategy="skip_existing")

# Show status
sync_tool.show_status()
```

## 🤝 Contributing

To contribute to the location classification tools:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
