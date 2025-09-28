# Efficient Cluster Management Guide

Denne guide viser den mest effektive løsning for store datasæt med cluster_id og GPS lokationer.

## 🎯 Problem

Du har:
- **Store Parquet filer** med mange datapunkter og cluster_id
- **Behov for cluster navne** til reporting
- **GPS lokationer** per cluster
- **Mean points** til plotting
- **Ingen genprocessering** af data

## ✅ Løsning

### 1. **Lightweight SQLite Setup**
```sql
-- cluster_names: cluster_id → name
-- cluster_locations: cluster_id → GPS points
-- cluster_means: cluster_id → mean point for plotting
```

### 2. **Fast Lookup System**
- **In-memory cache** for cluster names
- **No reprocessing** af data
- **Minimal overhead** for store datasæt
- **Fast enrichment** til reporting

### 3. **GPS Locations & Mean Points**
- **Alle GPS punkter** per cluster
- **Mean point** (gennemsnit) til plotting
- **Point count** per cluster
- **Export til CSV** for plotting

## 🚀 Brug

### 1. **Setup Cluster Names**
```bash
# Tilføj enkelt cluster navn
python -m hugin.cluster_cli_fast add-name cluster_001 "North Forest"

# Batch tilføj fra JSON
python -m hugin.cluster_cli_fast batch-add-names cluster_names.json
```

### 2. **Extract GPS Locations**
```bash
# Extract GPS locations fra Parquet til SQLite
python -m hugin.cluster_cli_fast extract-locations data.parquet
```

### 3. **Fast Data Enrichment**
```bash
# Enrich data med cluster navne (ingen genprocessering)
python -m hugin.cluster_cli_fast enrich data.parquet enriched_data.csv
```

### 4. **Plotting Data**
```bash
# Export mean points til plotting
python -m hugin.cluster_cli_fast export-means cluster_means.csv

# List alle mean points
python -m hugin.cluster_cli_fast list-means
```

### 5. **Fast Reporting**
```bash
# Generate cluster report
python -m hugin.cluster_cli_fast enrich data.parquet report.csv

# Species analysis
python -m hugin.cluster_cli_fast species-analysis data.parquet species.csv

# Temporal analysis
python -m hugin.cluster_cli_fast temporal-analysis data.parquet temporal.csv
```

## 📊 Data Struktur

### Parquet Data (Store filer)
```python
# Original data med cluster_id
df = pl.read_parquet('data.parquet')
# Columns: observation_id, cluster_id, latitude, longitude, species, confidence, timestamp
```

### SQLite Database (Lille setup)
```sql
-- cluster_names
cluster_id | name
-----------|----------
cluster_001| North Forest
cluster_002| South Meadow

-- cluster_locations  
cluster_id | latitude | longitude
-----------|----------|----------
cluster_001| 59.1234  | 18.5678
cluster_001| 59.1235  | 18.5679

-- cluster_means
cluster_id | mean_latitude | mean_longitude | point_count
-----------|---------------|----------------|------------
cluster_001| 59.1234       | 18.5678        | 15
```

## ⚡ Performance

### **Store Datasæt (1M+ rows)**
- **Memory usage**: Minimal overhead
- **Lookup speed**: O(1) cache lookup
- **Enrichment**: Ingen genprocessering
- **Export**: Fast CSV/Parquet export

### **GPS Locations**
- **Storage**: Efficient SQLite storage
- **Mean calculation**: Automatic per cluster
- **Plotting**: Ready-to-use CSV export

## 🔧 CLI Commands

### **Data Management**
```bash
# Extract locations fra Parquet
python -m hugin.cluster_cli_fast extract-locations data.parquet

# Enrich data med navne
python -m hugin.cluster_cli_fast enrich data.parquet enriched.csv

# Batch enrich multiple files
python -m hugin.cluster_cli_fast batch-enrich input_dir/ output_dir/
```

### **Cluster Names**
```bash
# Add single name
python -m hugin.cluster_cli_fast add-name cluster_001 "North Forest"

# Batch add names
python -m hugin.cluster_cli_fast batch-add-names names.json

# Export names
python -m hugin.cluster_cli_fast export-names names.json

# Import names
python -m hugin.cluster_cli_fast import-names names.json
```

