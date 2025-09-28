#!/usr/bin/env python3
"""
Odin Teardown - Infrastructure Cleanup

This script handles complete teardown of AWS infrastructure:
- AWS Batch compute environments
- CloudFormation stacks
- S3 buckets (optional)
- IAM roles and policies
"""

import boto3
import time
import sys
from pathlib import Path
import argparse

class OdinTeardown:
    def __init__(self, region='eu-north-1'):
        """Initialize teardown manager."""
        self.region = region
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.batch = boto3.client('batch', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.iam = boto3.client('iam', region_name=region)
        
    def list_stacks(self):
        """List all wildlife-related stacks."""
        print("📋 Listing Wildlife Stacks")
        print("=" * 30)
        
        try:
            response = self.cloudformation.list_stacks(
                StackStatusFilter=[
                    'CREATE_COMPLETE', 'UPDATE_COMPLETE', 'ROLLBACK_COMPLETE',
                    'DELETE_FAILED', 'UPDATE_ROLLBACK_COMPLETE'
                ]
            )
            
            wildlife_stacks = []
            for stack in response['StackSummaries']:
                if 'wildlife' in stack['StackName'].lower():
                    wildlife_stacks.append(stack)
                    print(f"   📦 {stack['StackName']}: {stack['StackStatus']}")
            
            return wildlife_stacks
            
        except Exception as e:
            print(f"❌ Error listing stacks: {e}")
            return []
    
    def list_batch_resources(self):
        """List AWS Batch resources."""
        print("\n⚙️  Listing AWS Batch Resources")
        print("=" * 35)
        
        try:
            # List compute environments
            ce_response = self.batch.describe_compute_environments()
            wildlife_ces = []
            for ce in ce_response['computeEnvironments']:
                if 'wildlife' in ce['computeEnvironmentName'].lower():
                    wildlife_ces.append(ce)
                    print(f"   🏗️  Compute Environment: {ce['computeEnvironmentName']} ({ce['status']})")
            
            # List job queues
            jq_response = self.batch.describe_job_queues()
            wildlife_jqs = []
            for jq in jq_response['jobQueues']:
                if 'wildlife' in jq['jobQueueName'].lower():
                    wildlife_jqs.append(jq)
                    print(f"   📋 Job Queue: {jq['jobQueueName']} ({jq['state']})")
            
            # List job definitions
            jd_response = self.batch.describe_job_definitions()
            wildlife_jds = []
            for jd in jd_response['jobDefinitions']:
                if 'wildlife' in jd['jobDefinitionName'].lower():
                    wildlife_jds.append(jd)
                    print(f"   📄 Job Definition: {jd['jobDefinitionName']} ({jd['status']})")
            
            return wildlife_ces, wildlife_jqs, wildlife_jds
            
        except Exception as e:
            print(f"❌ Error listing batch resources: {e}")
            return [], [], []
    
    def list_s3_buckets(self):
        """List S3 buckets."""
        print("\n📁 Listing S3 Buckets")
        print("=" * 25)
        
        try:
            response = self.s3.list_buckets()
            wildlife_buckets = []
            
            for bucket in response['Buckets']:
                if 'wildlife' in bucket['Name'].lower():
                    wildlife_buckets.append(bucket)
                    print(f"   📦 {bucket['Name']} (created: {bucket['CreationDate']})")
            
            return wildlife_buckets
            
        except Exception as e:
            print(f"❌ Error listing S3 buckets: {e}")
            return []
    
    def teardown_stack(self, stack_name, force=False):
        """Teardown a CloudFormation stack."""
        print(f"\n🗑️  Teardown Stack: {stack_name}")
        print("=" * 40)
        
        try:
            # Check if stack exists
            try:
                response = self.cloudformation.describe_stacks(StackName=stack_name)
                stack = response['Stacks'][0]
                status = stack['StackStatus']
                
                if status in ['DELETE_COMPLETE']:
                    print(f"✅ Stack {stack_name} already deleted")
                    return True
                    
                print(f"📋 Stack status: {status}")
                
            except Exception as e:
                if 'does not exist' in str(e):
                    print(f"✅ Stack {stack_name} does not exist")
                    return True
                else:
                    raise e
            
            # Delete stack
            print(f"🗑️  Deleting stack: {stack_name}")
            self.cloudformation.delete_stack(StackName=stack_name)
            
            # Wait for deletion
            print("⏳ Waiting for stack deletion...")
            try:
                waiter = self.cloudformation.get_waiter('stack_delete_complete')
                waiter.wait(StackName=stack_name)
                print("✅ Stack deleted successfully")
                return True
            except Exception as e:
                if 'DELETE_FAILED' in str(e):
                    print(f"⚠️  Stack deletion failed: {e}")
                    if force:
                        print("🔄 Retrying deletion...")
                        return self.teardown_stack(stack_name, force=True)
                    return False
                else:
                    print(f"❌ Stack deletion error: {e}")
                    return False
                    
        except Exception as e:
            print(f"❌ Stack teardown failed: {e}")
            return False
    
    def teardown_s3_bucket(self, bucket_name, force=False):
        """Teardown an S3 bucket."""
        print(f"\n🗑️  Teardown S3 Bucket: {bucket_name}")
        print("=" * 40)
        
        try:
            # List and delete all objects
            print("🗑️  Deleting all objects...")
            response = self.s3.list_objects_v2(Bucket=bucket_name)
            
            if 'Contents' in response:
                objects = response['Contents']
                print(f"📁 Found {len(objects)} objects to delete")
                
                # Delete objects in batches
                for obj in objects:
                    try:
                        self.s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
                        print(f"   ✅ Deleted: {obj['Key']}")
                    except Exception as e:
                        print(f"   ❌ Failed to delete {obj['Key']}: {e}")
            else:
                print("📁 Bucket is empty")
            
            # Delete bucket
            print(f"🗑️  Deleting bucket: {bucket_name}")
            self.s3.delete_bucket(Bucket=bucket_name)
            print("✅ Bucket deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ S3 bucket teardown failed: {e}")
            return False
    
    def teardown_all(self, include_s3=False, force=False):
        """Teardown all wildlife infrastructure."""
        print("🧹 Odin Complete Teardown")
        print("=" * 30)
        print("⚠️  WARNING: This will delete ALL wildlife infrastructure!")
        
        if not force:
            confirm = input("Type 'ODIN TEARDOWN' to confirm: ").strip()
            if confirm != 'ODIN TEARDOWN':
                print("❌ Teardown cancelled")
                return False
        
        success = True
        
        # 1. Teardown CloudFormation stacks
        print("\n1️⃣  Teardown CloudFormation Stacks")
        print("=" * 40)
        stacks = self.list_stacks()
        
        for stack in stacks:
            stack_name = stack['StackName']
            if not self.teardown_stack(stack_name, force=force):
                success = False
        
        # 2. Teardown S3 buckets (optional)
        if include_s3:
            print("\n2️⃣  Teardown S3 Buckets")
            print("=" * 30)
            buckets = self.list_s3_buckets()
            
            for bucket in buckets:
                bucket_name = bucket['Name']
                if not self.teardown_s3_bucket(bucket_name, force=force):
                    success = False
        
        # 3. Summary
        print("\n📊 Teardown Summary")
        print("=" * 25)
        if success:
            print("✅ All infrastructure teardown completed successfully")
        else:
            print("⚠️  Some teardown operations failed")
        
        return success

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Odin Infrastructure Teardown')
    parser.add_argument('--region', default='eu-north-1', 
                       help='AWS region (default: eu-north-1)')
    parser.add_argument('--include-s3', action='store_true',
                       help='Include S3 bucket teardown')
    parser.add_argument('--force', action='store_true',
                       help='Force teardown without confirmation')
    parser.add_argument('--list-only', action='store_true',
                       help='Only list resources, do not teardown')
    
    args = parser.parse_args()
    
    teardown = OdinTeardown(region=args.region)
    
    try:
        if args.list_only:
            # Just list resources
            teardown.list_stacks()
            teardown.list_batch_resources()
            teardown.list_s3_buckets()
            return True
        else:
            # Perform teardown
            return teardown.teardown_all(
                include_s3=args.include_s3,
                force=args.force
            )
        
    except KeyboardInterrupt:
        print("\n⏹️  Teardown interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Teardown failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
