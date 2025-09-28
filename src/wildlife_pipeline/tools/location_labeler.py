#!/usr/bin/env python3
"""
Interactive Location Labeling Tool

This tool helps identify and label unknown locations from wildlife camera images.
It provides an interactive interface to:
- View unknown locations on a map
- Create new location labels
- Batch process multiple locations
- Export/import location data
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser
import tempfile
from datetime import datetime

from .location_classifier import LocationClassifier, Location


class InteractiveLocationLabeler:
    """Interactive tool for labeling unknown locations."""
    
    def __init__(self, db_path: Path):
        self.classifier = LocationClassifier(db_path)
        self.db_path = db_path
    
    def show_unknown_locations(self, limit: int = 20) -> List[Dict]:
        """Show unknown locations that need review."""
        unknown_locations = self.classifier.get_unknown_locations()
        
        print(f"\n❓ Unknown Locations ({len(unknown_locations)} total):")
        print("=" * 60)
        
        for i, location in enumerate(unknown_locations[:limit]):
            print(f"\n{i+1}. Image: {Path(location['image_path']).name}")
            print(f"   Path: {location['image_path']}")
            print(f"   GPS: {location['latitude']:.6f}, {location['longitude']:.6f}")
            print(f"   SD Card: {location['sd_card']}")
            print(f"   Date: {location['created_at']}")
        
        if len(unknown_locations) > limit:
            print(f"\n... and {len(unknown_locations) - limit} more")
        
        return unknown_locations[:limit]
    
    def create_location_interactive(self, image_path: str) -> Optional[str]:
        """Interactively create a location from an image."""
        print(f"\n📍 Creating location for: {Path(image_path).name}")
        
        # Get image GPS data
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM image_locations WHERE image_path = ?
            """, (image_path,))
            
            row = cursor.fetchone()
            if not row:
                print(f"❌ Image location not found: {image_path}")
                return None
            
            image_data = dict(row)
        
        print(f"GPS Coordinates: {image_data['latitude']:.6f}, {image_data['longitude']:.6f}")
        
        # Get location name
        while True:
            location_name = input("\n🏷️  Enter location name: ").strip()
            if location_name:
                break
            print("❌ Location name cannot be empty")
        
        # Get description
        description = input("📝 Enter description (optional): ").strip()
        
        # Confirm creation
        print(f"\n📋 Location Details:")
        print(f"  Name: {location_name}")
        print(f"  Description: {description or '(none)'}")
        print(f"  GPS: {image_data['latitude']:.6f}, {image_data['longitude']:.6f}")
        
        confirm = input("\n✅ Create this location? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            location_id = self.classifier.create_location_from_unknown(
                image_path, location_name, description
            )
            print(f"✅ Created location: {location_name} (ID: {location_id})")
            return location_id
        else:
            print("❌ Location creation cancelled")
            return None
    
    def batch_create_locations(self, locations_data: List[Dict]) -> int:
        """Batch create locations from a list of data."""
        created_count = 0
        
        for location_data in locations_data:
            try:
                location_id = self.classifier.create_location_from_unknown(
                    location_data['image_path'],
                    location_data['name'],
                    location_data.get('description', '')
                )
                print(f"✅ Created: {location_data['name']} (ID: {location_id})")
                created_count += 1
            except Exception as e:
                print(f"❌ Error creating {location_data['name']}: {e}")
        
        return created_count
    
    def show_location_map(self, image_path: str) -> None:
        """Show location on a map using GPS coordinates."""
        # Get GPS coordinates
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT latitude, longitude FROM image_locations WHERE image_path = ?
            """, (image_path,))
            
            row = cursor.fetchone()
            if not row:
                print(f"❌ GPS coordinates not found for: {image_path}")
                return
            
            lat, lon = row['latitude'], row['longitude']
        
        # Create map URL
        map_url = f"https://www.google.com/maps?q={lat},{lon}"
        
        print(f"\n🗺️  Opening map for: {Path(image_path).name}")
        print(f"GPS: {lat:.6f}, {lon:.6f}")
        print(f"Map URL: {map_url}")
        
        # Try to open in browser
        try:
            webbrowser.open(map_url)
            print("✅ Map opened in browser")
        except Exception as e:
            print(f"⚠️  Could not open browser: {e}")
            print(f"Please open manually: {map_url}")
    
    def export_unknown_locations(self, output_file: Path) -> None:
        """Export unknown locations to JSON for external processing."""
        unknown_locations = self.classifier.get_unknown_locations()
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "unknown_locations": unknown_locations
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📤 Exported {len(unknown_locations)} unknown locations to {output_file}")
    
    def import_location_labels(self, input_file: Path) -> int:
        """Import location labels from JSON file."""
        with open(input_file, 'r') as f:
            import_data = json.load(f)
        
        locations_to_create = import_data.get('locations', [])
        
        if not locations_to_create:
            print("❌ No locations found in import file")
            return 0
        
        print(f"📥 Found {len(locations_to_create)} locations to import")
        
        # Show preview
        print("\n📋 Import Preview:")
        for i, location in enumerate(locations_to_create[:5]):
            print(f"  {i+1}. {location['name']} - {location.get('description', '')}")
        
        if len(locations_to_create) > 5:
            print(f"  ... and {len(locations_to_create) - 5} more")
        
        confirm = input(f"\n✅ Import {len(locations_to_create)} locations? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            created_count = self.batch_create_locations(locations_to_create)
            print(f"✅ Imported {created_count} locations")
            return created_count
        else:
            print("❌ Import cancelled")
            return 0
    
    def interactive_mode(self) -> None:
        """Run in interactive mode."""
        print("🏷️  Interactive Location Labeler")
        print("=" * 40)
        
        while True:
            print("\n📋 Available actions:")
            print("  1. Show unknown locations")
            print("  2. Create location from image")
            print("  3. Show location on map")
            print("  4. Export unknown locations")
            print("  5. Import location labels")
            print("  6. Show statistics")
            print("  7. Exit")
            
            choice = input("\n🔢 Choose action (1-7): ").strip()
            
            if choice == "1":
                limit = input("📊 Number of locations to show (default 20): ").strip()
                limit = int(limit) if limit.isdigit() else 20
                self.show_unknown_locations(limit)
            
            elif choice == "2":
                image_path = input("📁 Enter image path: ").strip()
                if image_path:
                    self.create_location_interactive(image_path)
                else:
                    print("❌ Image path cannot be empty")
            
            elif choice == "3":
                image_path = input("📁 Enter image path: ").strip()
                if image_path:
                    self.show_location_map(image_path)
                else:
                    print("❌ Image path cannot be empty")
            
            elif choice == "4":
                output_file = input("📤 Enter output file path: ").strip()
                if output_file:
                    self.export_unknown_locations(Path(output_file))
                else:
                    print("❌ Output file path cannot be empty")
            
            elif choice == "5":
                input_file = input("📥 Enter input file path: ").strip()
                if input_file and Path(input_file).exists():
                    self.import_location_labels(Path(input_file))
                else:
                    print("❌ Input file not found or path empty")
            
            elif choice == "6":
                stats = self.classifier.get_statistics()
                print(f"\n📊 Statistics:")
                print(f"  Total images: {stats['total_images']}")
                print(f"  Classified: {stats['classified_images']}")
                print(f"  Unknown: {stats['unknown_locations']}")
                print(f"  Classification rate: {stats['classification_rate']:.1%}")
            
            elif choice == "7":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-7.")


def main():
    """Main CLI for interactive location labeling."""
    parser = argparse.ArgumentParser(description="Interactive Location Labeling Tool")
    parser.add_argument("--db", default="./location_classifier.db", help="SQLite database path")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Show unknown locations
    show_parser = subparsers.add_parser("show", help="Show unknown locations")
    show_parser.add_argument("--limit", type=int, default=20, help="Limit number of results")
    
    # Create location
    create_parser = subparsers.add_parser("create", help="Create location from image")
    create_parser.add_argument("image_path", help="Image path")
    create_parser.add_argument("--name", help="Location name")
    create_parser.add_argument("--description", help="Location description")
    
    # Show map
    map_parser = subparsers.add_parser("map", help="Show location on map")
    map_parser.add_argument("image_path", help="Image path")
    
    # Export/Import
    export_parser = subparsers.add_parser("export", help="Export unknown locations")
    export_parser.add_argument("output_file", help="Output JSON file")
    
    import_parser = subparsers.add_parser("import", help="Import location labels")
    import_parser.add_argument("input_file", help="Input JSON file")
    
    # Statistics
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    # Initialize labeler
    db_path = Path(args.db)
    labeler = InteractiveLocationLabeler(db_path)
    
    # Run interactive mode if requested
    if args.interactive or not args.command:
        labeler.interactive_mode()
        return
    
    # Execute command
    if args.command == "show":
        labeler.show_unknown_locations(args.limit)
    
    elif args.command == "create":
        if args.name:
            # Non-interactive creation
            location_id = labeler.classifier.create_location_from_unknown(
                args.image_path, args.name, args.description or ""
            )
            print(f"✅ Created location: {args.name} (ID: {location_id})")
        else:
            # Interactive creation
            labeler.create_location_interactive(args.image_path)
    
    elif args.command == "map":
        labeler.show_location_map(args.image_path)
    
    elif args.command == "export":
        labeler.export_unknown_locations(Path(args.output_file))
    
    elif args.command == "import":
        labeler.import_location_labels(Path(args.input_file))
    
    elif args.command == "stats":
        stats = labeler.classifier.get_statistics()
        print(f"\n📊 Statistics:")
        print(f"  Total images: {stats['total_images']}")
        print(f"  Classified: {stats['classified_images']}")
        print(f"  Unknown: {stats['unknown_locations']}")
        print(f"  Classification rate: {stats['classification_rate']:.1%}")


if __name__ == "__main__":
    main()
