"""
File utility functions.
"""

# Removed unused import os
from pathlib import Path
from typing import Union, List
import mimetypes


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory

    Returns:
        Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(file_path: Union[str, Path]) -> str:
    """Get the file extension (without dot).

    Args:
        file_path: Path to the file

    Returns:
        File extension without dot
    """
    return Path(file_path).suffix.lstrip('.').lower()


def is_image_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is an image.

    Args:
        file_path: Path to the file

    Returns:
        True if the file is an image
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    return get_file_extension(file_path) in image_extensions


def is_video_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is a video.

    Args:
        file_path: Path to the file

    Returns:
        True if the file is a video
    """
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    return get_file_extension(file_path) in video_extensions


def get_file_size(file_path: Union[str, Path]) -> int:
    """Get the size of a file in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes
    """
    return Path(file_path).stat().st_size


def get_mime_type(file_path: Union[str, Path]) -> str:
    """Get the MIME type of a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


def find_files(directory: Union[str, Path],
               pattern: str = "*",
               recursive: bool = True) -> List[Path]:
    """Find files matching a pattern in a directory.

    Args:
        directory: Directory to search
        pattern: File pattern to match
        recursive: Whether to search recursively

    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def safe_filename(filename: str) -> str:
    """Create a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')

    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')

    # Ensure it's not empty
    if not safe_name:
        safe_name = 'unnamed'

    return safe_name
