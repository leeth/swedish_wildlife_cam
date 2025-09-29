"""
GPS Utilities for Wildlife Pipeline

Common GPS distance calculations and proximity functions.
"""

import math
from typing import Tuple

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates in kilometers using Haversine formula.
    
    Args:
        lat1, lon1: First GPS coordinates
        lat2, lon2: Second GPS coordinates
    
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    earth_radius_km = 6371.0
    
    return earth_radius_km * c

def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates in meters using Haversine formula.
    
    Args:
        lat1, lon1: First GPS coordinates
        lat2, lon2: Second GPS coordinates
    
    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in meters
    earth_radius_m = 6371000.0
    
    return earth_radius_m * c

def is_within_proximity(lat1: float, lon1: float, lat2: float, lon2: float, 
                       radius_km: float) -> bool:
    """
    Check if two GPS coordinates are within specified radius.
    
    Args:
        lat1, lon1: First GPS coordinates
        lat2, lon2: Second GPS coordinates
        radius_km: Proximity radius in kilometers
    
    Returns:
        True if coordinates are within radius
    """
    distance = calculate_distance_km(lat1, lon1, lat2, lon2)
    return distance <= radius_km

def parse_cache_key(cache_key: str) -> Tuple[float, float]:
    """
    Parse cache key to extract GPS coordinates.
    
    Args:
        cache_key: Cache key in format "lat_lon"
    
    Returns:
        Tuple of (latitude, longitude)
    """
    if '_' not in cache_key:
        raise ValueError(f"Invalid cache key format: {cache_key}")
    
    lat_str, lon_str = cache_key.split('_', 1)
    return float(lat_str), float(lon_str)
