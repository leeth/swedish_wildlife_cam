from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import os
from PIL import Image, ExifTags
import exifread

def _exif_from_pil(path: Path) -> Dict[str, Any]:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return {}
            result = {}
            for k, v in exif.items():
                tag = ExifTags.TAGS.get(k, k)
                result[tag] = v
            return result
    except Exception:
        return {}

def _exif_from_exifread(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False, strict=True)
        # Convert Tags to str
        return {str(k): str(v) for k, v in tags.items()}
    except Exception:
        return {}

def get_timestamp_from_exif(exif: Dict[str, Any]) -> Optional[datetime]:
    if not exif:
        return None
    
    # Try common tags
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        value = exif.get(key)
        if value:
            # PIL often returns "YYYY:MM:DD HH:MM:SS"
            try:
                dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                return dt.replace(tzinfo=timezone.utc)  # naive -> UTC (best effort)
            except Exception:
                # exifread keys are like "EXIF DateTimeOriginal"
                if " " in key:
                    alt = exif.get(f"EXIF {key}")
                    if alt:
                        try:
                            dt = datetime.strptime(str(alt), "%Y:%m:%d %H:%M:%S")
                            return dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            pass
    return None

def extract_exif(path: Path) -> Dict[str, Any]:
    exif = _exif_from_pil(path)
    if not exif:
        exif = _exif_from_exifread(path)
    return exif or {}

def best_timestamp(path: Path, exif: Dict[str, Any]) -> datetime:
    ts = get_timestamp_from_exif(exif)
    if ts:
        return ts
    # Fallback to filesystem mtime
    stat = os.stat(path)
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

def infer_camera_id(image_path: Path, input_root: Path) -> str:
    """
    Camera id = first directory under input_root.
    e.g. input_root/camera_A/2025-08/img.jpg -> camera_A
    """
    rel = image_path.relative_to(input_root)
    parts = rel.parts
    return parts[0] if len(parts) > 1 else parts[0]  # first folder under root
