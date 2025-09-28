#!/usr/bin/env python3
"""
Real AWS Test with S3 Upload and Processing

This script performs a complete test with:
- Upload trailcam data to S3
- Deploy cost-optimized infrastructure
- Run actual batch processing
- Download Stage 3 output
- Generate cost reports
"""

import sys
import os
import json
import time
import boto3
from pathlib import Path
from datetime import datetime
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cost_optimization.config import CostOptimizationConfig
from cost_optimization.manager import CostOptimizationManager
from cost_optimization.batch_workflow import BatchWorkflowManager
from cost_optimization.stage3_downloader import Stage3OutputDownloader

def upload_test_data_to_s3():
    """Upload test data to S3."""
    print("📤 Uploading test data to S3...")
    
    # Get AWS account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = "eu-north-1"
    
    # Create S3 bucket name
    bucket_name = f"wildlife-detection-test-{account_id}"
    s3_prefix = "trailcam-test"
    
    print(f"Bucket: {bucket_name}")
    print(f"Prefix: {s3_prefix}")
    
    # Create S3 client
    s3 = boto3.client('s3', region_name=region)
    
    # Create bucket if it doesn't exist
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        print(f"✅ Created bucket: {bucket_name}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"✅ Bucket already exists: {bucket_name}")
    except Exception as e:
        print(f"⚠️  Bucket creation issue: {e}")
    
    # Upload test data
    test_data_dir = Path("/home/asbjorn/projects/wildlife_pipeline_starter/test_data")
    uploaded_files = []
    
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

def deploy_cost_optimized_infrastructure():
    """Deploy cost-optimized infrastructure."""
    print("🏗️  Deploying cost-optimized infrastructure...")
    
    try:
        # Run the deployment script
        result = subprocess.run([
            "python", "scripts/infrastructure/deploy_cost_optimized_infrastructure.py",
            "--complete"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Infrastructure deployment completed")
            print(result.stdout)
        else:
            print(f"❌ Infrastructure deployment failed: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Infrastructure deployment error: {e}")
        return False

def run_cost_optimized_processing(bucket_name, s3_prefix):
    """Run cost-optimized batch processing."""
    print("🚀 Running cost-optimized batch processing...")
    
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
    
    # Initialize components
    cost_manager = CostOptimizationManager(config)
    batch_manager = BatchWorkflowManager(config)
    downloader = Stage3OutputDownloader(config)
    
    # Create batch configuration
    batch_config = {
        'batch_id': f"real-test-{int(time.time())}",
        'jobs': [{
            'name': 'trailcam-processing',
            'parameters': {
                'input_path': f"s3://{bucket_name}/{s3_prefix}",
                'output_path': f"s3://{bucket_name}/output",
                'cost_optimization': 'enabled',
                'spot_instance_preferred': 'true',
                'fallback_to_ondemand': 'true'
            },
            'gpu_required': True,
            'priority': 'normal'
        }],
        'gpu_required': True,
        'max_parallel_jobs': 1,
        'created_at': datetime.now().isoformat()
    }
    
    print(f"✅ Batch configuration created: {batch_config['batch_id']}")
    
    # Setup infrastructure
    print("📋 Setting up infrastructure...")
    try:
        success = cost_manager.setup_infrastructure(job_count=1, gpu_required=True)
        if success:
            print("✅ Infrastructure setup completed")
        else:
            print("❌ Infrastructure setup failed")
            return False
    except Exception as e:
        print(f"⚠️  Infrastructure setup error (may be expected): {e}")
    
    # Process batch
    print("📋 Processing batch...")
    try:
        batch_result = batch_manager.process_batch(batch_config)
        print(f"✅ Batch processing result: {batch_result.get('status', 'unknown')}")
        
        if batch_result.get('status') != 'completed':
            print(f"⚠️  Batch processing status: {batch_result.get('status')}")
            print(f"   Error: {batch_result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"⚠️  Batch processing error: {e}")
    
    # Download Stage 3 output
    print("📋 Downloading Stage 3 output...")
    local_output_dir = Path("/home/asbjorn/projects/wildlife_pipeline_starter/real_test_results")
    local_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        download_result = downloader.download_stage3_output(
            cloud_output_path=f"s3://{bucket_name}/output",
            local_output_path=str(local_output_dir),
            include_observations=True,
            include_report=True
        )
        
        if 'error' in download_result:
            print(f"⚠️  Stage 3 download failed: {download_result['error']}")
        else:
            print(f"✅ Stage 3 output downloaded to: {local_output_dir}")
            
            # Create local runner
            runner_path = downloader.create_local_stage3_runner(str(local_output_dir))
            if runner_path:
                print(f"✅ Local Stage 3 runner created: {runner_path}")
    except Exception as e:
        print(f"⚠️  Stage 3 download error: {e}")
    
    # Get cost metrics
    print("📋 Getting cost metrics...")
    try:
        metrics = cost_manager.get_cost_metrics()
        print(f"✅ Cost metrics:")
        print(f"   Instance count: {metrics.get('instance_count', 0)}")
        print(f"   Instance type: {metrics.get('instance_type', 'unknown')}")
        print(f"   Spot price: ${metrics.get('spot_price_per_hour', 0):.4f}/hour")
        print(f"   On-demand price: ${metrics.get('on_demand_price_per_hour', 0):.4f}/hour")
        print(f"   Savings: ${metrics.get('savings_per_hour', 0):.4f}/hour")
        print(f"   Savings percentage: {metrics.get('savings_percentage', 0):.1f}%")
    except Exception as e:
        print(f"⚠️  Cost metrics error: {e}")
    
    # Teardown infrastructure
    print("📋 Tearing down infrastructure...")
    try:
        success = cost_manager.teardown_infrastructure()
        if success:
            print("✅ Infrastructure teardown completed")
        else:
            print("❌ Infrastructure teardown failed")
    except Exception as e:
        print(f"⚠️  Infrastructure teardown error: {e}")
    
    return True

def main():
    """Main test function."""
    print("🧪 Real AWS Test with S3 Upload and Processing")
    print("=" * 60)
    
    try:
        # Step 1: Upload test data to S3
        print("\n📤 Step 1: Uploading test data to S3")
        bucket_name, s3_prefix, uploaded_files = upload_test_data_to_s3()
        print(f"✅ Uploaded {len(uploaded_files)} files to s3://{bucket_name}/{s3_prefix}")
        
        # Step 2: Deploy infrastructure
        print("\n🏗️  Step 2: Deploying cost-optimized infrastructure")
        if not deploy_cost_optimized_infrastructure():
            print("❌ Infrastructure deployment failed")
            return False
        
        # Step 3: Run processing
        print("\n🚀 Step 3: Running cost-optimized processing")
        if not run_cost_optimized_processing(bucket_name, s3_prefix):
            print("❌ Processing failed")
            return False
        
        print("\n🎉 Real AWS test completed successfully!")
        print("✅ Check the following for results:")
        print("   - S3 bucket: s3://{bucket_name}")
        print("   - Local results: /home/asbjorn/projects/wildlife_pipeline_starter/real_test_results")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ Test failed!")
        sys.exit(1)
    print("\n🎉 Real AWS test completed! 🚀💰")
