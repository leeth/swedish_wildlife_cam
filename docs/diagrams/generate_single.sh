#!/bin/bash
# Generate single PlantUML diagram script

if [ $# -eq 0 ]; then
    echo "🎨 PlantUML Diagram Generator"
    echo ""
    echo "Usage: $0 <diagram_name> [format]"
    echo ""
    echo "Available diagrams:"
    ls *.puml 2>/dev/null | sed 's/.puml//' | sed 's/^/   /'
    echo ""
    echo "Available formats:"
    echo "   png (default)"
    echo "   svg"
    echo "   pdf"
    echo "   eps"
    echo ""
    echo "Examples:"
    echo "   $0 system_workflow"
    echo "   $0 munin_workflow svg"
    echo "   $0 infrastructure_architecture pdf"
    exit 1
fi

DIAGRAM=$1
FORMAT=${2:-png}

# Check if PlantUML is installed
if ! command -v plantuml &> /dev/null; then
    echo "❌ PlantUML is not installed. Please install it first:"
    echo "   sudo apt-get install plantuml"
    echo "   or"
    echo "   brew install plantuml"
    exit 1
fi

# Check if diagram exists
if [ ! -f "${DIAGRAM}.puml" ]; then
    echo "❌ Diagram $DIAGRAM.puml not found"
    echo ""
    echo "Available diagrams:"
    ls *.puml 2>/dev/null | sed 's/.puml//' | sed 's/^/   /'
    exit 1
fi

# Create output directory
mkdir -p "$FORMAT"

echo "🎨 Generating $DIAGRAM in $FORMAT format..."

# Generate diagram
case $FORMAT in
    png)
        plantuml "${DIAGRAM}.puml" -o "$FORMAT/"
        echo "✅ Generated $DIAGRAM.png"
        ;;
    svg)
        plantuml -tsvg "${DIAGRAM}.puml" -o "$FORMAT/"
        echo "✅ Generated $DIAGRAM.svg"
        ;;
    pdf)
        plantuml -tpdf "${DIAGRAM}.puml" -o "$FORMAT/"
        echo "✅ Generated $DIAGRAM.pdf"
        ;;
    eps)
        plantuml -teps "${DIAGRAM}.puml" -o "$FORMAT/"
        echo "✅ Generated $DIAGRAM.eps"
        ;;
    *)
        echo "❌ Unknown format: $FORMAT"
        echo "Available formats: png, svg, pdf, eps"
        exit 1
        ;;
esac

echo "📁 Output: docs/diagrams/$FORMAT/$DIAGRAM.$FORMAT"
