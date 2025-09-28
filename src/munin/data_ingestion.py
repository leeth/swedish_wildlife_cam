"""
Optimized I/O operations for wildlife pipeline.

This module provides high-performance Python-based I/O operations:
- Fast file walking and hashing with multiprocessing
- Efficient EXIF data extraction with caching
- Parallel image preprocessing with memory optimization
- Batch operations with progress tracking
"""

import hashlib
import multiprocessing as mp
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

try:
    import numpy as np
    import piexif
    from PIL import Image
    from tqdm import tqdm
except ImportError as e:
    print(f"Missing dependencies for optimized I/O: {e}")
    print("Install with: pip install pillow piexif tqdm opencv-python numpy")
    sys.exit(1)

from .logging_config import get_logger

logger = get_logger("wildlife_pipeline.io_optimized")


@dataclass
class FileInfo:
    """File information with metadata."""
    path: str
    size: int
    hash: str
    modified: float
    is_image: bool
    is_video: bool
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None


@dataclass
class ExifData:
    """EXIF data extracted from images."""
    datetime_original: Optional[str] = None
    datetime_digitized: Optional[str] = None
    datetime: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None


@dataclass
class ImagePreprocessResult:
    """Image preprocessing result."""
    path: str
    width: int
    height: int
    channels: int
    format: str
    size_bytes: int
    hash: str
    processed_data: Optional[np.ndarray] = None


