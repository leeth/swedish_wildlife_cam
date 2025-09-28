"""
Cost Optimization Manager

This module provides the core cost optimization functionality that can be used
by both Munin and Hugin for infrastructure lifecycle management.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import boto3

from .config import CostOptimizationConfig

logger = logging.getLogger(__name__)


class CostOptimizationManager:
    """Manages cost-optimized infrastructure lifecycle."""

    def __init__(self, config: CostOptimizationConfig):
        self.config = config
        self.batch = boto3.client('batch', region_name=config.region)
        self.ec2 = boto3.client('ec2', region_name=config.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=config.region)

        # Resource names
        self.compute_env_name = f"wildlife-detection-compute-{config.environment}"
        self.job_queue_name = f"wildlife-detection-queue-{config.environment}"
        self.job_def_name = f"wildlife-detection-job-{config.environment}"

    def setup_infrastructure(self, job_count: int = 1, gpu_required: bool = None) -> bool:
        """Set up cost-optimized infrastructure for batch processing."""
        try:
            if gpu_required is None:
                gpu_required = self.config.gpu_required

            logger.info(f"Setting up cost-optimized infrastructure for {job_count} jobs")
            logger.info(f"GPU required: {gpu_required}")
            logger.info(f"Spot bid percentage: {self.config.spot_bid_percentage}%")

            # Calculate required vCPUs based on job count
            vcpus_per_job = 4 if gpu_required else 2
            desired_vcpus = min(job_count * vcpus_per_job, self.config.max_vcpus)

            # Select optimal instance type
            instance_type, instance_strategy = self._select_optimal_instance_type(gpu_required)
            logger.info(f"Selected instance type: {instance_type} ({instance_strategy})")

            # Scale up compute environment
            success = self._scale_compute_environment(desired_vcpus)
            if not success:
                return False

            # Wait for compute environment to be ready
            logger.info("Waiting for compute environment to be ready...")
            self._wait_for_compute_environment_ready()

            logger.info("✅ Infrastructure setup completed")
            return True

        except Exception as e:
            logger.error(f"Error setting up infrastructure: {e}")
            return False

    def teardown_infrastructure(self) -> bool:
        """Tear down infrastructure to save costs."""
        try:
            logger.info("Tearing down cost-optimized infrastructure")

            # Scale down compute environment to 0
            success = self._scale_compute_environment(0)
            if not success:
                return False

            # Wait for instances to terminate
            logger.info("Waiting for instances to terminate...")
            self._wait_for_compute_environment_empty()

            logger.info("✅ Infrastructure teardown completed")
            return True

        except Exception as e:
            logger.error(f"Error tearing down infrastructure: {e}")
            return False

    def get_compute_environment_status(self) -> Dict:
        """Get current status of compute environment."""
        try:
            response = self.batch.describe_compute_environments(
                computeEnvironments=[self.compute_env_name]
            )
            if response['computeEnvironments']:
                return response['computeEnvironments'][0]
            return {}
        except Exception as e:
            logger.error(f"Error getting compute environment status: {e}")
            return {}

    def get_cost_metrics(self) -> Dict:
        """Get cost metrics for the infrastructure."""
        try:
            # Get compute environment status
            status = self.get_compute_environment_status()
            compute_resources = status.get('computeResources', {})

            # Calculate estimated costs
            instance_count = compute_resources.get('desiredvCpus', 0) // 4  # Assuming 4 vCPUs per instance
            instance_type = 'g4dn.xlarge'  # Default instance type

            # Get pricing
            spot_pricing = self._get_spot_pricing([instance_type])
            on_demand_pricing = self._get_on_demand_pricing([instance_type])

            spot_price = spot_pricing.get(instance_type, 0.0)
            on_demand_price = on_demand_pricing.get(instance_type, 0.0)

            # Calculate hourly costs
            spot_cost_per_hour = instance_count * spot_price
            on_demand_cost_per_hour = instance_count * on_demand_price
            savings_per_hour = on_demand_cost_per_hour - spot_cost_per_hour

            return {
                'instance_count': instance_count,
                'instance_type': instance_type,
                'spot_price_per_hour': spot_price,
                'on_demand_price_per_hour': on_demand_price,
                'spot_cost_per_hour': spot_cost_per_hour,
                'on_demand_cost_per_hour': on_demand_cost_per_hour,
                'savings_per_hour': savings_per_hour,
                'savings_percentage': (savings_per_hour / on_demand_cost_per_hour * 100) if on_demand_cost_per_hour > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting cost metrics: {e}")
            return {}

    def _scale_compute_environment(self, desired_vcpus: int) -> bool:
        """Scale compute environment to desired vCPUs."""
        try:
            logger.info(f"Scaling compute environment to {desired_vcpus} vCPUs")
            response = self.batch.update_compute_environment(
                computeEnvironment=self.compute_env_name,
                desiredvCpus=desired_vcpus
            )
            logger.info(f"Compute environment scaling initiated: {response}")
            return True
        except Exception as e:
            logger.error(f"Error scaling compute environment: {e}")
            return False

    def _select_optimal_instance_type(self, required_gpu: bool = True) -> Tuple[str, str]:
        """Select optimal instance type based on spot availability and pricing."""
        try:
            # GPU instance types in order of preference (cost vs performance)
            gpu_instance_types = [
                'g4dn.xlarge',    # Cheapest GPU instance
                'g4dn.2xlarge',  # Good balance
                'g4dn.4xlarge',  # More powerful
                'g4dn.8xlarge',   # High performance
                'p3.2xlarge',    # Latest generation
                'p3.8xlarge'     # Maximum performance
            ]

            if not required_gpu:
                # Non-GPU instances for non-GPU workloads
                instance_types = ['t3.medium', 't3.large', 't3.xlarge', 'm5.large', 'm5.xlarge']
            else:
                instance_types = gpu_instance_types

            # Get current pricing
            spot_pricing = self._get_spot_pricing(instance_types)
            on_demand_pricing = self._get_on_demand_pricing(instance_types)

            # Calculate cost savings
            best_spot = None
            best_on_demand = None
            max_savings = 0

            for instance_type in instance_types:
                if instance_type in spot_pricing and instance_type in on_demand_pricing:
                    spot_price = spot_pricing[instance_type]
                    on_demand_price = on_demand_pricing[instance_type]
                    savings = (on_demand_price - spot_price) / on_demand_price

                    if savings > max_savings:
                        max_savings = savings
                        best_spot = instance_type

                    if not best_on_demand:
                        best_on_demand = instance_type

            # Return spot instance if savings > threshold, otherwise on-demand
            if max_savings > self.config.cost_threshold_percentage and best_spot:
                return best_spot, 'spot'
            else:
                return best_on_demand or instance_types[0], 'on-demand'

        except Exception as e:
            logger.error(f"Error selecting optimal instance type: {e}")
            return 'g4dn.xlarge', 'on-demand'

    def _get_spot_pricing(self, instance_types: List[str], availability_zone: str = None) -> Dict[str, float]:
        """Get current spot pricing for instance types."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            response = self.ec2.describe_spot_price_history(
                InstanceTypes=instance_types,
                ProductDescriptions=['Linux/UNIX'],
                StartTime=start_time,
                EndTime=end_time,
                MaxResults=100
            )

            pricing = {}
            for price in response['SpotPriceHistory']:
                instance_type = price['InstanceType']
                if instance_type not in pricing or price['SpotPrice'] < pricing[instance_type]:
                    pricing[instance_type] = float(price['SpotPrice'])

            return pricing
        except Exception as e:
            logger.error(f"Error getting spot pricing: {e}")
            return {}

    def _get_on_demand_pricing(self, instance_types: List[str]) -> Dict[str, float]:
        """Get on-demand pricing for instance types."""
        try:
            # This would typically use AWS Pricing API or a pricing service
            # For now, return estimated pricing
            on_demand_pricing = {
                'g4dn.xlarge': 0.526,
                'g4dn.2xlarge': 0.752,
                'g4dn.4xlarge': 1.204,
                'g4dn.8xlarge': 2.176,
                'p3.2xlarge': 3.06,
                'p3.8xlarge': 12.24,
                't3.medium': 0.0416,
                't3.large': 0.0832,
                't3.xlarge': 0.1664,
                'm5.large': 0.096,
                'm5.xlarge': 0.192
            }
            return {instance_type: on_demand_pricing.get(instance_type, 1.0)
                   for instance_type in instance_types}
        except Exception as e:
            logger.error(f"Error getting on-demand pricing: {e}")
            return {}

    def _wait_for_compute_environment_ready(self, timeout_minutes: int = 10):
        """Wait for compute environment to be ready."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            status = self.get_compute_environment_status()
            if status.get('status') == 'VALID':
                logger.info("Compute environment is ready")
                return True
            logger.info(f"Compute environment status: {status.get('status', 'UNKNOWN')}")
            time.sleep(30)

        logger.warning("Compute environment did not become ready in time")
        return False

    def _wait_for_compute_environment_empty(self, timeout_minutes: int = 10):
        """Wait for compute environment to be empty."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            status = self.get_compute_environment_status()
            desired_vcpus = status.get('computeResources', {}).get('desiredvCpus', 0)
            if desired_vcpus == 0:
                logger.info("Compute environment is empty")
                return True
            logger.info(f"Compute environment desired vCPUs: {desired_vcpus}")
            time.sleep(30)

        logger.warning("Compute environment did not empty in time")
        return False
