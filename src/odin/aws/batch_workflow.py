"""
Batch Workflow Manager

This module provides batch workflow management for cost-optimized processing.
"""

import builtins
import contextlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from ..config import CostOptimizationConfig
from .manager import CostOptimizationManager

logger = logging.getLogger(__name__)


class BatchWorkflowManager:
    """Manages cost-optimized batch workflows."""

    def __init__(self, config: CostOptimizationConfig):
        self.config = config
        self.cost_manager = CostOptimizationManager(config)

    def process_batch(self, batch_config: Dict) -> Dict:
        """Process a complete batch with cost optimization."""
        try:
            batch_id = batch_config.get('batch_id', f"batch-{int(time.time())}")
            jobs = batch_config.get('jobs', [])
            gpu_required = batch_config.get('gpu_required', self.config.gpu_required)
            max_parallel_jobs = batch_config.get('max_parallel_jobs', self.config.max_parallel_jobs)

            logger.info(f"Starting cost-optimized batch processing: {batch_id}")
            logger.info(f"Jobs to process: {len(jobs)}")
            logger.info(f"GPU required: {gpu_required}")
            logger.info(f"Max parallel jobs: {max_parallel_jobs}")

            # Step 1: Setup infrastructure
            logger.info("Step 1: Setting up cost-optimized infrastructure")
            if not self.cost_manager.setup_infrastructure(
                job_count=len(jobs),
                gpu_required=gpu_required
            ):
                return {'status': 'failed', 'error': 'Infrastructure setup failed'}

            # Step 2: Submit jobs with cost optimization
            logger.info("Step 2: Submitting jobs with cost optimization")
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
            with contextlib.suppress(builtins.BaseException):
                self.cost_manager.teardown_infrastructure()
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
            gpu_required = job.get('gpu_required', self.config.gpu_required)

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

            # Submit job (this would integrate with the actual job submission system)
            # For now, we'll simulate job submission
            job_id = f"job-{int(time.time())}-{hash(job_name) % 10000}"

            logger.info(f"Job submitted: {job_name} (ID: {job_id})")

            return {
                'job': job,
                'job_id': job_id,
                'status': 'submitted',
                'submitted_at': datetime.utcnow().isoformat()
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

            # Simulate job completion monitoring
            # In a real implementation, this would monitor actual job status
            time.sleep(1)  # Simulate processing time

            return {
                'job_result': job_result,
                'final_status': 'SUCCEEDED',
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
