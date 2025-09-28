#!/usr/bin/env python3
"""
Location Classification Tool for Wildlife Camera Images

This tool helps classify and organize wildlife camera images by location:
- Moves images to cloud storage with SD card folder structure
- Classifies locations within 10m radius
- Identifies unknown locations for manual labeling
- Stores location mappings in SQLite database
- Shares location labels via Git
"""

import argparse
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil
import subprocess
import tempfile

from ..metadata import get_gps_from_exif, get_timestamp_from_exif
from ..cloud.storage import create_storage_adapter
from ..cloud.interfaces import StorageLocation


@dataclass
class Location:
    """Location data structure."""
    id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: float = 10.0
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ImageLocation:
    """Image location mapping."""
    image_path: str
    sd_card: str
    location_id: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    distance_meters: Optional[float]
    needs_review: bool = False
    created_at: str = ""


class LocationClassifier:
    """Location classification and image organization tool."""
    
    def __init__(self, db_path: Path, storage_adapter=None):
        self.db_path = db_path
        self.storage_adapter = storage_adapter
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with location tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Locations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    radius_meters REAL DEFAULT 10.0,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Image locations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    sd_card TEXT NOT NULL,
                    location_id TEXT,
                    latitude REAL,
                    longitude REAL,
                    distance_meters REAL,
                    needs_review BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (location_id) REFERENCES locations (id)
                )
            """)
            
            # SD card mappings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sd_card_mappings (
                    sd_card TEXT PRIMARY KEY,
                    description TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    image_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_coords ON locations(latitude, longitude)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_locations_path ON image_locations(image_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_locations_sd_card ON image_locations(sd_card)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_locations_location ON image_locations(location_id)")
            
            conn.commit()
    
    def add_location(self, location: Location) -> str:
        """Add a new location to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO locations 
                (id, name, latitude, longitude, radius_meters, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                location.id,
                location.name,
                location.latitude,
                location.longitude,
                location.radius_meters,
                location.description,
                location.created_at or datetime.now().isoformat(),
                location.updated_at or datetime.now().isoformat()
            ))
            
            conn.commit()
            return location.id
    
    def get_locations(self) -> List[Location]:
        """Get all locations from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM locations ORDER BY name")
            rows = cursor.fetchall()
            
            return [Location(**dict(row)) for row in rows]
    
    def find_nearby_location(self, latitude: float, longitude: float, 
                           max_distance: float = 10.0) -> Optional[Location]:
        """Find the nearest location within max_distance meters."""
        locations = self.get_locations()
        
        for location in locations:
            distance = self._calculate_distance(
                latitude, longitude, 
                location.latitude, location.longitude
            )
            
            if distance <= max_distance:
                return location
        
        return None
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters."""
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine formula
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Earth radius in meters
        
        return c * r
    
    def classify_image(self, image_path: Path, sd_card: str) -> ImageLocation:
        """Classify an image location."""
        # Extract GPS coordinates
        gps = get_gps_from_exif(image_path)
        latitude = gps.get('latitude') if gps else None
        longitude = gps.get('longitude') if gps else None
        
        location_id = None
        distance_meters = None
        needs_review = False
        
        if latitude and longitude:
            # Find nearby location
            nearby_location = self.find_nearby_location(latitude, longitude)
            
            if nearby_location:
                location_id = nearby_location.id
                distance_meters = self._calculate_distance(
                    latitude, longitude,
                    nearby_location.latitude, nearby_location.longitude
                )
            else:
                needs_review = True
        
        # Create image location record
        image_location = ImageLocation(
            image_path=str(image_path),
            sd_card=sd_card,
            location_id=location_id,
            latitude=latitude,
            longitude=longitude,
            distance_meters=distance_meters,
            needs_review=needs_review,
            created_at=datetime.now().isoformat()
        )
        
        # Store in database
        self._store_image_location(image_location)
        
        return image_location
    
    def _store_image_location(self, image_location: ImageLocation):
        """Store image location in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO image_locations 
                (image_path, sd_card, location_id, latitude, longitude, 
                 distance_meters, needs_review, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image_location.image_path,
                image_location.sd_card,
                image_location.location_id,
                image_location.latitude,
                image_location.longitude,
                image_location.distance_meters,
                image_location.needs_review,
                image_location.created_at
            ))
            
            conn.commit()
    
    def get_unknown_locations(self) -> List[Dict]:
        """Get images with unknown locations that need review."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM image_locations 
                WHERE needs_review = 1 
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_location_from_unknown(self, image_path: str, location_name: str, 
                                   description: str = "") -> str:
        """Create a new location from an unknown image location."""
        # Get the image location data
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM image_locations WHERE image_path = ?
            """, (image_path,))
            
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Image location not found: {image_path}")
            
            image_data = dict(row)
        
        # Create new location
        location_id = self._generate_location_id(location_name)
        location = Location(
            id=location_id,
            name=location_name,
            latitude=image_data['latitude'],
            longitude=image_data['longitude'],
            description=description,
            created_at=datetime.now().isoformat()
        )
        
        # Add location to database
        self.add_location(location)
        
        # Update image location
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE image_locations 
                SET location_id = ?, needs_review = 0
                WHERE image_path = ?
            """, (location_id, image_path))
            
            conn.commit()
        
        return location_id
    
    def _generate_location_id(self, name: str) -> str:
        """Generate a unique location ID."""
        # Create hash from name and timestamp
        timestamp = datetime.now().isoformat()
        hash_input = f"{name}_{timestamp}".encode()
        hash_suffix = hashlib.md5(hash_input).hexdigest()[:8]
        
        # Clean name for ID
        clean_name = "".join(c for c in name if c.isalnum() or c in "_-").lower()
        
        return f"{clean_name}_{hash_suffix}"
    
    def move_images_to_cloud(self, input_dir: Path, output_prefix: str, 
                           dry_run: bool = False) -> Dict[str, int]:
        """Move images to cloud storage with SD card folder structure."""
        stats = {"moved": 0, "skipped": 0, "errors": 0}
        
        # Get all images that need to be moved
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT sd_card, image_path, location_id 
                FROM image_locations 
                WHERE image_path LIKE ?
                ORDER BY sd_card, image_path
            """, (f"{input_dir}%",))
            
            images = cursor.fetchall()
        
        for image_data in images:
            try:
                source_path = Path(image_data['image_path'])
                sd_card = image_data['sd_card']
                location_id = image_data['location_id']
                
                if not source_path.exists():
                    print(f"⚠️  Source file not found: {source_path}")
                    stats["skipped"] += 1
                    continue
                
                # Create cloud path: {output_prefix}/{sd_card}/{location_id or 'unknown'}/{filename}
                location_folder = location_id or "unknown"
                cloud_path = f"{output_prefix}/{sd_card}/{location_folder}/{source_path.name}"
                
                if not dry_run:
                    # Read image data
                    with open(source_path, 'rb') as f:
                        image_data_bytes = f.read()
                    
                    # Upload to cloud storage
                    location = StorageLocation.from_url(cloud_path)
                    self.storage_adapter.put(location, image_data_bytes)
                    
                    # Update database with cloud path
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            UPDATE image_locations 
                            SET image_path = ?
                            WHERE image_path = ?
                        """, (cloud_path, str(source_path)))
                        
                        conn.commit()
                
                print(f"✅ {'Would move' if dry_run else 'Moved'}: {source_path} -> {cloud_path}")
                stats["moved"] += 1
                
            except Exception as e:
                print(f"❌ Error moving {source_path}: {e}")
                stats["errors"] += 1
        
        return stats
    
    def export_location_labels(self, output_file: Path) -> None:
        """Export location labels to JSON file for Git sharing."""
        locations = self.get_locations()
        
        # Convert to exportable format
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "locations": [asdict(loc) for loc in locations]
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📤 Exported {len(locations)} locations to {output_file}")
    
    def import_location_labels(self, input_file: Path) -> int:
        """Import location labels from JSON file."""
        with open(input_file, 'r') as f:
            import_data = json.load(f)
        
        imported_count = 0
        
        for location_data in import_data.get('locations', []):
            # Remove id to generate new one
            if 'id' in location_data:
                del location_data['id']
            
            location = Location(**location_data)
            location.id = self._generate_location_id(location.name)
            
            self.add_location(location)
            imported_count += 1
        
        print(f"📥 Imported {imported_count} locations from {input_file}")
        return imported_count
    
    def get_statistics(self) -> Dict[str, any]:
        """Get classification statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total images
            cursor.execute("SELECT COUNT(*) FROM image_locations")
            total_images = cursor.fetchone()[0]
            
            # Images with GPS
            cursor.execute("SELECT COUNT(*) FROM image_locations WHERE latitude IS NOT NULL")
            gps_images = cursor.fetchone()[0]
            
            # Classified images
            cursor.execute("SELECT COUNT(*) FROM image_locations WHERE location_id IS NOT NULL")
            classified_images = cursor.fetchone()[0]
            
            # Unknown locations
            cursor.execute("SELECT COUNT(*) FROM image_locations WHERE needs_review = 1")
            unknown_locations = cursor.fetchone()[0]
            
            # SD cards
            cursor.execute("SELECT COUNT(DISTINCT sd_card) FROM image_locations")
            sd_cards = cursor.fetchone()[0]
            
            # Locations
            cursor.execute("SELECT COUNT(*) FROM locations")
            total_locations = cursor.fetchone()[0]
            
            return {
                "total_images": total_images,
                "gps_images": gps_images,
                "classified_images": classified_images,
                "unknown_locations": unknown_locations,
                "sd_cards": sd_cards,
                "total_locations": total_locations,
                "classification_rate": classified_images / total_images if total_images > 0 else 0
            }


def main():
    """Main CLI for location classification tool."""
    parser = argparse.ArgumentParser(description="Location Classification Tool")
    parser.add_argument("--db", default="./location_classifier.db", help="SQLite database path")
    parser.add_argument("--storage", choices=["local", "s3", "gcs"], default="local", help="Storage adapter")
    parser.add_argument("--storage-config", help="Storage configuration file")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Classify images command
    classify_parser = subparsers.add_parser("classify", help="Classify images by location")
    classify_parser.add_argument("input_dir", help="Input directory with images")
    classify_parser.add_argument("--sd-card", required=True, help="SD card identifier")
    classify_parser.add_argument("--recursive", action="store_true", help="Process recursively")
    
    # Move to cloud command
    move_parser = subparsers.add_parser("move", help="Move images to cloud storage")
    move_parser.add_argument("input_dir", help="Input directory with images")
    move_parser.add_argument("output_prefix", help="Cloud storage prefix")
    move_parser.add_argument("--dry-run", action="store_true", help="Show what would be moved")
    
    # Unknown locations command
    unknown_parser = subparsers.add_parser("unknown", help="Show unknown locations needing review")
    unknown_parser.add_argument("--limit", type=int, default=50, help="Limit number of results")
    
    # Create location command
    create_parser = subparsers.add_parser("create-location", help="Create location from unknown image")
    create_parser.add_argument("image_path", help="Image path")
    create_parser.add_argument("location_name", help="Location name")
    create_parser.add_argument("--description", help="Location description")
    
    # Export/Import commands
    export_parser = subparsers.add_parser("export", help="Export location labels")
    export_parser.add_argument("output_file", help="Output JSON file")
    
    import_parser = subparsers.add_parser("import", help="Import location labels")
    import_parser.add_argument("input_file", help="Input JSON file")
    
    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show classification statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize classifier
    db_path = Path(args.db)
    storage_adapter = create_storage_adapter(args.storage) if args.storage != "local" else None
    classifier = LocationClassifier(db_path, storage_adapter)
    
    # Execute command
    if args.command == "classify":
        input_dir = Path(args.input_dir)
        
        if not input_dir.exists():
            print(f"❌ Input directory not found: {input_dir}")
            return
        
        # Find images
        image_exts = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        image_files = []
        
        if args.recursive:
            for ext in image_exts:
                image_files.extend(input_dir.rglob(f"*{ext}"))
        else:
            for ext in image_exts:
                image_files.extend(input_dir.glob(f"*{ext}"))
        
        print(f"🔍 Found {len(image_files)} images to classify")
        
        # Classify each image
        for image_path in image_files:
            try:
                image_location = classifier.classify_image(image_path, args.sd_card)
                
                if image_location.location_id:
                    print(f"✅ {image_path.name} -> {image_location.location_id}")
                elif image_location.needs_review:
                    print(f"❓ {image_path.name} -> Unknown location (needs review)")
                else:
                    print(f"⚠️  {image_path.name} -> No GPS data")
                    
            except Exception as e:
                print(f"❌ Error processing {image_path}: {e}")
    
    elif args.command == "move":
        input_dir = Path(args.input_dir)
        stats = classifier.move_images_to_cloud(input_dir, args.output_prefix, args.dry_run)
        
        print(f"\n📊 Move Statistics:")
        print(f"  Moved: {stats['moved']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
    
    elif args.command == "unknown":
        unknown_locations = classifier.get_unknown_locations()
        
        print(f"❓ Unknown locations needing review ({len(unknown_locations)}):")
        
        for i, location in enumerate(unknown_locations[:args.limit]):
            print(f"  {i+1}. {location['image_path']}")
            print(f"     GPS: {location['latitude']:.6f}, {location['longitude']:.6f}")
            print(f"     SD Card: {location['sd_card']}")
            print()
    
    elif args.command == "create-location":
        location_id = classifier.create_location_from_unknown(
            args.image_path, args.location_name, args.description or ""
        )
        print(f"✅ Created location: {args.location_name} (ID: {location_id})")
    
    elif args.command == "export":
        output_file = Path(args.output_file)
        classifier.export_location_labels(output_file)
    
    elif args.command == "import":
        input_file = Path(args.input_file)
        imported_count = classifier.import_location_labels(input_file)
        print(f"📥 Imported {imported_count} locations")
    
    elif args.command == "stats":
        stats = classifier.get_statistics()
        
        print("📊 Classification Statistics:")
        print(f"  Total images: {stats['total_images']}")
        print(f"  GPS images: {stats['gps_images']}")
        print(f"  Classified images: {stats['classified_images']}")
        print(f"  Unknown locations: {stats['unknown_locations']}")
        print(f"  SD cards: {stats['sd_cards']}")
        print(f"  Total locations: {stats['total_locations']}")
        print(f"  Classification rate: {stats['classification_rate']:.1%}")


if __name__ == "__main__":
    main()
