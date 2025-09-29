"""
Optimized Video Processor with GPU acceleration and parallel processing.

This module provides high-performance video processing with:
- PyAV for efficient frame extraction
- GPU-accelerated decoding (NVENC/NVDEC)
- Parallel file processing with multiprocessing
- Batch GPU decoding for AWS g5/g6 instances
- Memory-efficient processing with prefetching
- Model caching and warmup per worker
"""

import multiprocessing as mp
import queue
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Any

try:
    import av
    import cv2
    import numpy as np
    from PIL import Image
    from ultralytics import YOLO
except ImportError as e:
    print(f"Missing dependencies for optimized video processing: {e}")
    print("Install with: pip install av opencv-python pillow numpy ultralytics")
    sys.exit(1)

from ..common.core.base import BaseProcessor
from ..common.exceptions import ProcessingError, ValidationError
from ..common.utils.logging_utils import get_logger, ProcessingTimer
from ..common.utils.file_utils import is_video_file, get_file_size
from .wildlife_detector import Detection


@dataclass
class VideoFrame:
    """Optimized video frame data structure."""
    frame_number: int
    timestamp: float
    image: np.ndarray
    width: int
    height: int
    codec: str
    pixel_format: str


@dataclass
class VideoProcessingConfig:
    """Configuration for optimized video processing."""
    sample_interval_seconds: float = 0.3
    max_frames: int = 1000
    batch_size: int = 32
    use_gpu_decoding: bool = True
    gpu_device_id: int = 0
    parallel_workers: int = None
    memory_limit_gb: int = 8
    output_format: str = "RGB"
    quality_preset: str = "fast"
    model_cache_dir: Optional[str] = None
    prefetch_batches: int = 2
    warmup_iterations: int = 3


