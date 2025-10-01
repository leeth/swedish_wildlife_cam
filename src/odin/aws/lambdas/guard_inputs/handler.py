import json
import logging
import jsonschema
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Validate input schema for wildlife pipeline using JSON Schema.

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
        },
        "images": {
            "count": 100,
            "max_images": 1000
        }
    }
    """
    try:
        # Load JSON Schema
        schema_path = Path(__file__).parent.parent.parent / "conf" / "input.schema.json"
        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Validate against JSON Schema
        jsonschema.validate(instance=event, schema=schema)

        # Additional business logic validation
        if "images" in event:
            images = event["images"]
            if images["count"] > images["max_images"]:
                raise ValueError(f"Image count ({images['count']}) exceeds max_images ({images['max_images']})")

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
            "images": event.get("images"),
            "session_id": event["run_id"],  # For compatibility
            "validated_at": context.aws_request_id,
            "status": "validated"
        }

    except jsonschema.ValidationError as e:
        logger.error(f"JSON Schema validation failed: {e.message}")
        raise Exception("InvalidInput") from e
    except Exception as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise Exception("InvalidInput") from e
