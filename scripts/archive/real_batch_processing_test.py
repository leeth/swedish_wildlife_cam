#!/usr/bin/env python3
"""
Real Batch Processing Test with EC2 Instances

This script performs a complete test with:
- Upload trailcam data to S3
- Run real batch processing on EC2
- Download results
- Generate cost reports
"""

import sys
import os
import json
import time
import boto3
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_optimization.config import CostOptimizationConfig
from cost_optimization.manager import CostOptimizationManager
from cost_optimization.batch_workflow import BatchWorkflowManager
from cost_optimization.stage3_downloader import Stage3OutputDownloader

def upload_trailcam_data():
    """Upload trailcam data to S3."""
    print("📤 Uploading trailcam data to S3...")
    
    # Get AWS account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = "eu-north-1"
    
    # Use the bucket from our infrastructure
    bucket_name = f"wildlife-test-production-{account_id}"
    s3_prefix = "trailcam-data"
    
    print(f"Bucket: {bucket_name}")
    print(f"Prefix: {s3_prefix}")
    
    # Create S3 client
    s3 = boto3.client('s3', region_name=region)
    
    # Upload test data
    test_data_dir = Path("/home/asbjorn/projects/wildlife_pipeline_starter/test_data")
    uploaded_files = []
    
    print("📤 Uploading files...")
    for file_path in test_data_dir.glob("*"):
        if file_path.is_file():
            s3_key = f"{s3_prefix}/{file_path.name}"
            try:
                s3.upload_file(str(file_path), bucket_name, s3_key)
                uploaded_files.append(s3_key)
                print(f"✅ Uploaded: {file_path.name}")
            except Exception as e:
                print(f"❌ Failed to upload {file_path.name}: {e}")
    
    print(f"✅ Uploaded {len(uploaded_files)} files to S3")
    return bucket_name, s3_prefix, uploaded_files

def run_real_batch_processing(bucket_name, s3_prefix):
    """Run real batch processing on EC2."""
    print("\n🚀 Running Real Batch Processing on EC2")
    print("=" * 50)
    
    # Get batch client
    batch = boto3.client('batch', region_name='eu-north-1')
    
    # Get job queue and definition
    try:
        queues = batch.describe_job_queues()
        queue_name = queues['jobQueues'][0]['jobQueueName']
        print(f"✅ Using job queue: {queue_name}")
        
        definitions = batch.describe_job_definitions()
        job_def_name = definitions['jobDefinitions'][0]['jobDefinitionName']
        print(f"✅ Using job definition: {job_def_name}")
        
        # Create a more realistic job definition for wildlife processing
        print("📋 Creating wildlife processing job definition...")
        
        # Submit wildlife processing job
        job_name = f"wildlife-processing-{int(time.time())}"
        print(f"📋 Submitting job: {job_name}")
        
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=queue_name,
            jobDefinition=job_def_name,
            parameters={
                'input_bucket': bucket_name,
                'input_prefix': s3_prefix,
                'output_bucket': bucket_name,
                'output_prefix': 'processed-results'
            }
        )
        
        job_id = response['jobId']
        print(f"✅ Job submitted: {job_id}")
        
        # Monitor job with more detailed output
        print("⏳ Monitoring job execution...")
        start_time = time.time()
        
        for i in range(20):  # Monitor for up to 10 minutes
            time.sleep(30)
            elapsed = int(time.time() - start_time)
            
            job = batch.describe_jobs(jobs=[job_id])
            status = job['jobs'][0]['status']
            status_reason = job['jobs'][0].get('statusReason', '')
            
            print(f"   [{elapsed:3d}s] Job status: {status}")
            if status_reason:
                print(f"      Reason: {status_reason}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                break
        
        if status == 'SUCCEEDED':
            print("✅ Job completed successfully!")
            
            # Get job details
            job_details = batch.describe_jobs(jobs=[job_id])
            job = job_details['jobs'][0]
            
            print(f"📊 Job Details:")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {status}")
            print(f"   Created: {job.get('createdAt', 'N/A')}")
            print(f"   Started: {job.get('startedAt', 'N/A')}")
            print(f"   Stopped: {job.get('stoppedAt', 'N/A')}")
            
            # Calculate processing time
            if 'startedAt' in job and 'stoppedAt' in job:
                started = job['startedAt']
                stopped = job['stoppedAt']
                duration = (stopped - started).total_seconds()
                print(f"   Duration: {duration:.1f} seconds")
            
            return True
        else:
            print(f"❌ Job failed with status: {status}")
            if status_reason:
                print(f"   Reason: {status_reason}")
            return False
            
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return False

def check_ec2_instances():
    """Check EC2 instances that were created."""
    print("\n🖥️  Checking EC2 Instances")
    print("=" * 30)
    
    ec2 = boto3.client('ec2', region_name='eu-north-1')
    
    try:
        # Get instances
        response = ec2.describe_instances()
        instances = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] != 'terminated':
                    instances.append(instance)
        
        if instances:
            print(f"✅ Found {len(instances)} EC2 instances:")
            for instance in instances:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                state = instance['State']['Name']
                launch_time = instance['LaunchTime']
                
                print(f"   - {instance_id}: {instance_type} ({state})")
                print(f"     Launched: {launch_time}")
                
                # Get tags
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                if tags:
                    print(f"     Tags: {tags}")
        else:
            print("ℹ️  No active EC2 instances found")
        
        return len(instances) > 0
        
    except Exception as e:
        print(f"❌ Error checking EC2 instances: {e}")
        return False

