"""
Time correction utilities for wildlife camera data.

Handles camera clock drift and timezone corrections for accurate timestamp processing.
"""

import csv
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)


class TimeCorrectionManager:
    """Manages time corrections for wildlife cameras."""
    
    def __init__(self, corrections_file: str = "conf/time_corrections.csv"):
        """Initialize with time corrections file."""
        self.corrections_file = Path(corrections_file)
        self.corrections = self._load_corrections()
        self.audit_log = []
    
    def _load_corrections(self) -> Dict[str, Dict]:
        """Load time corrections from CSV file."""
        corrections = {}
        
        if not self.corrections_file.exists():
            logger.warning(f"Time corrections file not found: {self.corrections_file}")
            return corrections
        
        try:
            with open(self.corrections_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    camera_id = row['camera_id']
                    corrections[camera_id] = {
                        'location': row['location'],
                        'timezone': row['timezone'],
                        'offset_seconds': int(row['offset_seconds']),
                        'clock_drift_ppm': float(row['clock_drift_ppm']),
                        'notes': row['notes']
                    }
            logger.info(f"Loaded time corrections for {len(corrections)} cameras")
        except Exception as e:
            logger.error(f"Error loading time corrections: {e}")
        
        return corrections
    
    def correct_timestamp(self, camera_id: str, original_timestamp: datetime) -> Tuple[datetime, Dict]:
        """
        Apply time corrections to a timestamp.
        
        Args:
            camera_id: Camera identifier
            original_timestamp: Original timestamp from camera
            
        Returns:
            Tuple of (corrected_timestamp, correction_info)
        """
        if camera_id not in self.corrections:
            logger.warning(f"No time corrections found for camera {camera_id}")
            return original_timestamp, {'corrected': False, 'reason': 'no_corrections'}
        
        correction = self.corrections[camera_id]
        
        # Apply timezone correction
        timezone_str = correction['timezone']
        try:
            tz = pytz.timezone(timezone_str)
            # Convert to timezone-aware datetime
            if original_timestamp.tzinfo is None:
                # Assume UTC if no timezone info
                original_timestamp = original_timestamp.replace(tzinfo=timezone.utc)
            
            # Convert to local timezone
            local_time = original_timestamp.astimezone(tz)
            
            # Apply offset correction
            offset_seconds = correction['offset_seconds']
            corrected_time = local_time + timedelta(seconds=offset_seconds)
            
            # Apply clock drift correction (simplified - assumes linear drift)
            drift_ppm = correction['clock_drift_ppm']
            if drift_ppm != 0:
                # Calculate drift correction (simplified model)
                time_since_epoch = (corrected_time - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
                drift_correction = (drift_ppm / 1_000_000) * time_since_epoch
                corrected_time = corrected_time + timedelta(seconds=drift_correction)
            
            # Convert back to UTC for storage
            corrected_utc = corrected_time.astimezone(timezone.utc)
            
            correction_info = {
                'corrected': True,
                'camera_id': camera_id,
                'original_timestamp': original_timestamp.isoformat(),
                'corrected_timestamp': corrected_utc.isoformat(),
                'timezone': timezone_str,
                'offset_seconds': offset_seconds,
                'drift_ppm': drift_ppm,
                'correction_applied': True
            }
            
            # Log correction for audit
            self._log_correction(correction_info)
            
            return corrected_utc, correction_info
            
        except Exception as e:
            logger.error(f"Error applying time correction for camera {camera_id}: {e}")
            return original_timestamp, {'corrected': False, 'reason': f'error: {e}'}
    
    def _log_correction(self, correction_info: Dict):
        """Log time correction for audit trail."""
        self.audit_log.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'correction': correction_info
        })
        
        logger.info(f"Time correction applied: {correction_info}")
    
    def get_audit_log(self) -> List[Dict]:
        """Get audit log of all time corrections."""
        return self.audit_log
    
    def validate_gps_timezone(self, gps_lat: float, gps_lon: float, timestamp: datetime) -> Dict:
        """
        Validate GPS coordinates against Swedish timezones.
        
        Args:
            gps_lat: GPS latitude
            gps_lon: GPS longitude  
            timestamp: Timestamp to validate
            
        Returns:
            Validation result with timezone info
        """
        # Swedish timezone boundaries (simplified)
        sweden_bounds = {
            'lat_min': 55.3, 'lat_max': 69.1,
            'lon_min': 10.6, 'lon_max': 24.2
        }
        
        # Check if coordinates are within Sweden
        in_sweden = (
            sweden_bounds['lat_min'] <= gps_lat <= sweden_bounds['lat_max'] and
            sweden_bounds['lon_min'] <= gps_lon <= sweden_bounds['lon_max']
        )
        
        if not in_sweden:
            return {
                'valid': False,
                'reason': 'coordinates_outside_sweden',
                'gps_lat': gps_lat,
                'gps_lon': gps_lon
            }
        
        # Determine Swedish timezone (simplified)
        # Most of Sweden is in Europe/Stockholm timezone
        swedish_timezone = 'Europe/Stockholm'
        
        # Convert timestamp to Swedish timezone
        tz = pytz.timezone(swedish_timezone)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        swedish_time = timestamp.astimezone(tz)
        
        return {
            'valid': True,
            'timezone': swedish_timezone,
            'swedish_time': swedish_time.isoformat(),
            'utc_time': timestamp.isoformat(),
            'gps_lat': gps_lat,
            'gps_lon': gps_lon
        }
    
    def normalize_to_utc(self, timestamp: datetime, camera_id: str) -> datetime:
        """
        Normalize timestamp to UTC with timezone validation.
        
        Args:
            timestamp: Input timestamp
            camera_id: Camera identifier
            
        Returns:
            UTC normalized timestamp
        """
        if camera_id in self.corrections:
            correction = self.corrections[camera_id]
            timezone_str = correction['timezone']
            
            try:
                tz = pytz.timezone(timezone_str)
                if timestamp.tzinfo is None:
                    # Assume local timezone if no timezone info
                    timestamp = tz.localize(timestamp)
                else:
                    # Convert to local timezone
                    timestamp = timestamp.astimezone(tz)
                
                # Convert to UTC
                return timestamp.astimezone(timezone.utc)
                
            except Exception as e:
                logger.error(f"Error normalizing timezone for camera {camera_id}: {e}")
                return timestamp
        
        # Default to UTC if no corrections
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)


def create_time_corrections_template(output_file: str = "conf/time_corrections_template.csv"):
    """Create a template for time corrections CSV."""
    template_data = [
        {
            'camera_id': 'cam01',
            'location': 'Stockholm',
            'timezone': 'Europe/Stockholm',
            'offset_seconds': '0',
            'clock_drift_ppm': '0',
            'notes': 'Reference camera - no correction needed'
        },
        {
            'camera_id': 'cam02', 
            'location': 'Gothenburg',
            'timezone': 'Europe/Stockholm',
            'offset_seconds': '120',
            'clock_drift_ppm': '5',
            'notes': '2 minutes fast, 5ppm drift'
        }
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['camera_id', 'location', 'timezone', 'offset_seconds', 'clock_drift_ppm', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(template_data)
    
    logger.info(f"Created time corrections template: {output_file}")


if __name__ == "__main__":
    # Example usage
    manager = TimeCorrectionManager()
    
    # Test time correction
    test_timestamp = datetime.now()
    corrected_time, info = manager.correct_timestamp("cam01", test_timestamp)
    print(f"Original: {test_timestamp}")
    print(f"Corrected: {corrected_time}")
    print(f"Info: {info}")
