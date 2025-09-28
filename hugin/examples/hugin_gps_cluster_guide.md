# Hugin GPS Cluster Management Guide

Dette guide viser hvordan man bruger det specialiserede `hugin_gps_cluster_management` script til GPS cluster management i Hugin ecosystemet.

## Overview

`hugin_gps_cluster_management` er et specialiseret Hugin script der fokuserer på GPS cluster management og integrerer med det bredere Hugin ecosystem for wildlife camera data analyse.

## Installation og Setup

```bash
# Install Hugin med GPS cluster management
pip install -e .

# Setup database
python -m hugin.hugin_gps_cluster_management --config examples/hugin_gps_cluster_config.yaml
```

## Basic Usage

### 1. Process Observations with GPS Clustering

Processer observations og opretter GPS clusters automatisk:

```bash
# Process observations med GPS clustering
python -m hugin.hugin_gps_cluster_management process \
    examples/sample_observations.yaml \
    outputs/cluster_analysis \
    --config examples/hugin_gps_cluster_config.yaml
```

**Output:**
```
✅ GPS clustering completed successfully
  Observations: 8
  Clusters: 3 new, 8 assigned
  Output: outputs/cluster_analysis
```

### 2. Run Cluster Tagging Workflow

Kør en komplet cluster tagging workflow:

```bash
# Run tagging workflow
python -m hugin.hugin_gps_cluster_management workflow \
    examples/hugin_gps_workflow_example.yaml \
    --config examples/hugin_gps_cluster_config.yaml
```

### 3. Regenerate Analytics with Cluster Data

Genkør analytics med nuværende cluster data:

```bash
# Regenerate analytics
python -m hugin.hugin_gps_cluster_management regenerate \
    examples/sample_observations.yaml \
    outputs/updated_analysis
```

## Advanced Usage

### Cluster Management Commands

Deleger til cluster CLI for detaljeret cluster management:

```bash
# List clusters
python -m hugin.hugin_gps_cluster_management cluster list

# Request unknown clusters
python -m hugin.hugin_gps_cluster_management cluster request-unknown --limit 20

# Submit cluster names
python -m hugin.hugin_gps_cluster_management cluster submit-names naming.yaml

# Detect overlaps
python -m hugin.hugin_gps_cluster_management cluster detect-overlaps --threshold 10.0

# Merge clusters
python -m hugin.hugin_gps_cluster_management cluster merge-clusters merge_requests.yaml
```

### Analytics with Cluster Data

Generer cluster-aware analytics:

```bash
# Generate analytics
python -m hugin.hugin_gps_cluster_management analytics \
    examples/sample_observations.yaml \
    --output analytics_report.json \
    --format json

# Export as GeoJSON
python -m hugin.hugin_gps_cluster_management analytics \
    examples/sample_observations.yaml \
    --output cluster_boundaries.geojson \
    --format geojson
```

## Configuration

### GPS Cluster Config

```yaml
# hugin_gps_cluster_config.yaml
database:
  path: "data/hugin_clusters.db"

clustering:
  radius_meters: 5.0
  min_points: 1
  auto_cluster: true

analytics:
  include_clusters: true
  cluster_analysis: true
  species_by_cluster: true
  temporal_by_cluster: true

workflow:
  auto_detect_overlaps: true
  overlap_threshold: 10.0
  auto_merge_similar: false
```

### Workflow Configuration

```yaml
# hugin_gps_workflow_example.yaml
workflow:
  name: "Wildlife Camera GPS Clustering"
  description: "GPS cluster management workflow"

request_unknown:
  enabled: true
  limit: 50
  min_points: 2

detect_overlaps:
  enabled: true
  threshold: 10.0

merge_requests:
  merges:
    - cluster_ids: ["cluster_123", "cluster_456"]
      new_name: "Wildlife Activity Zone"
      new_description: "Combined deer and fox activity area"
```

## Integration med Hugin Ecosystem

### 1. Wildlife Pipeline Integration

