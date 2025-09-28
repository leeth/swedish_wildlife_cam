# 🎨 PlantUML Diagrams for Odins Ravne

Dette dokument indeholder PlantUML diagrammer der konverterer alle Mermaid diagrammer fra dokumentationen.

## 🔄 System Workflow

### Main System Workflow
```plantuml
@startuml System Workflow
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:Wildlife Camera Images;
:Munin Stage 0: Video Processing;
:Munin Stage 1: Object Detection;
if (Positive Observations?) then (Yes)
    :Hugin Stage 2.1: Human/Animal Detection;
    :Hugin Stage 2.2: Species Detection;
    :Hugin Stage 2.3: GPS Clustering;
    :Hugin Stage 2.4: Cluster Enrichment;
    :Final Reports with Cluster Names;
    stop
else (No)
    :End: No Wildlife;
    stop
endif

note right
    User Labeling
    ↓
    Cluster Names
    ↓
    Cluster Enrichment
end note
@enduml
```

### Munin (Memory Keeper) - Stages 0-1
```plantuml
@startuml Munin Workflow
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #C8E6C9
    BorderColor #388E3C
    FontColor #000000
}

start
:Camera Images/Video;
:Stage 0: Video Processing;
:Frame Extraction;
:EXIF Metadata Processing;
:Stage 1: Object Detection;
:Swedish Wildlife Detector;
if (Wildlife Detected?) then (Yes)
    :Positive Observations;
    :Munin Complete;
    :Pass to Hugin;
    stop
else (No)
    :No Wildlife - End;
    stop
endif
@enduml
```

### Hugin (Thought Bringer) - Stages 2.1-2.4
```plantuml
@startuml Hugin Workflow
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E8F5E8
    BorderColor #4CAF50
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:Munin Results;
:Stage 2.1: Human/Animal Detection;
if (Is Animal?) then (Yes)
    :Stage 2.2: Species Detection;
    :Species Classification;
    :Stage 2.3: GPS Clustering;
    :Location Clustering 5m radius;
    :Data Condensation;
    :Time Windows 10min;
    :Stage 2.4: Cluster Enrichment;
    :User Labeling;
    :Cluster Names;
    :Final Reports;
    stop
else (No)
    :Human - Skip;
    stop
endif
@enduml
```

## 🗺️ GPS Clustering Workflow

```plantuml
@startuml GPS Clustering
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E8F5E8
    BorderColor #4CAF50
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:GPS Observations;
:Proximity Clustering;
:5m Radius Clusters;
:Unknown Clusters;
:User Labeling;
:Cluster Names;
:Enriched Reports;

note right
    Overlap Detection
    ↓
    Merge Clusters
    ↓
    New Cluster Names
    ↓
    Cluster Names
end note
@enduml
```

## 📊 Data Condensation Workflow

```plantuml
@startuml Data Condensation
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E8F5E8
    BorderColor #4CAF50
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:Observations;
:Time Window Grouping;
:10 Minute Windows;
:Species Counting;
:Activity Patterns;
:Condensed Data;
fork
    :CSV Export;
fork again
    :JSON Export;
fork again
    :Analytics Reports;
end fork
stop
@enduml
```

## 🏷️ User Labeling Workflow

```plantuml
@startuml User Labeling
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E8F5E8
    BorderColor #4CAF50
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:Unknown Clusters;
:Request Labels;
:YAML Template;
:User Edits;
:Submit Labels;
:Cluster Names;
:Enriched Reports;

note right
    Overlap Detection
    ↓
    Merge Requests
    ↓
    User Approval
    ↓
    Merged Clusters
    ↓
    New Names
    ↓
    Cluster Names
end note
@enduml
```

## 🏗️ System Integration

```plantuml
@startuml System Integration
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}

package "Odin Infrastructure" {
    [Odin Infrastructure] --> [Munin Processing]
    [Munin Processing] --> [Hugin Analysis]
    [Hugin Analysis] --> [Final Reports]
}

package "Local Development" {
    [Local Development] --> [Docker Compose]
    [Docker Compose] --> [LocalStack]
    [LocalStack] --> [MinIO]
    [MinIO] --> [Redis]
    [Redis] --> [PostgreSQL]
}

package "Cloud Deployment" {
    [Cloud Deployment] --> [AWS S3]
    [AWS S3] --> [AWS Batch]
    [AWS Batch] --> [AWS ECR]
    [AWS ECR] --> [CloudFormation]
}
@enduml
```

## 🏗️ Infrastructure Architecture

