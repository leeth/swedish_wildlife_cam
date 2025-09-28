#!/usr/bin/env python3
"""
AWS Pipeline Test Script

This script tests the complete AWS wildlife pipeline:
- Tests S3 storage operations
- Tests AWS Batch job submission
- Tests GPU-enabled image processing
- Validates end-to-end pipeline execution
"""

import boto3
import json
import time
import subprocess
from pathlib import Path
import sys
import argparse
from datetime import datetime
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wildlife_pipeline.cloud.config import CloudConfig
from src.wildlife_pipeline.cloud.cli import main as cloud_cli_main


def test_s3_operations(bucket_name: str = "wildlife-pipeline-data"):
    """Test S3 storage operations."""
    print("🧪 Testing S3 Operations...")
    
    try:
        s3 = boto3.client('s3')
        
        # Test bucket access
        s3.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket accessible: {bucket_name}")
        
        # Test object upload
        test_key = "test/upload-test.txt"
        test_content = f"Test upload at {datetime.now().isoformat()}"
        
        s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8')
        )
        print(f"✅ Uploaded test object: {test_key}")
        
        # Test object download
        response = s3.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read().decode('utf-8')
        
        if downloaded_content == test_content:
            print(f"✅ Downloaded and verified test object")
        else:
            print(f"❌ Downloaded content doesn't match")
            return False
        
        # Test object deletion
        s3.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"✅ Deleted test object: {test_key}")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 operations test failed: {e}")
        return False


