# Video Processing Guide

## Overview

The Swedish Wildlife Detector now supports video processing! This allows you to analyze video files from camera traps and extract wildlife detections from video frames.

## Supported Video Formats

The pipeline supports these video formats:
- **MP4** (.mp4) - Most common camera trap format
- **AVI** (.avi) - Traditional video format
- **MOV** (.mov) - Apple QuickTime format
- **MKV** (.mkv) - Matroska format
- **WMV** (.wmv) - Windows Media format
- **FLV** (.flv) - Flash video format
- **WebM** (.webm) - Web video format
- **M4V** (.m4v) - iTunes video format

## How Video Processing Works

1. **Frame Extraction**: Videos are processed by extracting frames at regular intervals
2. **Frame Analysis**: Each extracted frame is analyzed using the Swedish Wildlife Detector
3. **Detection Summary**: Results are summarized per video and per frame
4. **Temporary Storage**: Frames are temporarily saved for analysis, then cleaned up

## Usage

### Basic Video Processing

```bash
# Process both images and videos
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/camera_traps \
  --output /path/to/output.csv \
  --model megadetector \
  --process-videos \
  --conf-thres 0.25
```

### Video-Specific Options

```bash
# Customize video processing
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/camera_traps \
  --output /path/to/output.csv \
  --model megadetector \
  --process-videos \
  --frame-interval 15 \    # Extract every 15th frame (more frequent)
  --max-frames 200 \       # Extract up to 200 frames per video
  --conf-thres 0.25
```

### Frame Interval Guidelines

- **30 frames** (default): ~1 frame per second at 30fps
- **15 frames**: ~2 frames per second at 30fps
- **60 frames**: ~1 frame every 2 seconds at 30fps
- **10 frames**: ~3 frames per second at 30fps

## Output Format

### Video Summary Row
Each video gets a summary row with:
```csv
file_path,file_type,camera_id,timestamp,total_frames,frames_with_detections,total_detections,detection_rate,species_detected,detection_timeline,observation_any
/path/video.mp4,video,camera_1,2025-08-24T20:44:25,100,15,23,0.15,"{""moose"": 12, ""boar"": 8, ""roedeer"": 3}","[{""timestamp"": 5.2, ""species"": ""moose"", ""confidence"": 0.85}]",True
```

### Individual Frame Rows
Frames with detections also get individual rows:
```csv
image_path,file_type,video_source,frame_number,frame_timestamp,camera_id,timestamp,observation_any,observations,top_label,top_confidence
/tmp/frame_000150.jpg,video_frame,/path/video.mp4,150,5.0,camera_1,2025-08-24T20:44:25,True,"[{""label"": ""moose"", ""confidence"": 0.85, ""bbox"": [100, 200, 300, 400]}]",moose,0.85
```

## Performance Considerations

### Processing Speed
- **Frame extraction**: ~1-2 seconds per video minute
- **Detection analysis**: Depends on model and hardware
- **Memory usage**: Temporary frames stored in system temp directory

### Optimization Tips
1. **Lower frame interval** for faster processing (fewer frames)
2. **Higher confidence threshold** for fewer false positives
3. **Limit max frames** for very long videos
4. **Use SSD storage** for faster frame I/O

## Example Workflow

### 1. Quick Scan
```bash
# Quick scan with fewer frames
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/videos \
  --output quick_scan.csv \
  --model megadetector \
  --process-videos \
  --frame-interval 60 \
  --max-frames 50
```

### 2. Detailed Analysis
```bash
# Detailed analysis with more frames
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/videos \
  --output detailed_analysis.csv \
  --model megadetector \
  --process-videos \
  --frame-interval 15 \
  --max-frames 200 \
  --conf-thres 0.25
```

### 3. Mixed Content
```bash
# Process both images and videos in same folder
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/mixed_content \
  --output all_detections.csv \
  --model megadetector \
  --process-videos \
  --frame-interval 30
```

## Troubleshooting

### Common Issues

1. **"Could not open video file"**
   - Check if video file is corrupted
   - Ensure video codec is supported
   - Try converting to MP4 format

2. **"No frames extracted"**
   - Video might be very short
   - Check frame interval setting
   - Verify video has valid frames

3. **Slow processing**
   - Reduce frame interval
   - Lower max frames limit
   - Use faster storage

4. **Memory issues**
   - Reduce max frames
   - Process videos in smaller batches
   - Check available system memory

### Video Quality Tips

1. **Good lighting** improves detection accuracy
2. **Stable camera** reduces motion blur
3. **Proper resolution** (1080p or higher recommended)
4. **Clear view** of wildlife areas

## Advanced Usage

### Custom Frame Extraction
```python
from wildlife_pipeline.video_processor import VideoProcessor
from wildlife_pipeline.megadetector import SwedishWildlifeDetector

# Custom video processing
detector = SwedishWildlifeDetector(conf=0.25)
processor = VideoProcessor(
    detector=detector,
    frame_interval=10,  # Every 10th frame
    max_frames=500      # Up to 500 frames
)

# Process single video
video_frames = processor.process_video(Path("video.mp4"))
summary = processor.summarize_video_detections(video_frames)
```

### Batch Processing
```bash
# Process multiple folders
for folder in camera_folders; do
    python -m wildlife_pipeline.run_pipeline \
      --input "$folder" \
      --output "${folder}_results.csv" \
      --model megadetector \
      --process-videos
done
```

The video processing feature makes it easy to analyze camera trap videos and extract valuable wildlife detection data from your video recordings!

