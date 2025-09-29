import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Validate input schema for wildlife pipeline.
    
    Expected input:
    {
        "run_id": "string",
        "input_uri": "s3://bucket/path/",
        "output_uri": "s3://bucket/path/",
        "budget_dkk": 25,
        "use_spot": true,
        "max_job_duration": 1800,
        "coordinates": {
            "lat": 59.9139,
            "lon": 10.7522
        }
    }
    """
    try:
        # Validate required fields
        required_fields = [
            "run_id", "input_uri", "output_uri", 
            "budget_dkk", "use_spot", "max_job_duration"
        ]
        
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate data types
        if not isinstance(event["run_id"], str) or not event["run_id"].strip():
            raise ValueError("run_id must be a non-empty string")
        
        if not isinstance(event["input_uri"], str) or not event["input_uri"].startswith("s3://"):
            raise ValueError("input_uri must be a valid S3 URI")
        
        if not isinstance(event["output_uri"], str) or not event["output_uri"].startswith("s3://"):
            raise ValueError("output_uri must be a valid S3 URI")
        
        if not isinstance(event["budget_dkk"], (int, float)) or event["budget_dkk"] <= 0:
            raise ValueError("budget_dkk must be a positive number")
        
        if not isinstance(event["use_spot"], bool):
            raise ValueError("use_spot must be a boolean")
        
        if not isinstance(event["max_job_duration"], int) or event["max_job_duration"] <= 0:
            raise ValueError("max_job_duration must be a positive integer")
        
        # Validate coordinates if provided
        if "coordinates" in event:
            coords = event["coordinates"]
            if not isinstance(coords, dict):
                raise ValueError("coordinates must be a dictionary")
            
            if "lat" not in coords or "lon" not in coords:
                raise ValueError("coordinates must contain lat and lon")
            
            lat, lon = coords["lat"], coords["lon"]
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                raise ValueError("lat and lon must be numbers")
            
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("Invalid latitude or longitude values")
        
        logger.info(f"Input validation successful for run_id: {event['run_id']}")
        
        # Return validated input with additional metadata
        return {
            "run_id": event["run_id"],
            "input_uri": event["input_uri"],
            "output_uri": event["output_uri"],
            "budget_dkk": event["budget_dkk"],
            "use_spot": event["use_spot"],
            "max_job_duration": event["max_job_duration"],
            "coordinates": event.get("coordinates"),
            "session_id": event["run_id"],  # For compatibility
            "validated_at": context.aws_request_id,
            "status": "validated"
        }
        
    except Exception as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise Exception("InvalidInput") from e
