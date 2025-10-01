#!/usr/bin/env python3
"""
Upload Test Data to AWS S3

This script uploads all test data from the test_data directory to AWS S3
for comprehensive testing of the wildlife pipeline.
"""

import boto3
import os
from pathlib import Path
import sys
from datetime import datetime

def upload_test_data_to_s3(bucket_name: str = "wildlife-pipeline-test", region: str = "eu-north-1"):
    """Upload all test data to S3 bucket."""
    print("📤 Uploading Test Data to AWS S3")
    print("=" * 50)
    
    # Initialize S3 client
    s3 = boto3.client('s3', region_name=region)
    
    # Test data directory
    test_data_dir = Path(__file__).parent.parent / 'test_data'
    if not test_data_dir.exists():
        print("❌ Test data directory not found")
        return False
    
    # Create bucket if it doesn't exist
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket exists: {bucket_name}")
    except:
        try:
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
            print(f"✅ Created bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ Error creating bucket: {e}")
            return False
    
    # Upload all test files
    files_uploaded = 0
    total_size = 0
    
    for root, dirs, files in os.walk(test_data_dir):
        for file in files:
            if file.startswith('.'):
                continue
                
            local_path = Path(root) / file
            relative_path = local_path.relative_to(test_data_dir)
            s3_key = f"test-data/{relative_path}"
            
            try:
                file_size = local_path.stat().st_size
                s3.upload_file(str(local_path), bucket_name, s3_key)
                print(f"✅ Uploaded: {s3_key} ({file_size:,} bytes)")
                files_uploaded += 1
                total_size += file_size
            except Exception as e:
                print(f"❌ Failed to upload {local_path}: {e}")
    
    print(f"\n📊 Upload Summary:")
    print(f"   Files uploaded: {files_uploaded}")
    print(f"   Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    print(f"   Bucket: s3://{bucket_name}/test-data/")
    
    return files_uploaded > 0

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload test data to AWS S3")
    parser.add_argument("--bucket", default="wildlife-pipeline-test", help="S3 bucket name")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    
    args = parser.parse_args()
    
    success = upload_test_data_to_s3(args.bucket, args.region)
    
    if success:
        print("\n🎉 Test data upload completed successfully!")
        print(f"   You can now run comprehensive tests with:")
        print(f"   python scripts/infrastructure/test_aws_pipeline.py --comprehensive --bucket {args.bucket}")
    else:
        print("\n❌ Test data upload failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

