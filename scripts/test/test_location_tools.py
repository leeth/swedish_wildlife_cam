#!/usr/bin/env python3
"""
Test script for location classification tools.

This script demonstrates the location classification workflow:
1. Classify images by location
2. Identify unknown locations
3. Create location labels
4. Move images to cloud storage
5. Sync labels with Git
"""

import sys
import tempfile
from pathlib import Path
import json
import sqlite3

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wildlife_pipeline.tools.location_classifier import LocationClassifier
from src.wildlife_pipeline.tools.location_labeler import InteractiveLocationLabeler
from src.wildlife_pipeline.tools.location_sync import LocationSync


def create_test_images():
    """Create test images with GPS data for testing."""
    from PIL import Image
    import piexif
    
    test_dir = Path("test_images")
    test_dir.mkdir(exist_ok=True)
    
    # Test images with GPS data
    test_locations = [
        {
            "name": "test_image_1.jpg",
            "gps": {"latitude": 59.3293, "longitude": 18.0686},  # Stockholm
            "sd_card": "SD001"
        },
        {
            "name": "test_image_2.jpg", 
            "gps": {"latitude": 59.3294, "longitude": 18.0687},  # Stockholm (nearby)
            "sd_card": "SD001"
        },
        {
            "name": "test_image_3.jpg",
            "gps": {"latitude": 59.5000, "longitude": 18.0000},  # Stockholm (far)
            "sd_card": "SD002"
        },
        {
            "name": "test_image_4.jpg",
            "gps": None,  # No GPS
            "sd_card": "SD002"
        }
    ]
    
    for location in test_locations:
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_path = test_dir / location["name"]
        img.save(img_path)
        
        # Add GPS EXIF data if available
        if location["gps"]:
            exif_dict = piexif.load(img.info.get('exif', b''))
            
            # Add GPS data
            gps_ifd = {
                piexif.GPSIFD.GPSLatitudeRef: 'N',
                piexif.GPSIFD.GPSLatitude: [(int(location["gps"]["latitude"]), 1), (0, 1), (0, 1)],
                piexif.GPSIFD.GPSLongitudeRef: 'E', 
                piexif.GPSIFD.GPSLongitude: [(int(location["gps"]["longitude"]), 1), (0, 1), (0, 1)]
            }
            
            exif_dict['GPS'] = gps_ifd
            exif_bytes = piexif.dump(exif_dict)
            
            # Save with EXIF
            img.save(img_path, exif=exif_bytes)
    
    return test_dir


def test_location_classifier():
    """Test the location classifier."""
    print("🧪 Testing Location Classifier")
    print("=" * 40)
    
    # Create test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        # Initialize classifier
        classifier = LocationClassifier(db_path)
        
        # Add some test locations
        from src.wildlife_pipeline.tools.location_classifier import Location
        
        stockholm_location = Location(
            id="stockholm_001",
            name="Stockholm Central",
            latitude=59.3293,
            longitude=18.0686,
            description="Stockholm central station area"
        )
        classifier.add_location(stockholm_location)
        
        # Create test images
        test_dir = create_test_images()
        
        # Classify images
        print(f"\n📁 Classifying images in {test_dir}")
        for image_path in test_dir.glob("*.jpg"):
            print(f"🔍 Processing: {image_path.name}")
            
            # Determine SD card from filename
            sd_card = "SD001" if "1" in image_path.name or "2" in image_path.name else "SD002"
            
            image_location = classifier.classify_image(image_path, sd_card)
            
            if image_location.location_id:
                print(f"  ✅ Classified as: {image_location.location_id}")
            elif image_location.needs_review:
                print(f"  ❓ Unknown location (needs review)")
            else:
                print(f"  ⚠️  No GPS data")
        
        # Show statistics
        stats = classifier.get_statistics()
        print(f"\n📊 Classification Statistics:")
        print(f"  Total images: {stats['total_images']}")
        print(f"  GPS images: {stats['gps_images']}")
        print(f"  Classified: {stats['classified_images']}")
        print(f"  Unknown: {stats['unknown_locations']}")
        print(f"  Classification rate: {stats['classification_rate']:.1%}")
        
        # Show unknown locations
        unknown_locations = classifier.get_unknown_locations()
        if unknown_locations:
            print(f"\n❓ Unknown locations needing review:")
            for location in unknown_locations:
                print(f"  - {Path(location['image_path']).name}: {location['latitude']:.6f}, {location['longitude']:.6f}")
        
        return classifier, test_dir
        
    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()


