#!/usr/bin/env python3
"""
Cost Optimization Infrastructure Manager

This script manages the lifecycle of AWS infrastructure for cost optimization:
- Sets up infrastructure when starting a batch job
- Tears down infrastructure when jobs are complete
- Manages spot instances with fallback to on-demand
- Implements batch-oriented resource management
"""

import boto3
import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CostOptimizationManager:
    """Manages cost-optimized infrastructure lifecycle."""
    
    def __init__(self, region: str = "eu-north-1", environment: str = "production"):
        self.region = region
        self.environment = environment
        self.batch = boto3.client('batch', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
        # Resource names
        self.compute_env_name = f"wildlife-detection-compute-{environment}"
        self.job_queue_name = f"wildlife-detection-queue-{environment}"
        self.job_def_name = f"wildlife-detection-job-{environment}"
        
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
    
    def scale_compute_environment(self, desired_vcpus: int) -> bool:
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
    
    def get_spot_pricing(self, instance_types: List[str], availability_zone: str = None) -> Dict[str, float]:
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
    
    def get_on_demand_pricing(self, instance_types: List[str]) -> Dict[str, float]:
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
                'p3.8xlarge': 12.24
            }
            return {instance_type: on_demand_pricing.get(instance_type, 1.0) 
                   for instance_type in instance_types}
        except Exception as e:
            logger.error(f"Error getting on-demand pricing: {e}")
            return {}
    
    def select_optimal_instance_type(self, required_gpu: bool = True) -> Tuple[str, str]:
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
            spot_pricing = self.get_spot_pricing(instance_types)
            on_demand_pricing = self.get_on_demand_pricing(instance_types)
            
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
            
            # Return spot instance if savings > 50%, otherwise on-demand
            if max_savings > 0.5 and best_spot:
                return best_spot, 'spot'
            else:
                return best_on_demand or instance_types[0], 'on-demand'
                
        except Exception as e:
            logger.error(f"Error selecting optimal instance type: {e}")
            return 'g4dn.xlarge', 'on-demand'
    
    def setup_infrastructure(self, job_count: int = 1, gpu_required: bool = True) -> bool:
        """Set up infrastructure for batch processing."""
        try:
            logger.info(f"Setting up infrastructure for {job_count} jobs")
            
            # Calculate required vCPUs based on job count
            # Assume 4 vCPUs per job for GPU instances
            vcpus_per_job = 4 if gpu_required else 2
            desired_vcpus = min(job_count * vcpus_per_job, 100)  # Cap at 100 vCPUs
            
            # Select optimal instance type
            instance_type, instance_strategy = self.select_optimal_instance_type(gpu_required)
            logger.info(f"Selected instance type: {instance_type} ({instance_strategy})")
            
            # Scale up compute environment
            success = self.scale_compute_environment(desired_vcpus)
            if not success:
                return False
            
            # Wait for compute environment to be ready
            logger.info("Waiting for compute environment to be ready...")
            self._wait_for_compute_environment_ready()
            
            logger.info("Infrastructure setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up infrastructure: {e}")
            return False
    
    def teardown_infrastructure(self) -> bool:
        """Tear down infrastructure to save costs."""
        try:
            logger.info("Tearing down infrastructure")
            
            # Scale down compute environment to 0
            success = self.scale_compute_environment(0)
            if not success:
                return False
            
            # Wait for instances to terminate
            logger.info("Waiting for instances to terminate...")
            self._wait_for_compute_environment_empty()
            
            logger.info("Infrastructure teardown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error tearing down infrastructure: {e}")
            return False
    
    def submit_batch_job(self, job_name: str, job_parameters: Dict = None) -> str:
        """Submit a batch job to the queue."""
        try:
            logger.info(f"Submitting batch job: {job_name}")
            
            response = self.batch.submit_job(
                jobName=job_name,
                jobQueue=self.job_queue_name,
                jobDefinition=self.job_def_name,
                parameters=job_parameters or {}
            )
            
            job_id = response['jobId']
            logger.info(f"Job submitted successfully: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error submitting batch job: {e}")
            return None
    
    def wait_for_job_completion(self, job_id: str, timeout_minutes: int = 120) -> str:
        """Wait for job completion and return final status."""
        try:
            logger.info(f"Waiting for job completion: {job_id}")
            start_time = time.time()
            timeout_seconds = timeout_minutes * 60
            
            while time.time() - start_time < timeout_seconds:
                response = self.batch.describe_jobs(jobs=[job_id])
                if response['jobs']:
                    job = response['jobs'][0]
                    status = job['jobStatus']
                    
                    if status in ['SUCCEEDED', 'FAILED']:
                        logger.info(f"Job {job_id} completed with status: {status}")
                        return status
                    
                    logger.info(f"Job {job_id} status: {status}")
                    time.sleep(30)  # Check every 30 seconds
                else:
                    logger.warning(f"Job {job_id} not found")
                    return 'NOT_FOUND'
            
            logger.warning(f"Job {job_id} timed out after {timeout_minutes} minutes")
            return 'TIMEOUT'
            
        except Exception as e:
            logger.error(f"Error waiting for job completion: {e}")
            return 'ERROR'
    
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
            spot_pricing = self.get_spot_pricing([instance_type])
            on_demand_pricing = self.get_on_demand_pricing([instance_type])
            
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


