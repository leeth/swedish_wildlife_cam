#!/usr/bin/env python3
"""
S3 Cleanup Utility

This script cleans up S3 buckets used for wildlife processing tests.
Use this when you want to clean up test data manually.
"""

import boto3
import sys
from pathlib import Path

def cleanup_s3_bucket(bucket_name):
    """Clean up S3 bucket contents."""
    print(f"🧹 Cleaning up S3 bucket: {bucket_name}")
    print("=" * 50)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    
    try:
        # List all objects
        response = s3.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            print("✅ Bucket is already empty")
            return True
        
        objects = response['Contents']
        print(f"📁 Found {len(objects)} objects to delete")
        
        # Show what will be deleted
        print("\n📋 Objects to delete:")
        for obj in objects:
            key = obj['Key']
            size = obj['Size']
            print(f"   📄 {key} ({size} bytes)")
        
        # Confirm deletion
        print(f"\n⚠️  This will delete ALL objects in bucket: {bucket_name}")
        confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Deletion cancelled")
            return False
        
        # Delete all objects
        print("🗑️  Deleting objects...")
        deleted_count = 0
        
        for obj in objects:
            try:
                s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
                deleted_count += 1
                print(f"   ✅ Deleted: {obj['Key']}")
            except Exception as e:
                print(f"   ❌ Failed to delete {obj['Key']}: {e}")
        
        print(f"\n✅ Deleted {deleted_count} objects")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def list_s3_buckets():
    """List S3 buckets."""
    print("📋 Available S3 Buckets")
    print("=" * 30)
    
    s3 = boto3.client('s3', region_name='eu-north-1')
    
    try:
        response = s3.list_buckets()
        buckets = response['Buckets']
        
        if not buckets:
            print("No buckets found")
            return []
        
        print(f"Found {len(buckets)} buckets:")
        for bucket in buckets:
            name = bucket['Name']
            created = bucket['CreationDate']
            print(f"   📦 {name} (created: {created})")
        
        return [bucket['Name'] for bucket in buckets]
        
    except Exception as e:
        print(f"❌ Error listing buckets: {e}")
        return []

def main():
    """Main function."""
    print("🧹 S3 Cleanup Utility")
    print("=" * 30)
    print("This utility helps clean up S3 buckets used for wildlife processing tests.")
    print()
    
    try:
        # List available buckets
        buckets = list_s3_buckets()
        
        if not buckets:
            print("No buckets found")
            return True
        
        # Find wildlife test buckets
        wildlife_buckets = [b for b in buckets if 'wildlife' in b.lower()]
        
        if not wildlife_buckets:
            print("No wildlife test buckets found")
            return True
        
        print(f"\n🦌 Wildlife Test Buckets:")
        for i, bucket in enumerate(wildlife_buckets, 1):
            print(f"   {i}. {bucket}")
        
        # Let user choose bucket
        print("\nOptions:")
        print("1. Clean specific bucket")
        print("2. Clean all wildlife buckets")
        print("3. Exit")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            bucket_name = input("Enter bucket name: ").strip()
            if bucket_name in buckets:
                cleanup_s3_bucket(bucket_name)
            else:
                print(f"❌ Bucket '{bucket_name}' not found")
                return False
        
        elif choice == '2':
            for bucket in wildlife_buckets:
                cleanup_s3_bucket(bucket)
                print()
        
        elif choice == '3':
            print("👋 Goodbye!")
            return True
        
        else:
            print("❌ Invalid choice")
            return False
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Cleanup interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
