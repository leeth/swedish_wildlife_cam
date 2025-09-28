#!/usr/bin/env python3
"""
Batch Workflow Manager

This script implements hyper batch-oriented processing with cost optimization:
- Sets up infrastructure when starting a batch
- Processes all jobs in the batch
- Tears down infrastructure when complete
- Manages spot instances with fallback to on-demand
- Implements cost optimization strategies
"""

import boto3
import json
import time
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import cost optimization manager
from cost_optimization_manager import CostOptimizationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchWorkflowManager:
    """Manages hyper batch-oriented processing with cost optimization."""
    
    def __init__(self, region: str = "eu-north-1", environment: str = "production"):
        self.region = region
        self.environment = environment
        self.cost_manager = CostOptimizationManager(region, environment)
        self.batch = boto3.client('batch', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Batch configuration
        self.job_queue_name = f"wildlife-detection-queue-{environment}"
        self.job_def_name = f"wildlife-detection-job-{environment}"
        
        # Cost optimization settings
        self.spot_fallback_timeout = 300  # 5 minutes to wait for spot instances
        self.max_retry_attempts = 3
        self.cost_threshold_percentage = 50  # Minimum 50% savings to use spot
        
    def process_batch(self, batch_config: Dict) -> Dict:
        """Process a complete batch with cost optimization."""
        try:
            batch_id = batch_config.get('batch_id', f"batch-{int(time.time())}")
            jobs = batch_config.get('jobs', [])
            gpu_required = batch_config.get('gpu_required', True)
            max_parallel_jobs = batch_config.get('max_parallel_jobs', 10)
            
            logger.info(f"Starting batch processing: {batch_id}")
            logger.info(f"Jobs to process: {len(jobs)}")
            logger.info(f"GPU required: {gpu_required}")
            logger.info(f"Max parallel jobs: {max_parallel_jobs}")
            
            # Step 1: Setup infrastructure
            logger.info("Step 1: Setting up infrastructure")
            if not self.cost_manager.setup_infrastructure(
                job_count=len(jobs),
                gpu_required=gpu_required
            ):
                return {'status': 'failed', 'error': 'Infrastructure setup failed'}
            
            # Step 2: Submit jobs with cost optimization
            logger.info("Step 2: Submitting jobs")
            job_results = self._submit_jobs_with_cost_optimization(
                jobs, max_parallel_jobs, gpu_required
            )
            
            # Step 3: Monitor job completion
            logger.info("Step 3: Monitoring job completion")
            completion_results = self._monitor_job_completion(job_results)
            
            # Step 4: Teardown infrastructure
            logger.info("Step 4: Tearing down infrastructure")
            self.cost_manager.teardown_infrastructure()
            
            # Step 5: Generate cost report
            logger.info("Step 5: Generating cost report")
            cost_report = self._generate_cost_report(batch_id, job_results, completion_results)
            
            return {
                'status': 'completed',
                'batch_id': batch_id,
                'job_results': job_results,
                'completion_results': completion_results,
                'cost_report': cost_report
            }
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            # Ensure infrastructure is torn down on error
            try:
                self.cost_manager.teardown_infrastructure()
            except:
                pass
            return {'status': 'failed', 'error': str(e)}
    
    def _submit_jobs_with_cost_optimization(self, jobs: List[Dict], 
                                          max_parallel_jobs: int, 
                                          gpu_required: bool) -> List[Dict]:
        """Submit jobs with cost optimization strategies."""
        job_results = []
        
        # Group jobs by priority and resource requirements
        job_groups = self._group_jobs_by_priority(jobs)
        
        for group_name, group_jobs in job_groups.items():
            logger.info(f"Processing job group: {group_name} ({len(group_jobs)} jobs)")
            
            # Submit jobs in parallel with cost optimization
            with ThreadPoolExecutor(max_workers=max_parallel_jobs) as executor:
                future_to_job = {
                    executor.submit(self._submit_single_job, job, gpu_required): job
                    for job in group_jobs
                }
                
                for future in as_completed(future_to_job):
                    job = future_to_job[future]
                    try:
                        result = future.result()
                        job_results.append(result)
                    except Exception as e:
                        logger.error(f"Error submitting job {job.get('name', 'unknown')}: {e}")
                        job_results.append({
                            'job': job,
                            'status': 'failed',
                            'error': str(e)
                        })
        
        return job_results
    
    def _group_jobs_by_priority(self, jobs: List[Dict]) -> Dict[str, List[Dict]]:
        """Group jobs by priority and resource requirements."""
        groups = {
            'high_priority_gpu': [],
            'high_priority_cpu': [],
            'normal_priority_gpu': [],
            'normal_priority_cpu': [],
            'low_priority': []
        }
        
        for job in jobs:
            priority = job.get('priority', 'normal')
            gpu_required = job.get('gpu_required', True)
            
            if priority == 'high':
                if gpu_required:
                    groups['high_priority_gpu'].append(job)
                else:
                    groups['high_priority_cpu'].append(job)
            elif priority == 'normal':
                if gpu_required:
                    groups['normal_priority_gpu'].append(job)
                else:
                    groups['normal_priority_cpu'].append(job)
            else:
                groups['low_priority'].append(job)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _submit_single_job(self, job: Dict, gpu_required: bool) -> Dict:
        """Submit a single job with cost optimization."""
        try:
            job_name = job.get('name', f"job-{int(time.time())}")
            job_parameters = job.get('parameters', {})
            
            # Add cost optimization parameters
            job_parameters.update({
                'cost_optimization': 'enabled',
                'spot_instance_preferred': 'true',
                'fallback_to_ondemand': 'true'
            })
            
            # Submit job
            job_id = self.cost_manager.submit_batch_job(job_name, job_parameters)
            
            if job_id:
                return {
                    'job': job,
                    'job_id': job_id,
                    'status': 'submitted',
                    'submitted_at': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'job': job,
                    'status': 'failed',
                    'error': 'Job submission failed'
                }
                
        except Exception as e:
            logger.error(f"Error submitting single job: {e}")
            return {
                'job': job,
                'status': 'failed',
                'error': str(e)
            }
    
    def _monitor_job_completion(self, job_results: List[Dict]) -> List[Dict]:
        """Monitor job completion with cost optimization."""
        completion_results = []
        
        # Monitor jobs in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_job = {
                executor.submit(self._monitor_single_job, job_result): job_result
                for job_result in job_results
                if job_result.get('status') == 'submitted'
            }
            
            for future in as_completed(future_to_job):
                job_result = future_to_job[future]
                try:
                    result = future.result()
                    completion_results.append(result)
                except Exception as e:
                    logger.error(f"Error monitoring job {job_result.get('job_id', 'unknown')}: {e}")
                    completion_results.append({
                        'job_result': job_result,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        return completion_results
    
    def _monitor_single_job(self, job_result: Dict) -> Dict:
        """Monitor a single job completion."""
        try:
            job_id = job_result.get('job_id')
            if not job_id:
                return {
                    'job_result': job_result,
                    'status': 'failed',
                    'error': 'No job ID provided'
                }
            
            # Wait for job completion
            final_status = self.cost_manager.wait_for_job_completion(job_id, timeout_minutes=120)
            
            return {
                'job_result': job_result,
                'final_status': final_status,
                'completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error monitoring single job: {e}")
            return {
                'job_result': job_result,
                'status': 'failed',
                'error': str(e)
            }
    
    def _generate_cost_report(self, batch_id: str, job_results: List[Dict], 
                            completion_results: List[Dict]) -> Dict:
        """Generate cost report for the batch."""
        try:
            # Get cost metrics
            cost_metrics = self.cost_manager.get_cost_metrics()
            
            # Calculate job statistics
            total_jobs = len(job_results)
            successful_jobs = len([r for r in completion_results if r.get('final_status') == 'SUCCEEDED'])
            failed_jobs = total_jobs - successful_jobs
            
            # Calculate processing time
            start_time = min([r.get('submitted_at', '') for r in job_results if r.get('submitted_at')])
            end_time = max([r.get('completed_at', '') for r in completion_results if r.get('completed_at')])
            
            processing_time = None
            if start_time and end_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                processing_time = (end_dt - start_dt).total_seconds() / 3600  # hours
            
            # Calculate estimated costs
            estimated_hours = processing_time or 1  # Default to 1 hour if unknown
            spot_cost = cost_metrics.get('spot_cost_per_hour', 0) * estimated_hours
            on_demand_cost = cost_metrics.get('on_demand_cost_per_hour', 0) * estimated_hours
            savings = on_demand_cost - spot_cost
            
            return {
                'batch_id': batch_id,
                'total_jobs': total_jobs,
                'successful_jobs': successful_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                'processing_time_hours': processing_time,
                'cost_metrics': cost_metrics,
                'estimated_spot_cost': spot_cost,
                'estimated_ondemand_cost': on_demand_cost,
                'estimated_savings': savings,
                'savings_percentage': (savings / on_demand_cost * 100) if on_demand_cost > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating cost report: {e}")
            return {'error': str(e)}
    
    def create_batch_config(self, input_data: List[str], 
                          job_type: str = "image_processing",
                          gpu_required: bool = True,
                          priority: str = "normal") -> Dict:
        """Create batch configuration from input data."""
        try:
            jobs = []
            
            for i, data_path in enumerate(input_data):
                job = {
                    'name': f"{job_type}-{i+1}",
                    'parameters': {
                        'input_path': data_path,
                        'job_type': job_type,
                        'gpu_required': gpu_required,
                        'priority': priority
                    },
                    'gpu_required': gpu_required,
                    'priority': priority
                }
                jobs.append(job)
            
            return {
                'batch_id': f"batch-{int(time.time())}",
                'jobs': jobs,
                'gpu_required': gpu_required,
                'max_parallel_jobs': 10,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating batch config: {e}")
            return {}


def main():
    """Main CLI for batch workflow manager."""
    parser = argparse.ArgumentParser(description="Batch Workflow Manager")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--environment", default="production", help="Environment name")
    parser.add_argument("--action", required=True,
                       choices=['process-batch', 'create-config', 'status', 'costs'],
                       help="Action to perform")
    parser.add_argument("--batch-config", help="Batch configuration JSON file")
    parser.add_argument("--input-data", nargs='+', help="Input data paths")
    parser.add_argument("--job-type", default="image_processing", help="Job type")
    parser.add_argument("--gpu-required", action="store_true", help="Require GPU instances")
    parser.add_argument("--priority", default="normal", choices=['low', 'normal', 'high'],
                       help="Job priority")
    parser.add_argument("--max-parallel", type=int, default=10, help="Max parallel jobs")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = BatchWorkflowManager(args.region, args.environment)
    
    try:
        if args.action == 'process-batch':
            if not args.batch_config:
                print("❌ Batch config file is required for process-batch action")
                sys.exit(1)
            
            # Load batch configuration
            with open(args.batch_config, 'r') as f:
                batch_config = json.load(f)
            
            # Process batch
            result = manager.process_batch(batch_config)
            
            # Save results
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
            
            print(f"Batch processing result: {json.dumps(result, indent=2)}")
        
        elif args.action == 'create-config':
            if not args.input_data:
                print("❌ Input data is required for create-config action")
                sys.exit(1)
            
            # Create batch configuration
            batch_config = manager.create_batch_config(
                input_data=args.input_data,
                job_type=args.job_type,
                gpu_required=args.gpu_required,
                priority=args.priority
            )
            
            # Save configuration
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(batch_config, f, indent=2)
                print(f"✅ Batch configuration saved to {args.output}")
            else:
                print(f"Batch configuration: {json.dumps(batch_config, indent=2)}")
        
        elif args.action == 'status':
            status = manager.cost_manager.get_compute_environment_status()
            print(f"Compute Environment Status: {json.dumps(status, indent=2)}")
        
        elif args.action == 'costs':
            metrics = manager.cost_manager.get_cost_metrics()
            print(f"Cost Metrics: {json.dumps(metrics, indent=2)}")
    
    except Exception as e:
        logger.error(f"Error executing action {args.action}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
