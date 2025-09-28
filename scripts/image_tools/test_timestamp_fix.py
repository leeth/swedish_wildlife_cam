#!/usr/bin/env python3
"""
Test script for the timestamp fixing utility.
Creates test images with wrong timestamps and demonstrates the fix.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import piexif


def create_test_image_with_timestamp(output_path: Path, timestamp: datetime):
    """Create a test image with specific EXIF timestamp."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Create EXIF data with timestamp
    exif_dict = {
        '0th': {
            306: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTime
        },
        'Exif': {
            36867: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTimeOriginal
            36868: timestamp.strftime('%Y:%m:%d %H:%M:%S').encode('utf-8'),  # DateTimeDigitized
        },
        'GPS': {},
        '1st': {},
        'thumbnail': None,
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img.save(output_path, exif=exif_bytes)
    print(f"Created test image: {output_path} with timestamp: {timestamp}")


def main():
    """Create test images and demonstrate timestamp fixing."""
    # Create temporary directory for test images
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("Creating test images with wrong timestamps...")
        
        # Create test images with wrong dates
        wrong_dates = [
            datetime(2024, 1, 1, 10, 30, 0),  # Camera set to 2024-01-01
            datetime(2024, 1, 1, 14, 45, 0),  # Camera set to 2024-01-01
            datetime(2024, 1, 1, 18, 20, 0),  # Camera set to 2024-01-01
        ]
        
        for i, wrong_date in enumerate(wrong_dates):
            img_path = temp_path / f"test_image_{i+1}.jpg"
            create_test_image_with_timestamp(img_path, wrong_date)
        
        print(f"\nTest images created in: {temp_path}")
        print("\nTo fix these timestamps, you could run:")
        print(f"python scripts/fix_camera_timestamps.py --target-date '2025-09-07' {temp_path}")
        print(f"python scripts/fix_camera_timestamps.py --offset-days 250 {temp_path}")
        
        # Show current timestamps
        print("\nCurrent timestamps:")
        for img_path in temp_path.glob("*.jpg"):
            try:
                from PIL import Image
                import piexif
                
                with Image.open(img_path) as img:
                    exif_dict = piexif.load(img.info.get('exif', b''))
                    dt_str = exif_dict['0th'].get(306, b'').decode('utf-8')
                    if dt_str:
                        current_dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                        print(f"  {img_path.name}: {current_dt}")
                    else:
                        print(f"  {img_path.name}: No timestamp found")
            except Exception as e:
                print(f"  {img_path.name}: Error reading timestamp - {e}")


if __name__ == '__main__':
    main()
