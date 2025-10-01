"""
LocalStack Batch Fallback Handler

Fallback for submitJob.sync when it fails in local environment.
Uses boto3.batch.submit_job and polls in Lambda for short duration.
Only used when ENV=local.
"""

# Removed unused import json
import logging
import time
import boto3
from typing import Dict, Any

logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    LocalStack fallback for Batch job submission.

    Args:
        event: Batch job parameters
        context: Lambda context

    Returns:
        Batch job result
    """
    try:
        # Check if we're in local environment
        if not _is_local_environment():
            raise Exception("Batch fallback only available in local environment")

        # Extract batch parameters
        job_name = event.get("JobName")
        job_queue = event.get("JobQueue")
        job_definition = event.get("JobDefinition")
        container_overrides = event.get("ContainerOverrides", {})
        retry_strategy = event.get("RetryStrategy", {})
        timeout = event.get("Timeout", {})

        if not all([job_name, job_queue, job_definition]):
            raise ValueError("Missing required batch parameters")

        # Submit job using boto3
        batch_client = boto3.client('batch')

        submit_params = {
            'jobName': job_name,
            'jobQueue': job_queue,
            'jobDefinition': job_definition,
            'containerOverrides': container_overrides,
            'retryStrategy': retry_strategy,
            'timeout': timeout
        }

        logger.info(f"Submitting batch job: {job_name}")
        response = batch_client.submit_job(**submit_params)

        job_id = response['jobId']
        logger.info(f"Batch job submitted with ID: {job_id}")

        # Poll for job completion (short duration for Lambda)
        max_poll_time = 300  # 5 minutes max
        poll_interval = 10   # 10 seconds
        start_time = time.time()

        while time.time() - start_time < max_poll_time:
            try:
                job_status = batch_client.describe_jobs(jobs=[job_id])

                if not job_status['jobs']:
                    raise Exception(f"Job {job_id} not found")

                job = job_status['jobs'][0]
                job_status_name = job['jobStatus']

                logger.info(f"Job {job_id} status: {job_status_name}")

                if job_status_name in ['SUCCEEDED', 'FAILED']:
                    # Job completed
                    return {
                        'jobId': job_id,
                        'jobName': job_name,
                        'jobStatus': job_status_name,
                        'jobQueue': job_queue,
                        'jobDefinition': job_definition,
                        'startedAt': job.get('startedAt'),
                        'stoppedAt': job.get('stoppedAt'),
                        'exitCode': job.get('exitCode'),
                        'reason': job.get('reason'),
                        'statusReason': job.get('statusReason')
                    }

                # Wait before next poll
                time.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Error polling job {job_id}: {e}")
                time.sleep(poll_interval)

        # Timeout reached
        logger.warning(f"Job {job_id} polling timeout after {max_poll_time}s")
        return {
            'jobId': job_id,
            'jobName': job_name,
            'jobStatus': 'TIMEOUT',
            'reason': f'Polling timeout after {max_poll_time}s'
        }

    except Exception as e:
        logger.error(f"Batch fallback failed: {e}")
        raise Exception("BatchFallbackError") from e

def _is_local_environment() -> bool:
    """Check if we're running in local environment."""
    import os
    return os.getenv('ENV') == 'local' or os.getenv('LOCALSTACK_ENDPOINT') is not None
