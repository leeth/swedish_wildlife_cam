#!/usr/bin/env python3
"""
AWS Batch Dashboard with Real-time Logging

This script provides a comprehensive dashboard for monitoring AWS Batch jobs
with real-time logging, cost tracking, and progress monitoring.
"""

import boto3
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_optimization.config import CostOptimizationConfig
from cost_optimization.manager import CostOptimizationManager

class BatchDashboard:
    """Comprehensive dashboard for AWS Batch monitoring."""
    
    def __init__(self, region: str = "eu-north-1"):
        self.region = region
        self.batch = boto3.client('batch', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        self.monitoring_active = False
        self.jobs = {}
        self.instances = {}
        self.costs = {}
        
    def clear_screen(self):
        """Clear screen for dashboard display."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Print dashboard header."""
        print("🚀 AWS Batch Dashboard - Wildlife Detection Pipeline")
        print("=" * 70)
        print(f"Region: {self.region} | Time: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)
    
    def get_job_queues(self) -> List[Dict]:
        """Get job queues information."""
        try:
            response = self.batch.describe_job_queues()
            return response.get('jobQueues', [])
        except Exception as e:
            return []
    
    def get_compute_environments(self) -> List[Dict]:
        """Get compute environments information."""
        try:
            response = self.batch.describe_compute_environments()
            return response.get('computeEnvironments', [])
        except Exception as e:
            return []
    
    def get_running_jobs(self) -> List[Dict]:
        """Get running jobs."""
        try:
            queues = self.get_job_queues()
            if not queues:
                return []
            
            all_jobs = []
            for queue in queues:
                queue_name = queue['jobQueueName']
                
                # Get running jobs
                running = self.batch.list_jobs(
                    jobQueue=queue_name,
                    jobStatus='RUNNING'
                )
                
                # Get runnable jobs
                runnable = self.batch.list_jobs(
                    jobQueue=queue_name,
                    jobStatus='RUNNABLE'
                )
                
                # Get job details
                job_ids = []
                job_ids.extend([job['jobId'] for job in running['jobSummaryList']])
                job_ids.extend([job['jobId'] for job in runnable['jobSummaryList']])
                
                if job_ids:
                    job_details = self.batch.describe_jobs(jobs=job_ids)
                    all_jobs.extend(job_details['jobs'])
            
            return all_jobs
        except Exception as e:
            return []
    
    def get_running_instances(self) -> List[Dict]:
        """Get running EC2 instances."""
        try:
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
            
            return instances
        except Exception as e:
            return []
    
    def calculate_costs(self, instances: List[Dict]) -> Dict:
        """Calculate costs for instances."""
        if not instances:
            return {'total_cost': 0, 'savings': 0, 'savings_percentage': 0}
        
        # Simple pricing (would be better to get from pricing API)
        pricing = {
            'm5.large': {'on_demand': 0.096, 'spot': 0.029},
            'm5.xlarge': {'on_demand': 0.192, 'spot': 0.058},
            't3.medium': {'on_demand': 0.0416, 'spot': 0.012},
            't3.large': {'on_demand': 0.0832, 'spot': 0.025}
        }
        
        total_cost = 0
        total_on_demand = 0
        
        for instance in instances:
            instance_type = instance['InstanceType']
            launch_time = instance['LaunchTime']
            runtime_hours = (datetime.now(launch_time.tzinfo) - launch_time).total_seconds() / 3600
            
            # Check if spot instance
            is_spot = any(tag['Key'] == 'aws:ec2spot:fleet-request-id' for tag in instance.get('Tags', []))
            
            price_info = pricing.get(instance_type, {'on_demand': 0.1, 'spot': 0.03})
            price_per_hour = price_info['spot'] if is_spot else price_info['on_demand']
            
            instance_cost = runtime_hours * price_per_hour
            on_demand_cost = runtime_hours * price_info['on_demand']
            
            total_cost += instance_cost
            total_on_demand += on_demand_cost
        
        savings = total_on_demand - total_cost
        savings_percentage = (savings / total_on_demand * 100) if total_on_demand > 0 else 0
        
        return {
            'total_cost': total_cost,
            'on_demand_cost': total_on_demand,
            'savings': savings,
            'savings_percentage': savings_percentage
        }
    
    def display_jobs(self, jobs: List[Dict]):
        """Display job information."""
        print("📋 BATCH JOBS")
        print("-" * 30)
        
        if not jobs:
            print("   No active jobs")
            return
        
        for job in jobs:
            job_name = job.get('jobName', 'Unknown')
            status = job.get('status', 'UNKNOWN')
            job_id = job.get('jobId', 'Unknown')
            
            # Status emoji
            status_emoji = {
                'RUNNING': '🟢',
                'RUNNABLE': '🟡',
                'SUCCEEDED': '✅',
                'FAILED': '❌',
                'SUBMITTED': '📤'
            }.get(status, '❓')
            
            print(f"   {status_emoji} {job_name}")
            print(f"      ID: {job_id}")
            print(f"      Status: {status}")
            
            # Get timing info
            created_at = job.get('createdAt')
            started_at = job.get('startedAt')
            
            if created_at:
                runtime = datetime.now(created_at.tzinfo) - created_at
                print(f"      Runtime: {runtime}")
            
            if started_at:
                processing_time = datetime.now(started_at.tzinfo) - started_at
                print(f"      Processing: {processing_time}")
            
            # Get attempt info
            if 'attempts' in job and job['attempts']:
                latest_attempt = job['attempts'][-1]
                if 'container' in latest_attempt:
                    container = latest_attempt['container']
                    if 'logStreamName' in container:
                        print(f"      Log: {container['logStreamName']}")
            
            print()
    
    def display_instances(self, instances: List[Dict]):
        """Display instance information."""
        print("🖥️  EC2 INSTANCES")
        print("-" * 30)
        
        if not instances:
            print("   No running instances")
            return
        
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            launch_time = instance['LaunchTime']
            runtime = datetime.now(launch_time.tzinfo) - launch_time
            
            # Check if spot instance
            is_spot = any(tag['Key'] == 'aws:ec2spot:fleet-request-id' for tag in instance.get('Tags', []))
            spot_indicator = "🟢 SPOT" if is_spot else "🔴 ON-DEMAND"
            
            print(f"   {instance_id}")
            print(f"      Type: {instance_type} {spot_indicator}")
            print(f"      Runtime: {runtime}")
            print(f"      Launch: {launch_time.strftime('%H:%M:%S')}")
            print()
    
    def display_costs(self, cost_info: Dict):
        """Display cost information."""
        print("💰 COST ANALYSIS")
        print("-" * 30)
        print(f"   Current cost: ${cost_info['total_cost']:.3f}")
        print(f"   On-demand cost: ${cost_info['on_demand_cost']:.3f}")
        print(f"   Savings: ${cost_info['savings']:.3f}")
        print(f"   Savings %: {cost_info['savings_percentage']:.1f}%")
        print()
    
    def display_infrastructure(self):
        """Display infrastructure status."""
        print("🏗️  INFRASTRUCTURE")
        print("-" * 30)
        
        # Job queues
        queues = self.get_job_queues()
        print(f"   Job Queues: {len(queues)}")
        for queue in queues:
            status = queue.get('status', 'UNKNOWN')
            state = queue.get('state', 'UNKNOWN')
            print(f"      {queue['jobQueueName']}: {state} ({status})")
        
        # Compute environments
        environments = self.get_compute_environments()
        print(f"   Compute Environments: {len(environments)}")
        for env in environments:
            status = env.get('status', 'UNKNOWN')
            state = env.get('state', 'UNKNOWN')
            print(f"      {env['computeEnvironmentName']}: {state} ({status})")
        
        print()
    
    def update_dashboard(self):
        """Update dashboard display."""
        self.clear_screen()
        self.print_header()
        
        # Get current data
        jobs = self.get_running_jobs()
        instances = self.get_running_instances()
        cost_info = self.calculate_costs(instances)
        
        # Display sections
        self.display_infrastructure()
        self.display_jobs(jobs)
        self.display_instances(instances)
        self.display_costs(cost_info)
        
        # Footer
        print("=" * 70)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 70)
    
    def start_monitoring(self, refresh_interval: int = 10):
        """Start real-time monitoring."""
        print("🚀 Starting AWS Batch Dashboard...")
        print(f"Refresh interval: {refresh_interval} seconds")
        print("Press Ctrl+C to stop")
        print()
        
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                self.update_dashboard()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n⏹️  Dashboard stopped by user")
            self.monitoring_active = False
        except Exception as e:
            print(f"\n❌ Dashboard error: {e}")
            self.monitoring_active = False
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False

def main():
    """Main function."""
    print("🚀 AWS Batch Dashboard")
    print("=" * 40)
    
    dashboard = BatchDashboard()
    
    try:
        # Start dashboard
        dashboard.start_monitoring(refresh_interval=5)  # Update every 5 seconds
        
    except Exception as e:
        print(f"❌ Dashboard failed: {e}")

if __name__ == "__main__":
    main()


