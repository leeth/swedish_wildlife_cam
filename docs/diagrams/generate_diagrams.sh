#!/bin/bash
# Generate PlantUML diagrams script

echo "🎨 Generating PlantUML diagrams for Odins Ravne..."

# Check if PlantUML is installed
if ! command -v plantuml &> /dev/null; then
    echo "❌ PlantUML is not installed. Please install it first:"
    echo "   sudo apt-get install plantuml"
    echo "   or"
    echo "   brew install plantuml"
    exit 1
fi

# Create output directories
mkdir -p png svg pdf eps

echo "📁 Creating output directories..."

# Generate PNG files
echo "🖼️  Generating PNG files..."
for file in *.puml; do
    if [ -f "$file" ]; then
        echo "   Generating PNG for $file"
        plantuml "$file" -o png/
    fi
done

# Generate SVG files
echo "🎨 Generating SVG files..."
for file in *.puml; do
    if [ -f "$file" ]; then
        echo "   Generating SVG for $file"
        plantuml -tsvg "$file" -o svg/
    fi
done

# Generate PDF files
echo "📄 Generating PDF files..."
for file in *.puml; do
    if [ -f "$file" ]; then
        echo "   Generating PDF for $file"
        plantuml -tpdf "$file" -o pdf/
    fi
done

# Generate EPS files
echo "📐 Generating EPS files..."
for file in *.puml; do
    if [ -f "$file" ]; then
        echo "   Generating EPS for $file"
        plantuml -teps "$file" -o eps/
    fi
done

echo "✅ All diagrams generated successfully!"
echo ""
echo "📊 Generated files:"
echo "   PNG files: $(ls png/ 2>/dev/null | wc -l)"
echo "   SVG files: $(ls svg/ 2>/dev/null | wc -l)"
echo "   PDF files: $(ls pdf/ 2>/dev/null | wc -l)"
echo "   EPS files: $(ls eps/ 2>/dev/null | wc -l)"
echo ""
echo "🎯 Output directories:"
echo "   PNG: docs/diagrams/png/"
echo "   SVG: docs/diagrams/svg/"
echo "   PDF: docs/diagrams/pdf/"
echo "   EPS: docs/diagrams/eps/"
