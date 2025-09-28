#!/usr/bin/env python3
"""
Utility to fix camera timestamps by applying a time offset to EXIF data.

This script helps correct timestamps when cameras were set to wrong dates.
Example: Camera set to 2024-01-01 but actual date should be 2025-09-07
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image
from PIL.ExifTags import TAGS
import piexif


def parse_date_offset(offset_str: str) -> timedelta:
    """
    Parse a date offset string in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
    Returns the offset as a timedelta from 1970-01-01.
    """
    try:
        if ' ' in offset_str:
            # Full datetime format
            target_date = datetime.strptime(offset_str, '%Y-%m-%d %H:%M:%S')
        else:
            # Date only format
            target_date = datetime.strptime(offset_str, '%Y-%m-%d')
        
        # Calculate offset from epoch (1970-01-01)
        epoch = datetime(1970, 1, 1)
        return target_date - epoch
    except ValueError as e:
        raise ValueError(f"Invalid date format '{offset_str}'. Use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'") from e


def get_exif_datetime(image_path: Path) -> Optional[datetime]:
    """Extract datetime from EXIF data."""
    try:
        with Image.open(image_path) as img:
            exif_dict = piexif.load(img.info.get('exif', b''))
            
            # Try different datetime fields
            datetime_fields = [
                'DateTime',
                'DateTimeOriginal', 
                'DateTimeDigitized'
            ]
            
            for field in datetime_fields:
                if field in exif_dict['0th']:
                    dt_str = exif_dict['0th'][field].decode('utf-8')
                    return datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
            
            return None
    except Exception as e:
        print(f"Warning: Could not read EXIF from {image_path}: {e}")
        return None


def update_exif_datetime(image_path: Path, new_datetime: datetime, backup: bool = True) -> bool:
    """Update EXIF datetime fields in the image."""
    try:
        # Create backup if requested
        if backup:
            backup_path = image_path.with_suffix(f'.backup{image_path.suffix}')
            backup_path.write_bytes(image_path.read_bytes())
            print(f"Backup created: {backup_path}")
        
        # Load existing EXIF or create new
        with Image.open(image_path) as img:
            try:
                exif_dict = piexif.load(img.info.get('exif', b''))
            except:
                exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
            
            # Format datetime for EXIF
            dt_str = new_datetime.strftime('%Y:%m:%d %H:%M:%S')
            
            # Update all datetime fields
            datetime_fields = [
                'DateTime',
                'DateTimeOriginal', 
                'DateTimeDigitized'
            ]
            
            for field in datetime_fields:
                exif_dict['0th'][field] = dt_str.encode('utf-8')
            
            # Convert back to EXIF bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Save with updated EXIF
            img.save(image_path, exif=exif_bytes)
            
        return True
    except Exception as e:
        print(f"Error updating {image_path}: {e}")
        return False


def process_image(image_path: Path, target_date: datetime, offset: timedelta, dry_run: bool = False) -> bool:
    """Process a single image to fix its timestamp."""
    print(f"\nProcessing: {image_path.name}")
    
    # Get current EXIF datetime
    current_dt = get_exif_datetime(image_path)
    if current_dt is None:
        print(f"  No EXIF datetime found")
        return False
    
    print(f"  Current EXIF datetime: {current_dt}")
    
    # Calculate new datetime
    # Method 1: If target_date is provided, use it directly
    if target_date:
        new_dt = target_date
        print(f"  Setting to target date: {new_dt}")
    else:
        # Method 2: Apply offset to current datetime
        new_dt = current_dt + offset
        print(f"  Applying offset {offset}: {new_dt}")
    
    if dry_run:
        print(f"  [DRY RUN] Would update to: {new_dt}")
        return True
    
    # Update the image
    success = update_exif_datetime(image_path, new_dt, backup=True)
    if success:
        print(f"  ✓ Updated successfully")
    else:
        print(f"  ✗ Failed to update")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Fix camera timestamps by applying time offsets to EXIF data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set all images to a specific date
  python fix_camera_timestamps.py --target-date "2025-09-07" /path/to/images/

  # Apply a time offset (e.g., add 8 months and 6 days)
  python fix_camera_timestamps.py --offset-days 250 /path/to/images/

  # Dry run to see what would change
  python fix_camera_timestamps.py --target-date "2025-09-07" --dry-run /path/to/images/

  # Process specific file types
  python fix_camera_timestamps.py --extensions jpg jpeg --target-date "2025-09-07" /path/to/images/
        """
    )
    
    parser.add_argument('path', help='Path to image file or directory')
    parser.add_argument('--target-date', help='Set all images to this specific date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--offset-days', type=int, help='Add this many days to current EXIF datetime')
    parser.add_argument('--offset-hours', type=int, help='Add this many hours to current EXIF datetime')
    parser.add_argument('--extensions', nargs='+', default=['jpg', 'jpeg', 'tiff', 'tif'], 
                       help='Image file extensions to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.target_date and not args.offset_days and not args.offset_hours:
        print("Error: Must specify either --target-date or --offset-days/--offset-hours")
        sys.exit(1)
    
    if args.target_date and (args.offset_days or args.offset_hours):
        print("Error: Cannot use --target-date with offset options")
        sys.exit(1)
    
    # Parse target date if provided
    target_date = None
    if args.target_date:
        try:
            if ' ' in args.target_date:
                target_date = datetime.strptime(args.target_date, '%Y-%m-%d %H:%M:%S')
            else:
                target_date = datetime.strptime(args.target_date, '%Y-%m-%d')
        except ValueError as e:
            print(f"Error: Invalid date format '{args.target_date}': {e}")
            sys.exit(1)
    
    # Calculate offset if provided
    offset = timedelta()
    if args.offset_days:
        offset += timedelta(days=args.offset_days)
    if args.offset_hours:
        offset += timedelta(hours=args.offset_hours)
    
    # Find images to process
    path = Path(args.path)
    if path.is_file():
        image_paths = [path]
    elif path.is_dir():
        image_paths = []
        for ext in args.extensions:
            image_paths.extend(path.glob(f'**/*.{ext}'))
            image_paths.extend(path.glob(f'**/*.{ext.upper()}'))
    else:
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    if not image_paths:
        print(f"No images found with extensions: {args.extensions}")
        sys.exit(1)
    
    print(f"Found {len(image_paths)} images to process")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    
    # Process images
    success_count = 0
    for image_path in image_paths:
        try:
            success = process_image(
                image_path, 
                target_date, 
                offset, 
                dry_run=args.dry_run
            )
            if success:
                success_count += 1
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
    
    print(f"\nProcessed {success_count}/{len(image_paths)} images successfully")
    
    if args.dry_run:
        print("\nTo apply changes, run without --dry-run")


if __name__ == '__main__':
    main()