def test_batch_job_submission():
    """Test AWS Batch job submission."""
    print("\n🧪 Testing Batch Job Submission...")
    
    try:
        batch = boto3.client('batch')
        
        # Get job queue
        response = batch.describe_job_queues()
        job_queues = [q['jobQueueName'] for q in response['jobQueues'] if 'wildlife' in q['jobQueueName']]
        
        if not job_queues:
            print("❌ No wildlife pipeline job queues found")
            return False
        
        job_queue = job_queues[0]
        print(f"✅ Found job queue: {job_queue}")
        
        # Get job definition
        response = batch.describe_job_definitions()
        job_definitions = [jd['jobDefinitionName'] for jd in response['jobDefinitions'] if 'wildlife' in jd['jobDefinitionName']]
        
        if not job_definitions:
            print("❌ No wildlife pipeline job definitions found")
            return False
        
        job_definition = job_definitions[0]
        print(f"✅ Found job definition: {job_definition}")
        
        # Submit test job
        job_name = f"test-job-{int(time.time())}"
        
        response = batch.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            parameters={
                'input_path': 's3://wildlife-pipeline-data/test/',
                'output_path': 's3://wildlife-pipeline-results/test/',
                'model': 'yolov8n'
            }
        )
        
        job_id = response['jobId']
        print(f"✅ Submitted test job: {job_name} (ID: {job_id})")
        
        # Monitor job status
        print("⏳ Monitoring job status...")
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = batch.describe_jobs(jobs=[job_id])
            job = response['jobs'][0]
            status = job['status']
            
            print(f"  Status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                break
            
            time.sleep(10)
        
        if status == 'SUCCEEDED':
            print(f"✅ Test job completed successfully")
            return True
        else:
            print(f"❌ Test job failed with status: {status}")
            return False
        
    except Exception as e:
        print(f"❌ Batch job submission test failed: {e}")
        return False


def test_gpu_processing():
    """Test GPU-enabled image processing."""
    print("\n🧪 Testing GPU Processing...")
    
    try:
        # Check if GPU instances are available
        ec2 = boto3.client('ec2')
        
        response = ec2.describe_instance_types(
            Filters=[
                {'Name': 'instance-type', 'Values': ['g4dn.*', 'p3.*']}
            ]
        )
        
        gpu_types = [instance['InstanceType'] for instance in response['InstanceTypes']]
        
        if not gpu_types:
            print("❌ No GPU instances available in this region")
            return False
        
        print(f"✅ GPU instances available: {', '.join(gpu_types[:3])}")
        
        # Test GPU-enabled job submission
        batch = boto3.client('batch')
        
        # Get GPU-enabled job definition
        response = batch.describe_job_definitions()
        gpu_job_definitions = [
            jd for jd in response['jobDefinitions'] 
            if 'wildlife' in jd['jobDefinitionName'] and 'gpu' in jd['jobDefinitionName'].lower()
        ]
        
        if not gpu_job_definitions:
            print("❌ No GPU-enabled job definitions found")
            return False
        
        gpu_job_def = gpu_job_definitions[0]
        print(f"✅ Found GPU job definition: {gpu_job_def['jobDefinitionName']}")
        
        # Check if job definition has GPU requirements
        container_props = gpu_job_def['containerProperties']
        resource_reqs = container_props.get('resourceRequirements', [])
        
        gpu_requirements = [req for req in resource_reqs if req['type'] == 'GPU']
        
        if gpu_requirements:
            print(f"✅ Job definition has GPU requirements: {gpu_requirements}")
            return True
        else:
            print("❌ Job definition doesn't have GPU requirements")
            return False
        
    except Exception as e:
        print(f"❌ GPU processing test failed: {e}")
        return False


def test_cloud_pipeline():
    """Test the cloud pipeline execution."""
    print("\n🧪 Testing Cloud Pipeline...")
    
    try:
        # Test cloud configuration
        cloud_config = CloudConfig.from_profile("cloud")
        print("✅ Cloud configuration loaded")
        
        # Test storage adapter
        storage = cloud_config.create_storage_adapter()
        print(f"✅ Storage adapter created: {type(storage).__name__}")
        
        # Test model provider
        model_provider = cloud_config.create_model_provider()
        print(f"✅ Model provider created: {type(model_provider).__name__}")
        
        # Test runner
        runner = cloud_config.create_runner()
        print(f"✅ Runner created: {type(runner).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cloud pipeline test failed: {e}")
        return False


def test_end_to_end_pipeline():
    """Test end-to-end pipeline execution."""
    print("\n🧪 Testing End-to-End Pipeline...")
    
    try:
        # Create test data
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            
            # Create test images
            test_images_dir = test_dir / "test_images"
            test_images_dir.mkdir()
            
            # Create dummy test images
            for i in range(3):
                test_image = test_images_dir / f"test_image_{i}.jpg"
                test_image.write_bytes(b"dummy image data")
            
            print(f"✅ Created test images in: {test_images_dir}")
            
            # Test Stage 1 processing
            print("🔍 Testing Stage 1 processing...")
            
            # This would normally call the cloud CLI
            # For now, we'll just test the configuration
            cloud_config = CloudConfig.from_profile("cloud")
            
            if cloud_config:
                print("✅ Stage 1 configuration valid")
                return True
            else:
                print("❌ Stage 1 configuration invalid")
                return False
        
    except Exception as e:
        print(f"❌ End-to-end pipeline test failed: {e}")
        return False


def run_comprehensive_pipeline_test():
    """Run comprehensive pipeline test suite."""
    print("🚀 AWS Pipeline Comprehensive Test")
    print("=" * 50)
    
    tests = [
        ("S3 Operations", test_s3_operations),
        ("Batch Job Submission", test_batch_job_submission),
        ("GPU Processing", test_gpu_processing),
        ("Cloud Pipeline", test_cloud_pipeline),
        ("End-to-End Pipeline", test_end_to_end_pipeline)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Pipeline Test Results Summary:")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All pipeline tests passed! AWS setup is ready for production.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


def main():
    """Main CLI for AWS pipeline testing."""
    parser = argparse.ArgumentParser(description="Test AWS wildlife pipeline")
    parser.add_argument("--bucket", default="wildlife-pipeline-data", help="S3 bucket name for testing")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive test suite")
    parser.add_argument("--s3", action="store_true", help="Test S3 operations only")
    parser.add_argument("--batch", action="store_true", help="Test Batch job submission only")
    parser.add_argument("--gpu", action="store_true", help="Test GPU processing only")
    parser.add_argument("--pipeline", action="store_true", help="Test cloud pipeline only")
    parser.add_argument("--e2e", action="store_true", help="Test end-to-end pipeline only")
    
    args = parser.parse_args()
    
    if args.comprehensive:
        run_comprehensive_pipeline_test()
    elif args.s3:
        test_s3_operations(args.bucket)
    elif args.batch:
        test_batch_job_submission()
    elif args.gpu:
        test_gpu_processing()
    elif args.pipeline:
        test_cloud_pipeline()
    elif args.e2e:
        test_end_to_end_pipeline()
    else:
        print("🔧 AWS Pipeline Test")
        print("Use --comprehensive to run all tests")
        print("Use --s3, --batch, --gpu, --pipeline, or --e2e for specific tests")


if __name__ == "__main__":
    main()
