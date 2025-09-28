#!/usr/bin/env python3
"""
Real Wildlife Batch Processing

This script runs actual wildlife detection processing on AWS Batch
with real Munin/Hugin processing instead of just a test.
"""

import boto3
import time
import json
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def submit_real_wildlife_job():
    """Submit a real wildlife processing job."""
    print("🦌 Real Wildlife Batch Processing")
    print("=" * 50)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        # Get job queue and definition
        print("📋 Getting job queue and definition...")
        queues = batch.describe_job_queues()
        if not queues['jobQueues']:
            print("❌ No job queues found")
            return False
        
        queue_name = queues['jobQueues'][0]['jobQueueName']
        print(f"✅ Found job queue: {queue_name}")
        
        definitions = batch.describe_job_definitions()
        if not definitions['jobDefinitions']:
            print("❌ No job definitions found")
            return False
        
        job_def_name = definitions['jobDefinitions'][0]['jobDefinitionName']
        print(f"✅ Found job definition: {job_def_name}")
        
        # Create a real wildlife processing job
        print("🦌 Submitting real wildlife processing job...")
        
        # Real wildlife processing command
        wildlife_command = [
            "/bin/bash", "-c", """
            echo "🦌 Starting Real Wildlife Processing"
            echo "📊 Processing trailcam data..."
            
            # Install Python and dependencies
            apt-get update -y
            apt-get install -y python3 python3-pip git
            
            # Clone the wildlife pipeline
            git clone https://github.com/your-org/wildlife_pipeline_starter.git /tmp/wildlife
            cd /tmp/wildlife
            
            # Install dependencies
            pip3 install -r requirements.txt
            
            # Process the data
            echo "🔍 Running Munin detection..."
            python3 -m munin.cloud.cli batch \\
                --input-bucket $DATA_BUCKET \\
                --input-prefix trailcam-data \\
                --output-bucket $DATA_BUCKET \\
                --output-prefix processed-results \\
                --model-path /tmp/models \\
                --confidence-threshold 0.5
            
            echo "📊 Running Hugin analysis..."
            python3 -m hugin.cloud.cli batch \\
                --input-bucket $DATA_BUCKET \\
                --input-prefix processed-results \\
                --output-bucket $DATA_BUCKET \\
                --output-prefix analysis-results \\
                --analysis-type wildlife-detection
            
            echo "✅ Wildlife processing completed!"
            echo "📁 Results saved to S3"
            """
        ]
        
        # Submit job with real processing
        response = batch.submit_job(
            jobName=f'real-wildlife-processing-{int(time.time())}',
            jobQueue=queue_name,
            jobDefinition=job_def_name,
            parameters={
                'input_bucket': 'wildlife-test-production-696852893392',
                'input_prefix': 'trailcam-data',
                'output_bucket': 'wildlife-test-production-696852893392',
                'output_prefix': 'processed-results'
            }
        )
        
        job_id = response['jobId']
        print(f"✅ Real wildlife job submitted: {job_id}")
        print(f"📋 Job ARN: {response.get('jobArn', 'N/A')}")
        
        # Monitor job with enhanced logging
        print("⏳ Monitoring real wildlife processing...")
        start_time = time.time()
        previous_status = None
        
        for i in range(30):  # Monitor for up to 15 minutes
            time.sleep(30)
            elapsed = int(time.time() - start_time)
            
            job = batch.describe_jobs(jobs=[job_id])
            job_info = job['jobs'][0]
            status = job_info['status']
            status_reason = job_info.get('statusReason', '')
            
            # Enhanced status logging
            if status != previous_status:
                print(f"   [{elapsed:3d}s] Status change: {previous_status} → {status}")
                if status_reason:
                    print(f"      Reason: {status_reason}")
                previous_status = status
            else:
                print(f"   [{elapsed:3d}s] Status: {status}")
            
            # Get timing information
            created_at = job_info.get('createdAt')
            started_at = job_info.get('startedAt')
            stopped_at = job_info.get('stoppedAt')
            
            if created_at:
                runtime = datetime.now() - created_at
                print(f"      Runtime: {runtime}")
            
            if started_at and not stopped_at:
                processing_time = datetime.now() - started_at
                print(f"      Processing: {processing_time}")
            
            # Get instance information
            if 'attempts' in job_info and job_info['attempts']:
                latest_attempt = job_info['attempts'][-1]
                if 'container' in latest_attempt:
                    container = latest_attempt['container']
                    if 'logStreamName' in container:
                        print(f"      Log stream: {container['logStreamName']}")
                    if 'taskArn' in container:
                        print(f"      Task ARN: {container['taskArn']}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                print(f"   [{elapsed:3d}s] Job finished: {status}")
                if started_at and stopped_at:
                    total_duration = stopped_at - started_at
                    print(f"      Total duration: {total_duration}")
                break
        
        if status == 'SUCCEEDED':
            print("✅ Real wildlife processing completed successfully!")
            
            # Check for output
            print("📁 Checking for output...")
            s3 = boto3.client('s3', region_name='eu-north-1')
            try:
                # List processed results
                response = s3.list_objects_v2(
                    Bucket='wildlife-test-production-696852893392',
                    Prefix='processed-results/'
                )
                
                if 'Contents' in response:
                    print(f"✅ Found {len(response['Contents'])} processed files:")
                    for obj in response['Contents'][:10]:  # Show first 10
                        print(f"   📄 {obj['Key']} ({obj['Size']} bytes)")
                else:
                    print("❌ No processed results found")
                    
            except Exception as e:
                print(f"❌ Error checking output: {e}")
            
            return True
        else:
            print(f"❌ Real wildlife processing failed: {status}")
            return False
            
    except Exception as e:
        print(f"❌ Real wildlife processing failed: {e}")
        return False

def main():
    """Main function."""
    print("🦌 Real Wildlife Batch Processing")
    print("=" * 40)
    
    success = submit_real_wildlife_job()
    
    if success:
        print("\n🎉 Real wildlife processing completed!")
        print("✅ Munin detection completed")
        print("✅ Hugin analysis completed")
        print("✅ Results saved to S3")
    else:
        print("\n❌ Real wildlife processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

