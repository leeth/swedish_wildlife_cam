# GPS Cluster Tagging Workflow

Dette guide viser hvordan man bruger det nye cluster tagging system til at navngive og merge GPS clusters.

## Workflow Overview

1. **Request Unknown Clusters** - Få liste af clusters der mangler navn
2. **Submit Names** - Send tilbage navngivne clusters
3. **Detect Overlaps** - Find overlappende clusters
4. **Merge Clusters** - Slå overlappende clusters sammen
5. **Track Changes** - Se ændringer siden sidste check

## 1. Request Unknown Clusters

Få en liste af clusters der mangler navn:

```bash
# Request unknown clusters
python -m hugin.cluster_cli request-unknown --limit 50 --min-points 2

# Save to YAML file for editing
python -m hugin.cluster_cli request-unknown --limit 50 --output unknown_clusters.yaml
```

**Output:**
```
Found 5 unknown clusters (filtered from 8 total)
  cluster_123 - 3 points at (55.6761, 12.5683)
  cluster_456 - 2 points at (55.6800, 12.5700)
  cluster_789 - 2 points at (55.6900, 12.5800)
  cluster_101 - 1 points at (55.7000, 12.5900)
```

## 2. Create Tagging Template

Opret en template til at navngive clusters:

```bash
# Create template with current unknown clusters
python -m hugin.cluster_cli create-template tagging_template.yaml
```

Dette opretter en YAML fil med unknown clusters der kan redigeres:

```yaml
tagging_workflow:
  version: "1.0"
  created_at: "2024-01-15T10:00:00Z"
  description: "Cluster tagging workflow template"

unknown_clusters:
  request_id: "unknown_20240115_100000"
  clusters:
    - cluster_id: "cluster_123"
      suggested_name: ""  # Fill in name
      description: ""    # Fill in description
      notes: ""          # Optional notes
    - cluster_id: "cluster_456"
      suggested_name: ""
      description: ""
      notes: ""
```

## 3. Submit Cluster Names

Efter at have redigeret YAML filen, submit navnene:

```bash
# Submit names from YAML file
python -m hugin.cluster_cli submit-names tagging_template.yaml
```

**Output:**
```
✅ Processed 4 changes from tagging_template.yaml
  Named: 4
  Failed: 0
```

## 4. Detect Overlapping Clusters

Find clusters der overlapper og muligvis skal merges:

```bash
# Detect overlaps within 10m
python -m hugin.cluster_cli detect-overlaps --threshold 10.0
```

**Output:**
```
Found 2 overlapping groups with 4 total clusters
  Group overlap_0: 2 clusters (distance: 8.5m)
    cluster_123 - Deer Feeding Area - 3 points
    cluster_456 - Fox Den Area - 2 points
  Group overlap_1: 2 clusters (distance: 12.3m)
    cluster_789 - Wild Boar Wallow - 2 points
    cluster_101 - Fox Hunting Ground - 1 points
```

## 5. Merge Overlapping Clusters

Opret merge requests i YAML format:

```yaml
merge_requests:
  description: "Clusters that overlap and should be merged"
  merges:
    - cluster_ids: ["cluster_123", "cluster_456"]
      new_name: "Wildlife Activity Zone"
      new_description: "Combined deer and fox activity area"
      reason: "Clusters are within 10m of each other"
```

Kør merge:

```bash
# Merge clusters from YAML file
python -m hugin.cluster_cli merge-clusters merge_requests.yaml
```

**Output:**
```
✅ Processed merge requests from merge_requests.yaml
  Successful merges: 2
  Failed merges: 0
```

## 6. Track Changes

Se ændringer siden sidste check:

```bash
# Get changes since last check
python -m hugin.cluster_cli changes

# Get changes since specific timestamp
python -m hugin.cluster_cli changes --since "2024-01-15T09:00:00Z"
```

**Output:**
```
Changes since 2024-01-15T09:00:00Z:
  Newly named clusters: 4
  Overlapping groups: 2
  Recently named clusters:
    cluster_123 - Deer Feeding Area - 3 points
    cluster_456 - Fox Den Area - 2 points
    cluster_789 - Wild Boar Wallow - 2 points
    cluster_101 - Fox Hunting Ground - 1 points
```

## Complete Workflow Example

### Step 1: Request Unknown Clusters
```bash
python -m hugin.cluster_cli request-unknown --limit 20 --output unknown.yaml
```

### Step 2: Edit YAML File
Rediger `unknown.yaml` og tilføj navne:

```yaml
unknown_clusters:
  clusters:
    - cluster_id: "cluster_123"
      suggested_name: "Deer Feeding Area"
      description: "Main deer feeding location"
      notes: "High activity area"
    - cluster_id: "cluster_456"
      suggested_name: "Fox Den Area"
      description: "Red fox denning area"
      notes: "Consistent fox activity"
```

### Step 3: Submit Names
```bash
python -m hugin.cluster_cli submit-names unknown.yaml
```

### Step 4: Check for Overlaps
```bash
python -m hugin.cluster_cli detect-overlaps --threshold 15.0
```

### Step 5: Create Merge Requests (if needed)
```yaml
merge_requests:
  merges:
    - cluster_ids: ["cluster_123", "cluster_456"]
      new_name: "Wildlife Activity Zone"
      new_description: "Combined deer and fox area"
```

### Step 6: Apply Merges
```bash
python -m hugin.cluster_cli merge-clusters merge_requests.yaml
```

### Step 7: Check Results
```bash
python -m hugin.cluster_cli stats
python -m hugin.cluster_cli changes
```

## YAML File Structure

### Unknown Clusters Request
```yaml
tagging_workflow:
  version: "1.0"
  created_at: "2024-01-15T10:00:00Z"

unknown_clusters:
  request_id: "unknown_20240115_100000"
  timestamp: "2024-01-15T10:00:00Z"
  total_unknown: 5
  filtered_count: 5
  clusters:
    - cluster_id: "cluster_123"
      center_latitude: 55.6761
      center_longitude: 12.5683
      point_count: 3
      first_seen: "2024-01-15T08:30:00Z"
      last_seen: "2024-01-15T09:15:00Z"
      sample_observations: ["obs_001", "obs_002", "obs_003"]
      suggested_name: ""  # Fill this in
      description: ""     # Fill this in
      notes: ""          # Optional
```

### Merge Requests
```yaml
merge_requests:
  description: "Clusters that overlap and should be merged"
  merges:
    - cluster_ids: ["cluster_123", "cluster_456"]
      new_name: "Wildlife Activity Zone"
      new_description: "Combined deer and fox activity area"
      reason: "Clusters are within 10m of each other"
```

## Database

Alle ændringer gemmes i SQLite database (`clusters.db` by default):

- **gps_clusters** - Cluster information med navne
- **gps_cluster_assignments** - Point assignments til clusters
- **Change tracking** - Automatisk tracking af ændringer

Database filer er ekskluderet fra Git via `.gitignore`.

## Tips

1. **Start med høj-aktivitet clusters** - Navngiv clusters med flest points først
2. **Brug beskrivende navne** - "Deer Feeding Area" er bedre end "Cluster 1"
3. **Check overlaps regelmæssigt** - Merge overlappende clusters
4. **Brug notes feltet** - Tilføj ekstra information om clusters
5. **Backup database** - Tag backup af `clusters.db` før store ændringer
