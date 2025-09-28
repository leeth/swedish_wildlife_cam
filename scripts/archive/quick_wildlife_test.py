#!/usr/bin/env python3
"""
Quick Wildlife Test with Infrastructure Management

This script:
1. Ensures infrastructure exists
2. Scales up if needed
3. Runs a quick wildlife processing test
4. Keeps infrastructure running (costs nothing when idle)
"""

import boto3
import time
import json
from datetime import datetime
from pathlib import Path
import sys

# Import our infrastructure manager
sys.path.append(str(Path(__file__).parent))
from infrastructure_manager import InfrastructureManager

def upload_test_data():
    """Upload small test dataset."""
    print("📤 Uploading Test Data")
    print("=" * 30)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    # Get test data directory
    test_data_dir = Path(__file__).parent.parent / 'test_data'
    if not test_data_dir.exists():
        print("❌ Test data directory not found")
        return False
    
    # Upload first 3 files for quick test
    files_uploaded = 0
    for file_path in test_data_dir.iterdir():
        if files_uploaded >= 3:  # Limit to 3 files for quick test
            break
            
        if file_path.is_file():
            key = f'trailcam-data/{file_path.name}'
            try:
                s3.upload_file(str(file_path), bucket_name, key)
                print(f"✅ Uploaded: {file_path.name}")
                files_uploaded += 1
            except Exception as e:
                print(f"❌ Failed to upload {file_path.name}: {e}")
    
    print(f"📊 Uploaded {files_uploaded} files to s3://{bucket_name}/trailcam-data/")
    return files_uploaded > 0

def create_quick_job_definition():
    """Create a quick job definition."""
    print("\n🦌 Creating Quick Wildlife Job Definition")
    print("=" * 45)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        # Create quick job definition
        response = batch.register_job_definition(
            jobDefinitionName='wildlife-quick-test',
            type='container',
            platformCapabilities=['EC2'],
            containerProperties={
                'image': 'public.ecr.aws/docker/library/ubuntu:20.04',
                'vcpus': 1,
                'memory': 2048,
                'jobRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'executionRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'environment': [
                    {'name': 'AWS_DEFAULT_REGION', 'value': 'eu-north-1'},
                    {'name': 'DATA_BUCKET', 'value': 'wildlife-test-production-696852893392'},
                    {'name': 'INPUT_PREFIX', 'value': 'trailcam-data'},
                    {'name': 'OUTPUT_PREFIX', 'value': 'quick-results'}
                ],
                'command': [
                    '/bin/bash', '-c', '''
                    echo "🦌 Quick Wildlife Test"
                    echo "📊 Processing 3 test files..."
                    
                    # Update and install
                    apt-get update -y
                    apt-get install -y python3 python3-pip curl
                    
                    # Install AWS CLI
                    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                    unzip awscliv2.zip
                    ./aws/install
                    
                    # Install boto3
                    pip3 install boto3
                    
                    # Quick processing script
                    cat > quick_process.py << 'EOF'
import os
import json
import boto3
from datetime import datetime

s3 = boto3.client('s3', region_name='eu-north-1')
bucket = os.environ['DATA_BUCKET']
input_prefix = os.environ['INPUT_PREFIX']
output_prefix = os.environ['OUTPUT_PREFIX']

# List input files
response = s3.list_objects_v2(Bucket=bucket, Prefix=input_prefix)
files = response.get('Contents', [])

print(f"📁 Found {len(files)} files to process")

results = []
for file_obj in files:
    file_key = file_obj['Key']
    file_name = os.path.basename(file_key)
    
    print(f"🔍 Processing: {file_name}")
    
    # Quick detection simulation
    detection_result = {
        'file_name': file_name,
        'timestamp': datetime.now().isoformat(),
        'detections': [
            {'class': 'deer', 'confidence': 0.85, 'bbox': [100, 150, 200, 300]},
            {'class': 'bird', 'confidence': 0.72, 'bbox': [300, 200, 400, 350]}
        ],
        'processing_time': 1.0
    }
    
    results.append(detection_result)
    
    # Save result
    result_key = f"{output_prefix}/detections/{file_name}.json"
    s3.put_object(
        Bucket=bucket,
        Key=result_key,
        Body=json.dumps(detection_result, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Saved: {result_key}")

# Save summary
summary = {
    'total_files': len(files),
    'processed_files': len(results),
    'processing_time': datetime.now().isoformat(),
    'results': results
}

summary_key = f"{output_prefix}/summary.json"
s3.put_object(
    Bucket=bucket,
    Key=summary_key,
    Body=json.dumps(summary, indent=2),
    ContentType='application/json'
)

print(f"📊 Summary saved: {summary_key}")
print(f"✅ Quick processing completed! Processed {len(results)} files")
EOF
                    
                    # Run quick processing
                    python3 quick_process.py
                    
                    echo "✅ Quick wildlife test completed!"
                    '''
                ]
            },
            retryStrategy={'attempts': 2},
            timeout={'attemptDurationSeconds': 300}
        )
        
        print(f"✅ Quick job definition created: {response['jobDefinitionArn']}")
        return True
        
    except Exception as e:
        print(f"❌ Job definition creation failed: {e}")
        return False

