#!/usr/bin/env python3
"""
Utility to fix video timestamps by modifying file creation/modification times.

This script helps correct timestamps when video cameras were set to wrong dates.
Video files don't have EXIF data like images, so we modify the file system timestamps.
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import av
except ImportError:
    print("Error: PyAV library not found. Install with: pip install av")
    sys.exit(1)


def get_video_metadata(video_path: Path) -> Optional[dict]:
    """Extract metadata from video file."""
    try:
        container = av.open(str(video_path))
        video_stream = container.streams.video[0]
        
        metadata = {
            'duration': float(video_stream.duration * video_stream.time_base),
            'fps': float(video_stream.rate),
            'width': video_stream.width,
            'height': video_stream.height,
            'codec': video_stream.codec.name,
            'file_size': video_path.stat().st_size,
            'creation_time': datetime.fromtimestamp(video_path.stat().st_ctime),
            'modification_time': datetime.fromtimestamp(video_path.stat().st_mtime)
        }
        
        container.close()
        return metadata
        
    except Exception as e:
        print(f"Warning: Could not read metadata from {video_path}: {e}")
        return None


def update_video_timestamps(video_path: Path, new_datetime: datetime, backup: bool = True) -> bool:
    """Update file system timestamps for video file."""
    try:
        # Create backup if requested
        if backup:
            backup_path = video_path.with_suffix(f'.backup{video_path.suffix}')
            backup_path.write_bytes(video_path.read_bytes())
            print(f"Backup created: {backup_path}")
        
        # Update file timestamps
        timestamp = new_datetime.timestamp()
        os.utime(video_path, (timestamp, timestamp))
        
        return True
        
    except Exception as e:
        print(f"Error updating {video_path}: {e}")
        return False


def process_video(video_path: Path, target_date: datetime, offset: timedelta, 
                 output_dir: Optional[Path] = None, dry_run: bool = False, 
                 no_backup: bool = False) -> bool:
    """Process a single video to fix its timestamp."""
    print(f"\nProcessing: {video_path.name}")
    
    # Get current video metadata
    metadata = get_video_metadata(video_path)
    if metadata is None:
        print(f"  No metadata found")
        return False
    
    current_dt = metadata['modification_time']
    print(f"  Current modification time: {current_dt}")
    
    # Calculate new datetime
    if target_date:
        new_dt = target_date
        print(f"  Setting to target date: {new_dt}")
    else:
        new_dt = current_dt + offset
        print(f"  Applying offset {offset}: {new_dt}")
    
    if dry_run:
        print(f"  [DRY RUN] Would update to: {new_dt}")
        return True
    
    # Determine output path
    if output_dir:
        output_path = output_dir / video_path.name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  Output will be saved to: {output_path}")
        
        # Copy file to output directory
        output_path.write_bytes(video_path.read_bytes())
        target_path = output_path
    else:
        target_path = video_path
    
    # Update the video timestamps
    success = update_video_timestamps(target_path, new_dt, backup=not no_backup)
    if success:
        print(f"  ✓ Updated successfully")
    else:
        print(f"  ✗ Failed to update")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Fix video timestamps by modifying file system timestamps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set all videos to a specific date
  python fix_video_timestamps.py --target-date "2025-09-07" /path/to/videos/

  # Apply a time offset (e.g., add 8 months and 6 days)
  python fix_video_timestamps.py --offset-days 250 /path/to/videos/

  # Apply a time offset with minutes (e.g., add 2 hours and 30 minutes)
  python fix_video_timestamps.py --offset-hours 2 --offset-minutes 30 /path/to/videos/

  # Dry run to see what would change
  python fix_video_timestamps.py --target-date "2025-09-07" --dry-run /path/to/videos/

  # Process specific file types
  python fix_video_timestamps.py --extensions mp4 mov avi --target-date "2025-09-07" /path/to/videos/

  # Process with output directory
  python fix_video_timestamps.py --target-date "2025-09-07" --output-dir /path/to/output /path/to/videos/
        """
    )
    
    parser.add_argument('path', help='Path to video file or directory')
    parser.add_argument('--target-date', help='Set all videos to this specific date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--offset-days', type=int, help='Add this many days to current timestamp')
    parser.add_argument('--offset-hours', type=int, help='Add this many hours to current timestamp')
    parser.add_argument('--offset-minutes', type=int, help='Add this many minutes to current timestamp')
    parser.add_argument('--extensions', nargs='+', default=['mp4', 'mov', 'avi', 'mkv', 'm4v'], 
                       help='Video file extensions to process')
    parser.add_argument('--output-dir', help='Output directory for processed files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.target_date and not args.offset_days and not args.offset_hours and not args.offset_minutes:
        print("Error: Must specify either --target-date or --offset-days/--offset-hours/--offset-minutes")
        sys.exit(1)
    
    if args.target_date and (args.offset_days or args.offset_hours or args.offset_minutes):
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
    if args.offset_minutes:
        offset += timedelta(minutes=args.offset_minutes)
    
    # Find videos to process
    path = Path(args.path)
    if path.is_file():
        video_paths = [path]
    elif path.is_dir():
        video_paths = []
        for ext in args.extensions:
            video_paths.extend(path.glob(f'**/*.{ext}'))
            video_paths.extend(path.glob(f'**/*.{ext.upper()}'))
    else:
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    if not video_paths:
        print(f"No videos found with extensions: {args.extensions}")
        sys.exit(1)
    
    print(f"Found {len(video_paths)} videos to process")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    
    # Create output directory if specified
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")
    
    # Process videos
    success_count = 0
    for video_path in video_paths:
        try:
            success = process_video(
                video_path, 
                target_date, 
                offset, 
                output_dir=output_dir,
                dry_run=args.dry_run,
                no_backup=args.no_backup
            )
            if success:
                success_count += 1
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
    
    print(f"\nProcessed {success_count}/{len(video_paths)} videos successfully")
    
    if args.dry_run:
        print("\nTo apply changes, run without --dry-run")


if __name__ == '__main__':
    main()
