# GPS Cluster Workflow Example

Dette eksempel viser hvordan man bruger GPS cluster systemet til at gruppere wildlife camera lokationer.

## 1. Process Observations

Først processer vi observations for at oprette clusters:

```bash
# Process observations fra YAML fil
python -m hugin.cluster_cli process examples/sample_observations.yaml --output results.json

# Eller fra JSON fil
python -m hugin.cluster_cli process data/observations.json --output results.json
```

## 2. List Clusters

Se alle clusters:

```bash
# List alle clusters
python -m hugin.cluster_cli list

# List kun navngivne clusters
python -m hugin.cluster_cli list --named-only
```

## 3. Find Unknown Clusters

Find clusters der mangler navn:

```bash
# Find unknown clusters
python -m hugin.cluster_cli unknown --limit 20
```

## 4. Name Clusters

Navngiv unknown clusters:

```bash
# Name en cluster
python -m hugin.cluster_cli name cluster_123 "Deer Feeding Area" --description "Main deer feeding location"

# Name flere clusters
python -m hugin.cluster_cli name cluster_456 "Fox Den" --description "Red fox denning area"
```

## 5. Get Cluster Details

Se detaljer om en specifik cluster:

```bash
# Get cluster details
python -m hugin.cluster_cli details cluster_123

# Get cluster boundary for mapping
python -m hugin.cluster_cli boundary cluster_123
```

## 6. Export for Mapping

Export clusters til mapping formater:

```bash
# Export alle formater
python -m hugin.cluster_cli export exports/

# Export specifikke formater
python -m hugin.cluster_cli export exports/ --formats geojson kml
```

## 7. Search Clusters

Søg efter clusters nær en lokation:

```bash
# Search within 100m
python -m hugin.cluster_cli search 55.6761 12.5683 --radius 100

# Search within 50m
python -m hugin.cluster_cli search 55.6761 12.5683 --radius 50
```

## 8. Statistics

Se cluster statistikker:

```bash
python -m hugin.cluster_cli stats
```

## YAML Configuration

Brug en custom konfiguration:

```bash
# Med custom config
python -m hugin.cluster_cli --config my_config.yaml process observations.yaml
```

## Eksempel Output

### Process Results
```
Processed 8 observations
Created 3 new clusters
```

### List Clusters
```
Found 3 clusters:
  cluster_123 - Deer Feeding Area (Named) - 3 points
  cluster_456 - Fox Den (Named) - 2 points  
  cluster_789 - Unnamed (Unknown) - 2 points
```

### Unknown Clusters
```
Found 1 unknown clusters:
  cluster_789 - 2 points at (55.6900, 12.5800)
```

### Statistics
```
📊 Cluster Statistics:
  Total clusters: 3
  Named clusters: 2
  Unknown clusters: 1
  Total assignments: 8
  Average points per cluster: 2.7
  Naming rate: 66.7%
```

## Export Formats

### GeoJSON
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "cluster_id": "cluster_123",
        "name": "Deer Feeding Area",
        "point_count": 3,
        "is_named": true
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[12.5683, 55.6761], [12.5684, 55.6762], ...]]
      }
    }
  ]
}
```

### KML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <name>GPS Clusters</name>
    <Placemark>
        <name>Deer Feeding Area (Center)</name>
        <Point>
            <coordinates>12.5683,55.6761,0</coordinates>
        </Point>
    </Placemark>
</Document>
</kml>
```

## Database

Clusters gemmes i SQLite database (`clusters.db` by default) med følgende tabeller:

- `gps_clusters` - Cluster information
- `gps_cluster_assignments` - Point assignments til clusters

Database filer er ekskluderet fra Git via `.gitignore`.
