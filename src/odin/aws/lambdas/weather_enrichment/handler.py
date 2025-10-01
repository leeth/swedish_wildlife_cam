#!/usr/bin/env python3
"""
Simple Weather Enrichment Lambda Handler for testing
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple Lambda handler for weather enrichment.
    """
    logger.info(f"Weather Enrichment handler invoked with event: {json.dumps(event)}")

    # Simulate weather enrichment
    result = event.copy()
    result.update({
        "weather_data": {
            "temperature": 15.5,
            "humidity": 65,
            "conditions": "partly_cloudy"
        },
        "enriched_detections": 1
    })

    logger.info("Weather enrichment completed")
    return result
