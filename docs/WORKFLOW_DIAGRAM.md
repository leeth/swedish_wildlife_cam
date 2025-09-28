# Odins Ravne Workflow Diagram

Dette dokument indeholder det komplette workflow diagram for Odins Ravne systemet.

## System Overview

```mermaid
graph TD
    A[Wildlife Camera Images] --> B[Munin Stage 0: Video Processing]
    B --> C[Munin Stage 1: Object Detection]
    C --> D{Positive Observations?}
    D -->|Yes| E[Hugin Stage 2.1: Human/Animal Detection]
    D -->|No| F[End: No Wildlife]
    
    E --> G[Hugin Stage 2.2: Species Detection]
    G --> H[Hugin Stage 2.3: GPS Clustering]
    H --> I[Hugin Stage 2.4: Cluster Enrichment]
    I --> J[Final Reports with Cluster Names]
    
    K[User Labeling] --> L[Cluster Names]
    L --> I
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#f3e5f5
    style E fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#e8f5e8
    style I fill:#e8f5e8
    style J fill:#fff3e0
```

## Detailed Workflow

### Munin (Memory Keeper) - Stages 0-1

```mermaid
graph TD
    A[Camera Images/Video] --> B[Stage 0: Video Processing]
    B --> C[Frame Extraction]
    C --> D[EXIF Metadata Processing]
    D --> E[Stage 1: Object Detection]
    E --> F[Swedish Wildlife Detector]
    F --> G{Wildlife Detected?}
    G -->|Yes| H[Positive Observations]
    G -->|No| I[No Wildlife - End]
    
    H --> J[Munin Complete]
    J --> K[Pass to Hugin]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#f3e5f5
    style D fill:#f3e5f5
    style E fill:#f3e5f5
    style F fill:#f3e5f5
    style H fill:#c8e6c9
    style J fill:#c8e6c9
    style K fill:#c8e6c9
```

### Hugin (Thought Bringer) - Stages 2.1-2.4

```mermaid
graph TD
    A[Munin Results] --> B[Stage 2.1: Human/Animal Detection]
    B --> C{Is Animal?}
    C -->|Yes| D[Stage 2.2: Species Detection]
    C -->|No| E[Human - Skip]
    
    D --> F[Species Classification]
    F --> G[Stage 2.3: GPS Clustering]
    G --> H[Location Clustering 5m radius]
    H --> I[Data Condensation]
    I --> J[Time Windows 10min]
    J --> K[Stage 2.4: Cluster Enrichment]
    K --> L[User Labeling]
    L --> M[Cluster Names]
    M --> N[Final Reports]
    
    style A fill:#e1f5fe
    style B fill:#e8f5e8
    style D fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#e8f5e8
    style I fill:#e8f5e8
    style J fill:#e8f5e8
    style K fill:#e8f5e8
    style L fill:#fff3e0
    style M fill:#fff3e0
    style N fill:#fff3e0
```

## GPS Clustering Workflow

```mermaid
graph TD
    A[GPS Observations] --> B[Proximity Clustering]
    B --> C[5m Radius Clusters]
    C --> D[Unknown Clusters]
    D --> E[User Labeling]
    E --> F[Cluster Names]
    F --> G[Enriched Reports]
    
    H[Overlap Detection] --> I[Merge Clusters]
    I --> J[New Cluster Names]
    J --> F
    
    style A fill:#e1f5fe
    style B fill:#e8f5e8
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#fff3e0
    style G fill:#fff3e0
    style H fill:#ffecb3
    style I fill:#ffecb3
    style J fill:#ffecb3
```

## Data Condensation Workflow

```mermaid
graph TD
    A[Observations] --> B[Time Window Grouping]
    B --> C[10 Minute Windows]
    C --> D[Species Counting]
    D --> E[Activity Patterns]
    E --> F[Condensed Data]
    F --> G[CSV Export]
    F --> H[JSON Export]
    F --> I[Analytics Reports]
    
    style A fill:#e1f5fe
    style B fill:#e8f5e8
    style C fill:#e8f5e8
    style D fill:#e8f5e8
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#fff3e0
    style H fill:#fff3e0
    style I fill:#fff3e0
```

## User Labeling Workflow

```mermaid
graph TD
    A[Unknown Clusters] --> B[Request Labels]
    B --> C[YAML Template]
    C --> D[User Edits]
    D --> E[Submit Labels]
    E --> F[Cluster Names]
    F --> G[Enriched Reports]
    
    H[Overlap Detection] --> I[Merge Requests]
    I --> J[User Approval]
    J --> K[Merged Clusters]
    K --> L[New Names]
    L --> F
    
    style A fill:#e1f5fe
    style B fill:#e8f5e8
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#e8f5e8
    style F fill:#fff3e0
    style G fill:#fff3e0
    style H fill:#ffecb3
    style I fill:#ffecb3
    style J fill:#fff3e0
    style K fill:#ffecb3
    style L fill:#fff3e0
```

## System Integration

```mermaid
graph TD
    A[Odin Infrastructure] --> B[Munin Processing]
    B --> C[Hugin Analysis]
    C --> D[Final Reports]
    
    E[Local Development] --> F[Docker Compose]
    F --> G[LocalStack]
    G --> H[MinIO]
    H --> I[Redis]
    I --> J[PostgreSQL]
    
    K[Cloud Deployment] --> L[AWS S3]
    L --> M[AWS Batch]
    M --> N[AWS ECR]
    N --> O[CloudFormation]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#e1f5fe
    style F fill:#f3e5f5
    style G fill:#f3e5f5
    style H fill:#f3e5f5
    style I fill:#f3e5f5
    style J fill:#f3e5f5
    style K fill:#e1f5fe
    style L fill:#f3e5f5
    style M fill:#f3e5f5
    style N fill:#f3e5f5
    style O fill:#f3e5f5
```

## Key Features

### Munin (Memory Keeper)
- **Stage 0**: Video frame ekstraktion og analyse
- **Stage 1**: Objekt detektion (positive observations)
- **Done**: Munin er færdig når der er konstateret positive observations

### Hugin (Thought Bringer)
- **Stage 2.1**: Menneske eller dyr detection
- **Stage 2.2**: Species detection (hvilket dyr)
- **Stage 2.3**: Dan cluster og data observations
- **Stage 2.4**: Berig med cluster navn for pretty reporting

### Key Technologies
- **GPS Clustering**: 5m radius proximity clustering
- **Data Condensation**: Configurable time windows (10 min default)
- **Decoupled Labeling**: User naming separate from processing
- **YAML Workflows**: Configuration-driven processing
- **Cluster Analytics**: Species and temporal analysis by cluster
