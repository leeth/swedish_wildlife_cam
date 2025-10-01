#!/usr/bin/env python3
"""
Simple Stage 2 Post Lambda Handler for testing
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple Lambda handler for Stage 2 post-processing.
    """
    logger.info(f"Stage 2 Post handler invoked with event: {json.dumps(event)}")
    
    # Simulate post-processing
    result = event.copy()
    result.update({
        "stage2_output_uri": event["output_uri"],
        "detections": 1,
        "clusters": 1,
        "species_detected": ["test-species"]
    })
    
    logger.info("Stage 2 post-processing completed")
    return result
