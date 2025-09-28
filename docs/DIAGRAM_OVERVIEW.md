# 🎨 Diagram Overview for Odins Ravne

Dette dokument giver en oversigt over alle diagrammer i Odins Ravne systemet.

## 📊 Diagram Statistics

- **Total Diagrams**: 12 PlantUML diagrams
- **Workflow Diagrams**: 6
- **Architecture Diagrams**: 6
- **Formats Supported**: PNG, SVG, PDF, EPS

## 🔄 Workflow Diagrams

### 1. System Workflow (`system_workflow.puml`)
**Formål**: Hovedworkflow for hele systemet
- **Input**: Wildlife Camera Images
- **Process**: Munin → Hugin pipeline
- **Output**: Final Reports with Cluster Names
- **Key Decision**: Positive Observations?

### 2. Munin Workflow (`munin_workflow.puml`)
**Formål**: Munin (Memory Keeper) processing stages
- **Stage 0**: Video Processing
- **Stage 1**: Object Detection
- **Key Decision**: Wildlife Detected?
- **Output**: Positive Observations

### 3. Hugin Workflow (`hugin_workflow.puml`)
**Formål**: Hugin (Thought Bringer) analysis stages
- **Stage 2.1**: Human/Animal Detection
- **Stage 2.2**: Species Detection
- **Stage 2.3**: GPS Clustering
- **Stage 2.4**: Cluster Enrichment

### 4. GPS Clustering (`gps_clustering.puml`)
**Formål**: GPS proximity clustering process
- **Input**: GPS Observations
- **Process**: 5m radius clustering
- **Output**: Enriched Reports
- **User Interaction**: Labeling unknown clusters

### 5. Data Condensation (`data_condensation.puml`)
**Formål**: Data condensation and export
- **Input**: Observations
- **Process**: Time window grouping (10 min)
- **Output**: CSV, JSON, Analytics Reports

### 6. User Labeling (`user_labeling.puml`)
**Formål**: User labeling workflow
- **Input**: Unknown Clusters
- **Process**: YAML template → User edits
- **Output**: Cluster Names
- **Features**: Overlap detection and merging

## 🏗️ Architecture Diagrams

### 7. System Integration (`system_integration.puml`)
**Formål**: System integration overview
- **Odin Infrastructure**: Munin → Hugin → Reports
- **Local Development**: Docker → LocalStack → MinIO → Redis → PostgreSQL
- **Cloud Deployment**: AWS S3 → Batch → ECR → CloudFormation

### 8. Infrastructure Architecture (`infrastructure_architecture.puml`)
**Formål**: Infrastructure component relationships
- **AWS Cloud**: S3, Batch, ECR, CloudFormation, IAM
- **Local Development**: Docker Compose, LocalStack, MinIO, Redis, PostgreSQL
- **Processing**: Odin CLI, Munin Processing, Hugin Analysis

### 9. Data Flow (`data_flow.puml`)
**Formål**: Data flow through the system
- **Input**: Camera Images, Video Files, Image Files
- **Processing**: Munin Stages 0-1, Hugin Stages 2.1-2.4
- **Output**: Final Reports, Cluster Names, Analytics

### 10. Component Architecture (`component_architecture.puml`)
**Formål**: Component relationships and dependencies
- **Odin**: Infrastructure, Pipeline, Cost, Resource Management
- **Munin**: Video Processing, Object Detection, Metadata, Data Ingestion
- **Hugin**: Species Detection, GPS Clustering, Data Condensation, Cluster Enrichment

### 11. Performance Monitoring (`performance_monitoring.puml`)
**Formål**: Monitoring and alerting system
- **Monitoring**: CloudWatch, Cost, Performance, Resource Usage
- **Alerts**: Cost, Performance, Resource Alerts
- **Reporting**: Cost, Performance, Resource Reports

