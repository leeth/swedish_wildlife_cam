#!/usr/bin/env python3
"""
Simple Guard Budget Lambda Handler for testing
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple Lambda handler for budget guard.
    """
    logger.info(f"Guard Budget handler invoked with event: {json.dumps(event)}")

    # Simple budget validation
    budget_dkk = event.get("budget_dkk", 0)
    estimated_cost = 5.0  # Simulated cost

    if estimated_cost > budget_dkk:
        raise Exception("BudgetExceeded: Estimated cost exceeds budget")

    # Update event with profile
    result = event.copy()
    result.update({
        "estimated_cost_dkk": estimated_cost,
        "session_id": "test-session-123",
        "stage0_output_uri": event["input_uri"],
        "intermediate_uri": event["output_uri"]
    })

    logger.info(f"Budget validation passed: {estimated_cost:.2f} DKK")
    return result
