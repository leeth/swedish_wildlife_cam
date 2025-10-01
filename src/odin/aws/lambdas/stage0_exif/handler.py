#!/usr/bin/env python3
"""
Simple Stage 0 EXIF Lambda Handler for testing
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple Lambda handler for Stage 0 EXIF processing.
    """
    logger.info(f"Stage 0 EXIF handler invoked with event: {json.dumps(event)}")
    
    # Simulate EXIF processing
    result = event.copy()
    result.update({
        "stage0_output_uri": event["input_uri"],
        "intermediate_uri": event["output_uri"],
        "processed_files": 1,
        "exif_data": {"timestamp": "2024-09-30T21:00:00Z", "camera": "test-camera"}
    })
    
    logger.info("Stage 0 EXIF processing completed")
    return result
