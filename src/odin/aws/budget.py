#!/usr/bin/env python3
"""
Budget Guard System for Wildlife Pipeline

This module provides budget estimation and guard functionality
for the Step Functions workflow to prevent cost overruns.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ComputeMode(Enum):
    """Compute mode for cost estimation."""
    SPOT = "spot"
    ON_DEMAND = "on_demand"
    HYBRID = "hybrid"


@dataclass
class Budget:
    """Budget configuration for pipeline execution."""
    max_dkk: float
    mode: ComputeMode = ComputeMode.HYBRID
    max_runtime_min: int = 60
    max_images: int = 5000
    use_spot: bool = True
    
    def __post_init__(self):
        """Validate budget configuration."""
        if self.max_dkk <= 0:
            raise ValueError("Budget must be positive")
        if self.max_runtime_min <= 0:
            raise ValueError("Max runtime must be positive")
        if self.max_images <= 0:
            raise ValueError("Max images must be positive")


class BudgetExceeded(Exception):
    """Exception raised when estimated cost exceeds budget."""
    pass


def estimate_images_and_rate(input_uri: str) -> Tuple[int, float]:
    """
    Estimate number of images and processing rate.
    
    Args:
        input_uri: S3 URI to input data
        
    Returns:
        Tuple of (estimated_images, seconds_per_image)
    """
    # This is a simplified estimation - in practice, you'd scan S3
    # to count actual images and estimate based on historical data
    
    # Rough estimation based on URI pattern
    if "cam01" in input_uri:
        estimated_images = 1200
        seconds_per_image = 0.8  # Conservative estimate
    elif "cam02" in input_uri:
        estimated_images = 800
        seconds_per_image = 0.6
    else:
        # Default estimation
        estimated_images = 1000
        seconds_per_image = 0.7
    
    logger.info(f"Estimated {estimated_images} images at {seconds_per_image}s per image")
    return estimated_images, seconds_per_image


def calculate_compute_cost(
    images: int, 
    seconds_per_image: float, 
    mode: ComputeMode,
    use_spot: bool = True
) -> float:
    """
    Calculate estimated compute cost in DKK.
    
    Args:
        images: Number of images to process
        seconds_per_image: Processing time per image
        mode: Compute mode
        use_spot: Whether to use spot instances
        
    Returns:
        Estimated cost in DKK
    """
    # AWS pricing (approximate, in DKK)
    # These would be updated with current pricing
    spot_vcpu_hour = 0.15  # DKK per vCPU hour
    on_demand_vcpu_hour = 0.45  # DKK per vCPU hour
    
    # Estimated vCPUs needed
    vcpus = 2  # Standard for wildlife detection
    
    # Total processing time in hours
    total_seconds = images * seconds_per_image
    total_hours = total_seconds / 3600
    
    # Calculate cost based on mode
    if mode == ComputeMode.SPOT or (mode == ComputeMode.HYBRID and use_spot):
        cost_per_hour = vcpus * spot_vcpu_hour
    else:
        cost_per_hour = vcpus * on_demand_vcpu_hour
    
    total_cost = total_hours * cost_per_hour
    
    # Add overhead for Step Functions, Lambda, etc.
    overhead_multiplier = 1.2
    total_cost *= overhead_multiplier
    
    logger.info(f"Estimated cost: {total_cost:.2f} DKK for {images} images")
    return total_cost


def guard_budget(
    budget: Budget, 
    images: int, 
    seconds_per_image: float
) -> Tuple[Dict[str, Any], float]:
    """
    Guard budget and return execution profile.
    
    Args:
        budget: Budget configuration
        images: Number of images to process
        seconds_per_image: Processing time per image
        
    Returns:
        Tuple of (execution_profile, estimated_cost)
        
    Raises:
        BudgetExceeded: If estimated cost exceeds budget
    """
    # Calculate estimated cost
    estimated_cost = calculate_compute_cost(
        images, seconds_per_image, budget.mode, budget.use_spot
    )
    
    # Check if cost exceeds budget
    if estimated_cost > budget.max_dkk:
        raise BudgetExceeded(
            f"Estimated cost {estimated_cost:.2f} DKK exceeds budget {budget.max_dkk} DKK"
        )
    
    # Create execution profile
    profile = {
        "compute_mode": budget.mode.value,
        "use_spot": budget.use_spot,
        "max_images": min(images, budget.max_images),
        "max_runtime_min": budget.max_runtime_min,
        "estimated_cost_dkk": estimated_cost,
        "budget_remaining_dkk": budget.max_dkk - estimated_cost
    }
    
    logger.info(f"Budget check passed: {estimated_cost:.2f} DKK <= {budget.max_dkk} DKK")
    return profile, estimated_cost


def estimate_storage_cost(output_uri: str, estimated_images: int) -> float:
    """
    Estimate storage cost for output data.
    
    Args:
        output_uri: S3 output URI
        estimated_images: Number of images
        
    Returns:
        Estimated storage cost in DKK
    """
    # Rough estimation: 2MB per image for processed data
    estimated_size_gb = (estimated_images * 2) / 1024  # Convert to GB
    
    # S3 pricing (approximate, in DKK per GB per month)
    s3_standard_cost = 0.02  # DKK per GB per month
    
    # Assume data is stored for 1 month
    storage_cost = estimated_size_gb * s3_standard_cost
    
    logger.info(f"Estimated storage cost: {storage_cost:.2f} DKK")
    return storage_cost


def create_execution_profile(
    input_uri: str,
    output_uri: str,
    budget_dkk: float,
    use_spot: bool = True,
    max_images: int = 5000,
    max_job_duration: int = 3600
) -> Dict[str, Any]:
    """
    Create execution profile for Step Functions workflow.
    
    Args:
        input_uri: S3 input URI
        output_uri: S3 output URI
        budget_dkk: Budget in DKK
        use_spot: Whether to use spot instances
        max_images: Maximum number of images
        max_job_duration: Maximum job duration in seconds
        
    Returns:
        Execution profile dictionary
    """
    # Estimate images and processing rate
    images, sec_per_image = estimate_images_and_rate(input_uri)
    
    # Create budget configuration
    budget = Budget(
        max_dkk=budget_dkk,
        mode=ComputeMode.HYBRID,
        max_runtime_min=max_job_duration // 60,
        max_images=max_images,
        use_spot=use_spot
    )
    
    # Guard budget
    profile, estimated_cost = guard_budget(budget, images, sec_per_image)
    
    # Add additional metadata
    profile.update({
        "input_uri": input_uri,
        "output_uri": output_uri,
        "estimated_images": images,
        "seconds_per_image": sec_per_image,
        "session_id": f"run-{hash(input_uri)}"[-8:],
        "intermediate_uri": output_uri.rstrip("/") + "/stage1/",
        "weather_uri": output_uri.rstrip("/") + "/weather/"
    })
    
    return profile

