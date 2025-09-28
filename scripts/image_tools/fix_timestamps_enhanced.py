#!/usr/bin/env python3
"""
Enhanced utility to fix camera timestamps with detailed logging and summary.

This script helps correct timestamps when cameras were set to wrong dates.
Features:
- Detailed logging to file and console
- Summary report with statistics
- Support for both images and videos
- Recursive directory processing
- Output directory support
"""

import argparse
import sys
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

from PIL import Image
import piexif

try:
    import av
    VIDEO_SUPPORT = True
except ImportError:
    VIDEO_SUPPORT = False
    print("Warning: PyAV not available. Video processing disabled.")

# Setup logging
def setup_logging(log_file: str = 'timestamp_fix.log'):
    """Setup detailed logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class TimestampFixer:
    """Enhanced timestamp fixer with logging and summary."""
    
    def __init__(self, dry_run: bool = False, no_backup: bool = False):
        self.dry_run = dry_run
        self.no_backup = no_backup
        self.results = []
        self.stats = defaultdict(int)
        
    def get_image_datetime(self, image_path: Path) -> Optional[datetime]:
        """Extract datetime from image EXIF data."""
        try:
            logger.debug(f"Reading EXIF from {image_path}")
            with Image.open(image_path) as img:
                exif_dict = piexif.load(img.info.get('exif', b''))
                
                datetime_fields = [306, 36867, 36868]  # DateTime, DateTimeOriginal, DateTimeDigitized
                
                for field in datetime_fields:
                    if field in exif_dict['0th']:
                        dt_str = exif_dict['0th'][field].decode('utf-8')
                        dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                        logger.debug(f"Found {field}: {dt}")
                        return dt
                
                logger.warning(f"No EXIF datetime found in {image_path}")
                return None
        except Exception as e:
            logger.error(f"Could not read EXIF from {image_path}: {e}")
            return None
    
    def get_video_datetime(self, video_path: Path) -> Optional[datetime]:
        """Extract creation time from video file."""
        try:
            stat = video_path.stat()
            dt = datetime.fromtimestamp(stat.st_mtime)
            logger.debug(f"Video {video_path}: modification time {dt}")
            return dt
        except Exception as e:
            logger.error(f"Could not read video timestamp from {video_path}: {e}")
            return None
    
    def update_image_timestamp(self, image_path: Path, new_datetime: datetime) -> bool:
        """Update EXIF datetime fields in image."""
        try:
            if not self.no_backup:
                backup_path = image_path.with_suffix(f'.backup{image_path.suffix}')
                backup_path.write_bytes(image_path.read_bytes())
                logger.info(f"Backup created: {backup_path}")
            
            with Image.open(image_path) as img:
                try:
                    exif_dict = piexif.load(img.info.get('exif', b''))
                except:
                    exif_dict = {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'thumbnail': None}
                
                dt_str = new_datetime.strftime('%Y:%m:%d %H:%M:%S')
                datetime_fields = [306, 36867, 36868]  # DateTime, DateTimeOriginal, DateTimeDigitized
                
                for field in datetime_fields:
                    exif_dict['0th'][field] = dt_str.encode('utf-8')
                
                exif_bytes = piexif.dump(exif_dict)
                img.save(image_path, exif=exif_bytes)
                
            return True
        except Exception as e:
            logger.error(f"Error updating {image_path}: {e}")
            return False
    
    def update_video_timestamp(self, video_path: Path, new_datetime: datetime) -> bool:
        """Update file system timestamp for video."""
        try:
            if not self.no_backup:
                backup_path = video_path.with_suffix(f'.backup{video_path.suffix}')
                backup_path.write_bytes(video_path.read_bytes())
                logger.info(f"Backup created: {backup_path}")
            
            timestamp = new_datetime.timestamp()
            import os
            os.utime(video_path, (timestamp, timestamp))
            return True
        except Exception as e:
            logger.error(f"Error updating {video_path}: {e}")
            return False
    
    def process_file(self, file_path: Path, target_date: Optional[datetime], 
                    offset: Optional[timedelta], output_dir: Optional[Path] = None) -> Dict:
        """Process a single file (image or video)."""
        result = {
            'file': str(file_path),
            'file_type': 'unknown',
            'success': False,
            'error': None,
            'old_timestamp': None,
            'new_timestamp': None,
            'output_path': None
        }
        
        logger.info(f"Processing: {file_path.name}")
        print(f"\nProcessing: {file_path.name}")
        
        # Determine file type
        ext = file_path.suffix.lower()
        if ext in ['.jpg', '.jpeg', '.tiff', '.tif']:
            result['file_type'] = 'image'
            current_dt = self.get_image_datetime(file_path)
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.m4v'] and VIDEO_SUPPORT:
            result['file_type'] = 'video'
            current_dt = self.get_video_datetime(file_path)
        else:
            error_msg = f"Unsupported file type: {ext}"
            logger.warning(f"{file_path.name}: {error_msg}")
            result['error'] = error_msg
            return result
        
        if current_dt is None:
            error_msg = f"No timestamp found in {file_path.name}"
            logger.warning(error_msg)
            result['error'] = error_msg
            return result
        
        result['old_timestamp'] = current_dt
        logger.info(f"{file_path.name}: Current timestamp: {current_dt}")
        print(f"  Current timestamp: {current_dt}")
        
        # Calculate new datetime
        if target_date:
            new_dt = target_date
            logger.info(f"{file_path.name}: Setting to target date: {new_dt}")
            print(f"  Setting to target date: {new_dt}")
        else:
            new_dt = current_dt + offset
            logger.info(f"{file_path.name}: Applying offset {offset}: {new_dt}")
            print(f"  Applying offset {offset}: {new_dt}")
        
        result['new_timestamp'] = new_dt
        
        if self.dry_run:
            logger.info(f"{file_path.name}: [DRY RUN] Would update to: {new_dt}")
            print(f"  [DRY RUN] Would update to: {new_dt}")
            result['success'] = True
            return result
        
        # Determine output path
        if output_dir:
            output_path = output_dir / file_path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"{file_path.name}: Output will be saved to: {output_path}")
            print(f"  Output will be saved to: {output_path}")
            
            # Copy file to output directory
            output_path.write_bytes(file_path.read_bytes())
            target_path = output_path
            result['output_path'] = str(output_path)
        else:
            target_path = file_path
            result['output_path'] = str(file_path)
        
        # Update the file
        if result['file_type'] == 'image':
            success = self.update_image_timestamp(target_path, new_dt)
        else:
            success = self.update_video_timestamp(target_path, new_dt)
        
        if success:
            logger.info(f"{file_path.name}: ✓ Updated successfully")
            print(f"  ✓ Updated successfully")
            result['success'] = True
        else:
            error_msg = "Failed to update"
            logger.error(f"{file_path.name}: ✗ {error_msg}")
            print(f"  ✗ {error_msg}")
            result['error'] = error_msg
        
        return result
    
    def process_directory(self, input_path: Path, target_date: Optional[datetime], 
                        offset: Optional[timedelta], output_dir: Optional[Path] = None,
                        extensions: List[str] = None) -> List[Dict]:
        """Process all files in directory recursively."""
        if extensions is None:
            extensions = ['jpg', 'jpeg', 'tiff', 'tif', 'mp4', 'mov', 'avi', 'mkv', 'm4v']
        
        file_paths = []
        for ext in extensions:
            file_paths.extend(input_path.glob(f'**/*.{ext}'))
            file_paths.extend(input_path.glob(f'**/*.{ext.upper()}'))
        
        logger.info(f"Found {len(file_paths)} files to process")
        print(f"Found {len(file_paths)} files to process")
        
        if self.dry_run:
            print("DRY RUN MODE - No files will be modified")
        
        results = []
        for file_path in file_paths:
            try:
                result = self.process_file(file_path, target_date, offset, output_dir)
                results.append(result)
                self.results.append(result)
                
                # Update statistics
                self.stats['total_files'] += 1
                if result['success']:
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
                    self.stats['errors'] += 1
                
            except Exception as e:
                error_msg = f"Error processing {file_path}: {e}"
                logger.error(error_msg)
                print(f"Error processing {file_path}: {e}")
                self.stats['total_files'] += 1
                self.stats['failed'] += 1
                self.stats['errors'] += 1
        
        return results
    
    def generate_summary(self) -> Dict:
        """Generate detailed summary report."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_files': self.stats['total_files'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': 0,
            'file_types': defaultdict(int),
            'errors': []
        }
        
        if self.stats['total_files'] > 0:
            summary['success_rate'] = (self.stats['successful'] / self.stats['total_files']) * 100
        
        # Analyze results
        for result in self.results:
            summary['file_types'][result['file_type']] += 1
            if result['error']:
                summary['errors'].append({
                    'file': result['file'],
                    'error': result['error']
                })
        
        return summary
    
    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.generate_summary()
        
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        print(f"Total files processed: {summary['total_files']}")
        print(f"Successful: {summary['successful']} ({summary['success_rate']:.1f}%)")
        print(f"Failed: {summary['failed']}")
        
        if summary['file_types']:
            print("\nFile types processed:")
            for file_type, count in summary['file_types'].items():
                print(f"  {file_type}: {count}")
        
        if summary['errors']:
            print(f"\nErrors encountered: {len(summary['errors'])}")
            for error in summary['errors'][:5]:  # Show first 5 errors
                print(f"  {error['file']}: {error['error']}")
            if len(summary['errors']) > 5:
                print(f"  ... and {len(summary['errors']) - 5} more errors")
        
        print("="*60)
        
        # Save detailed report
        report_file = f"timestamp_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': summary,
                'detailed_results': self.results
            }, f, indent=2, default=str)
        
        logger.info(f"Detailed report saved to: {report_file}")
        print(f"📄 Detailed report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced timestamp fixer with detailed logging and summary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix images with offset (593 days, 3 hours)
  python fix_timestamps_enhanced.py --offset-days 593 --offset-hours 3 /path/to/images/

  # Fix with output directory
  python fix_timestamps_enhanced.py --offset-days 593 --offset-hours 3 --output-dir /output /path/to/images/

  # Dry run to see what would change
  python fix_timestamps_enhanced.py --offset-days 593 --offset-hours 3 --dry-run /path/to/images/

  # Process specific file types
  python fix_timestamps_enhanced.py --extensions jpg mp4 --offset-days 593 --offset-hours 3 /path/to/files/
        """
    )
    
    parser.add_argument('path', help='Path to file or directory')
    parser.add_argument('--target-date', help='Set all files to this specific date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--offset-days', type=int, help='Add this many days to current timestamp')
    parser.add_argument('--offset-hours', type=int, help='Add this many hours to current timestamp')
    parser.add_argument('--offset-minutes', type=int, help='Add this many minutes to current timestamp')
    parser.add_argument('--extensions', nargs='+', default=['jpg', 'jpeg', 'tiff', 'tif', 'mp4', 'mov', 'avi', 'mkv', 'm4v'], 
                       help='File extensions to process')
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
    
    # Create output directory if specified
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        print(f"Output directory: {output_dir}")
    
    # Initialize fixer
    fixer = TimestampFixer(dry_run=args.dry_run, no_backup=args.no_backup)
    
    # Process files
    path = Path(args.path)
    if path.is_file():
        result = fixer.process_file(path, target_date, offset, output_dir)
        fixer.results.append(result)
    elif path.is_dir():
        fixer.process_directory(path, target_date, offset, output_dir, args.extensions)
    else:
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    # Print summary
    fixer.print_summary()


if __name__ == '__main__':
    main()
