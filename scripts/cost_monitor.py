#!/usr/bin/env python3
"""
Real-time Cost Monitor for AWS Batch Jobs

This script provides real-time cost monitoring and tracking for AWS Batch jobs
with detailed cost breakdowns and savings calculations.
"""

import boto3
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CostMonitor:
    """Real-time cost monitoring for AWS Batch jobs."""
    
    def __init__(self, region: str = "eu-north-1"):
        self.region = region
        self.ec2 = boto3.client('ec2', region_name=region)
        self.batch = boto3.client('batch', region_name=region)
        self.pricing = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # Instance pricing (approximate, would be better to get from pricing API)
        self.instance_pricing = {
            'm5.large': {'on_demand': 0.096, 'spot': 0.029},
            'm5.xlarge': {'on_demand': 0.192, 'spot': 0.058},
            'm5.2xlarge': {'on_demand': 0.384, 'spot': 0.115},
            't3.medium': {'on_demand': 0.0416, 'spot': 0.012},
            't3.large': {'on_demand': 0.0832, 'spot': 0.025},
            't3.small': {'on_demand': 0.0208, 'spot': 0.006},
            't3.micro': {'on_demand': 0.0104, 'spot': 0.003}
        }
    
    def get_running_instances(self) -> List[Dict]:
        """Get all running instances for wildlife detection."""
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
            print(f"❌ Error getting instances: {e}")
            return []
    
    def calculate_instance_cost(self, instance: Dict) -> Dict:
        """Calculate cost for a specific instance."""
        instance_type = instance['InstanceType']
        launch_time = instance['LaunchTime']
        current_time = datetime.now(launch_time.tzinfo)
        runtime_hours = (current_time - launch_time).total_seconds() / 3600
        
        # Get pricing
        pricing = self.instance_pricing.get(instance_type, {'on_demand': 0.1, 'spot': 0.03})
        
        # Determine if it's a spot instance
        is_spot = any(tag['Key'] == 'aws:ec2spot:fleet-request-id' for tag in instance.get('Tags', []))
        price_per_hour = pricing['spot'] if is_spot else pricing['on_demand']
        
        current_cost = runtime_hours * price_per_hour
        on_demand_cost = runtime_hours * pricing['on_demand']
        savings = on_demand_cost - current_cost
        savings_percentage = (savings / on_demand_cost * 100) if on_demand_cost > 0 else 0
        
        return {
            'instance_id': instance['InstanceId'],
            'instance_type': instance_type,
            'runtime_hours': runtime_hours,
            'is_spot': is_spot,
            'current_cost': current_cost,
            'on_demand_cost': on_demand_cost,
            'savings': savings,
            'savings_percentage': savings_percentage,
            'price_per_hour': price_per_hour
        }
    
    def get_batch_jobs(self) -> List[Dict]:
        """Get current batch jobs."""
        try:
            # Get job queues
            queues = self.batch.describe_job_queues()
            if not queues['jobQueues']:
                return []
            
            queue_name = queues['jobQueues'][0]['jobQueueName']
            
            # Get running jobs
            running_jobs = self.batch.list_jobs(
                jobQueue=queue_name,
                jobStatus='RUNNING'
            )
            
            # Get job details
            jobs = []
            if running_jobs['jobSummaryList']:
                job_ids = [job['jobId'] for job in running_jobs['jobSummaryList']]
                job_details = self.batch.describe_jobs(jobs=job_ids)
                jobs = job_details['jobs']
            
            return jobs
        except Exception as e:
            print(f"❌ Error getting batch jobs: {e}")
            return []
    
    def monitor_costs(self, duration_minutes: int = 10):
        """Monitor costs in real-time."""
        print("💰 Real-time Cost Monitor")
        print("=" * 50)
        print(f"Monitoring for {duration_minutes} minutes...")
        print()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        total_cost = 0
        max_cost = 0
        
        try:
            while time.time() < end_time:
                current_time = datetime.now().strftime("%H:%M:%S")
                elapsed = int(time.time() - start_time)
                
                # Get running instances
                instances = self.get_running_instances()
                
                if instances:
                    print(f"[{current_time}] Running instances: {len(instances)}")
                    
                    instance_costs = []
                    for instance in instances:
                        cost_info = self.calculate_instance_cost(instance)
                        instance_costs.append(cost_info)
                        
                        # Display instance details
                        spot_indicator = "🟢 SPOT" if cost_info['is_spot'] else "🔴 ON-DEMAND"
                        print(f"   {instance['InstanceId']}: {cost_info['instance_type']} {spot_indicator}")
                        print(f"      Runtime: {cost_info['runtime_hours']:.1f}h")
                        print(f"      Cost: ${cost_info['current_cost']:.3f} (${cost_info['price_per_hour']:.3f}/h)")
                        print(f"      Savings: ${cost_info['savings']:.3f} ({cost_info['savings_percentage']:.1f}%)")
                    
                    # Calculate totals
                    current_total = sum(cost['current_cost'] for cost in instance_costs)
                    on_demand_total = sum(cost['on_demand_cost'] for cost in instance_costs)
                    total_savings = on_demand_total - current_total
                    savings_percentage = (total_savings / on_demand_total * 100) if on_demand_total > 0 else 0
                    
                    total_cost = current_total
                    max_cost = max(max_cost, current_total)
                    
                    print(f"   💰 Total cost: ${current_total:.3f}")
                    print(f"   💰 On-demand cost: ${on_demand_total:.3f}")
                    print(f"   💰 Total savings: ${total_savings:.3f} ({savings_percentage:.1f}%)")
                    
                else:
                    print(f"[{current_time}] No running instances")
                
                # Get batch job status
                jobs = self.get_batch_jobs()
                if jobs:
                    print(f"   📋 Active jobs: {len(jobs)}")
                    for job in jobs:
                        status = job.get('status', 'UNKNOWN')
                        job_name = job.get('jobName', 'Unknown')
                        print(f"      {job_name}: {status}")
                
                print()
                time.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        
        # Final summary
        print("📊 Final Cost Summary")
        print("=" * 30)
        print(f"Total monitoring time: {elapsed // 60}m {elapsed % 60}s")
        print(f"Peak cost: ${max_cost:.3f}")
        print(f"Final cost: ${total_cost:.3f}")
        
        if total_cost > 0:
            print(f"Average cost per hour: ${total_cost / (elapsed / 3600):.3f}")
        
        return {
            'total_cost': total_cost,
            'max_cost': max_cost,
            'monitoring_time': elapsed,
            'instances': len(instances) if 'instances' in locals() else 0
        }

def main():
    """Main function."""
    print("💰 AWS Batch Cost Monitor")
    print("=" * 40)
    
    monitor = CostMonitor()
    
    try:
        # Start monitoring
        results = monitor.monitor_costs(duration_minutes=5)  # Monitor for 5 minutes
        
        print("\n🎉 Cost monitoring completed!")
        print(f"✅ Monitored for {results['monitoring_time']} seconds")
        print(f"✅ Peak cost: ${results['max_cost']:.3f}")
        print(f"✅ Final cost: ${results['total_cost']:.3f}")
        
    except Exception as e:
        print(f"❌ Cost monitoring failed: {e}")

if __name__ == "__main__":
    main()
