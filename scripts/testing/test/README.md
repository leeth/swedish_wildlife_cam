# Test Scripts

This directory contains test scripts for validating the wildlife pipeline.

## Scripts

### `test_classification_improvement.py`
Tests the improved classification mapping for Swedish wildlife.

**Usage:**
```bash
python test_classification_improvement.py
```

### `test_cloud_architecture.py`
Tests the cloud-optional architecture components.

**Usage:**
```bash
python test_cloud_architecture.py
```

### `test_fox_badger_detection.py`
Tests detection of red fox and badger in images.

**Usage:**
```bash
python test_fox_badger_detection.py
```

### `test_gps_sqlite.py`
Tests GPS extraction and SQLite database integration.

**Usage:**
```bash
python test_gps_sqlite.py
```

### `test_location_tools.py`
Tests the location classification tools.

**Usage:**
```bash
python test_location_tools.py
```

### `test_megadetector.py`
Tests the Swedish Wildlife Detector (MegaDetector).

**Usage:**
```bash
python test_megadetector.py
```

### `test_video_processing.py`
Tests video processing and frame extraction.

**Usage:**
```bash
python test_video_processing.py
```

### `test_wildlife_detection.py`
Tests the basic wildlife detection functionality.

**Usage:**
```bash
python test_wildlife_detection.py
```

## Test Categories

### Unit Tests
- Individual component testing
- Function validation
- Error handling

### Integration Tests
- Component interaction testing
- End-to-end workflows
- System validation

### Performance Tests
- Processing speed validation
- Memory usage testing
- GPU utilization

## Prerequisites

- Python 3.8+
- Test dependencies installed
- Sample test data available
- AWS credentials (for cloud tests)

## Running Tests

```bash
# Run all tests
python -m pytest scripts/test/

# Run specific test
python scripts/test/test_wildlife_detection.py

# Run with verbose output
python -m pytest scripts/test/ -v
```