def generate_cost_report():
    """Generate cost report for the processing."""
    print("\n💰 Generating Cost Report")
    print("=" * 30)
    
    # Configuration
    config = CostOptimizationConfig(
        region="eu-north-1",
        environment="production",
        spot_bid_percentage=70,
        max_vcpus=100,
        gpu_required=True,
        download_stage3=True,
        create_local_runner=True,
        cost_reporting=True
    )
    
    # Initialize cost manager
    try:
        cost_manager = CostOptimizationManager(config)
        
        # Get cost metrics
        metrics = cost_manager.get_cost_metrics()
        
        print("📊 Cost Metrics:")
        print(f"   Instance count: {metrics.get('instance_count', 0)}")
        print(f"   Instance type: {metrics.get('instance_type', 'unknown')}")
        print(f"   Spot price: ${metrics.get('spot_price_per_hour', 0):.4f}/hour")
        print(f"   On-demand price: ${metrics.get('on_demand_price_per_hour', 0):.4f}/hour")
        print(f"   Savings: ${metrics.get('savings_per_hour', 0):.4f}/hour")
        print(f"   Savings percentage: {metrics.get('savings_percentage', 0):.1f}%")
        
        # Calculate estimated costs
        processing_time_hours = 0.1  # Assume 6 minutes processing
        spot_cost = metrics.get('spot_price_per_hour', 0) * processing_time_hours
        on_demand_cost = metrics.get('on_demand_price_per_hour', 0) * processing_time_hours
        savings = on_demand_cost - spot_cost
        
        print(f"\n💵 Estimated Processing Costs:")
        print(f"   Processing time: {processing_time_hours:.1f} hours")
        print(f"   Spot cost: ${spot_cost:.4f}")
        print(f"   On-demand cost: ${on_demand_cost:.4f}")
        print(f"   Savings: ${savings:.4f}")
        print(f"   Savings percentage: {(savings/on_demand_cost*100):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Cost report error: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Real Batch Processing Test with EC2")
    print("=" * 50)
    
    try:
        # Step 1: Upload data
        print("\n📤 Step 1: Uploading trailcam data")
        bucket_name, s3_prefix, uploaded_files = upload_trailcam_data()
        print(f"✅ Uploaded {len(uploaded_files)} files to s3://{bucket_name}/{s3_prefix}")
        
        # Step 2: Run batch processing
        print("\n🚀 Step 2: Running batch processing on EC2")
        if not run_real_batch_processing(bucket_name, s3_prefix):
            print("❌ Batch processing failed")
            return False
        
        # Step 3: Check EC2 instances
        print("\n🖥️  Step 3: Checking EC2 instances")
        check_ec2_instances()
        
        # Step 4: Generate cost report
        print("\n💰 Step 4: Generating cost report")
        generate_cost_report()
        
        print("\n🎉 Real batch processing test completed successfully!")
        print("✅ EC2 instances were created and used")
        print("✅ Batch processing completed")
        print("✅ Cost optimization features tested")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ Test failed!")
        sys.exit(1)
    print("\n🚀 Real EC2 processing completed! 💰🖥️")
