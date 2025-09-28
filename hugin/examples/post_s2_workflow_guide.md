# Post-S2 Workflow Guide

Dette guide viser den komplette workflow efter S2 (species detection) er færdig:

1. **S2 er done** → Hugin tager over
2. **Billede analyse** med artsbestemmelse
3. **Samle billeder i lokations_cluster** (GPS clustering)
4. **Kondensere data** i cluster (tæl observationer hvert 10 min)
5. **Output med cluster navne** - men navne kan kun brugeren give
6. **Afkobling mellem labeling og processering** - navne bruges kun til afrapportering

## Workflow Overview

```
S2 Results → Image Analysis → Location Clustering → Data Condensation → Output
     ↓              ↓              ↓                    ↓              ↓
Species Data → Species Analysis → GPS Clusters → Time Windows → Reports
```

## 1. Process Post-S2 Workflow

Efter S2 er færdig, kør post-S2 workflow:

```bash
# Process S2 results med post-S2 workflow
python -m hugin.post_s2_workflow process \
    examples/s2_results_example.json \
    outputs/post_s2_analysis \
    --config examples/post_s2_config.yaml
```

**Output:**
```
✅ Post-S2 workflow completed successfully
  S2 observations: 8
  Steps: load_s2_results, image_analysis, location_clustering, data_condensation, generate_output
  Clusters: 3 total, 3 unknown
```

## 2. Request Unknown Clusters for Labeling

Få unknown clusters der mangler navn (decoupled fra processing):

```bash
# Request unknown clusters for labeling
python -m hugin.post_s2_workflow request-labels \
    --limit 20 \
    --output unknown_clusters.yaml
```

**Output:**
```
Found 3 unknown clusters needing labels
  cluster_123 - Unknown_Cluster_1 - 3 points
  cluster_456 - Unknown_Cluster_2 - 2 points
  cluster_789 - Unknown_Cluster_3 - 2 points
```

## 3. Submit Cluster Labels

Efter at have navngivet clusters, submit labels:

```yaml
# unknown_clusters.yaml
cluster_123:
  name: "Deer Feeding Area"
  description: "Main deer feeding location"
  
cluster_456:
  name: "Fox Den Area"
  description: "Red fox denning area"
  
cluster_789:
  name: "Wild Boar Wallow"
  description: "Wild boar wallowing area"
```

```bash
# Submit cluster labels
python -m hugin.post_s2_workflow submit-labels unknown_clusters.yaml
```

**Output:**
```
✅ Submitted 3 cluster labels
  Successful: 3
  Failed: 0
```

## 4. Data Condensation

Systemet kondenserer data i konfigurerbare time windows:

### Configuration
```yaml
# post_s2_config.yaml
data_condensation:
  enabled: true
  time_window_minutes: 10          # 10 minutters vinduer
  aggregation_method: "count"      # Tæl observationer
  include_species_breakdown: true  # Inkluder species breakdown
```

### Output
```csv
window_start,window_end,total_observations,roe_deer,red_fox,wild_boar
2024-01-15T08:30:00,2024-01-15T08:40:00,2,2,0,0
2024-01-15T09:10:00,2024-01-15T09:20:00,1,0,1,0
2024-01-15T11:30:00,2024-01-15T11:40:00,2,2,0,0
2024-01-15T14:00:00,2024-01-15T14:10:00,2,0,0,2
```

## 5. Output Files

### Cluster Analysis
```json
{
  "processing_timestamp": "2024-01-15T10:00:00Z",
  "total_observations": 8,
  "clusters": [
    {
      "cluster_id": "cluster_123",
      "name": "Deer Feeding Area",
      "center_latitude": 55.6761,
      "center_longitude": 12.5683,
      "point_count": 3,
      "description": "Main deer feeding location"
    }
  ],
  "unknown_clusters": [
    {
      "cluster_id": "cluster_456",
      "generated_name": "Unknown_Cluster_2",
      "center_latitude": 55.6800,
      "center_longitude": 12.5700,
      "point_count": 2
    }
  ],
  "decoupled_labeling": true
}
```

### Cluster Boundaries
- `cluster_boundaries.geojson` - For mapping applications
- `cluster_boundaries.kml` - For Google Earth
- `condensed_data.csv` - Time window data