def submit_quick_job():
    """Submit quick wildlife processing job."""
    print("\n🦌 Submitting Quick Wildlife Job")
    print("=" * 35)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        # Get job queue
        queues = batch.describe_job_queues()
        if not queues['jobQueues']:
            print("❌ No job queues found")
            return None
        
        queue_name = queues['jobQueues'][0]['jobQueueName']
        print(f"✅ Found job queue: {queue_name}")
        
        # Submit job
        job_name = f'quick-wildlife-{int(time.time())}'
        print(f"📋 Submitting job: {job_name}")
        
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=queue_name,
            jobDefinition='wildlife-quick-test'
        )
        
        job_id = response['jobId']
        print(f"✅ Job submitted: {job_id}")
        return job_id
        
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None

def monitor_quick_job(job_id):
    """Monitor quick job progress."""
    print(f"\n⏳ Monitoring Quick Job: {job_id}")
    print("=" * 40)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    start_time = time.time()
    previous_status = None
    
    try:
        for i in range(10):  # Monitor for up to 5 minutes
            time.sleep(30)
            elapsed = int(time.time() - start_time)
            
            job = batch.describe_jobs(jobs=[job_id])
            job_info = job['jobs'][0]
            status = job_info['status']
            
            if status != previous_status:
                print(f"   [{elapsed:3d}s] Status: {status}")
                previous_status = status
            else:
                print(f"   [{elapsed:3d}s] Status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                print(f"   [{elapsed:3d}s] Job finished: {status}")
                return status == 'SUCCEEDED'
        
        print("⏰ Job monitoring timeout")
        return False
        
    except Exception as e:
        print(f"❌ Job monitoring failed: {e}")
        return False

def verify_quick_output():
    """Verify quick output files."""
    print("\n📁 Verifying Quick Output")
    print("=" * 30)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    try:
        # List quick results
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='quick-results/'
        )
        
        if 'Contents' not in response:
            print("❌ No output files found")
            return False
        
        files = response['Contents']
        print(f"✅ Found {len(files)} output files:")
        
        for file_obj in files:
            key = file_obj['Key']
            size = file_obj['Size']
            print(f"   📄 {key} ({size} bytes)")
        
        # Show summary
        summary_key = 'quick-results/summary.json'
        try:
            response = s3.get_object(Bucket=bucket_name, Key=summary_key)
            summary = json.loads(response['Body'].read().decode('utf-8'))
            
            print(f"\n📊 Quick Test Summary:")
            print(f"   Total files: {summary['total_files']}")
            print(f"   Processed files: {summary['processed_files']}")
            print(f"   Processing time: {summary['processing_time']}")
            
        except Exception as e:
            print(f"⚠️  Could not read summary: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying output: {e}")
        return False

def main():
    """Main function."""
    print("🦌 Quick Wildlife Test with Infrastructure Management")
    print("=" * 60)
    print("This test will:")
    print("1. Ensure infrastructure exists")
    print("2. Scale up compute environment")
    print("3. Upload 3 test images")
    print("4. Run quick wildlife processing")
    print("5. Verify output files")
    print("6. Keep infrastructure running (costs nothing when idle)")
    print()
    
    try:
        # Step 1: Setup infrastructure
        manager = InfrastructureManager()
        if not manager.setup_infrastructure():
            print("❌ Infrastructure setup failed")
            return False
        
        # Step 2: Scale up
        if not manager.scale_up(desired_vcpus=2):
            print("❌ Scale up failed")
            return False
        
        # Step 3: Upload test data
        if not upload_test_data():
            print("❌ Test data upload failed")
            return False
        
        # Step 4: Create job definition
        if not create_quick_job_definition():
            print("❌ Job definition creation failed")
            return False
        
        # Step 5: Submit job
        job_id = submit_quick_job()
        if not job_id:
            print("❌ Job submission failed")
            return False
        
        # Step 6: Monitor job
        if not monitor_quick_job(job_id):
            print("❌ Job monitoring failed")
            return False
        
        # Step 7: Verify output
        if not verify_quick_output():
            print("❌ Output verification failed")
            return False
        
        print("\n🎉 Quick Wildlife Test Completed Successfully!")
        print("✅ Infrastructure ready and scaled")
        print("✅ Test data uploaded")
        print("✅ Quick wildlife processing completed")
        print("✅ Output files verified")
        print("ℹ️  Infrastructure kept running (costs nothing when idle)")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
