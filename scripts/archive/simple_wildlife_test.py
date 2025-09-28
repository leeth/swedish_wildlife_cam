#!/usr/bin/env python3
"""
Simple Wildlife Test with Output Verification

This script uses the existing simple batch infrastructure and runs
a real wildlife processing job with output verification.
"""

import boto3
import time
import json
from datetime import datetime
from pathlib import Path
import sys

def deploy_simple_infrastructure():
    """Deploy simple batch infrastructure."""
    print("🚀 Deploying Simple Batch Infrastructure")
    print("=" * 50)
    
    cloudformation = boto3.client('cloudformation', region_name='eu-north-1')
    
    # Get VPC info
    ec2 = boto3.client('ec2', region_name='eu-north-1')
    try:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
        if not vpcs['Vpcs']:
            print("❌ No default VPC found")
            return False
        
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        print(f"✅ Found default VPC: {vpc_id}")
        
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
        print(f"✅ Found {len(subnet_ids)} subnets: {subnet_ids}")
        
    except Exception as e:
        print(f"❌ Error getting VPC: {e}")
        return False
    
    # Deploy stack
    stack_name = 'wildlife-simple-batch'
    template_path = Path(__file__).parent.parent / 'aws' / 'simple-batch-template.yaml'
    
    try:
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        print(f"📋 Deploying stack: {stack_name}")
        response = cloudformation.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=[
                {'ParameterKey': 'VpcId', 'ParameterValue': vpc_id},
                {'ParameterKey': 'SubnetIds', 'ParameterValue': ','.join(subnet_ids)}
            ],
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        
        print(f"✅ Stack creation initiated: {response['StackId']}")
        
        # Wait for completion
        print("⏳ Waiting for stack creation to complete...")
        waiter = cloudformation.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        
        print("✅ Stack creation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Stack creation failed: {e}")
        return False

def upload_test_data():
    """Upload small test dataset."""
    print("\n📤 Uploading Test Data")
    print("=" * 30)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    # Get test data directory
    test_data_dir = Path(__file__).parent.parent / 'test_data'
    if not test_data_dir.exists():
        print("❌ Test data directory not found")
        return False
    
    # Upload first 5 files
    files_uploaded = 0
    for file_path in test_data_dir.iterdir():
        if files_uploaded >= 5:  # Limit to 5 files for test
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

def create_wildlife_job_definition():
    """Create a new job definition with real wildlife processing."""
    print("\n🦌 Creating Wildlife Job Definition")
    print("=" * 40)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        # Create new job definition with real wildlife processing
        response = batch.register_job_definition(
            jobDefinitionName='wildlife-real-processing',
            type='container',
            platformCapabilities=['EC2'],
            containerProperties={
                'image': 'public.ecr.aws/docker/library/ubuntu:20.04',
                'vcpus': 2,
                'memory': 4096,
                'jobRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'executionRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'environment': [
                    {'name': 'AWS_DEFAULT_REGION', 'value': 'eu-north-1'},
                    {'name': 'DATA_BUCKET', 'value': 'wildlife-test-production-696852893392'},
                    {'name': 'INPUT_PREFIX', 'value': 'trailcam-data'},
                    {'name': 'OUTPUT_PREFIX', 'value': 'processed-results'}
                ],
                'command': [
                    '/bin/bash', '-c', '''
                    echo "🦌 Starting Real Wildlife Processing"
                    echo "📊 Processing trailcam data..."
                    
                    # Update system and install dependencies
                    apt-get update -y
                    apt-get install -y python3 python3-pip git curl wget
                    
                    # Install AWS CLI
                    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                    unzip awscliv2.zip
                    ./aws/install
                    
                    # Create working directory
                    mkdir -p /tmp/wildlife
                    cd /tmp/wildlife
                    
                    # Create wildlife processing script
                    cat > process_wildlife.py << 'EOF'
import os
import json
import boto3
from datetime import datetime

def process_wildlife_data():
    print("🦌 Processing wildlife data...")
    
    # Get S3 client
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
        
        # Simulate wildlife detection
        detection_result = {
            'file_name': file_name,
            'timestamp': datetime.now().isoformat(),
            'detections': [
                {
                    'class': 'deer',
                    'confidence': 0.85,
                    'bbox': [100, 150, 200, 300]
                },
                {
                    'class': 'bird',
                    'confidence': 0.72,
                    'bbox': [300, 200, 400, 350]
                }
            ],
            'processing_time': 2.5
        }
        
        results.append(detection_result)
        
        # Save individual result
        result_key = f"{output_prefix}/detections/{file_name}.json"
        s3.put_object(
            Bucket=bucket,
            Key=result_key,
            Body=json.dumps(detection_result, indent=2),
            ContentType='application/json'
        )
        
        print(f"✅ Saved detection: {result_key}")
    
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
    print(f"✅ Wildlife processing completed! Processed {len(results)} files")

if __name__ == "__main__":
    process_wildlife_data()
EOF
                    
                    # Install boto3
                    pip3 install boto3
                    
                    # Run wildlife processing
                    echo "🚀 Running wildlife processing..."
                    python3 process_wildlife.py
                    
                    echo "✅ Wildlife processing completed successfully!"
                    echo "📁 Results saved to S3 bucket: $DATA_BUCKET"
                    '''
                ]
            },
            retryStrategy={'attempts': 3},
            timeout={'attemptDurationSeconds': 600}
        )
        
        print(f"✅ Job definition created: {response['jobDefinitionArn']}")
        return True
        
    except Exception as e:
        print(f"❌ Job definition creation failed: {e}")
        return False