## 6. Complete Workflow Example

### Step 1: S2 Completion
```bash
# S2 processer billeder og genererer species detection
python -m hugin.s2_pipeline process data/images/ outputs/s2_results/
```

### Step 2: Post-S2 Processing
```bash
# Process S2 results med location clustering
python -m hugin.post_s2_workflow process \
    outputs/s2_results/s2_results.json \
    outputs/post_s2_analysis \
    --config examples/post_s2_config.yaml
```

### Step 3: Request Labels
```bash
# Get unknown clusters for labeling
python -m hugin.post_s2_workflow request-labels \
    --limit 50 \
    --output unknown_clusters.yaml
```

### Step 4: User Labels Clusters
```yaml
# Edit unknown_clusters.yaml
cluster_123:
  name: "Deer Feeding Area"
  description: "Main deer feeding location near water source"
  
cluster_456:
  name: "Fox Den Area"
  description: "Red fox denning and hunting area"
```

### Step 5: Submit Labels
```bash
# Submit cluster labels
python -m hugin.post_s2_workflow submit-labels unknown_clusters.yaml
```

### Step 6: Generate Final Reports
```bash
# Regenerate analytics med cluster names
python -m hugin.post_s2_workflow process \
    outputs/s2_results/s2_results.json \
    outputs/final_analysis
```

## 7. Configuration Options

### Time Window Configuration
```yaml
data_condensation:
  time_window_minutes: 10          # 10 minutters vinduer
  time_window_minutes: 30          # 30 minutters vinduer
  time_window_minutes: 60          # 1 times vinduer
```

### Clustering Configuration
```yaml
location_clustering:
  radius_meters: 5.0              # 5m radius (10m diameter)
  radius_meters: 10.0             # 10m radius (20m diameter)
  min_points: 1                   # Minimum points per cluster
```

### Output Configuration
```yaml
output:
  unknown_cluster_prefix: "Unknown_Cluster_"  # Prefix for unknown clusters
  decouple_labeling: true          # Decouple labeling from processing
  include_cluster_names: true      # Include cluster names in output
```

## 8. Decoupled Labeling

### Processing vs Labeling
- **Processing** - Automatisk clustering og kondensation
- **Labeling** - Brugeren navngiver clusters manuelt
- **Reporting** - Navne bruges kun til afrapportering

### Workflow Separation
```bash
# 1. Process data (automatisk)
python -m hugin.post_s2_workflow process s2_results.json outputs/analysis

# 2. Request labels (manual)
python -m hugin.post_s2_workflow request-labels --output labels.yaml

# 3. Submit labels (manual)
python -m hugin.post_s2_workflow submit-labels labels.yaml

# 4. Generate reports (med navne)
python -m hugin.post_s2_workflow process s2_results.json outputs/final_reports
```

## 9. Integration med Hugin Ecosystem

### S2 Pipeline Integration
```bash
# S2 pipeline
python -m hugin.s2_pipeline process data/images/ outputs/s2/

# Post-S2 workflow
python -m hugin.post_s2_workflow process outputs/s2/s2_results.json outputs/clusters/

# Analytics
python -m hugin.analytics generate outputs/clusters/ outputs/analytics/

# Export
python -m hugin.export outputs/analytics/ outputs/export/
```

## 10. Tips og Best Practices

1. **Start med automatisk processing** - Lad systemet cluster automatisk
2. **Label unknown clusters** - Navngiv clusters manuelt efter processing
3. **Brug time windows** - Kondenser data i passende time windows
4. **Decouple labeling** - Hold processing og labeling adskilt
5. **Regenerate reports** - Genkør rapporter efter labeling
6. **Backup data** - Tag backup af database før store ændringer

## 11. Troubleshooting

### Common Issues
1. **No GPS data** - Check at S2 results indeholder GPS koordinater
2. **No clusters found** - Check GPS accuracy og clustering radius
3. **Labeling fails** - Check at cluster IDs matcher
4. **Time window issues** - Check timestamp format i S2 results

### Debug Mode
```bash
# Enable verbose logging
python -m hugin.post_s2_workflow process \
    s2_results.json \
    outputs/analysis \
    --verbose
```

Dette workflow giver en komplet løsning til post-S2 processing med decoupled labeling og configurable data condensation.