```plantuml
@startuml Infrastructure Architecture
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}

package "AWS Cloud" {
    [AWS S3] as S3
    [AWS Batch] as Batch
    [AWS ECR] as ECR
    [CloudFormation] as CF
    [AWS IAM] as IAM
}

package "Local Development" {
    [Docker Compose] as DC
    [LocalStack] as LS
    [MinIO] as MinIO
    [Redis] as Redis
    [PostgreSQL] as PG
}

package "Processing Components" {
    [Odin CLI] as Odin
    [Munin Processing] as Munin
    [Hugin Analysis] as Hugin
}

S3 --> Batch
Batch --> ECR
ECR --> CF
CF --> IAM

DC --> LS
LS --> MinIO
MinIO --> Redis
Redis --> PG

Odin --> Munin
Munin --> Hugin
@enduml
```

## 📊 Data Flow Architecture

```plantuml
@startuml Data Flow
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}

package "Input" {
    [Wildlife Camera Images] as Input
    [Video Files] as Video
    [Image Files] as Images
}

package "Processing" {
    [Munin Stage 0] as M0
    [Munin Stage 1] as M1
    [Hugin Stage 2.1] as H1
    [Hugin Stage 2.2] as H2
    [Hugin Stage 2.3] as H3
    [Hugin Stage 2.4] as H4
}

package "Output" {
    [Final Reports] as Output
    [Cluster Names] as Clusters
    [Analytics] as Analytics
}

Input --> M0
Video --> M0
Images --> M0
M0 --> M1
M1 --> H1
H1 --> H2
H2 --> H3
H3 --> H4
H4 --> Output
H4 --> Clusters
H4 --> Analytics
@enduml
```

## 🔧 Component Architecture

```plantuml
@startuml Component Architecture
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}

package "Odin (All-Father)" {
    [Infrastructure Management] as Infra
    [Pipeline Orchestration] as Pipeline
    [Cost Optimization] as Cost
    [Resource Management] as Resource
}

package "Munin (Memory Keeper)" {
    [Video Processing] as Video
    [Object Detection] as Detection
    [Metadata Processing] as Metadata
    [Data Ingestion] as Ingestion
}

package "Hugin (Thought Bringer)" {
    [Species Detection] as Species
    [GPS Clustering] as GPS
    [Data Condensation] as Condensation
    [Cluster Enrichment] as Enrichment
}

package "Infrastructure" {
    [AWS Services] as AWS
    [Local Services] as Local
    [Docker Containers] as Docker
}

Infra --> Video
Pipeline --> Detection
Cost --> Species
Resource --> GPS

Video --> AWS
Detection --> Local
Species --> Docker
GPS --> AWS
@enduml
```

## 📈 Performance Monitoring

```plantuml
@startuml Performance Monitoring
!theme plain
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
    FontColor #000000
}

package "Monitoring" {
    [CloudWatch] as CW
    [Cost Monitoring] as Cost
    [Performance Metrics] as Perf
    [Resource Usage] as Resource
}

package "Alerts" {
    [Cost Alerts] as CostAlert
    [Performance Alerts] as PerfAlert
    [Resource Alerts] as ResourceAlert
}

package "Reporting" {
    [Cost Reports] as CostReport
    [Performance Reports] as PerfReport
    [Resource Reports] as ResourceReport
}

CW --> Cost
CW --> Perf
CW --> Resource

Cost --> CostAlert
Perf --> PerfAlert
Resource --> ResourceAlert

CostAlert --> CostReport
PerfAlert --> PerfReport
ResourceAlert --> ResourceReport
@enduml
```

## 🚀 Deployment Pipeline

```plantuml
@startuml Deployment Pipeline
!theme plain
skinparam backgroundColor #FFFFFF
skinparam activity {
    BackgroundColor #E1F5FE
    BorderColor #1976D2
    FontColor #000000
}
skinparam activityDiamond {
    BackgroundColor #FFF3E0
    BorderColor #F57C00
    FontColor #000000
}

start
:Code Commit;
:Build Docker Images;
:Push to ECR;
:Deploy Infrastructure;
:Run Tests;
if (Tests Pass?) then (Yes)
    :Deploy to Production;
    :Monitor Performance;
    :Generate Reports;
    stop
else (No)
    :Rollback;
    :Fix Issues;
    stop
endif
@enduml
```

## 📋 Usage Instructions

### Online PlantUML Viewer
1. Gå til [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
2. Kopier PlantUML koden fra ovenstående diagrammer
3. Indsæt koden i textarea'en
4. Klik "Submit" for at generere diagrammet

### Local PlantUML Installation
```bash
# Install PlantUML
sudo apt-get install plantuml

# Generate PNG from PlantUML file
plantuml diagram.puml

# Generate SVG from PlantUML file
plantuml -tsvg diagram.puml
```

### VS Code Extension
1. Installer "PlantUML" extension i VS Code
2. Åbn PlantUML filer med `.puml` extension
3. Brug `Alt+D` for at preview diagrammet

## 🎨 Customization

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

---

**PlantUML Diagrams Status:** ✅ **ACTIVE**  
**Last Updated:** 2025-09-28  
**Version:** 1.0
