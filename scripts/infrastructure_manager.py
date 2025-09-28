#!/usr/bin/env python3
"""
AWS Batch Infrastructure Manager

This utility manages AWS Batch infrastructure:
- Setup infrastructure if it doesn't exist
- Scale compute environment up/down
- Monitor infrastructure status
- Manage job definitions
"""

import boto3
import time
import json
from datetime import datetime
from pathlib import Path
import sys
import argparse

class InfrastructureManager:
    def __init__(self, region='eu-north-1'):
        self.region = region
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.batch = boto3.client('batch', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.stack_name = 'wildlife-simple-batch'
        
    def get_default_vpc(self):
        """Get default VPC and subnets."""
        try:
            # Get default VPC
            vpcs = self.ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
            if not vpcs['Vpcs']:
                print("❌ No default VPC found")
                return None, None
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            print(f"✅ Found default VPC: {vpc_id}")
            
            # Get subnets
            subnets = self.ec2.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
            print(f"✅ Found {len(subnet_ids)} subnets: {subnet_ids}")
            
            return vpc_id, subnet_ids
            
        except Exception as e:
            print(f"❌ Error getting VPC: {e}")
            return None, None

    def check_infrastructure_exists(self):
        """Check if infrastructure already exists."""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            
            if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                print(f"✅ Infrastructure exists: {status}")
                return True
            else:
                print(f"⚠️  Infrastructure exists but status: {status}")
                return False
                
        except Exception as e:
            if 'does not exist' in str(e):
                print("ℹ️  Infrastructure does not exist")
                return False
            else:
                print(f"❌ Error checking infrastructure: {e}")
                return False

    def setup_infrastructure(self):
        """Setup AWS Batch infrastructure if it doesn't exist."""
        print("🚀 Setting up AWS Batch Infrastructure")
        print("=" * 50)
        
        if self.check_infrastructure_exists():
            print("✅ Infrastructure already exists, skipping setup")
            return True
        
        # Get VPC info
        vpc_id, subnet_ids = self.get_default_vpc()
        if not vpc_id:
            return False
        
        # Deploy stack
        template_path = Path(__file__).parent.parent / 'aws' / 'simple-batch-template.yaml'
        
        try:
            with open(template_path, 'r') as f:
                template_body = f.read()
            
            print(f"📋 Deploying stack: {self.stack_name}")
            response = self.cloudformation.create_stack(
                StackName=self.stack_name,
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
            waiter = self.cloudformation.get_waiter('stack_create_complete')
            waiter.wait(StackName=self.stack_name)
            
            print("✅ Infrastructure setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Infrastructure setup failed: {e}")
            return False

    def get_compute_environment_info(self):
        """Get compute environment information."""
        try:
            response = self.batch.describe_compute_environments()
            environments = response['computeEnvironments']
            
            for env in environments:
                if 'wildlife' in env['computeEnvironmentName']:
                    return env
            
            print("❌ No wildlife compute environment found")
            return None
            
        except Exception as e:
            print(f"❌ Error getting compute environment: {e}")
            return None

    def scale_compute_environment(self, min_vcpus, max_vcpus, desired_vcpus):
        """Scale compute environment up or down."""
        print(f"📊 Scaling Compute Environment")
        print("=" * 40)
        print(f"Min vCPUs: {min_vcpus}")
        print(f"Max vCPUs: {max_vcpus}")
        print(f"Desired vCPUs: {desired_vcpus}")
        
        try:
            # Get current compute environment
            env_info = self.get_compute_environment_info()
            if not env_info:
                return False
            
            env_name = env_info['computeEnvironmentName']
            print(f"📋 Updating compute environment: {env_name}")
            
            # Update compute environment
            response = self.batch.update_compute_environment(
                computeEnvironment=env_name,
                computeResources={
                    'minvCpus': min_vcpus,
                    'maxvCpus': max_vcpus,
                    'desiredvCpus': desired_vcpus
                }
            )
            
            print(f"✅ Compute environment update initiated")
            
            # Wait for update to complete
            print("⏳ Waiting for update to complete...")
            time.sleep(10)  # Give it a moment to start
            
            # Check status
            for i in range(30):  # Wait up to 5 minutes
                time.sleep(10)
                env_info = self.get_compute_environment_info()
                if env_info:
                    status = env_info['status']
                    print(f"   Status: {status}")
                    if status == 'VALID':
                        print("✅ Scaling completed successfully!")
                        return True
                    elif status == 'INVALID':
                        print("❌ Scaling failed - environment is invalid")
                        return False
            
            print("⏰ Scaling timeout")
            return False
            
        except Exception as e:
            print(f"❌ Scaling failed: {e}")
            return False

    def scale_up(self, desired_vcpus=4):
        """Scale up compute environment."""
        print("⬆️  Scaling UP Compute Environment")
        print("=" * 40)
        return self.scale_compute_environment(0, 8, desired_vcpus)

    def scale_down(self):
        """Scale down compute environment to 0."""
        print("⬇️  Scaling DOWN Compute Environment")
        print("=" * 40)
        print("ℹ️  Note: AWS Batch automatically scales down when no jobs are running")
        print("ℹ️  The compute environment will scale to 0 vCPUs when idle")
        print("ℹ️  No manual action needed - it's already cost-optimized!")
        return True

    def get_infrastructure_status(self):
        """Get comprehensive infrastructure status."""
        print("📊 Infrastructure Status")
        print("=" * 30)
        
        try:
            # Stack status
            try:
                response = self.cloudformation.describe_stacks(StackName=self.stack_name)
                stack = response['Stacks'][0]
                print(f"📋 Stack: {stack['StackStatus']}")
            except:
                print("📋 Stack: NOT_FOUND")
            
            # Compute environments
            response = self.batch.describe_compute_environments()
            environments = response['computeEnvironments']
            
            print(f"🏗️  Compute Environments: {len(environments)}")
            for env in environments:
                if 'wildlife' in env['computeEnvironmentName']:
                    print(f"   {env['computeEnvironmentName']}: {env['status']}")
                    if 'computeResources' in env:
                        resources = env['computeResources']
                        print(f"      Min vCPUs: {resources.get('minvCpus', 'N/A')}")
                        print(f"      Max vCPUs: {resources.get('maxvCpus', 'N/A')}")
                        print(f"      Desired vCPUs: {resources.get('desiredvCpus', 'N/A')}")
            
            # Job queues
            response = self.batch.describe_job_queues()
            queues = response['jobQueues']
            
            print(f"📋 Job Queues: {len(queues)}")
            for queue in queues:
                if 'wildlife' in queue['jobQueueName']:
                    print(f"   {queue['jobQueueName']}: {queue['state']}")
            
            # Job definitions
            response = self.batch.describe_job_definitions()
            definitions = response['jobDefinitions']
            
            wildlife_definitions = [d for d in definitions if 'wildlife' in d['jobDefinitionName']]
            print(f"📋 Wildlife Job Definitions: {len(wildlife_definitions)}")
            for defn in wildlife_definitions:
                print(f"   {defn['jobDefinitionName']}: {defn['status']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return False

    def list_active_jobs(self):
        """List active batch jobs."""
        print("📋 Active Batch Jobs")
        print("=" * 25)
        
        try:
            response = self.batch.list_jobs(
                jobQueue='wildlife-queue-production',
                jobStatus='RUNNING'
            )
            
            jobs = response['jobSummaryList']
            if not jobs:
                print("ℹ️  No active jobs")
                return True
            
            print(f"🔄 {len(jobs)} active jobs:")
            for job in jobs:
                print(f"   {job['jobName']}: {job['status']}")
                print(f"      Job ID: {job['jobId']}")
                print(f"      Created: {datetime.fromtimestamp(job['createdAt'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error listing jobs: {e}")
            return False

    def cleanup_infrastructure(self):
        """Clean up infrastructure (only if really needed)."""
        print("🧹 Cleaning Up Infrastructure")
        print("=" * 35)
        print("⚠️  WARNING: This will delete all AWS Batch infrastructure!")
        print("⚠️  AWS Batch costs nothing when idle, so cleanup is usually not needed.")
        
        confirm = input("Are you sure you want to delete infrastructure? Type 'DELETE' to confirm: ").strip()
        
        if confirm != 'DELETE':
            print("❌ Cleanup cancelled")
            return False
        
        try:
            print(f"🗑️  Deleting stack: {self.stack_name}")
            self.cloudformation.delete_stack(StackName=self.stack_name)
            
            # Wait for deletion
            print("⏳ Waiting for stack deletion...")
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.stack_name)
            
            print("✅ Infrastructure deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='AWS Batch Infrastructure Manager')
    parser.add_argument('action', choices=[
        'setup', 'status', 'scale-up', 'scale-down', 'jobs', 'cleanup'
    ], help='Action to perform')
    parser.add_argument('--vcpus', type=int, default=4, 
                       help='Number of vCPUs for scale-up (default: 4)')
    parser.add_argument('--region', default='eu-north-1', 
                       help='AWS region (default: eu-north-1)')
    
    args = parser.parse_args()
    
    manager = InfrastructureManager(region=args.region)
    
    try:
        if args.action == 'setup':
            success = manager.setup_infrastructure()
        elif args.action == 'status':
            success = manager.get_infrastructure_status()
        elif args.action == 'scale-up':
            success = manager.scale_up(desired_vcpus=args.vcpus)
        elif args.action == 'scale-down':
            success = manager.scale_down()
        elif args.action == 'jobs':
            success = manager.list_active_jobs()
        elif args.action == 'cleanup':
            success = manager.cleanup_infrastructure()
        else:
            print(f"❌ Unknown action: {args.action}")
            success = False
        
        return success
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
