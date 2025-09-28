#!/usr/bin/env python3
"""
Test script for video processing functionality.
Demonstrates how to process videos with the Swedish Wildlife Detector.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wildlife_pipeline.video_processor import VideoProcessor, iter_videos
from wildlife_pipeline.megadetector import SwedishWildlifeDetector
from wildlife_pipeline.utils import to_json

def test_video_processing():
    """Test video processing with a sample video"""
    
    print("🎬 Testing Video Processing with Swedish Wildlife Detector")
    print("=" * 60)
    
    # Initialize detector
    print("1. Initializing Swedish Wildlife Detector...")
    detector = SwedishWildlifeDetector(conf=0.25)
    
    # Initialize video processor
    print("2. Setting up video processor...")
    processor = VideoProcessor(
        detector=detector,
        frame_interval=30,  # Every 30th frame (~1 frame per second at 30fps)
        max_frames=20       # Maximum 20 frames per video
    )
    
    # Find video files
    print("3. Looking for video files...")
    video_path = Path("/mnt/c/Users/asbjo/OneDrive/Pictures/Trailcams")
    
    if not video_path.exists():
        print(f"❌ Video directory not found: {video_path}")
        print("Please update the path to your video directory")
        return
    
    video_files = list(iter_videos(video_path))
    
    if not video_files:
        print("❌ No video files found")
        return
    
    print(f"✅ Found {len(video_files)} video files")
    
    # Process first video as example
    test_video = video_files[0]
    print(f"\n4. Processing test video: {test_video.name}")
    
    try:
        # Process video
        video_frames = processor.process_video(test_video)
        
        # Summarize results
        summary = processor.summarize_video_detections(video_frames)
        
        print(f"\n📊 Video Analysis Results:")
        print(f"   Video: {test_video.name}")
        print(f"   Total frames analyzed: {summary['total_frames']}")
        print(f"   Frames with detections: {summary['frames_with_detections']}")
        print(f"   Total detections: {summary['total_detections']}")
        print(f"   Detection rate: {summary['detection_rate']:.1%}")
        
        if summary['species_detected']:
            print(f"\n🦌 Species Detected:")
            for species, count in summary['species_detected'].items():
                print(f"   {species}: {count} detections")
        
        if summary['detection_timeline']:
            print(f"\n⏰ Detection Timeline:")
            for i, detection in enumerate(summary['detection_timeline'][:5]):  # Show first 5
                print(f"   {detection['timestamp']:.1f}s: {detection['species']} (conf: {detection['confidence']:.2f})")
            
            if len(summary['detection_timeline']) > 5:
                print(f"   ... and {len(summary['detection_timeline']) - 5} more detections")
        
        print(f"\n✅ Video processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error processing video: {e}")
    
    finally:
        # Clean up temporary files
        processor.cleanup_temp_files()
        print("🧹 Temporary files cleaned up")

def show_video_processing_tips():
    """Show tips for video processing"""
    
    print("\n💡 Video Processing Tips:")
    print("=" * 40)
    
    tips = [
        "🎯 Frame Interval:",
        "   - 30 frames = ~1 frame per second (default)",
        "   - 15 frames = ~2 frames per second (more detailed)",
        "   - 60 frames = ~1 frame every 2 seconds (faster)",
        "",
        "⚡ Performance:",
        "   - Lower frame interval = faster processing",
        "   - Higher max_frames = more detailed analysis",
        "   - Use SSD storage for faster I/O",
        "",
        "🎬 Supported Formats:",
        "   - MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V",
        "",
        "📊 Output:",
        "   - Video summary with detection statistics",
        "   - Individual frame results with detections",
        "   - Detection timeline with timestamps",
        "",
        "🔧 Usage:",
        "   python -m wildlife_pipeline.run_pipeline \\",
        "     --input /path/to/videos \\",
        "     --output results.csv \\",
        "     --model megadetector \\",
        "     --process-videos \\",
        "     --frame-interval 30 \\",
        "     --max-frames 100"
    ]
    
    for tip in tips:
        print(tip)

def main():
    """Main function"""
    print("🎬 Swedish Wildlife Detector - Video Processing Test")
    print("=" * 60)
    
    try:
        test_video_processing()
        show_video_processing_tips()
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