class OptimizedFileWalker:
    """High-performance file walking with parallel processing."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.logger = logger

        # Image and video extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}

        self.logger.info(f"🚀 File walker initialized with {self.max_workers} workers")

    def walk_files_parallel(self, root_path: Union[str, Path],
                           extensions: List[str] = None,
                           max_depth: Optional[int] = None) -> List[FileInfo]:
        """
        Walk files in parallel with optimized processing.

        Args:
            root_path: Root directory to walk
            extensions: List of file extensions to include
            max_depth: Maximum directory depth

        Returns:
            List of FileInfo objects
        """
        root_path = Path(root_path)
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {root_path}")

        if extensions is None:
            extensions = list(self.image_extensions | self.video_extensions)

        self.logger.info(f"📁 Walking files in: {root_path}")
        start_time = time.time()

        # Collect all files first
        all_files = []
        for root, dirs, files in os.walk(root_path):
            current_depth = root.count(os.sep) - str(root_path).count(os.sep)
            if max_depth is not None and current_depth >= max_depth:
                dirs.clear()
                continue

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in extensions:
                    all_files.append(file_path)

        self.logger.info(f"📊 Found {len(all_files)} files to process")

        # Process files in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_file, file_path): file_path
                for file_path in all_files
            }

            # Collect results with progress bar
            results = []
            with tqdm(total=len(all_files), desc="Processing files") as pbar:
                for future in as_completed(future_to_path):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        file_path = future_to_path[future]
                        self.logger.warning(f"⚠️  Error processing {file_path}: {e}")
                    finally:
                        pbar.update(1)

        processing_time = time.time() - start_time
        self.logger.info(f"✅ Processed {len(results)} files in {processing_time:.2f}s")

        return results

    def _process_single_file(self, file_path: Path) -> Optional[FileInfo]:
        """Process a single file and return FileInfo."""
        try:
            stat = file_path.stat()

            # Determine file type
            ext = file_path.suffix.lower()
            is_image = ext in self.image_extensions
            is_video = ext in self.video_extensions

            # Get image dimensions if it's an image
            width, height, format = None, None, None
            if is_image:
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        format = img.format
                except Exception:
                    pass  # Skip if image can't be opened

            # Compute hash
            file_hash = self._compute_file_hash(file_path)

            return FileInfo(
                path=str(file_path),
                size=stat.st_size,
                hash=file_hash,
                modified=stat.st_mtime,
                is_image=is_image,
                is_video=is_video,
                width=width,
                height=height,
                format=format
            )

        except Exception as e:
            self.logger.debug(f"Error processing {file_path}: {e}")
            return None

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


class OptimizedExifExtractor:
    """High-performance EXIF data extraction with caching."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".wildlife_cache" / "exif"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

        # Cache for EXIF data
        self._exif_cache = {}
        self._cache_file = self.cache_dir / "exif_cache.pkl"
        self._load_cache()

        self.logger.info("🚀 EXIF extractor initialized with caching")

    def _load_cache(self):
        """Load EXIF cache from disk."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, 'rb') as f:
                    self._exif_cache = pickle.load(f)
                self.logger.info(f"📦 Loaded {len(self._exif_cache)} cached EXIF entries")
            except Exception as e:
                self.logger.warning(f"⚠️  Failed to load EXIF cache: {e}")
                self._exif_cache = {}

    def _save_cache(self):
        """Save EXIF cache to disk."""
        try:
            with open(self._cache_file, 'wb') as f:
                pickle.dump(self._exif_cache, f)
        except Exception as e:
            self.logger.warning(f"⚠️  Failed to save EXIF cache: {e}")

    def extract_exif_data(self, image_path: Union[str, Path]) -> ExifData:
        """Extract EXIF data from image with caching."""
        image_path = Path(image_path)
        cache_key = str(image_path)

        # Check cache first
        if cache_key in self._exif_cache:
            return self._exif_cache[cache_key]

        try:
            # Extract EXIF data
            exif_data = self._extract_exif_from_image(image_path)

            # Cache the result
            self._exif_cache[cache_key] = exif_data

            # Save cache periodically
            if len(self._exif_cache) % 100 == 0:
                self._save_cache()

            return exif_data

        except Exception as e:
            self.logger.debug(f"Error extracting EXIF from {image_path}: {e}")
            return ExifData()

    def _extract_exif_from_image(self, image_path: Path) -> ExifData:
        """Extract EXIF data from image file."""
        exif_data = ExifData()

        try:
            # Use piexif for EXIF extraction
            with open(image_path, 'rb') as f:
                exif_dict = piexif.load(f.read())

            # Extract datetime fields
            if '0th' in exif_dict and piexif.ExifIFD.DateTime in exif_dict['0th']:
                exif_data.datetime = exif_dict['0th'][piexif.ExifIFD.DateTime].decode('utf-8')

            if 'Exif' in exif_dict:
                if piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                    exif_data.datetime_original = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                if piexif.ExifIFD.DateTimeDigitized in exif_dict['Exif']:
                    exif_data.datetime_digitized = exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized].decode('utf-8')

            # Extract GPS coordinates
            if 'GPS' in exif_dict:
                lat, lon = self._extract_gps_coordinates(exif_dict['GPS'])
                if lat is not None and lon is not None:
                    exif_data.gps_latitude = lat
                    exif_data.gps_longitude = lon

            # Extract camera info
            if '0th' in exif_dict:
                if piexif.ImageIFD.Make in exif_dict['0th']:
                    exif_data.camera_make = exif_dict['0th'][piexif.ImageIFD.Make].decode('utf-8')
                if piexif.ImageIFD.Model in exif_dict['0th']:
                    exif_data.camera_model = exif_dict['0th'][piexif.ImageIFD.Model].decode('utf-8')

            # Extract image dimensions
            if '0th' in exif_dict:
                if piexif.ImageIFD.ImageWidth in exif_dict['0th']:
                    exif_data.image_width = exif_dict['0th'][piexif.ImageIFD.ImageWidth]
                if piexif.ImageIFD.ImageLength in exif_dict['0th']:
                    exif_data.image_height = exif_dict['0th'][piexif.ImageIFD.ImageLength]

        except Exception as e:
            self.logger.debug(f"Error extracting EXIF from {image_path}: {e}")

        return exif_data

    def _extract_gps_coordinates(self, gps_dict: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS coordinates from GPS EXIF data."""
        try:
            # Extract latitude
            if piexif.GPSIFD.GPSLatitude in gps_dict and piexif.GPSIFD.GPSLatitudeRef in gps_dict:
                lat = self._convert_dms_to_decimal(gps_dict[piexif.GPSIFD.GPSLatitude])
                lat_ref = gps_dict[piexif.GPSIFD.GPSLatitudeRef].decode('utf-8')
                if lat_ref == 'S':
                    lat = -lat
            else:
                lat = None

            # Extract longitude
            if piexif.GPSIFD.GPSLongitude in gps_dict and piexif.GPSIFD.GPSLongitudeRef in gps_dict:
                lon = self._convert_dms_to_decimal(gps_dict[piexif.GPSIFD.GPSLongitude])
                lon_ref = gps_dict[piexif.GPSIFD.GPSLongitudeRef].decode('utf-8')
                if lon_ref == 'W':
                    lon = -lon
            else:
                lon = None

            return lat, lon

        except Exception:
            return None, None

    def _convert_dms_to_decimal(self, dms_tuple: Tuple) -> float:
        """Convert degrees, minutes, seconds to decimal degrees."""
        try:
            degrees = dms_tuple[0][0] / dms_tuple[0][1]
            minutes = dms_tuple[1][0] / dms_tuple[1][1]
            seconds = dms_tuple[2][0] / dms_tuple[2][1]
            return degrees + minutes / 60.0 + seconds / 3600.0
        except Exception:
            return 0.0

    def extract_exif_batch(self, image_paths: List[Union[str, Path]]) -> Dict[str, ExifData]:
        """Extract EXIF data from multiple images in parallel."""
        self.logger.info(f"📸 Extracting EXIF from {len(image_paths)} images")

        results = {}
        with ThreadPoolExecutor(max_workers=min(len(image_paths), 8)) as executor:
            future_to_path = {
                executor.submit(self.extract_exif_data, path): path
                for path in image_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    exif_data = future.result()
                    results[str(path)] = exif_data
                except Exception as e:
                    self.logger.warning(f"⚠️  Error extracting EXIF from {path}: {e}")

        # Save cache after batch processing
        self._save_cache()

        self.logger.info(f"✅ Extracted EXIF from {len(results)} images")
        return results


class OptimizedImageProcessor:
    """High-performance image preprocessing with memory optimization."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 4)
        self.logger = logger

        self.logger.info(f"🚀 Image processor initialized with {self.max_workers} workers")

    def preprocess_image(self, image_path: Union[str, Path],
                        target_width: int = 640,
                        target_height: int = 640,
                        normalize: bool = True,
                        format: str = "RGB") -> ImagePreprocessResult:
        """Preprocess single image with optimization."""
        image_path = Path(image_path)

        try:
            # Load image
            with Image.open(image_path) as img:
                original_width, original_height = img.size

                # Convert format if needed
                if format and img.mode != format:
                    img = img.convert(format)

                # Resize image
                resized = img.resize((target_width, target_height), Image.LANCZOS)

                # Convert to numpy array
                img_array = np.array(resized)

                # Normalize if requested
                if normalize:
                    img_array = img_array.astype(np.float32) / 255.0

                # Compute hash
                img_hash = hashlib.sha256(img_array.tobytes()).hexdigest()

                return ImagePreprocessResult(
                    path=str(image_path),
                    width=target_width,
                    height=target_height,
                    channels=img_array.shape[2] if len(img_array.shape) == 3 else 1,
                    format=format,
                    size_bytes=img_array.nbytes,
                    hash=img_hash,
                    processed_data=img_array
                )

        except Exception as e:
            self.logger.error(f"❌ Error preprocessing {image_path}: {e}")
            raise

    def preprocess_images_batch(self, image_paths: List[Union[str, Path]],
                               target_width: int = 640,
                               target_height: int = 640,
                               normalize: bool = True,
                               format: str = "RGB") -> List[ImagePreprocessResult]:
        """Preprocess multiple images in parallel."""
        self.logger.info(f"🖼️  Preprocessing {len(image_paths)} images")

        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(
                    self.preprocess_image,
                    path,
                    target_width,
                    target_height,
                    normalize,
                    format
                ): path
                for path in image_paths
            }

            # Collect results with progress bar
            with tqdm(total=len(image_paths), desc="Preprocessing images") as pbar:
                for future in as_completed(future_to_path):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        path = future_to_path[future]
                        self.logger.warning(f"⚠️  Error preprocessing {path}: {e}")
                    finally:
                        pbar.update(1)

        self.logger.info(f"✅ Preprocessed {len(results)} images")
        return results

    def compute_hashes_parallel(self, file_paths: List[Union[str, Path]]) -> Dict[str, str]:
        """Compute hashes for multiple files in parallel."""
        self.logger.info(f"🔐 Computing hashes for {len(file_paths)} files")

        results = {}
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._compute_file_hash, Path(path)): path
                for path in file_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_hash = future.result()
                    results[str(path)] = file_hash
                except Exception as e:
                    self.logger.warning(f"⚠️  Error computing hash for {path}: {e}")

        self.logger.info(f"✅ Computed hashes for {len(results)} files")
        return results

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


def main():
    """Test the optimized I/O operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Optimized I/O Operations")
    parser.add_argument("input_path", help="Input directory or file")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--workers", type=int, help="Number of workers")
    parser.add_argument("--extract-exif", action="store_true", help="Extract EXIF data")
    parser.add_argument("--preprocess", action="store_true", help="Preprocess images")
    parser.add_argument("--compute-hashes", action="store_true", help="Compute file hashes")

    args = parser.parse_args()

    input_path = Path(args.input_path)

    if input_path.is_file():
        # Process single file
        if args.extract_exif:
            extractor = OptimizedExifExtractor()
            exif_data = extractor.extract_exif_data(input_path)
            print(f"EXIF data: {exif_data}")

        if args.preprocess:
            processor = OptimizedImageProcessor()
            result = processor.preprocess_image(input_path)
            print(f"Preprocessed: {result}")

    else:
        # Process directory
        walker = OptimizedFileWalker(max_workers=args.workers)
        files = walker.walk_files_parallel(input_path)

        print(f"Found {len(files)} files")

        if args.extract_exif:
            image_files = [f for f in files if f.is_image]
            if image_files:
                extractor = OptimizedExifExtractor()
                exif_results = extractor.extract_exif_batch([f.path for f in image_files])
                print(f"Extracted EXIF from {len(exif_results)} images")

        if args.preprocess:
            image_files = [f for f in files if f.is_image]
            if image_files:
                processor = OptimizedImageProcessor()
                results = processor.preprocess_images_batch([f.path for f in image_files])
                print(f"Preprocessed {len(results)} images")

        if args.compute_hashes:
            processor = OptimizedImageProcessor()
            hashes = processor.compute_hashes_parallel([f.path for f in files])
            print(f"Computed hashes for {len(hashes)} files")


if __name__ == "__main__":
    main()
