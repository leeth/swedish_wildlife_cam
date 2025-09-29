#!/usr/bin/env python3
"""
Stage 0 EXIF Lambda Handler

This Lambda function handles EXIF data extraction and time correction
for the wildlife pipeline.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from munin.exif_extractor import get_timestamp_from_exif, _exif_from_pil, _exif_from_exifread

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run_exif_stage0(input_uri: str, time_offsets_file: str = "conf/time_offsets.yaml"):
    """
    Run EXIF stage 0 processing.
    
    Args:
        input_uri: S3 URI to input images
        time_offsets_file: Path to time offsets configuration
        
    Returns:
        Dictionary with output URI and processing results
    """
    logger.info(f"Starting EXIF stage 0 for {input_uri}")
    
    # This is a simplified implementation
    # In practice, you'd download images from S3, process them, and upload results
    
    # For now, return the input URI as output URI
    # In a real implementation, you'd process the images and upload to a new location
    output_uri = input_uri.replace("/raw/", "/processed/")
    
    result = {
        "output_uri": output_uri,
        "processed_images": 0,  # Would be actual count
        "exif_errors": 0,
        "time_corrections": 0
    }
    
    logger.info(f"EXIF stage 0 completed: {result}")
    return result


def handler(event, context):
    """
    Lambda handler for EXIF stage 0.
    
    Args:
        event: Step Functions input event
        context: Lambda context
        
    Returns:
        Updated event with EXIF processing results
    """
    logger.info(f"Stage 0 EXIF handler invoked with event: {json.dumps(event)}")
    
    try:
        input_uri = event["input_uri"]
        
        # Run EXIF processing
        result = run_exif_stage0(input_uri)
        
        # Update event with results
        event["stage0_output_uri"] = result["output_uri"]
        event["stage0_results"] = result
        
        logger.info(f"Stage 0 EXIF completed successfully")
        return event
        
    except Exception as e:
        logger.error(f"Error in EXIF stage 0: {e}")
        raise e

