#!/usr/bin/env python3
"""
Guard Budget Lambda Handler

This Lambda function validates budget constraints before starting
the wildlife pipeline workflow.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from odin.budget import create_execution_profile, BudgetExceeded

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda handler for budget guard.
    
    Args:
        event: Step Functions input event
        context: Lambda context
        
    Returns:
        Updated event with budget validation results
        
    Raises:
        BudgetExceeded: If budget constraints are violated
    """
    logger.info(f"Guard Budget handler invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters from event
        input_uri = event["input_uri"]
        output_uri = event["output_uri"]
        budget_dkk = event["budget_dkk"]
        use_spot = event.get("use_spot", True)
        max_images = event.get("max_images", 5000)
        max_job_duration = event.get("max_job_duration", 3600)
        
        # Create execution profile with budget validation
        profile = create_execution_profile(
            input_uri=input_uri,
            output_uri=output_uri,
            budget_dkk=budget_dkk,
            use_spot=use_spot,
            max_images=max_images,
            max_job_duration=max_job_duration
        )
        
        # Update event with profile
        event.update(profile)
        
        logger.info(f"Budget validation passed: {profile['estimated_cost_dkk']:.2f} DKK")
        return event
        
    except BudgetExceeded as e:
        logger.error(f"Budget exceeded: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in budget guard: {e}")
        raise e

