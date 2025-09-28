from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import exifread
from PIL import ExifTags, Image

if TYPE_CHECKING:
    from pathlib import Path


def _exif_from_pil(path: Path) -> dict[str, Any]:
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

def _exif_from_exifread(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False, strict=True)
        # Convert Tags to str
        return {str(k): str(v) for k, v in tags.items()}
    except Exception:
        return {}

def get_timestamp_from_exif(exif: dict[str, Any]) -> datetime | None:
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

def extract_exif(path: Path) -> dict[str, Any]:
    exif = _exif_from_pil(path)
    if not exif:
        exif = _exif_from_exifread(path)
    return exif or {}

def get_gps_from_exif(exif: dict[str, Any]) -> tuple[float, float] | None:
    """
    Extract GPS coordinates from EXIF data.
    Returns (latitude, longitude) in decimal degrees, or None if not found.
    """
    if not exif:
        return None

    # Try to get GPS data from different sources
    gps_data = exif.get('GPSInfo') or exif.get('GPS')
    if not gps_data:
        return None

    try:
        # Handle different GPS data formats
        if isinstance(gps_data, dict):
            # PIL format
            lat_ref = gps_data.get(1, 'N')  # North/South
            lat = gps_data.get(2, (0, 0, 0))  # (degrees, minutes, seconds)
            lon_ref = gps_data.get(3, 'E')  # East/West
            lon = gps_data.get(4, (0, 0, 0))  # (degrees, minutes, seconds)
        else:
            # exifread format
            lat_ref = gps_data.get('GPS GPSLatitudeRef', 'N')
            lat = gps_data.get('GPS GPSLatitude', (0, 0, 0))
            lon_ref = gps_data.get('GPS GPSLongitudeRef', 'E')
            lon = gps_data.get('GPS GPSLongitude', (0, 0, 0))

        # Convert DMS to decimal degrees
        def dms_to_decimal(dms_tuple, ref):
            if not dms_tuple or len(dms_tuple) != 3:
                return 0.0

            degrees, minutes, seconds = dms_tuple
            if isinstance(degrees, tuple):
                degrees = degrees[0] / degrees[1] if degrees[1] != 0 else 0
            if isinstance(minutes, tuple):
                minutes = minutes[0] / minutes[1] if minutes[1] != 0 else 0
            if isinstance(seconds, tuple):
                seconds = seconds[0] / seconds[1] if seconds[1] != 0 else 0

            decimal = degrees + minutes/60.0 + seconds/3600.0
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal

        latitude = dms_to_decimal(lat, lat_ref)
        longitude = dms_to_decimal(lon, lon_ref)

        # Validate coordinates
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return (latitude, longitude)
        else:
            return None

    except Exception:
        return None

def best_timestamp(path: Path, exif: dict[str, Any]) -> datetime:
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