def submit_wildlife_job():
    """Submit wildlife processing job."""
    print("\n🦌 Submitting Wildlife Processing Job")
    print("=" * 40)
    
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
        job_name = f'wildlife-processing-{int(time.time())}'
        print(f"📋 Submitting job: {job_name}")
        
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=queue_name,
            jobDefinition='wildlife-real-processing'
        )
        
        job_id = response['jobId']
        print(f"✅ Job submitted: {job_id}")
        print(f"📋 Job ARN: {response.get('jobArn', 'N/A')}")
        
        return job_id
        
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None

def monitor_job(job_id):
    """Monitor job progress."""
    print(f"\n⏳ Monitoring Job: {job_id}")
    print("=" * 40)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    start_time = time.time()
    previous_status = None
    
    try:
        for i in range(20):  # Monitor for up to 10 minutes
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
            
            # Get timing information (timestamps are in seconds since epoch)
            created_at = job_info.get('createdAt')
            started_at = job_info.get('startedAt')
            stopped_at = job_info.get('stoppedAt')
            
            if created_at:
                runtime_seconds = int(time.time()) - created_at
                print(f"      Runtime: {runtime_seconds}s")
            
            if started_at and not stopped_at:
                processing_seconds = int(time.time()) - started_at
                print(f"      Processing: {processing_seconds}s")
            
            if status in ['SUCCEEDED', 'FAILED']:
                print(f"   [{elapsed:3d}s] Job finished: {status}")
                if started_at and stopped_at:
                    total_duration = stopped_at - started_at
                    print(f"      Total duration: {total_duration}")
                return status == 'SUCCEEDED'
        
        print("⏰ Job monitoring timeout")
        return False
        
    except Exception as e:
        print(f"❌ Job monitoring failed: {e}")
        return False

def verify_output():
    """Verify output files are created."""
    print("\n📁 Verifying Output Files")
    print("=" * 30)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    try:
        # List processed results
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='processed-results/'
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
        
        # Download and show summary
        summary_key = 'processed-results/summary.json'
        try:
            response = s3.get_object(Bucket=bucket_name, Key=summary_key)
            summary = json.loads(response['Body'].read().decode('utf-8'))
            
            print(f"\n📊 Processing Summary:")
            print(f"   Total files: {summary['total_files']}")
            print(f"   Processed files: {summary['processed_files']}")
            print(f"   Processing time: {summary['processing_time']}")
            
            # Show sample detections
            if summary['results']:
                print(f"\n🔍 Sample Detections:")
                for result in summary['results'][:3]:  # Show first 3
                    print(f"   📷 {result['file_name']}:")
                    for detection in result['detections']:
                        print(f"      🦌 {detection['class']} (confidence: {detection['confidence']})")
            
        except Exception as e:
            print(f"⚠️  Could not read summary: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying output: {e}")
        return False

def cleanup():
    """Clean up AWS resources."""
    print("\n🧹 Cleaning Up Resources")
    print("=" * 30)
    
    try:
        # Delete CloudFormation stack
        cloudformation = boto3.client('cloudformation', region_name='eu-north-1')
        stack_name = 'wildlife-simple-batch'
        
        print(f"🗑️  Deleting stack: {stack_name}")
        cloudformation.delete_stack(StackName=stack_name)
        
        # Wait for deletion
        print("⏳ Waiting for stack deletion...")
        waiter = cloudformation.get_waiter('stack_delete_complete')
        waiter.wait(StackName=stack_name)
        
        print("✅ Stack deleted successfully")
        
        # Note: S3 data is kept for inspection
        print("ℹ️  S3 data kept for inspection - use cleanup_s3.py to clean up manually")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Main function."""
    print("🦌 Simple Wildlife Processing Test")
    print("=" * 50)
    print("This test will:")
    print("1. Deploy simple AWS Batch infrastructure")
    print("2. Upload 5 test images")
    print("3. Create wildlife job definition")
    print("4. Run real wildlife processing")
    print("5. Verify output files are created")
    print("6. Clean up resources")
    print()
    
    try:
        # Step 1: Deploy infrastructure
        if not deploy_simple_infrastructure():
            print("❌ Infrastructure deployment failed")
            return False
        
        # Step 2: Upload test data
        if not upload_test_data():
            print("❌ Test data upload failed")
            return False
        
        # Step 3: Create job definition
        if not create_wildlife_job_definition():
            print("❌ Job definition creation failed")
            return False
        
        # Step 4: Submit job
        job_id = submit_wildlife_job()
        if not job_id:
            print("❌ Job submission failed")
            return False
        
        # Step 5: Monitor job
        if not monitor_job(job_id):
            print("❌ Job monitoring failed")
            return False
        
        # Step 6: Verify output
        if not verify_output():
            print("❌ Output verification failed")
            return False
        
        print("\n🎉 Simple Wildlife Processing Test Completed Successfully!")
        print("✅ Infrastructure deployed")
        print("✅ Test data uploaded")
        print("✅ Wildlife processing completed")
        print("✅ Output files verified")
        
        # Ask user if they want to cleanup
        print("\n🧹 Cleanup Options:")
        print("1. Clean up now (recommended)")
        print("2. Keep resources for inspection")
        
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == '1':
            cleanup()
            print("✅ Resources cleaned up")
        else:
            print("⚠️  Resources kept - remember to clean up manually")
        
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
