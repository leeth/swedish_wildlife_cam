# Camera Timestamp Fix Utility

This utility helps fix incorrect camera timestamps when cameras were set to wrong dates.

## Problem
Cameras were incorrectly set to dates like 2024-01-01, but the actual photos were taken on 2025-09-07. This utility can correct the EXIF timestamps in bulk.

## Installation
```bash
pip install piexif
```

## Usage Examples

### 1. Set all images to a specific date
```bash
python scripts/fix_camera_timestamps.py --target-date "2025-09-07" /path/to/images/
```

### 2. Apply a time offset (add days/hours)
```bash
# Add 250 days to all timestamps
python scripts/fix_camera_timestamps.py --offset-days 250 /path/to/images/

# Add 6 hours to all timestamps  
python scripts/fix_camera_timestamps.py --offset-hours 6 /path/to/images/

# Combine offsets
python scripts/fix_camera_timestamps.py --offset-days 250 --offset-hours 6 /path/to/images/
```

### 3. Dry run to preview changes
```bash
python scripts/fix_camera_timestamps.py --target-date "2025-09-07" --dry-run /path/to/images/
```

### 4. Process specific file types
```bash
python scripts/fix_camera_timestamps.py --extensions jpg jpeg tiff --target-date "2025-09-07" /path/to/images/
```

### 5. Skip backup creation
```bash
python scripts/fix_camera_timestamps.py --target-date "2025-09-07" --no-backup /path/to/images/
```

## Features

- **Multiple timestamp fields**: Updates DateTime, DateTimeOriginal, and DateTimeDigitized
- **Backup creation**: Automatically creates `.backup` files before modification
- **Dry run mode**: Preview changes without modifying files
- **Flexible input**: Works with single files or entire directories
- **Multiple formats**: Supports JPG, JPEG, TIFF, and other image formats
- **Error handling**: Gracefully handles files without EXIF data

## Date Format Options

- `YYYY-MM-DD` (e.g., "2025-09-07")
- `YYYY-MM-DD HH:MM:SS` (e.g., "2025-09-07 14:30:00")

## Example Workflow

1. **Check current timestamps**:
   ```bash
   python scripts/test_timestamp_fix.py
   ```

2. **Preview changes**:
   ```bash
   python scripts/fix_camera_timestamps.py --target-date "2025-09-07" --dry-run /path/to/images/
   ```

3. **Apply fixes**:
   ```bash
   python scripts/fix_camera_timestamps.py --target-date "2025-09-07" /path/to/images/
   ```

## Safety Features

- **Automatic backups**: Original files are backed up with `.backup` extension
- **Dry run mode**: Test changes before applying
- **Error handling**: Continues processing even if some files fail
- **Validation**: Checks for valid date formats and file accessibility

## Common Use Cases

### Camera set to wrong year
```bash
# Camera set to 2024-01-01, actual date is 2025-09-07
python scripts/fix_camera_timestamps.py --target-date "2025-09-07" /path/to/images/
```

### Camera timezone offset
```bash
# Add 2 hours to all timestamps
python scripts/fix_camera_timestamps.py --offset-hours 2 /path/to/images/
```

### Seasonal adjustment
```bash
# Add 6 months (approximately 180 days)
python scripts/fix_camera_timestamps.py --offset-days 180 /path/to/images/
```

## Output

The utility provides detailed feedback:
- Shows current EXIF timestamps
- Displays new timestamps after changes
- Reports success/failure for each file
- Creates backup files automatically
- Shows summary of processed files

## Error Handling

- Files without EXIF data are skipped with warnings
- Invalid date formats are rejected with clear error messages
- Permission errors are handled gracefully
- Corrupted EXIF data is handled without crashing

## Integration with Wildlife Pipeline

This utility works perfectly with the wildlife detection pipeline:

1. **Fix timestamps first**:
   ```bash
   python scripts/fix_camera_timestamps.py --target-date "2025-09-07" /path/to/camera/images/
   ```

2. **Run wildlife detection**:
   ```bash
   python src/wildlife_pipeline/run_pipeline.py --model megadetector /path/to/camera/images/
   ```

The corrected timestamps will be properly extracted and used in the detection pipeline.
