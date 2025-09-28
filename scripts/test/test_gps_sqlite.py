#!/usr/bin/env python3
"""
Test script for GPS extraction and SQLite database functionality.
"""

import tempfile
from pathlib import Path
from datetime import datetime
from PIL import Image
import piexif


def create_test_image_with_gps(output_path: Path, timestamp: datetime, lat: float, lon: float):
    """Create a test image with specific EXIF timestamp and GPS coordinates."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Convert decimal degrees to DMS
    def decimal_to_dms(decimal_deg, is_latitude=True):
        if is_latitude:
            ref = 'N' if decimal_deg >= 0 else 'S'
        else:
            ref = 'E' if decimal_deg >= 0 else 'W'
        
        decimal_deg = abs(decimal_deg)
        degrees = int(decimal_deg)
        minutes_float = (decimal_deg - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        return (degrees, minutes, seconds), ref
    
    lat_dms, lat_ref = decimal_to_dms(lat, True)
    lon_dms, lon_ref = decimal_to_dms(lon, False)
    
    # Create EXIF data with timestamp and GPS
    exif_dict = {
        '0th': {
            306: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTime
        },
        'Exif': {
            36867: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTimeOriginal
            36868: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTimeDigitized
        },
        'GPS': {
            1: lat_ref,  # GPSLatitudeRef
            2: lat_dms,  # GPSLatitude
            3: lon_ref,  # GPSLongitudeRef
            4: lon_dms,  # GPSLongitude
        },
        '1st': {},
        'thumbnail': None,
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img.save(output_path, exif=exif_bytes)
    print(f"Created test image: {output_path} with timestamp: {timestamp}, GPS: {lat}, {lon}")


def test_gps_extraction():
    """Test GPS coordinate extraction."""
    print("Testing GPS coordinate extraction...")
    
    # Test GPS extraction function directly
    from src.wildlife_pipeline.metadata import get_gps_from_exif
    
    # Test with mock EXIF data
    test_exif_data = {
        'GPSInfo': {
            1: 'N',  # GPSLatitudeRef
            2: (59, 19, 45),  # GPSLatitude (degrees, minutes, seconds)
            3: 'E',  # GPSLongitudeRef
            4: (18, 4, 7),  # GPSLongitude (degrees, minutes, seconds)
        }
    }
    
    gps_coords = get_gps_from_exif(test_exif_data)
    if gps_coords:
        lat, lon = gps_coords
        print(f"  GPS extraction successful: {lat:.4f}, {lon:.4f}")
    else:
        print("  GPS extraction failed")
    
    # Test with empty EXIF
    empty_exif = {}
    gps_coords = get_gps_from_exif(empty_exif)
    if gps_coords is None:
        print("  Empty EXIF handled correctly")
    else:
        print("  Empty EXIF not handled correctly")


def test_sqlite_database():
    """Test SQLite database functionality."""
    print("\nTesting SQLite database functionality...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "test_wildlife.db"
        
        from src.wildlife_pipeline.database import WildlifeDatabase
        
        # Create database
        db = WildlifeDatabase(db_path)
        print(f"Created database: {db_path}")
        
        # Insert test detections
        test_detections = [
            {
                'file_path': '/path/to/image1.jpg',
                'file_type': 'image',
                'camera_id': 'camera_1',
                'timestamp': '2025-09-07T10:30:00',
                'latitude': 59.3293,
                'longitude': 18.0686,
                'image_width': 1920,
                'image_height': 1080,
                'stage1_dropped': 2,
                'manual_review_count': 1,
                'detection_results': [
                    {'label': 'moose', 'confidence': 0.85, 'bbox': {'x1': 100, 'y1': 200, 'x2': 300, 'y2': 400}, 'stage': 1},
                    {'label': 'roedeer', 'confidence': 0.72, 'bbox': {'x1': 400, 'y1': 100, 'x2': 500, 'y2': 300}, 'stage': 1}
                ]
            },
            {
                'file_path': '/path/to/image2.jpg',
                'file_type': 'image',
                'camera_id': 'camera_2',
                'timestamp': '2025-09-07T14:45:00',
                'latitude': 55.6761,
                'longitude': 12.5683,
                'image_width': 1920,
                'image_height': 1080,
                'stage1_dropped': 0,
                'manual_review_count': 0,
                'detection_results': [
                    {'label': 'boar', 'confidence': 0.91, 'bbox': {'x1': 150, 'y1': 250, 'x2': 350, 'y2': 450}, 'stage': 1}
                ]
            }
        ]
        
        for detection in test_detections:
            detection_id = db.insert_detection(detection)
            print(f"Inserted detection ID: {detection_id}")
        
        # Test queries
        print("\nDatabase queries:")
        
        # Get summary stats
        stats = db.get_summary_stats()
        print(f"Total detections: {stats['total_detections']}")
        print(f"Detections with GPS: {stats['gps_detections']}")
        print(f"Species detected: {stats['species_counts']}")
        print(f"Cameras: {stats['camera_counts']}")
        
        # Get detections by camera
        camera_detections = db.get_detections_by_camera('camera_1')
        print(f"\nDetections for camera_1: {len(camera_detections)}")
        
        # Get detections by species
        moose_detections = db.get_detections_by_species('moose')
        print(f"Moose detections: {len(moose_detections)}")
        
        # Get detections with GPS
        gps_detections = db.get_detections_with_gps()
        print(f"Detections with GPS: {len(gps_detections)}")
        
        # Export to CSV
        csv_path = temp_path / "export.csv"
        db.export_to_csv(csv_path)
        print(f"Exported to CSV: {csv_path}")


def main():
    """Run all tests."""
    print("Testing GPS extraction and SQLite database functionality...")
    
    try:
        test_gps_extraction()
        test_sqlite_database()
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
