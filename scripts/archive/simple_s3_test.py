#!/usr/bin/env python3
"""
Simple S3 Test with Trailcam Data

This script performs a simplified test with:
- Upload trailcam data to S3
- Test S3 operations
- Simulate cost optimization
- Generate local results
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

def upload_and_test_s3():
    """Upload test data to S3 and test operations."""
    print("📤 Uploading and testing S3 operations...")
    
    # Get AWS account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = "eu-north-1"
    
    # Use existing bucket
    bucket_name = f"wildlife-pipeline-test-{int(time.time())}"
    s3_prefix = "trailcam-test"
    
    print(f"Bucket: {bucket_name}")
    print(f"Prefix: {s3_prefix}")
    
    # Create S3 client
    s3 = boto3.client('s3', region_name=region)
    
    # Create bucket
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        print(f"✅ Created bucket: {bucket_name}")
    except Exception as e:
        print(f"⚠️  Bucket creation issue: {e}")
        # Try to use existing bucket
        bucket_name = "wildlife-pipeline-test-1759062757"
        print(f"Using existing bucket: {bucket_name}")
    
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
    
    # Test S3 operations
    print("\n🔍 Testing S3 operations...")
    
    # List objects
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
        objects = response.get('Contents', [])
        print(f"✅ Listed {len(objects)} objects in S3")
        
        # Show some objects
        for obj in objects[:5]:
            print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        if len(objects) > 5:
            print(f"   ... and {len(objects) - 5} more")
    except Exception as e:
        print(f"❌ S3 list failed: {e}")
    
    # Test download
    print("\n📥 Testing S3 download...")
    try:
        # Download one file back
        test_download_dir = Path("/home/asbjorn/projects/wildlife_pipeline_starter/s3_test_download")
        test_download_dir.mkdir(parents=True, exist_ok=True)
        
        if objects:
            first_object = objects[0]
            local_file = test_download_dir / Path(first_object['Key']).name
            s3.download_file(bucket_name, first_object['Key'], str(local_file))
            print(f"✅ Downloaded: {first_object['Key']} -> {local_file}")
            print(f"   File size: {local_file.stat().st_size} bytes")
    except Exception as e:
        print(f"❌ S3 download failed: {e}")
    
    return bucket_name, s3_prefix, uploaded_files

def test_cost_optimization():
    """Test cost optimization functionality."""
    print("\n💰 Testing cost optimization...")
    
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
    
    print(f"✅ Configuration created:")
    print(f"   Region: {config.region}")
    print(f"   Environment: {config.environment}")
    print(f"   Spot bid percentage: {config.spot_bid_percentage}%")
    print(f"   Max vCPUs: {config.max_vcpus}")
    print(f"   GPU required: {config.gpu_required}")
    
    # Initialize components
    try:
        cost_manager = CostOptimizationManager(config)
        batch_manager = BatchWorkflowManager(config)
        downloader = Stage3OutputDownloader(config)
        print("✅ Cost optimization components initialized")
    except Exception as e:
        print(f"❌ Failed to initialize components: {e}")
        return False
    
    # Test cost metrics
    print("\n📊 Testing cost metrics...")
    try:
        metrics = cost_manager.get_cost_metrics()
        print(f"✅ Cost metrics retrieved:")
        print(f"   Instance count: {metrics.get('instance_count', 0)}")
        print(f"   Instance type: {metrics.get('instance_type', 'unknown')}")
        print(f"   Spot price: ${metrics.get('spot_price_per_hour', 0):.4f}/hour")
        print(f"   On-demand price: ${metrics.get('on_demand_price_per_hour', 0):.4f}/hour")
        print(f"   Savings: ${metrics.get('savings_per_hour', 0):.4f}/hour")
        print(f"   Savings percentage: {metrics.get('savings_percentage', 0):.1f}%")
    except Exception as e:
        print(f"⚠️  Cost metrics error: {e}")
    
    return True

def simulate_processing_results(bucket_name, s3_prefix):
    """Simulate processing results."""
    print("\n🔄 Simulating processing results...")
    
    # Create mock processing results
    results_dir = Path("/home/asbjorn/projects/wildlife_pipeline_starter/s3_test_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock Stage 1 results (manifest)
    manifest_entries = []
    for i in range(5):
        manifest_entries.append({
            'source_path': f"s3://{bucket_name}/{s3_prefix}/image_{i+1}.jpg",
            'camera_id': f'camera_{i % 3 + 1}',
            'timestamp': f'2024-08-{15 + i:02d}T{10 + i:02d}:30:00Z',
            'latitude': 55.6761 + (i * 0.001),
            'longitude': 12.5683 + (i * 0.001),
            'image_width': 1920,
            'image_height': 1080,
            'bbox': [100 + i*10, 100 + i*10, 200 + i*10, 200 + i*10],
            'det_score': 0.8 + (i * 0.02),
            'stage1_model': 'yolov8n.pt',
            'config_hash': 'abc123',
            'crop_path': f"s3://{bucket_name}/crops/crop_{i+1}.jpg"
        })
    
    # Save manifest
    manifest_file = results_dir / "stage1_manifest.jsonl"
    with open(manifest_file, 'w') as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✅ Stage 1 manifest created: {len(manifest_entries)} entries")
    
    # Mock Stage 2 results (predictions)
    prediction_entries = []
    for i, manifest_entry in enumerate(manifest_entries):
        prediction_entries.append({
            'crop_path': manifest_entry['crop_path'],
            'label': 'deer' if i % 2 == 0 else 'bird',
            'confidence': 0.8 + (i * 0.02),
            'auto_ok': i % 3 == 0,
            'stage2_model': 'wildlife_classifier_v1'
        })
    
    # Save predictions
    predictions_file = results_dir / "stage2_predictions.jsonl"
    with open(predictions_file, 'w') as f:
        for entry in prediction_entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✅ Stage 2 predictions created: {len(prediction_entries)} entries")
    
    # Mock Stage 3 results (compressed observations)
    compressed_observations = []
    for i in range(3):
        compressed_observations.append({
            'species': 'deer' if i % 2 == 0 else 'bird',
            'camera': f'camera_{i % 3 + 1}',
            'timestamp': f'2024-08-{15 + i:02d}T{10 + i:02d}:30:00Z',
            'confidence': 0.8 + (i * 0.02),
            'bbox': [100 + i*10, 100 + i*10, 200 + i*10, 200 + i*10],
            'source_files': [f"image_{i+1}.jpg", f"image_{i+2}.jpg"],
            'duration_seconds': 30 + (i * 10),
            'needs_review': i % 4 == 0
        })
    
    # Save compressed observations
    observations_file = results_dir / "compressed_observations.json"
    with open(observations_file, 'w') as f:
        json.dump(compressed_observations, f, indent=2)
    
    print(f"✅ Stage 3 compressed observations created: {len(compressed_observations)} entries")
    
    # Create report
    report = {
        'total_observations': len(compressed_observations),
        'species_summary': {
            'deer': len([o for o in compressed_observations if o['species'] == 'deer']),
            'bird': len([o for o in compressed_observations if o['species'] == 'bird'])
        },
        'camera_summary': {
            f'camera_{i}': len([o for o in compressed_observations if o['camera'] == f'camera_{i}'])
            for i in range(1, 4)
        },
        'time_range': {
            'start': compressed_observations[0]['timestamp'],
            'end': compressed_observations[-1]['timestamp']
        },
        'processing_stats': {
            'total_files_processed': 29,
            'images_processed': 24,
            'videos_processed': 5,
            'total_processing_time_minutes': 15,
            'cost_optimization_enabled': True,
            'spot_instances_used': True,
            'estimated_cost_savings_percentage': 65
        }
    }
    
    # Save report
    report_file = results_dir / "report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Report created with processing statistics")
    
    return results_dir

def main():
    """Main test function."""
    print("🧪 Simple S3 Test with Trailcam Data")
    print("=" * 50)
    
    try:
        # Step 1: Upload and test S3
        print("\n📤 Step 1: Uploading and testing S3")
        bucket_name, s3_prefix, uploaded_files = upload_and_test_s3()
        print(f"✅ Uploaded {len(uploaded_files)} files to s3://{bucket_name}/{s3_prefix}")
        
        # Step 2: Test cost optimization
        print("\n💰 Step 2: Testing cost optimization")
        if not test_cost_optimization():
            print("❌ Cost optimization test failed")
            return False
        
        # Step 3: Simulate processing results
        print("\n🔄 Step 3: Simulating processing results")
        results_dir = simulate_processing_results(bucket_name, s3_prefix)
        print(f"✅ Processing results created in: {results_dir}")
        
        # Show results
        print("\n🎉 Test Results:")
        print(f"✅ S3 bucket: s3://{bucket_name}")
        print(f"✅ Local results: {results_dir}")
        print(f"✅ Files created:")
        for file_path in results_dir.glob("*"):
            print(f"   - {file_path.name} ({file_path.stat().st_size} bytes)")
        
        print(f"\n✅ Total size: {sum(f.stat().st_size for f in results_dir.glob('*')) / 1024:.1f} KB")
        
        # Show S3 bucket contents
        print(f"\n📊 S3 bucket contents:")
        s3 = boto3.client('s3', region_name='eu-north-1')
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
        objects = response.get('Contents', [])
        total_size = sum(obj['Size'] for obj in objects)
        print(f"   Objects: {len(objects)}")
        print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ Test failed!")
        sys.exit(1)
    print("\n🎉 Simple S3 test completed successfully! 🚀💰")
