# Image Tools

This directory contains scripts for image processing and metadata management.

## Scripts

### `fix_camera_timestamps.py`
Utility to correct EXIF timestamps in camera images.

**Usage:**
```bash
# Fix timestamps with offset
python fix_camera_timestamps.py /path/to/images --offset-days 365

# Fix to specific date
python fix_camera_timestamps.py /path/to/images --target-date 2025-08-31

# Dry run
python fix_camera_timestamps.py /path/to/images --dry-run
```

### `test_timestamp_fix.py`
Test script for timestamp correction utility.

**Usage:**
```bash
python test_timestamp_fix.py
```

## Features

- **EXIF Timestamp Correction:** Adjusts DateTimeOriginal, DateTimeDigitized, DateTime
- **Batch Processing:** Recursive directory processing
- **Dry Run Mode:** Preview changes before applying
- **Backup Support:** Creates backup copies
- **GPS Preservation:** Maintains GPS coordinates

## Prerequisites

- Python 3.8+
- Pillow library
- piexif library

## Use Cases

- Correcting camera time settings
- Synchronizing timestamps across cameras
- Preparing images for wildlife pipeline
- Metadata standardization
