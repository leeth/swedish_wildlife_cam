"""
Utility functions for the wildlife pipeline.
"""

from .file_utils import (
    ensure_directory,
    get_file_extension,
    is_image_file,
    is_video_file,
    get_file_size,
)
# Image utilities are conditionally available
try:
    from .image_utils import (
        load_image,
        save_image,
        resize_image,
        normalize_image,
        get_image_info,
    )
    IMAGE_UTILS_AVAILABLE = True
except ImportError:
    IMAGE_UTILS_AVAILABLE = False
# Video utilities are conditionally available
try:
    from .video_utils import (
        extract_frames,
        get_video_info,
        create_video_from_frames,
    )
    VIDEO_UTILS_AVAILABLE = True
except ImportError:
    VIDEO_UTILS_AVAILABLE = False
from .logging_utils import (
    setup_logging,
    get_logger,
    log_processing_start,
    log_processing_end,
)

__all__ = [
    # File utilities
    "ensure_directory",
    "get_file_extension",
    "is_image_file",
    "is_video_file", 
    "get_file_size",
    # Image utilities
    "load_image",
    "save_image",
    "resize_image",
    "normalize_image",
    "get_image_info",
    # Video utilities
    "extract_frames",
    "get_video_info",
    "create_video_from_frames",
    # Logging utilities
    "setup_logging",
    "get_logger",
    "log_processing_start",
    "log_processing_end",
]