### **GPS Locations**
```bash
# Get locations for cluster
python -m hugin.cluster_cli_fast get-locations cluster_001

# Get mean point for cluster
python -m hugin.cluster_cli_fast get-mean cluster_001

# Export all mean points
python -m hugin.cluster_cli_fast export-means means.csv

# List all mean points
python -m hugin.cluster_cli_fast list-means
```

### **Analysis**
```bash
# Species analysis
python -m hugin.cluster_cli_fast species-analysis data.parquet species.csv

# Temporal analysis
python -m hugin.cluster_cli_fast temporal-analysis data.parquet temporal.csv

# Activity analysis
python -m hugin.cluster_cli_fast activity-analysis data.parquet activity.csv
```

### **Utilities**
```bash
# Show unknown clusters
python -m hugin.cluster_cli_fast unknown-clusters data.parquet

# Show statistics
python -m hugin.cluster_cli_fast stats
```

## 📁 File Structure

```
project/
├── data.parquet              # Store dataset med cluster_id
├── cluster_names.db          # SQLite med navne og GPS
├── enriched_data.csv         # Enriched data med navne
├── cluster_means.csv         # Mean points til plotting
├── species_analysis.csv      # Species analysis
└── temporal_analysis.csv     # Temporal analysis
```

## 🎯 Key Benefits

### **1. Effektivitet**
- **Ingen genprocessering** af store datasæt
- **Fast lookup** med in-memory cache
- **Minimal overhead** for store filer

### **2. GPS Support**
- **Alle GPS punkter** per cluster
- **Mean points** til plotting
- **Point count** per cluster

### **3. Reporting**
- **Fast enrichment** med cluster navne
- **Multiple output formats** (CSV, Parquet, JSON)
- **Analytics** med cluster information

### **4. Skalabilitet**
- **Store datasæt** (1M+ rows)
- **Minimal memory usage**
- **Fast operations**

## 🔄 Workflow

### **1. Initial Setup**
```bash
# Extract GPS locations fra Parquet
python -m hugin.cluster_cli_fast extract-locations data.parquet

# Add cluster names
python -m hugin.cluster_cli_fast batch-add-names names.json
```

### **2. Fast Enrichment**
```bash
# Enrich data med navne (ingen genprocessering)
python -m hugin.cluster_cli_fast enrich data.parquet enriched.csv
```

### **3. Plotting**
```bash
# Export mean points til plotting
python -m hugin.cluster_cli_fast export-means means.csv
```

### **4. Analysis**
```bash
# Generate analytics
python -m hugin.cluster_cli_fast species-analysis data.parquet species.csv
python -m hugin.cluster_cli_fast temporal-analysis data.parquet temporal.csv
```

## 📊 Example Output

### **Cluster Means CSV**
```csv
cluster_id,cluster_name,latitude,longitude,point_count
cluster_001,North Forest,59.1234,18.5678,15
cluster_002,South Meadow,59.2345,18.6789,23
```

### **Enriched Data**
```csv
observation_id,cluster_id,cluster_name,latitude,longitude,species,confidence
obs_0001,cluster_001,North Forest,59.1234,18.5678,moose,0.85
obs_0002,cluster_001,North Forest,59.1235,18.5679,deer,0.92
```

## 🎯 Use Cases

### **1. Wildlife Monitoring**
- **GPS clusters** med dyreaktivitet
- **Mean points** til kortplotting
- **Species analysis** per cluster
- **Temporal patterns** per cluster

### **2. Research**
- **Large datasets** med cluster_id
- **Fast enrichment** til reporting
- **GPS analysis** per cluster
- **Statistical analysis** med cluster navne

### **3. Conservation**
- **Cluster naming** for områder
- **Activity patterns** per cluster
- **Species distribution** per cluster
- **Temporal trends** per cluster

Denne løsning giver dig den mest effektive måde at håndtere store datasæt med cluster_id og GPS lokationer, uden at genprocessere data!