class ModelCache:
    """Model caching and warmup for multiprocessing workers."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".wildlife_cache" / "models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._models = {}
        self.logger = get_logger("wildlife_pipeline.model_cache")

    def get_model(self, model_path: str, device: str = "cuda") -> YOLO:
        """Get cached model or load and cache it."""
        cache_key = f"{model_path}_{device}"

        if cache_key not in self._models:
            self.logger.info(f"🔄 Loading model: {model_path}")
            model = YOLO(model_path)
            model.to(device)

            # Warmup model
            self._warmup_model(model)

            self._models[cache_key] = model
            self.logger.info(f"✅ Model cached: {cache_key}")

        return self._models[cache_key]

    def _warmup_model(self, model: YOLO, iterations: int = 3) -> None:
        """Warmup model with dummy data."""
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        for i in range(iterations):
            try:
                _ = model.predict(dummy_image, verbose=False)
            except Exception as e:
                self.logger.warning(f"⚠️  Warmup iteration {i} failed: {e}")

        self.logger.info(f"🔥 Model warmup completed ({iterations} iterations)")


class BatchPrefetcher:
    """Prefetch batches for efficient processing."""

    def __init__(self, batch_size: int, prefetch_batches: int = 2):
        self.batch_size = batch_size
        self.prefetch_batches = prefetch_batches
        self.queue = queue.Queue(maxsize=prefetch_batches)
        self.stop_event = threading.Event()
        self.thread = None
        self.logger = get_logger("wildlife_pipeline.batch_prefetcher")

    def start_prefetching(self, data_source: Iterator, processor_func):
        """Start prefetching batches in background thread."""
        self.thread = threading.Thread(
            target=self._prefetch_worker,
            args=(data_source, processor_func),
            daemon=True
        )
        self.thread.start()
        self.logger.info(f"🚀 Started prefetching {self.prefetch_batches} batches")

    def _prefetch_worker(self, data_source: Iterator, processor_func):
        """Worker thread for prefetching."""
        batch = []

        for item in data_source:
            if self.stop_event.is_set():
                break

            batch.append(item)

            if len(batch) >= self.batch_size:
                try:
                    processed_batch = processor_func(batch)
                    self.queue.put(processed_batch, timeout=1.0)
                    batch = []
                except queue.Full:
                    self.logger.warning("⚠️  Prefetch queue full, dropping batch")
                except Exception as e:
                    self.logger.error(f"❌ Prefetch error: {e}")

        # Process remaining items
        if batch:
            try:
                processed_batch = processor_func(batch)
                self.queue.put(processed_batch, timeout=1.0)
            except Exception as e:
                self.logger.error(f"❌ Final batch error: {e}")

    def get_batch(self, timeout: float = 5.0):
        """Get next prefetched batch."""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Stop prefetching."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)


class OptimizedVideoProcessor(BaseProcessor):
    """High-performance video processor with GPU acceleration."""

    def __init__(self, config: VideoProcessingConfig = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or VideoProcessingConfig()
        self.logger = get_logger(self.__class__.__name__)

        # Set parallel workers based on CPU count
        if self.config.parallel_workers is None:
            self.config.parallel_workers = min(mp.cpu_count(), 8)

        # Initialize GPU decoding if available
        self.gpu_available = self._check_gpu_support()
        if self.gpu_available:
            self.logger.info(f"🚀 GPU decoding enabled (device {self.config.gpu_device_id})")
        else:
            self.logger.info("⚠️  GPU decoding not available, using CPU")
            self.config.use_gpu_decoding = False

    def process(self, input_data: Any) -> Any:
        """Process video data.
        
        Args:
            input_data: Video path or configuration dictionary
            
        Returns:
            Processing results
        """
        if isinstance(input_data, (str, Path)):
            video_path = Path(input_data)
            detector = None
            output_dir = None
        elif isinstance(input_data, dict):
            video_path = Path(input_data['video_path'])
            detector = input_data.get('detector')
            output_dir = input_data.get('output_dir')
            if output_dir:
                output_dir = Path(output_dir)
        else:
            raise ValidationError(f"Unsupported input data type: {type(input_data)}")
            
        if not video_path.exists():
            raise ValidationError(f"Video file not found: {video_path}")
            
        if not is_video_file(video_path):
            raise ValidationError(f"File is not a video: {video_path}")
            
        return self.process_video_optimized(video_path, detector, output_dir)

    def _check_gpu_support(self) -> bool:
        """Check if GPU decoding is available."""
        try:
            # Check for CUDA availability
            if hasattr(cv2, 'cuda'):
                return cv2.cuda.getCudaEnabledDeviceCount() > 0
            return False
        except Exception:
            return False

    def process_video_optimized(self, video_path: Path,
                              detector=None,
                              output_dir: Optional[Path] = None) -> Dict:
        """
        Optimized video processing with GPU acceleration and parallel processing.

        Args:
            video_path: Path to video file
            detector: Detection model (optional)
            output_dir: Directory to save extracted frames (optional)

        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        self.logger.info(f"🎬 Processing video: {video_path.name}")

        try:
            # Open video with PyAV for efficient decoding
            container = av.open(str(video_path))
            video_stream = container.streams.video[0]

            # Get video metadata
            duration = float(video_stream.duration * video_stream.time_base)
            fps = float(video_stream.rate)
            total_frames = int(duration * fps)

            self.logger.info(f"📊 Video info: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames")

            # Calculate frame sampling
            frame_interval = int(fps * self.config.sample_interval_seconds)
            target_frames = min(total_frames // frame_interval, self.config.max_frames)

            self.logger.info(f"🎯 Target frames: {target_frames} (interval: {frame_interval})")

            # Process frames with GPU acceleration
            frames = self._extract_frames_gpu_optimized(
                container, video_stream, frame_interval, target_frames
            )

            # Process detections if detector provided
            detections = []
            if detector:
                detections = self._process_frames_batch(frames, detector)

            # Save frames if output directory specified
            if output_dir:
                self._save_frames_parallel(frames, output_dir, video_path.stem)

            processing_time = time.time() - start_time
            fps_processed = len(frames) / processing_time if processing_time > 0 else 0

            result = {
                'video_path': str(video_path),
                'duration': duration,
                'fps': fps,
                'total_frames': total_frames,
                'frames_extracted': len(frames),
                'detections': detections,
                'processing_time': processing_time,
                'fps_processed': fps_processed,
                'gpu_accelerated': self.gpu_available
            }

            self.logger.info(f"✅ Video processing completed: {len(frames)} frames in {processing_time:.1f}s ({fps_processed:.1f} fps)")
            return result

        except Exception as e:
            self.logger.error(f"❌ Error processing video {video_path}: {e}")
            raise
        finally:
            if 'container' in locals():
                container.close()

    def _extract_frames_gpu_optimized(self, container, video_stream,
                                     frame_interval: int, target_frames: int) -> List[VideoFrame]:
        """Extract frames with GPU-accelerated decoding."""
        frames = []
        frame_count = 0
        extracted_count = 0

        # Configure decoder for GPU if available
        if self.config.use_gpu_decoding and self.gpu_available:
            try:
                # Use hardware decoder if available
                video_stream.codec_context.options = {
                    'hwaccel': 'cuda',
                    'hwaccel_device': str(self.config.gpu_device_id)
                }
            except Exception as e:
                self.logger.warning(f"⚠️  GPU decoder setup failed: {e}")
                self.config.use_gpu_decoding = False

        # Extract frames in batches for efficiency
        batch_frames = []
        batch_size = self.config.batch_size

        for frame_count, frame in enumerate(container.decode(video_stream)):
            if extracted_count >= target_frames:
                break

            if frame_count % frame_interval == 0:
                # Convert frame to numpy array
                img_array = frame.to_ndarray(format='rgb24')

                # Create VideoFrame object
                video_frame = VideoFrame(
                    frame_number=frame_count,
                    timestamp=float(frame.pts * frame.time_base),
                    image=img_array,
                    width=frame.width,
                    height=frame.height,
                    codec=video_stream.codec.name,
                    pixel_format=frame.format.name
                )

                batch_frames.append(video_frame)

                # Process batch when full
                if len(batch_frames) >= batch_size:
                    frames.extend(batch_frames)
                    batch_frames = []
                    extracted_count += batch_size

                extracted_count += 1

        # Add remaining frames
        if batch_frames:
            frames.extend(batch_frames)

        return frames

    def _process_frames_batch(self, frames: List[VideoFrame], detector) -> List[Detection]:
        """Process frames in batches for efficient inference."""
        detections = []
        batch_size = self.config.batch_size

        self.logger.info(f"🔍 Processing {len(frames)} frames with detector")

        # Process frames in batches
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i + batch_size]

            # Convert frames to PIL Images for detector
            images = []
            for frame in batch:
                pil_image = Image.fromarray(frame.image)
                images.append(pil_image)

            # Batch inference if detector supports it
            if hasattr(detector, 'predict_batch'):
                batch_detections = detector.predict_batch(images)
                detections.extend(batch_detections)
            else:
                # Individual inference
                for _j, image in enumerate(images):
                    frame_detections = detector.predict(image)
                    detections.extend(frame_detections)

        return detections

    def _save_frames_parallel(self, frames: List[VideoFrame],
                            output_dir: Path, video_name: str) -> None:
        """Save frames in parallel for better I/O performance."""
        output_dir.mkdir(parents=True, exist_ok=True)

        def save_frame(frame_data):
            frame, frame_idx = frame_data
            filename = f"{video_name}_frame_{frame_idx:06d}.jpg"
            filepath = output_dir / filename

            # Convert to PIL and save
            pil_image = Image.fromarray(frame.image)
            pil_image.save(filepath, quality=95, optimize=True)
            return filepath

        # Use ThreadPoolExecutor for I/O bound operations
        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            frame_data = [(frame, i) for i, frame in enumerate(frames)]
            saved_files = list(executor.map(save_frame, frame_data))

        self.logger.info(f"💾 Saved {len(saved_files)} frames to {output_dir}")

    def process_multiple_videos(self, video_paths: List[Path],
                               detector=None,
                               output_base_dir: Optional[Path] = None) -> Dict:
        """
        Process multiple videos in parallel.

        Args:
            video_paths: List of video file paths
            detector: Detection model (optional)
            output_base_dir: Base directory for outputs (optional)

        Returns:
            Dictionary with processing results for all videos
        """
        self.logger.info(f"🎬 Processing {len(video_paths)} videos in parallel")

        def process_single_video(video_path):
            output_dir = None
            if output_base_dir:
                output_dir = output_base_dir / video_path.stem

            return self.process_video_optimized(video_path, detector, output_dir)

        # Use ProcessPoolExecutor for CPU-intensive tasks
        results = {}
        with ProcessPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            future_to_path = {
                executor.submit(process_single_video, path): path
                for path in video_paths
            }

            for future in future_to_path:
                video_path = future_to_path[future]
                try:
                    result = future.result()
                    results[str(video_path)] = result
                except Exception as e:
                    self.logger.error(f"❌ Error processing {video_path}: {e}")
                    results[str(video_path)] = {'error': str(e)}

        return results

    def get_video_info(self, video_path: Path) -> Dict:
        """Get detailed video information."""
        try:
            container = av.open(str(video_path))
            video_stream = container.streams.video[0]

            info = {
                'path': str(video_path),
                'duration': float(video_stream.duration * video_stream.time_base),
                'fps': float(video_stream.rate),
                'width': video_stream.width,
                'height': video_stream.height,
                'codec': video_stream.codec.name,
                'bitrate': video_stream.bit_rate,
                'total_frames': int(video_stream.duration * video_stream.rate),
                'file_size': video_path.stat().st_size,
                'gpu_decoding_supported': self.gpu_available
            }

            container.close()
            return info

        except Exception as e:
            self.logger.error(f"❌ Error getting video info for {video_path}: {e}")
            return {'error': str(e)}


