# GPS Cluster Workflow Example

Dette eksempel viser hvordan du bruger GPS cluster funktionaliteten i Hugin.

## 🚀 Hurtig Start

### 1. **Process Observations**
```bash
# Process observations og opret clusters
python -m hugin.cluster_cli process sample_observations.yaml results.json --radius 5.0
```

### 2. **Request Unknown Clusters**
```bash
# Vis unknown clusters der skal navngives
python -m hugin.cluster_cli request-unknown --limit 20
```

### 3. **Submit Cluster Names**
```bash
# Submit cluster names fra YAML fil
python -m hugin.cluster_cli submit-names cluster_names.yaml
```

### 4. **Export Boundaries**
```bash
# Export cluster boundaries til mapping
python -m hugin.cluster_cli export-boundaries boundaries.geojson --format geojson
```

### 5. **Show Analytics**
```bash
# Vis cluster analytics
python -m hugin.cluster_cli analytics
```

## 📊 Workflow Steps

### **Step 1: Process Observations**
```yaml
# sample_observations.yaml
observations:
  - observation_id: "obs_001"
    latitude: 59.3293
    longitude: 18.0686
    timestamp: "2024-01-15T10:30:00Z"
    species: "moose"
    confidence: 0.85
```

### **Step 2: Request Unknown Clusters**
```bash
python -m hugin.cluster_cli request-unknown --limit 20
```

Output:
```
❓ Found 3 unknown clusters:
  1. cluster_001 - 15 points
     Center: 59.3294, 18.0687
  2. cluster_002 - 8 points
     Center: 59.3401, 18.0801
  3. cluster_003 - 12 points
     Center: 59.3500, 18.0900
```

### **Step 3: Submit Cluster Names**
```yaml
# cluster_names.yaml
cluster_names:
  cluster_001: "North Forest"
  cluster_002: "South Meadow"
  cluster_003: "East Lake"
```

```bash
python -m hugin.cluster_cli submit-names cluster_names.yaml
```

### **Step 4: Export Boundaries**
```bash
python -m hugin.cluster_cli export-boundaries boundaries.geojson --format geojson
```

### **Step 5: Show Analytics**
```bash
python -m hugin.cluster_cli analytics
```

Output:
```
📊 Cluster Analytics:
  Total clusters: 3
  Named clusters: 3
  Unnamed clusters: 0
  Total points: 35
  Average points per cluster: 11.7
```

## 🔧 Configuration

### **cluster_config.yaml**
```yaml
# Database settings
db_path: "clusters.db"

# Clustering parameters
clustering:
  radius_meters: 5.0
  min_points: 2
  max_clusters: 1000

# Export settings
export:
  formats: ["csv", "json", "geojson"]
  output_dir: "outputs"
```

## 📁 Output Files

### **results.json**
```json
{
  "success": true,
  "clusters_created": 3,
  "total_points": 35,
  "clusters": [
    {
      "cluster_id": "cluster_001",
      "name": null,
      "center_latitude": 59.3294,
      "center_longitude": 18.0687,
      "radius_meters": 5.0,
      "point_count": 15
    }
  ]
}
```

### **boundaries.geojson**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "cluster_id": "cluster_001",
        "area_square_meters": 78.5,
        "perimeter_meters": 31.4
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [18.0687, 59.3294],
          [18.0688, 59.3295],
          [18.0689, 59.3296]
        ]]
      }
    }
  ]
}
```

## 🎯 Key Features

### **1. Automatic Clustering**
- **GPS proximity clustering** med 5m radius
- **Automatic cluster creation** fra observations
- **Cluster statistics** og analytics

### **2. Cluster Naming**
- **Unknown cluster detection** for manual naming
- **Batch naming** fra YAML filer
- **Cluster lookup** og management

### **3. Export Capabilities**
- **GeoJSON export** til mapping
- **KML export** til Google Earth
- **CSV/JSON export** til analysis

### **4. Analytics**
- **Cluster statistics** og metrics
- **Temporal analysis** per cluster
- **Species analysis** per cluster

## 🚀 Advanced Usage

### **Batch Processing**
```bash
# Process multiple observation files
for file in observations/*.yaml; do
  python -m hugin.cluster_cli process "$file" "results/$(basename "$file" .yaml).json"
done
```

### **Automated Naming**
```bash
# Auto-name clusters based on location
python -m hugin.cluster_cli request-unknown --limit 100 | \
  python scripts/auto_name_clusters.py | \
  python -m hugin.cluster_cli submit-names auto_names.yaml
```

### **Export for Mapping**
```bash
# Export all formats for mapping
python -m hugin.cluster_cli export-boundaries boundaries.geojson --format geojson
python -m hugin.cluster_cli export-boundaries boundaries.kml --format kml
python -m hugin.cluster_cli export-data clusters.csv --format csv
```

Dette giver dig en komplet workflow for GPS cluster management i Hugin! 🎯
