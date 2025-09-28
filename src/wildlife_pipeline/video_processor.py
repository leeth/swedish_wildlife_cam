from __future__ import annotations
from typing import List, Dict, Any, Optional, Iterator, Tuple
from pathlib import Path
import cv2
import tempfile
import os
from dataclasses import dataclass
import numpy as np

from .detector import BaseDetector, Detection

@dataclass
class VideoFrame:
    """Represents a single frame from a video"""
    frame_number: int
    timestamp: float  # seconds from start of video
    image_path: Optional[Path] = None
    detections: List[Detection] = None

class VideoProcessor:
    """
    Process videos for wildlife detection by extracting frames and analyzing them.
    """
    
    def __init__(self, detector: BaseDetector, frame_interval: int = 30, 
                 max_frames: int = 100, temp_dir: Optional[Path] = None):
        """
        Initialize video processor.
        
        Args:
            detector: Wildlife detector to use for frame analysis
            frame_interval: Extract every Nth frame (default: every 30th frame = ~1 frame per second at 30fps)
            max_frames: Maximum number of frames to extract per video
            temp_dir: Directory to store temporary frame images
        """
        self.detector = detector
        self.frame_interval = frame_interval
        self.max_frames = max_frames
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "wildlife_video_frames"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def process_video(self, video_path: Path) -> List[VideoFrame]:
        """
        Process a video file and extract frames for wildlife detection.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of VideoFrame objects with detections
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Open video file
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            print(f"Processing video: {video_path.name}")
            print(f"  Duration: {duration:.1f} seconds")
            print(f"  FPS: {fps:.1f}")
            print(f"  Total frames: {total_frames}")
            print(f"  Extracting every {self.frame_interval}th frame")
            
            frames = []
            frame_count = 0
            extracted_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at specified interval
                if frame_count % self.frame_interval == 0 and extracted_count < self.max_frames:
                    timestamp = frame_count / fps if fps > 0 else 0
                    
                    # Save frame as temporary image
                    frame_filename = f"{video_path.stem}_frame_{frame_count:06d}.jpg"
                    frame_path = self.temp_dir / frame_filename
                    
                    cv2.imwrite(str(frame_path), frame)
                    
                    # Analyze frame for wildlife
                    detections = self.detector.predict(frame_path)
                    
                    # Create VideoFrame object
                    video_frame = VideoFrame(
                        frame_number=frame_count,
                        timestamp=timestamp,
                        image_path=frame_path,
                        detections=detections
                    )
                    
                    frames.append(video_frame)
                    extracted_count += 1
                    
                    # Print progress
                    if extracted_count % 10 == 0:
                        print(f"  Extracted {extracted_count} frames...")
                
                frame_count += 1
            
            print(f"  Completed: {len(frames)} frames analyzed")
            return frames
            
        finally:
            cap.release()
    
    def summarize_video_detections(self, video_frames: List[VideoFrame]) -> Dict[str, Any]:
        """
        Summarize detections across all frames in a video.
        
        Args:
            video_frames: List of VideoFrame objects from video processing
            
        Returns:
            Summary dictionary with detection statistics
        """
        if not video_frames:
            return {
                "total_frames": 0,
                "frames_with_detections": 0,
                "total_detections": 0,
                "species_detected": {},
                "detection_timeline": []
            }
        
        # Collect all detections
        all_detections = []
        frames_with_detections = 0
        species_count = {}
        
        for frame in video_frames:
            if frame.detections:
                frames_with_detections += 1
                all_detections.extend(frame.detections)
                
                # Count species
                for det in frame.detections:
                    species = det.label
                    species_count[species] = species_count.get(species, 0) + 1
        
        # Create detection timeline
        timeline = []
        for frame in video_frames:
            if frame.detections:
                for det in frame.detections:
                    timeline.append({
                        "timestamp": frame.timestamp,
                        "frame": frame.frame_number,
                        "species": det.label,
                        "confidence": det.confidence
                    })
        
        return {
            "total_frames": len(video_frames),
            "frames_with_detections": frames_with_detections,
            "total_detections": len(all_detections),
            "species_detected": species_count,
            "detection_timeline": timeline,
            "detection_rate": frames_with_detections / len(video_frames) if video_frames else 0
        }
    
    def cleanup_temp_files(self):
        """Clean up temporary frame images"""
        if self.temp_dir.exists():
            for file in self.temp_dir.glob("*.jpg"):
                try:
                    file.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete {file}: {e}")

def iter_videos(input_root: Path, video_exts: List[str] = None) -> Iterator[Path]:
    """
    Iterate through video files in the input directory.
    
    Args:
        input_root: Root directory to search
        video_exts: List of video file extensions (default: common video formats)
    
    Yields:
        Path to video files
    """
    if video_exts is None:
        video_exts = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"]
    
    root = Path(input_root)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in video_exts:
            yield p
