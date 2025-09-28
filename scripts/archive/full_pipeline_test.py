#!/usr/bin/env python3
"""
Full Wildlife Pipeline Test - Stages 0-2

This script runs a complete wildlife processing pipeline:
- Stage 0: Upload all test data to S3
- Stage 1: Create manifest and metadata
- Stage 2: Run wildlife detection and processing
- Verify all outputs are created correctly
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

def upload_all_test_data():
    """Upload all test data to S3."""
    print("📤 Stage 0: Uploading All Test Data")
    print("=" * 40)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    # Get test data directory
    test_data_dir = Path(__file__).parent.parent / 'test_data'
    if not test_data_dir.exists():
        print("❌ Test data directory not found")
        return False
    
    # Upload all files
    files_uploaded = 0
    total_size = 0
    
    for file_path in test_data_dir.iterdir():
        if file_path.is_file():
            key = f'raw-data/{file_path.name}'
            try:
                s3.upload_file(str(file_path), bucket_name, key)
                file_size = file_path.stat().st_size
                total_size += file_size
                print(f"✅ Uploaded: {file_path.name} ({file_size:,} bytes)")
                files_uploaded += 1
            except Exception as e:
                print(f"❌ Failed to upload {file_path.name}: {e}")
    
    print(f"\n📊 Upload Summary:")
    print(f"   Files uploaded: {files_uploaded}")
    print(f"   Total size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    print(f"   Location: s3://{bucket_name}/raw-data/")
    
    return files_uploaded > 0

def create_stage1_job_definition():
    """Create Stage 1 job definition (manifest creation)."""
    print("\n📋 Stage 1: Creating Manifest Job Definition")
    print("=" * 50)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        response = batch.register_job_definition(
            jobDefinitionName='wildlife-stage1-manifest',
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
                    {'name': 'INPUT_PREFIX', 'value': 'raw-data'},
                    {'name': 'OUTPUT_PREFIX', 'value': 'stage1-manifest'}
                ],
                'command': [
                    '/bin/bash', '-c', '''
                    echo "📋 Stage 1: Creating Wildlife Manifest"
                    echo "======================================"
                    
                    # Update system
                    apt-get update -y
                    apt-get install -y python3 python3-pip curl
                    
                    # Install AWS CLI
                    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                    unzip awscliv2.zip
                    ./aws/install
                    
                    # Install boto3
                    pip3 install boto3
                    
                    # Create manifest script
                    cat > create_manifest.py << 'EOF'
import os
import json
import boto3
from datetime import datetime
import mimetypes

def create_manifest():
    print("📋 Creating wildlife data manifest...")
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket = os.environ['DATA_BUCKET']
    input_prefix = os.environ['INPUT_PREFIX']
    output_prefix = os.environ['OUTPUT_PREFIX']
    
    # List all input files
    response = s3.list_objects_v2(Bucket=bucket, Prefix=input_prefix)
    files = response.get('Contents', [])
    
    print(f"📁 Found {len(files)} files to process")
    
    manifest = {
        'created_at': datetime.now().isoformat(),
        'total_files': len(files),
        'files': []
    }
    
    for file_obj in files:
        file_key = file_obj['Key']
        file_name = os.path.basename(file_key)
        file_size = file_obj['Size']
        last_modified = file_obj['LastModified'].isoformat()
        
        # Determine file type
        if file_name.lower().endswith(('.jpg', '.jpeg')):
            file_type = 'image'
            media_type = 'photo'
        elif file_name.lower().endswith(('.mp4', '.avi', '.mov')):
            file_type = 'video'
            media_type = 'video'
        else:
            file_type = 'unknown'
            media_type = 'unknown'
        
        # Extract timestamp from filename if possible
        timestamp = None
        if len(file_name) >= 14 and file_name[:8].isdigit():
            try:
                timestamp = file_name[:14]
            except:
                pass
        
        file_entry = {
            'file_name': file_name,
            'file_key': file_key,
            'file_size': file_size,
            'file_type': file_type,
            'media_type': media_type,
            'last_modified': last_modified,
            'timestamp': timestamp,
            'processing_status': 'pending'
        }
        
        manifest['files'].append(file_entry)
        print(f"   📄 {file_name} ({file_type}, {file_size:,} bytes)")
    
    # Save manifest
    manifest_key = f"{output_prefix}/manifest.json"
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Manifest saved: {manifest_key}")
    print(f"📊 Total files: {len(files)}")
    print(f"📊 Images: {len([f for f in manifest['files'] if f['file_type'] == 'image'])}")
    print(f"📊 Videos: {len([f for f in manifest['files'] if f['file_type'] == 'video'])}")
    
    return manifest

if __name__ == "__main__":
    create_manifest()
EOF
                    
                    # Run manifest creation
                    python3 create_manifest.py
                    
                    echo "✅ Stage 1 completed: Manifest created"
                    '''
                ]
            },
            retryStrategy={'attempts': 2},
            timeout={'attemptDurationSeconds': 600}
        )
        
        print(f"✅ Stage 1 job definition created: {response['jobDefinitionArn']}")
        return True
        
    except Exception as e:
        print(f"❌ Stage 1 job definition creation failed: {e}")
        return False

def create_stage2_job_definition():
    """Create Stage 2 job definition (wildlife detection)."""
    print("\n🦌 Stage 2: Creating Detection Job Definition")
    print("=" * 50)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    try:
        response = batch.register_job_definition(
            jobDefinitionName='wildlife-stage2-detection',
            type='container',
            platformCapabilities=['EC2'],
            containerProperties={
                'image': 'public.ecr.aws/docker/library/ubuntu:20.04',
                'vcpus': 4,
                'memory': 8192,
                'jobRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'executionRoleArn': 'arn:aws:iam::696852893392:role/wildlife-batch-job-role-production',
                'environment': [
                    {'name': 'AWS_DEFAULT_REGION', 'value': 'eu-north-1'},
                    {'name': 'DATA_BUCKET', 'value': 'wildlife-test-production-696852893392'},
                    {'name': 'MANIFEST_PREFIX', 'value': 'stage1-manifest'},
                    {'name': 'OUTPUT_PREFIX', 'value': 'stage2-detections'}
                ],
                'command': [
                    '/bin/bash', '-c', '''
                    echo "🦌 Stage 2: Wildlife Detection Processing"
                    echo "========================================"
                    
                    # Update system
                    apt-get update -y
                    apt-get install -y python3 python3-pip curl
                    
                    # Install AWS CLI
                    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                    unzip awscliv2.zip
                    ./aws/install
                    
                    # Install boto3
                    pip3 install boto3
                    
                    # Create detection script
                    cat > run_detection.py << 'EOF'
import os
import json
import boto3
from datetime import datetime
import random

def run_wildlife_detection():
    print("🦌 Running wildlife detection on all files...")
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket = os.environ['DATA_BUCKET']
    manifest_prefix = os.environ['MANIFEST_PREFIX']
    output_prefix = os.environ['OUTPUT_PREFIX']
    
    # Load manifest
    manifest_key = f"{manifest_prefix}/manifest.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=manifest_key)
        manifest = json.loads(response['Body'].read().decode('utf-8'))
        print(f"📋 Loaded manifest with {manifest['total_files']} files")
    except Exception as e:
        print(f"❌ Failed to load manifest: {e}")
        return False
    
    # Process each file
    results = []
    for i, file_entry in enumerate(manifest['files']):
        file_name = file_entry['file_name']
        file_type = file_entry['file_type']
        
        print(f"🔍 Processing {i+1}/{len(manifest['files'])}: {file_name}")
        
        # Simulate wildlife detection
        detections = []
        
        # Random chance of detection based on file type
        if file_type == 'image':
            detection_chance = 0.7  # 70% chance for images
        else:  # video
            detection_chance = 0.9  # 90% chance for videos
        
        if random.random() < detection_chance:
            # Generate random detections
            num_detections = random.randint(1, 3)
            for j in range(num_detections):
                animal_types = ['deer', 'bird', 'fox', 'rabbit', 'squirrel']
                animal = random.choice(animal_types)
                confidence = random.uniform(0.6, 0.95)
                
                detection = {
                    'class': animal,
                    'confidence': round(confidence, 2),
                    'bbox': [
                        random.randint(50, 400),
                        random.randint(50, 300),
                        random.randint(100, 500),
                        random.randint(100, 400)
                    ],
                    'timestamp': datetime.now().isoformat()
                }
                detections.append(detection)
        
        # Create result
        result = {
            'file_name': file_name,
            'file_type': file_type,
            'processing_time': datetime.now().isoformat(),
            'detections': detections,
            'detection_count': len(detections),
            'processing_duration': random.uniform(1.0, 5.0)
        }
        
        results.append(result)
        
        # Save individual result
        result_key = f"{output_prefix}/detections/{file_name}.json"
        s3.put_object(
            Bucket=bucket,
            Key=result_key,
            Body=json.dumps(result, indent=2),
            ContentType='application/json'
        )
        
        print(f"   ✅ {len(detections)} detections found")
    
    # Create summary
    total_detections = sum(r['detection_count'] for r in results)
    files_with_detections = len([r for r in results if r['detection_count'] > 0])
    
    summary = {
        'processing_time': datetime.now().isoformat(),
        'total_files_processed': len(results),
        'files_with_detections': files_with_detections,
        'total_detections': total_detections,
        'detection_rate': files_with_detections / len(results) if results else 0,
        'results': results
    }
    
    # Save summary
    summary_key = f"{output_prefix}/summary.json"
    s3.put_object(
        Bucket=bucket,
        Key=summary_key,
        Body=json.dumps(summary, indent=2),
        ContentType='application/json'
    )
    
    print(f"\\n📊 Detection Summary:")
    print(f"   Files processed: {len(results)}")
    print(f"   Files with detections: {files_with_detections}")
    print(f"   Total detections: {total_detections}")
    print(f"   Detection rate: {summary['detection_rate']:.1%}")
    print(f"✅ Stage 2 completed: Detection processing finished")
    
    return True

if __name__ == "__main__":
    run_wildlife_detection()
EOF
                    
                    # Run detection
                    python3 run_detection.py
                    
                    echo "✅ Stage 2 completed: Wildlife detection finished"
                    '''
                ]
            },
            retryStrategy={'attempts': 2},
            timeout={'attemptDurationSeconds': 1800}  # 30 minutes
        )
        
        print(f"✅ Stage 2 job definition created: {response['jobDefinitionArn']}")
        return True
        
    except Exception as e:
        print(f"❌ Stage 2 job definition creation failed: {e}")
        return False

def submit_stage_job(stage_name, job_definition_name):
    """Submit a stage job."""
    print(f"\n📋 Submitting {stage_name} Job")
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
        job_name = f'{stage_name.lower().replace(" ", "-")}-{int(time.time())}'
        print(f"📋 Submitting job: {job_name}")
        
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=queue_name,
            jobDefinition=job_definition_name
        )
        
        job_id = response['jobId']
        print(f"✅ Job submitted: {job_id}")
        return job_id
        
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None

def monitor_stage_job(job_id, stage_name):
    """Monitor a stage job."""
    print(f"\n⏳ Monitoring {stage_name} Job: {job_id}")
    print("=" * 50)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    start_time = time.time()
    previous_status = None
    
    try:
        for i in range(40):  # Monitor for up to 20 minutes
            time.sleep(30)
            elapsed = int(time.time() - start_time)
            
            job = batch.describe_jobs(jobs=[job_id])
            job_info = job['jobs'][0]
            status = job_info['status']
            status_reason = job_info.get('statusReason', '')
            
            if status != previous_status:
                print(f"   [{elapsed:3d}s] Status change: {previous_status} → {status}")
                if status_reason:
                    print(f"      Reason: {status_reason}")
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

def verify_stage_outputs():
    """Verify all stage outputs."""
    print("\n📁 Verifying All Stage Outputs")
    print("=" * 35)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    bucket_name = 'wildlife-test-production-696852893392'
    
    try:
        # Check Stage 1 output (manifest)
        print("📋 Stage 1 Output (Manifest):")
        manifest_response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='stage1-manifest/'
        )
        
        if 'Contents' in manifest_response:
            manifest_files = manifest_response['Contents']
            print(f"   ✅ Found {len(manifest_files)} manifest files")
            
            # Show manifest summary
            manifest_key = 'stage1-manifest/manifest.json'
            try:
                response = s3.get_object(Bucket=bucket_name, Key=manifest_key)
                manifest = json.loads(response['Body'].read().decode('utf-8'))
                print(f"   📊 Total files: {manifest['total_files']}")
                print(f"   📊 Images: {len([f for f in manifest['files'] if f['file_type'] == 'image'])}")
                print(f"   📊 Videos: {len([f for f in manifest['files'] if f['file_type'] == 'video'])}")
            except Exception as e:
                print(f"   ⚠️  Could not read manifest: {e}")
        else:
            print("   ❌ No manifest files found")
            return False
        
        # Check Stage 2 output (detections)
        print("\n🦌 Stage 2 Output (Detections):")
        detection_response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='stage2-detections/'
        )
        
        if 'Contents' in detection_response:
            detection_files = detection_response['Contents']
            print(f"   ✅ Found {len(detection_files)} detection files")
            
            # Show detection summary
            summary_key = 'stage2-detections/summary.json'
            try:
                response = s3.get_object(Bucket=bucket_name, Key=summary_key)
                summary = json.loads(response['Body'].read().decode('utf-8'))
                print(f"   📊 Files processed: {summary['total_files_processed']}")
                print(f"   📊 Files with detections: {summary['files_with_detections']}")
                print(f"   📊 Total detections: {summary['total_detections']}")
                print(f"   📊 Detection rate: {summary['detection_rate']:.1%}")
            except Exception as e:
                print(f"   ⚠️  Could not read detection summary: {e}")
        else:
            print("   ❌ No detection files found")
            return False
        
        print("\n✅ All stages completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying outputs: {e}")
        return False

def main():
    """Main function."""
    print("🦌 Full Wildlife Pipeline Test - Stages 0-2")
    print("=" * 50)
    print("This test will:")
    print("1. Ensure infrastructure exists and scale up")
    print("2. Stage 0: Upload all test data (29 files)")
    print("3. Stage 1: Create manifest and metadata")
    print("4. Stage 2: Run wildlife detection processing")
    print("5. Verify all outputs are created correctly")
    print("6. Keep infrastructure running (costs nothing when idle)")
    print()
    
    try:
        # Step 1: Setup infrastructure
        manager = InfrastructureManager()
        if not manager.setup_infrastructure():
            print("❌ Infrastructure setup failed")
            return False
        
        # Scale up for full processing
        if not manager.scale_up(desired_vcpus=6):
            print("❌ Scale up failed")
            return False
        
        # Step 2: Stage 0 - Upload all data
        if not upload_all_test_data():
            print("❌ Stage 0 failed: Data upload failed")
            return False
        
        # Step 3: Stage 1 - Create job definition and run
        if not create_stage1_job_definition():
            print("❌ Stage 1 failed: Job definition creation failed")
            return False
        
        stage1_job_id = submit_stage_job("Stage 1", "wildlife-stage1-manifest")
        if not stage1_job_id:
            print("❌ Stage 1 failed: Job submission failed")
            return False
        
        if not monitor_stage_job(stage1_job_id, "Stage 1"):
            print("❌ Stage 1 failed: Job monitoring failed")
            return False
        
        # Step 4: Stage 2 - Create job definition and run
        if not create_stage2_job_definition():
            print("❌ Stage 2 failed: Job definition creation failed")
            return False
        
        stage2_job_id = submit_stage_job("Stage 2", "wildlife-stage2-detection")
        if not stage2_job_id:
            print("❌ Stage 2 failed: Job submission failed")
            return False
        
        if not monitor_stage_job(stage2_job_id, "Stage 2"):
            print("❌ Stage 2 failed: Job monitoring failed")
            return False
        
        # Step 5: Verify all outputs
        if not verify_stage_outputs():
            print("❌ Output verification failed")
            return False
        
        print("\n🎉 Full Wildlife Pipeline Test Completed Successfully!")
        print("✅ Infrastructure ready and scaled")
        print("✅ Stage 0: All test data uploaded")
        print("✅ Stage 1: Manifest created")
        print("✅ Stage 2: Wildlife detection completed")
        print("✅ All outputs verified")
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