```bash
# Process med wildlife pipeline
python -m hugin.wildlife_pipeline process data/observations.json

# Derefter GPS clustering
python -m hugin.hugin_gps_cluster_management process \
    data/observations.json \
    outputs/cluster_analysis
```

### 2. Analytics Integration

```bash
# Regenerate analytics med cluster data
python -m hugin.hugin_gps_cluster_management regenerate \
    data/observations.json \
    outputs/updated_analytics
```

### 3. Export Integration

```bash
# Export cluster boundaries for mapping
python -m hugin.hugin_gps_cluster_management analytics \
    data/observations.json \
    --output cluster_boundaries.geojson \
    --format geojson
```

## Workflow Examples

### Complete Workflow

```bash
# 1. Process observations
python -m hugin.hugin_gps_cluster_management process \
    data/observations.yaml \
    outputs/initial_analysis

# 2. Request unknown clusters
python -m hugin.hugin_gps_cluster_management cluster request-unknown \
    --limit 20 --output unknown_clusters.yaml

# 3. Edit YAML med navne
# (Edit unknown_clusters.yaml)

# 4. Submit names
python -m hugin.hugin_gps_cluster_management cluster submit-names unknown_clusters.yaml

# 5. Detect overlaps
python -m hugin.hugin_gps_cluster_management cluster detect-overlaps --threshold 10.0

# 6. Create merge requests
# (Create merge_requests.yaml)

# 7. Apply merges
python -m hugin.hugin_gps_cluster_management cluster merge-clusters merge_requests.yaml

# 8. Regenerate analytics
python -m hugin.hugin_gps_cluster_management regenerate \
    data/observations.yaml \
    outputs/final_analysis
```

### Automated Workflow

```bash
# Run complete workflow from config
python -m hugin.hugin_gps_cluster_management workflow \
    examples/hugin_gps_workflow_example.yaml \
    --config examples/hugin_gps_cluster_config.yaml
```

## Output Files

### Analytics Output
- `cluster_analytics.json` - Complete analytics with cluster data
- `cluster_boundaries.geojson` - Cluster boundaries for mapping
- `cluster_boundaries.kml` - KML format for Google Earth
- `cluster_statistics.csv` - Cluster statistics in CSV format

### Workflow Output
- `unknown_clusters.yaml` - Unknown clusters for naming
- `merge_requests.yaml` - Merge requests for overlapping clusters
- `workflow_results.json` - Workflow execution results

## Database

GPS cluster data gemmes i SQLite database (`hugin_clusters.db` by default):

- **gps_clusters** - Cluster information
- **gps_cluster_assignments** - Point assignments
- **Change tracking** - Automatic change tracking

Database filer er ekskluderet fra Git via `.gitignore`.

## Tips og Best Practices

1. **Start med høj-aktivitet clusters** - Navngiv clusters med flest points først
2. **Brug beskrivende navne** - "Deer Feeding Area" er bedre end "Cluster 1"
3. **Check overlaps regelmæssigt** - Merge overlappende clusters
4. **Backup database** - Tag backup af `hugin_clusters.db` før store ændringer
5. **Integrer med analytics** - Regenerate analytics efter cluster changes
6. **Brug workflow configs** - Gem workflow konfigurationer til genbrug

## Troubleshooting

### Common Issues

1. **Database locked** - Stop andre processer der bruger database
2. **Memory issues** - Reducer batch_size i config
3. **GPS accuracy** - Check GPS accuracy threshold i config
4. **Overlap detection** - Juster overlap_threshold parameter

### Debug Mode

```bash
# Enable verbose logging
python -m hugin.hugin_gps_cluster_management process \
    data/observations.yaml \
    outputs/analysis \
    --verbose
```

## Integration med Andre Hugin Scripts

```bash
# Wildlife pipeline
python -m hugin.wildlife_pipeline process data/input

# GPS cluster management
python -m hugin.hugin_gps_cluster_management process data/input outputs/clusters

# Analytics
python -m hugin.analytics generate data/input outputs/analytics

# Export
python -m hugin.export data/input outputs/export
```

Dette script integrerer perfekt med det bredere Hugin ecosystem og giver specialiseret GPS cluster management funktionalitet.