def main():
    """Main CLI for cost optimization manager."""
    parser = argparse.ArgumentParser(description="Cost Optimization Infrastructure Manager")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--environment", default="production", help="Environment name")
    parser.add_argument("--action", required=True, 
                       choices=['setup', 'teardown', 'status', 'submit-job', 'wait-job', 'costs'],
                       help="Action to perform")
    parser.add_argument("--job-count", type=int, default=1, help="Number of jobs to process")
    parser.add_argument("--job-name", help="Job name for batch submission")
    parser.add_argument("--job-parameters", help="Job parameters as JSON string")
    parser.add_argument("--job-id", help="Job ID for waiting")
    parser.add_argument("--gpu-required", action="store_true", help="Require GPU instances")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in minutes")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = CostOptimizationManager(args.region, args.environment)
    
    try:
        if args.action == 'setup':
            success = manager.setup_infrastructure(
                job_count=args.job_count,
                gpu_required=args.gpu_required
            )
            if success:
                print("✅ Infrastructure setup completed")
            else:
                print("❌ Infrastructure setup failed")
                sys.exit(1)
        
        elif args.action == 'teardown':
            success = manager.teardown_infrastructure()
            if success:
                print("✅ Infrastructure teardown completed")
            else:
                print("❌ Infrastructure teardown failed")
                sys.exit(1)
        
        elif args.action == 'status':
            status = manager.get_compute_environment_status()
            print(f"Compute Environment Status: {json.dumps(status, indent=2)}")
        
        elif args.action == 'submit-job':
            if not args.job_name:
                print("❌ Job name is required for submit-job action")
                sys.exit(1)
            
            job_parameters = {}
            if args.job_parameters:
                job_parameters = json.loads(args.job_parameters)
            
            job_id = manager.submit_batch_job(args.job_name, job_parameters)
            if job_id:
                print(f"✅ Job submitted: {job_id}")
            else:
                print("❌ Job submission failed")
                sys.exit(1)
        
        elif args.action == 'wait-job':
            if not args.job_id:
                print("❌ Job ID is required for wait-job action")
                sys.exit(1)
            
            status = manager.wait_for_job_completion(args.job_id, args.timeout)
            print(f"Job completion status: {status}")
        
        elif args.action == 'costs':
            metrics = manager.get_cost_metrics()
            print(f"Cost Metrics: {json.dumps(metrics, indent=2)}")
    
    except Exception as e:
        logger.error(f"Error executing action {args.action}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
