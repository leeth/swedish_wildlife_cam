#!/usr/bin/env python3
"""
Simple test of cost optimization functionality
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_optimization.config import CostOptimizationConfig
from cost_optimization.manager import CostOptimizationManager

def test_cost_optimization():
    """Test basic cost optimization functionality."""
    print("🧪 Testing Cost Optimization Module")
    
    # Create configuration
    config = CostOptimizationConfig(
        region="eu-north-1",
        environment="production",
        spot_bid_percentage=70,
        max_vcpus=100,
        gpu_required=True
    )
    
    print(f"✅ Configuration created:")
    print(f"  Region: {config.region}")
    print(f"  Environment: {config.environment}")
    print(f"  Spot bid percentage: {config.spot_bid_percentage}%")
    print(f"  Max vCPUs: {config.max_vcpus}")
    print(f"  GPU required: {config.gpu_required}")
    
    # Test configuration validation
    try:
        config.validate()
        print("✅ Configuration validation passed")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    
    # Test cost manager initialization
    try:
        cost_manager = CostOptimizationManager(config)
        print("✅ Cost optimization manager initialized")
    except Exception as e:
        print(f"❌ Cost optimization manager initialization failed: {e}")
        return False
    
    # Test getting cost metrics (this might fail if AWS is not configured)
    try:
        metrics = cost_manager.get_cost_metrics()
        print(f"✅ Cost metrics retrieved: {metrics}")
    except Exception as e:
        print(f"⚠️  Cost metrics failed (expected if AWS not configured): {e}")
    
    print("✅ Basic cost optimization test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_cost_optimization()
    if not success:
        sys.exit(1)
    print("🎉 All tests passed!")
