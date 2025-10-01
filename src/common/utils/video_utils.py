"""
Video utility functions.
"""

from typing import List, Dict, Any, Union
from pathlib import Path

try:
    import cv2
    # import numpy as np  # Removed unused import
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def extract_frames(video_path: Union[str, Path],
                  output_dir: Union[str, Path],
                  frame_interval: int = 30) -> List[Path]:
    """Extract frames from video at specified intervals.

    Args:
        video_path: Path to video file
        output_dir: Directory to save frames
        frame_interval: Extract every Nth frame

    Returns:
        List of extracted frame paths
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    frame_count = 0
    extracted_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            frame_path = output_dir / f"frame_{frame_count:06d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            extracted_frames.append(frame_path)

        frame_count += 1

    cap.release()
    return extracted_frames


def get_video_info(video_path: Union[str, Path]) -> Dict[str, Any]:
    """Get information about a video file.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with video information
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")

    video_path = Path(video_path)

    cap = cv2.VideoCapture(str(video_path))

    info = {
        'path': str(video_path),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'duration': 0,  # Will be calculated
    }

    if info['fps'] > 0:
        info['duration'] = info['frame_count'] / info['fps']

    cap.release()
    return info


def create_video_from_frames(frames: List[Path],
                            output_path: Union[str, Path],
                            fps: float = 30.0) -> Path:
    """Create video from list of frame images.

    Args:
        frames: List of frame image paths
        output_path: Path for output video
        fps: Frames per second for output video

    Returns:
        Path to created video
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("OpenCV not available. Install opencv-python.")

    if not frames:
        raise ValueError("No frames provided")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get dimensions from first frame
    first_frame = cv2.imread(str(frames[0]))
    height, width, channels = first_frame.shape

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for frame_path in frames:
        frame = cv2.imread(str(frame_path))
        out.write(frame)

    out.release()
    return output_path
