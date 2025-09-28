# 🎨 PlantUML Diagrams for Odins Ravne

Dette directory indeholder PlantUML diagrammer der konverterer alle Mermaid diagrammer fra dokumentationen.

## 📁 Diagram Files

### Workflow Diagrams
- `system_workflow.puml` - Main system workflow
- `munin_workflow.puml` - Munin (Memory Keeper) workflow
- `hugin_workflow.puml` - Hugin (Thought Bringer) workflow
- `gps_clustering.puml` - GPS clustering workflow
- `data_condensation.puml` - Data condensation workflow
- `user_labeling.puml` - User labeling workflow

### Architecture Diagrams
- `system_integration.puml` - System integration overview
- `infrastructure_architecture.puml` - Infrastructure architecture
- `data_flow.puml` - Data flow architecture
- `component_architecture.puml` - Component architecture
- `performance_monitoring.puml` - Performance monitoring
- `deployment_pipeline.puml` - Deployment pipeline

## 🚀 Usage

### Online PlantUML Viewer
1. Gå til [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
2. Kopier PlantUML koden fra en `.puml` fil
3. Indsæt koden i textarea'en
4. Klik "Submit" for at generere diagrammet

### Local PlantUML Installation
```bash
# Install PlantUML
sudo apt-get install plantuml

# Generate PNG from PlantUML file
plantuml system_workflow.puml

# Generate SVG from PlantUML file
plantuml -tsvg system_workflow.puml

# Generate all diagrams
./generate_diagrams.sh
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

## 📊 Generated Output

Alle diagrammer kan genereres i følgende formater:
- **PNG** - Standard bitmap format
- **SVG** - Vector format for web
- **PDF** - Print-ready format
- **EPS** - PostScript format

## 🔧 Scripts

### Generate All Diagrams
```bash
#!/bin/bash
# generate_diagrams.sh

echo "Generating PlantUML diagrams..."

# Generate PNG files
for file in *.puml; do
    echo "Generating PNG for $file"
    plantuml "$file"
done

# Generate SVG files
for file in *.puml; do
    echo "Generating SVG for $file"
    plantuml -tsvg "$file"
done

echo "All diagrams generated!"
```

### Generate Specific Diagram
```bash
#!/bin/bash
# generate_single.sh

if [ $# -eq 0 ]; then
    echo "Usage: $0 <diagram_name>"
    echo "Available diagrams:"
    ls *.puml | sed 's/.puml//'
    exit 1
fi

DIAGRAM=$1
if [ -f "${DIAGRAM}.puml" ]; then
    echo "Generating $DIAGRAM..."
    plantuml "${DIAGRAM}.puml"
    plantuml -tsvg "${DIAGRAM}.puml"
    echo "Generated $DIAGRAM.png and $DIAGRAM.svg"
else
    echo "Diagram $DIAGRAM.puml not found"
    exit 1
fi
```

## 📋 Integration

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

---

**PlantUML Diagrams Status:** ✅ **ACTIVE**  
**Last Updated:** 2025-09-28  
**Version:** 1.0