### 12. Deployment Pipeline (`deployment_pipeline.puml`)
**Formål**: CI/CD deployment process
- **Process**: Code Commit → Build → Push → Deploy → Test
- **Decision**: Tests Pass?
- **Success**: Deploy to Production → Monitor → Reports
- **Failure**: Rollback → Fix Issues

## 🎯 Diagram Categories

### **Workflow Diagrams** (Process Flow)
- System Workflow
- Munin Workflow
- Hugin Workflow
- GPS Clustering
- Data Condensation
- User Labeling

### **Architecture Diagrams** (System Structure)
- System Integration
- Infrastructure Architecture
- Data Flow
- Component Architecture
- Performance Monitoring
- Deployment Pipeline

## 🚀 Usage Guide

### Generate All Diagrams
```bash
cd docs/diagrams
./generate_diagrams.sh
```

### Generate Single Diagram
```bash
cd docs/diagrams
./generate_single.sh system_workflow png
./generate_single.sh infrastructure_architecture svg
```

### Available Formats
- **PNG**: Standard bitmap format
- **SVG**: Vector format for web
- **PDF**: Print-ready format
- **EPS**: PostScript format

## 📁 File Structure

```
docs/diagrams/
├── README.md                           # Documentation
├── generate_diagrams.sh                # Generate all diagrams
├── generate_single.sh                  # Generate single diagram
├── system_workflow.puml               # Main system workflow
├── munin_workflow.puml                # Munin processing
├── hugin_workflow.puml                # Hugin analysis
├── gps_clustering.puml                # GPS clustering
├── data_condensation.puml             # Data condensation
├── user_labeling.puml                 # User labeling
├── system_integration.puml            # System integration
├── infrastructure_architecture.puml    # Infrastructure
├── data_flow.puml                     # Data flow
├── component_architecture.puml         # Component architecture
├── performance_monitoring.puml        # Performance monitoring
└── deployment_pipeline.puml           # Deployment pipeline
```

## 🔧 Customization

### Colors and Themes
```plantuml
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
```

### Layout Options
```plantuml
!define DIRECTION top to bottom
!define DIRECTION left to right
!define DIRECTION bottom to top
!define DIRECTION right to left
```

## 📊 Integration

### GitHub Actions
```yaml
name: Generate Diagrams
on: [push, pull_request]
jobs:
  generate-diagrams:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install PlantUML
        run: sudo apt-get install plantuml
      - name: Generate Diagrams
        run: |
          cd docs/diagrams
          ./generate_diagrams.sh
      - name: Upload Diagrams
        uses: actions/upload-artifact@v2
        with:
          name: diagrams
          path: docs/diagrams/*.png
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: plantuml
        name: Generate PlantUML diagrams
        entry: bash -c 'cd docs/diagrams && ./generate_diagrams.sh'
        language: system
        files: 'docs/diagrams/.*\.puml$'
```

## 🎨 Visual Design

### Color Scheme
- **Blue (#E1F5FE)**: Input/Output components
- **Purple (#F3E5F5)**: Processing components
- **Green (#E8F5E8)**: Analysis components
- **Orange (#FFF3E0)**: Decision points
- **Light Green (#C8E6C9)**: Success states

### Layout Principles
- **Top to Bottom**: Main workflow flow
- **Left to Right**: Component relationships
- **Grouped**: Related components in packages
- **Color Coded**: Different types of components

## 📈 Benefits

### **PlantUML Advantages**
- **Text-based**: Version control friendly
- **Multiple formats**: PNG, SVG, PDF, EPS
- **Customizable**: Colors, themes, layouts
- **Integration**: CI/CD, pre-commit hooks
- **Maintainable**: Easy to update and modify

### **Documentation Benefits**
- **Consistent**: All diagrams use same style
- **Comprehensive**: Complete system coverage
- **Accessible**: Multiple formats available
- **Maintainable**: Easy to update
- **Professional**: High-quality output

---

**Diagram Overview Status:** ✅ **ACTIVE**  
**Last Updated:** 2025-09-28  
**Version:** 1.0