def test_location_labeler():
    """Test the location labeler."""
    print("\n🏷️  Testing Location Labeler")
    print("=" * 40)
    
    # Create test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        # Initialize labeler
        labeler = InteractiveLocationLabeler(db_path)
        
        # Show unknown locations
        print("📋 Unknown locations:")
        unknown_locations = labeler.show_unknown_locations(limit=10)
        
        # Create a test location (simulate user input)
        if unknown_locations:
            test_location = unknown_locations[0]
            print(f"\n🏷️  Creating location for: {Path(test_location['image_path']).name}")
            
            # Simulate creating location
            location_id = labeler.classifier.create_location_from_unknown(
                test_location['image_path'],
                "Test Location",
                "A test location created by the test script"
            )
            print(f"✅ Created location: Test Location (ID: {location_id})")
        
        # Show statistics
        stats = labeler.classifier.get_statistics()
        print(f"\n📊 Updated Statistics:")
        print(f"  Total locations: {stats['total_locations']}")
        print(f"  Classified images: {stats['classified_images']}")
        print(f"  Unknown locations: {stats['unknown_locations']}")
        
    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()


def test_location_sync():
    """Test the location sync tool."""
    print("\n🔄 Testing Location Sync")
    print("=" * 40)
    
    # Create test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    # Create test Git repository
    with tempfile.TemporaryDirectory() as temp_dir:
        git_repo = Path(temp_dir) / "test_repo"
        git_repo.mkdir()
        
        try:
            # Initialize Git repository
            import subprocess
            subprocess.run(["git", "init"], cwd=git_repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=git_repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_repo, check=True)
            
            # Initialize sync tool
            sync_tool = LocationSync(db_path, git_repo)
            
            # Add some test locations
            classifier = LocationClassifier(db_path)
            from src.wildlife_pipeline.tools.location_classifier import Location
            
            test_locations = [
                Location(id="loc1", name="Location 1", latitude=59.3293, longitude=18.0686),
                Location(id="loc2", name="Location 2", latitude=59.5000, longitude=18.0000),
            ]
            
            for location in test_locations:
                classifier.add_location(location)
            
            # Export labels
            print("📤 Exporting labels...")
            export_file = sync_tool.export_labels()
            print(f"✅ Exported to: {export_file}")
            
            # Commit changes
            print("📝 Committing changes...")
            if sync_tool.commit_and_push("Add test locations"):
                print("✅ Successfully committed and pushed")
            else:
                print("❌ Failed to commit and push")
            
            # Show status
            print("\n📊 Repository Status:")
            sync_tool.show_status()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
        finally:
            # Cleanup
            if db_path.exists():
                db_path.unlink()


def main():
    """Run all tests."""
    print("🚀 Location Classification Tools Test Suite")
    print("=" * 50)
    
    try:
        # Test location classifier
        classifier, test_dir = test_location_classifier()
        
        # Test location labeler
        test_location_labeler()
        
        # Test location sync
        test_location_sync()
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Use 'location_classifier classify' to classify your images")
        print("2. Use 'location_labeler interactive' to label unknown locations")
        print("3. Use 'location_sync sync' to sync labels with Git")
        print("4. Use 'location_classifier move' to move images to cloud storage")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup test images
        test_dir = Path("test_images")
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")


if __name__ == "__main__":
    main()