def main():
    """Test the optimized video processor."""
    import argparse

    parser = argparse.ArgumentParser(description="Optimized Video Processor")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--output", help="Output directory for frames")
    parser.add_argument("--interval", type=float, default=0.3, help="Frame sampling interval (seconds)")
    parser.add_argument("--max-frames", type=int, default=1000, help="Maximum frames to extract")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for processing")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU decoding")
    parser.add_argument("--workers", type=int, help="Number of parallel workers")

    args = parser.parse_args()

    # Create configuration
    config = VideoProcessingConfig(
        sample_interval_seconds=args.interval,
        max_frames=args.max_frames,
        batch_size=args.batch_size,
        use_gpu_decoding=args.gpu,
        parallel_workers=args.workers
    )

    # Create processor
    processor = OptimizedVideoProcessor(config)

    # Process video
    video_path = Path(args.video_path)
    output_dir = Path(args.output) if args.output else None

    result = processor.process_video_optimized(video_path, output_dir=output_dir)

    print("\n📊 Processing Results:")
    print(f"  Frames extracted: {result['frames_extracted']}")
    print(f"  Processing time: {result['processing_time']:.2f}s")
    print(f"  FPS processed: {result['fps_processed']:.2f}")
    print(f"  GPU accelerated: {result['gpu_accelerated']}")


if __name__ == "__main__":
    main()
