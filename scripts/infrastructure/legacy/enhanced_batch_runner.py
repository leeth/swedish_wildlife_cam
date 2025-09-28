#!/usr/bin/env python3
"""
Enhanced Batch Runner with Detailed Logging

This script provides comprehensive logging and monitoring for AWS Batch jobs
with real-time progress tracking, cost monitoring, and detailed status updates.
"""

import sys
import os
import json
import time
import boto3
from pathlib import Path
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_optimization.config import CostOptimizationConfig
from cost_optimization.manager import CostOptimizationManager

class BatchJobLogger:
    """Enhanced logging for batch jobs with real-time monitoring."""
    
    def __init__(self, region: str = "eu-north-1"):
        self.region = region
        self.batch = boto3.client('batch', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.start_time = None
        self.job_id = None
        self.instance_id = None
        self.log_thread = None
        self.monitoring_active = False
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp and level."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄",
            "COST": "💰",
            "INSTANCE": "🖥️"
        }
        
        emoji = level_emoji.get(level, "📝")
        print(f"[{timestamp}] {emoji} {message}")
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get detailed job status."""
        try:
            response = self.batch.describe_jobs(jobs=[job_id])
            if response['jobs']:
                return response['jobs'][0]
            return {}
        except Exception as e:
            self.log(f"Error getting job status: {e}", "ERROR")
            return {}
    
    def get_instance_info(self, instance_id: str) -> Dict:
        """Get instance information."""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            if response['Reservations'] and response['Reservations'][0]['Instances']:
                return response['Reservations'][0]['Instances'][0]
            return {}
        except Exception as e:
            self.log(f"Error getting instance info: {e}", "ERROR")
            return {}
    
    def get_cost_metrics(self) -> Dict:
        """Get cost metrics for running instances."""
        try:
            # Get running instances
            response = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['running']},
                    {'Name': 'tag:Application', 'Values': ['wildlife-detection']}
                ]
            )
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(instance)
            
            if not instances:
                return {'instance_count': 0, 'total_cost': 0}
            
            # Calculate estimated costs
            total_cost = 0
            for instance in instances:
                instance_type = instance['InstanceType']
                launch_time = instance['LaunchTime']
                runtime_hours = (datetime.now(launch_time.tzinfo) - launch_time).total_seconds() / 3600
                
                # Rough cost estimates (these would be more accurate with real pricing API)
                cost_per_hour = {
                    'm5.large': 0.096,
                    'm5.xlarge': 0.192,
                    'm5.2xlarge': 0.384,
                    't3.medium': 0.0416,
                    't3.large': 0.0832
                }.get(instance_type, 0.1)
                
                instance_cost = runtime_hours * cost_per_hour
                total_cost += instance_cost
                
                self.log(f"Instance {instance['InstanceId']}: {instance_type} running {runtime_hours:.1f}h (${instance_cost:.3f})", "COST")
            
            return {
                'instance_count': len(instances),
                'total_cost': total_cost,
                'instances': instances
            }
            
        except Exception as e:
            self.log(f"Error getting cost metrics: {e}", "ERROR")
            return {'instance_count': 0, 'total_cost': 0}
    
    def monitor_job_progress(self, job_id: str):
        """Monitor job progress with detailed logging."""
        self.job_id = job_id
        self.start_time = datetime.now()
        self.monitoring_active = True
        
        self.log(f"Starting job monitoring for: {job_id}", "PROGRESS")
        
        previous_status = None
        status_count = 0
        
        while self.monitoring_active:
            try:
                job_info = self.get_job_status(job_id)
                if not job_info:
                    time.sleep(10)
                    continue
                
                status = job_info.get('status', 'UNKNOWN')
                status_reason = job_info.get('statusReason', '')
                
                # Log status changes
                if status != previous_status:
                    self.log(f"Job status changed: {previous_status} → {status}", "PROGRESS")
                    if status_reason:
                        self.log(f"Reason: {status_reason}", "INFO")
                    previous_status = status
                    status_count = 0
                else:
                    status_count += 1
                
                # Get timing information
                created_at = job_info.get('createdAt')
                started_at = job_info.get('startedAt')
                stopped_at = job_info.get('stoppedAt')
                
                if created_at:
                    elapsed = datetime.now(created_at.tzinfo) - created_at
                    self.log(f"Elapsed time: {elapsed}", "PROGRESS")
                
                # Get instance information
                if 'attempts' in job_info and job_info['attempts']:
                    latest_attempt = job_info['attempts'][-1]
                    if 'container' in latest_attempt:
                        container = latest_attempt['container']
                        if 'logStreamName' in container:
                            log_stream = container['logStreamName']
                            self.log(f"Log stream: {log_stream}", "INFO")
                        
                        if 'taskArn' in container:
                            task_arn = container['taskArn']
                            # Extract instance ID from task ARN if possible
                            self.log(f"Task ARN: {task_arn}", "INFO")
                
                # Get cost metrics every 5 status checks
                if status_count % 5 == 0:
                    cost_metrics = self.get_cost_metrics()
                    if cost_metrics['instance_count'] > 0:
                        self.log(f"Running instances: {cost_metrics['instance_count']}, Estimated cost: ${cost_metrics['total_cost']:.3f}", "COST")
                
                # Check if job is finished
                if status in ['SUCCEEDED', 'FAILED']:
                    self.log(f"Job finished with status: {status}", "SUCCESS" if status == 'SUCCEEDED' else "ERROR")
                    
                    if started_at and stopped_at:
                        duration = stopped_at - started_at
                        self.log(f"Job duration: {duration}", "PROGRESS")
                    
                    # Final cost report
                    final_cost = self.get_cost_metrics()
                    if final_cost['instance_count'] > 0:
                        self.log(f"Final cost: ${final_cost['total_cost']:.3f} for {final_cost['instance_count']} instances", "COST")
                    
                    self.monitoring_active = False
                    break
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                self.log("Monitoring interrupted by user", "WARNING")
                self.monitoring_active = False
                break
            except Exception as e:
                self.log(f"Error in monitoring: {e}", "ERROR")
                time.sleep(10)
    
    def submit_job_with_logging(self, job_name: str, job_queue: str, job_definition: str, 
                              parameters: Dict = None, timeout_minutes: int = 30) -> str:
        """Submit job with comprehensive logging."""
        
        self.log(f"Submitting job: {job_name}", "PROGRESS")
        self.log(f"Queue: {job_queue}", "INFO")
        self.log(f"Definition: {job_definition}", "INFO")
        
        if parameters:
            self.log(f"Parameters: {json.dumps(parameters, indent=2)}", "INFO")
        
        try:
            # Submit job
            submit_params = {
                'jobName': job_name,
                'jobQueue': job_queue,
                'jobDefinition': job_definition
            }
            
            if parameters:
                submit_params['parameters'] = parameters
            
            response = self.batch.submit_job(**submit_params)
            job_id = response['jobId']
            
            self.log(f"Job submitted successfully: {job_id}", "SUCCESS")
            self.log(f"Job ARN: {response.get('jobArn', 'N/A')}", "INFO")
            
            # Start monitoring in background thread
            self.log_thread = threading.Thread(
                target=self.monitor_job_progress, 
                args=(job_id,),
                daemon=True
            )
            self.log_thread.start()
            
            return job_id
            
        except Exception as e:
            self.log(f"Failed to submit job: {e}", "ERROR")
            raise
    
    def get_job_logs(self, job_id: str) -> List[str]:
        """Get job logs from CloudWatch."""
        try:
            job_info = self.get_job_status(job_id)
            if not job_info or 'attempts' not in job_info:
                return []
            
            logs = []
            for attempt in job_info['attempts']:
                if 'container' in attempt and 'logStreamName' in attempt['container']:
                    log_stream = attempt['container']['logStreamName']
                    
                    # Get logs from CloudWatch
                    response = self.cloudwatch.get_log_events(
                        logGroupName='/aws/batch/job',
                        logStreamName=log_stream,
                        startTime=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
                    )
                    
                    for event in response['events']:
                        logs.append(event['message'])
            
            return logs
            
        except Exception as e:
            self.log(f"Error getting job logs: {e}", "ERROR")
            return []
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=5)

def run_enhanced_batch_test():
    """Run enhanced batch test with detailed logging."""
    print("🚀 Enhanced Batch Runner with Detailed Logging")
    print("=" * 60)
    
    logger = BatchJobLogger()
    
    try:
        # Get job queue and definition
        logger.log("Getting job queue and definition...", "PROGRESS")
        
        queues = logger.batch.describe_job_queues()
        if not queues['jobQueues']:
            logger.log("No job queues found", "ERROR")
            return False
        
        queue_name = queues['jobQueues'][0]['jobQueueName']
        logger.log(f"Using job queue: {queue_name}", "SUCCESS")
        
        definitions = logger.batch.describe_job_definitions()
        if not definitions['jobDefinitions']:
            logger.log("No job definitions found", "ERROR")
            return False
        
        job_def_name = definitions['jobDefinitions'][0]['jobDefinitionName']
        logger.log(f"Using job definition: {job_def_name}", "SUCCESS")
        
        # Submit job with enhanced logging
        job_name = f"enhanced-test-{int(time.time())}"
        parameters = {
            'input_bucket': 'wildlife-test-bucket',
            'input_prefix': 'trailcam-data',
            'output_bucket': 'wildlife-test-bucket',
            'output_prefix': 'processed-results'
        }
        
        job_id = logger.submit_job_with_logging(
            job_name=job_name,
            job_queue=queue_name,
            job_definition=job_def_name,
            parameters=parameters,
            timeout_minutes=10
        )
        
        # Wait for monitoring to complete
        if logger.log_thread:
            logger.log_thread.join()
        
        # Get final job logs
        logger.log("Retrieving job logs...", "PROGRESS")
        logs = logger.get_job_logs(job_id)
        if logs:
            logger.log(f"Retrieved {len(logs)} log entries", "SUCCESS")
            # Show last few log entries
            for log_entry in logs[-5:]:
                logger.log(f"Log: {log_entry.strip()}", "INFO")
        
        logger.log("Enhanced batch test completed!", "SUCCESS")
        return True
        
    except Exception as e:
        logger.log(f"Enhanced batch test failed: {e}", "ERROR")
        return False
    finally:
        logger.stop_monitoring()

def main():
    """Main function."""
    print("🧪 Enhanced Batch Runner Test")
    print("=" * 40)
    
    success = run_enhanced_batch_test()
    
    if success:
        print("\n🎉 Enhanced batch runner test completed successfully!")
        print("✅ Detailed logging implemented")
        print("✅ Real-time monitoring active")
        print("✅ Cost tracking enabled")
    else:
        print("\n❌ Enhanced batch runner test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
