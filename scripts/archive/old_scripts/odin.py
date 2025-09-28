#!/usr/bin/env python3
"""
Odin - The All-Knowing Father

Odin manages the entire wildlife processing world:
- Reads odin.yaml configuration
- Sets up infrastructure as needed
- Runs Munin/Hugin pipelines
- Handles cost optimization
- Cleans up when done
"""

import yaml
import boto3
import time
import json
import sys
from datetime import datetime
from pathlib import Path
import argparse
import subprocess

class Odin:
    def __init__(self, config_path="odin.yaml"):
        """Initialize Odin with configuration."""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.region = self.config['infrastructure']['region']
        self.bucket_name = "wildlife-test-production-696852893392"
        
        # Initialize AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=self.region)
        self.batch = boto3.client('batch', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        self.ec2 = boto3.client('ec2', region_name=self.region)
        
    def load_config(self):
        """Load configuration from odin.yaml."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✅ Loaded configuration: {config['name']} v{config['version']}")
            return config
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
    
    def setup_infrastructure(self):
        """Setup complete infrastructure as defined in odin.yaml."""
        print("🏗️  Odin Setting Up Infrastructure")
        print("=" * 40)
        
        # Check if infrastructure already exists
        if self.check_infrastructure_exists():
            print("✅ Infrastructure already exists")
            return True
        
        # Deploy CloudFormation stack
        return self.deploy_cloudformation_stack()
    
    def check_infrastructure_exists(self):
        """Check if infrastructure already exists."""
        try:
            response = self.cloudformation.describe_stacks(
                StackName='wildlife-odin-infrastructure'
            )
            stack = response['Stacks'][0]
            status = stack['StackStatus']
            
            if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                return True
            else:
                print(f"⚠️  Infrastructure exists but status: {status}")
                return False
                
        except Exception as e:
            if 'does not exist' in str(e):
                return False
            else:
                print(f"❌ Error checking infrastructure: {e}")
                return False
    
    def deploy_cloudformation_stack(self):
        """Deploy CloudFormation stack based on odin.yaml."""
        print("📋 Deploying CloudFormation Stack")
        print("=" * 35)
        
        # Get VPC info
        vpc_id, subnet_ids = self.get_default_vpc()
        if not vpc_id:
            return False
        
        # Create CloudFormation template from odin.yaml
        template = self.generate_cloudformation_template()
        
        try:
            response = self.cloudformation.create_stack(
                StackName='wildlife-odin-infrastructure',
                TemplateBody=template,
                Parameters=[
                    {'ParameterKey': 'VpcId', 'ParameterValue': vpc_id},
                    {'ParameterKey': 'SubnetIds', 'ParameterValue': ','.join(subnet_ids)},
                    {'ParameterKey': 'BucketName', 'ParameterValue': self.bucket_name}
                ],
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
            
            print(f"✅ Stack creation initiated: {response['StackId']}")
            
            # Wait for completion
            print("⏳ Waiting for stack creation to complete...")
            waiter = self.cloudformation.get_waiter('stack_create_complete')
            waiter.wait(StackName='wildlife-odin-infrastructure')
            
            print("✅ Infrastructure setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Infrastructure setup failed: {e}")
            return False
    
    def get_default_vpc(self):
        """Get default VPC and subnets."""
        try:
            vpcs = self.ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
            if not vpcs['Vpcs']:
                print("❌ No default VPC found")
                return None, None
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            print(f"✅ Found default VPC: {vpc_id}")
            
            subnets = self.ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
            print(f"✅ Found {len(subnet_ids)} subnets")
            
            return vpc_id, subnet_ids
            
        except Exception as e:
            print(f"❌ Error getting VPC: {e}")
            return None, None
    
    def generate_cloudformation_template(self):
        """Generate CloudFormation template from odin.yaml config."""
        # This would generate a complete CloudFormation template
        # For now, return a simple template
        return """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Odin Wildlife Infrastructure'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: CommaDelimitedList
  BucketName:
    Type: String

Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      VersioningConfiguration:
        Status: Enabled

  BatchJobRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: wildlife-batch-job-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: batch.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:*
                Resource: '*'

  ComputeEnvironment:
    Type: AWS::Batch::ComputeEnvironment
    Properties:
      ComputeEnvironmentName: wildlife-compute-production
      Type: MANAGED
      State: ENABLED
      ServiceRole: !GetAtt BatchJobRole.Arn
      ComputeResources:
        Type: EC2
        MinvCpus: 0
        MaxvCpus: 20
        DesiredvCpus: 0
        InstanceTypes:
          - m5.large
          - m5.xlarge
        SecurityGroupIds:
          - !Ref SecurityGroup
        Subnets: !Ref SubnetIds
        InstanceRole: !GetAtt BatchJobRole.Arn

  SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: wildlife-batch-sg
      GroupDescription: Security group for wildlife batch processing
      VpcId: !Ref VpcId
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0

  JobQueue:
    Type: AWS::Batch::JobQueue
    Properties:
      JobQueueName: wildlife-queue-production
      State: ENABLED
      Priority: 1
      ComputeEnvironmentOrder:
        - Order: 1
          ComputeEnvironment: !Ref ComputeEnvironment

Outputs:
  DataBucket:
    Value: !Ref DataBucket
  ComputeEnvironment:
    Value: !Ref ComputeEnvironment
  JobQueue:
    Value: !Ref JobQueue
"""
    
    def run_pipeline(self, input_data="test_data", stages=None):
        """Run complete pipeline with Munin/Hugin."""
        print("🦌 Odin Running Complete Pipeline")
        print("=" * 35)
        
        if stages is None:
            stages = ["stage0", "stage1", "stage2", "stage3"]
        
        try:
            # Stage 0: Upload data
            if "stage0" in stages:
                print("\n📤 Stage 0: Uploading Data")
                if not self.upload_data(input_data):
                    return False
            
            # Stage 1: Create manifest
            if "stage1" in stages:
                print("\n📋 Stage 1: Creating Manifest")
                if not self.run_stage1():
                    return False
            
            # Stage 2: Run Munin/Hugin detection
            if "stage2" in stages:
                print("\n🦌 Stage 2: Wildlife Detection (Munin/Hugin)")
                if not self.run_stage2():
                    return False
            
            # Stage 3: Generate reports
            if "stage3" in stages:
                print("\n📊 Stage 3: Report Generation")
                if not self.run_stage3():
                    return False
            
            print("\n🎉 Pipeline completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            return False
    
    def upload_data(self, input_data):
        """Upload data to S3."""
        data_dir = Path(input_data)
        if not data_dir.exists():
            print(f"❌ Data directory not found: {data_dir}")
            return False
        
        files_uploaded = 0
        for file_path in data_dir.iterdir():
            if file_path.is_file():
                key = f"raw-data/{file_path.name}"
                try:
                    self.s3.upload_file(str(file_path), self.bucket_name, key)
                    print(f"✅ Uploaded: {file_path.name}")
                    files_uploaded += 1
                except Exception as e:
                    print(f"❌ Failed to upload {file_path.name}: {e}")
        
        print(f"📊 Uploaded {files_uploaded} files")
        return files_uploaded > 0
    
    def run_stage1(self):
        """Run Stage 1: Create manifest using Munin."""
        print("📋 Running Stage 1 with Munin...")
        
        # Use Munin to create manifest
        try:
            # This would call the actual Munin pipeline
            result = subprocess.run([
                'python', '-m', 'munin.pipeline.stage1',
                '--input', f's3://{self.bucket_name}/raw-data/',
                '--output', f's3://{self.bucket_name}/stage1-manifest/'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Stage 1 completed with Munin")
                return True
            else:
                print(f"❌ Stage 1 failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Stage 1 error: {e}")
            return False
    
    def run_stage2(self):
        """Run Stage 2: Wildlife detection using Hugin."""
        print("🦌 Running Stage 2 with Hugin...")
        
        # Use Hugin for wildlife detection
        try:
            result = subprocess.run([
                'python', '-m', 'hugin.pipeline.stage2',
                '--input', f's3://{self.bucket_name}/stage1-manifest/',
                '--output', f's3://{self.bucket_name}/stage2-detections/',
                '--models', 'munin,hugin',
                '--confidence', '0.7'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Stage 2 completed with Hugin")
                return True
            else:
                print(f"❌ Stage 2 failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Stage 2 error: {e}")
            return False
    
    def run_stage3(self):
        """Run Stage 3: Generate reports."""
        print("📊 Running Stage 3: Report Generation...")
        
        try:
            result = subprocess.run([
                'python', '-m', 'munin.pipeline.stage3',
                '--input', f's3://{self.bucket_name}/stage2-detections/',
                '--output', f's3://{self.bucket_name}/stage3-reports/'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Stage 3 completed")
                return True
            else:
                print(f"❌ Stage 3 failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Stage 3 error: {e}")
            return False
    
    def get_status(self):
        """Get infrastructure and pipeline status."""
        print("📊 Odin Status Report")
        print("=" * 25)
        
        # Infrastructure status
        try:
            response = self.cloudformation.describe_stacks(
                StackName='wildlife-odin-infrastructure'
            )
            stack = response['Stacks'][0]
            print(f"🏗️  Infrastructure: {stack['StackStatus']}")
        except:
            print("🏗️  Infrastructure: NOT_DEPLOYED")
        
        # Batch status
        try:
            response = self.batch.describe_compute_environments()
            for env in response['computeEnvironments']:
                if 'wildlife' in env['computeEnvironmentName']:
                    print(f"⚙️  Compute Environment: {env['status']}")
                    if 'computeResources' in env:
                        resources = env['computeResources']
                        print(f"   vCPUs: {resources.get('desiredvCpus', 0)}/{resources.get('maxvCpus', 0)}")
        except Exception as e:
            print(f"⚙️  Compute Environment: ERROR - {e}")
        
        # S3 data status
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in response:
                print(f"📁 S3 Data: {len(response['Contents'])} objects")
            else:
                print("📁 S3 Data: Empty")
        except Exception as e:
            print(f"📁 S3 Data: ERROR - {e}")
    
    def cleanup(self):
        """Clean up all resources."""
        print("🧹 Odin Cleaning Up All Resources")
        print("=" * 35)
        print("⚠️  WARNING: This will delete ALL infrastructure!")
        
        confirm = input("Type 'ODIN CLEANUP' to confirm: ").strip()
        if confirm != 'ODIN CLEANUP':
            print("❌ Cleanup cancelled")
            return False
        
        try:
            # Delete CloudFormation stack
            print("🗑️  Deleting infrastructure...")
            self.cloudformation.delete_stack(
                StackName='wildlife-odin-infrastructure'
            )
            
            # Wait for deletion
            print("⏳ Waiting for deletion...")
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(StackName='wildlife-odin-infrastructure')
            
            print("✅ Infrastructure deleted")
            
            # Delete S3 bucket
            print("🗑️  Deleting S3 bucket...")
            try:
                # Delete all objects first
                response = self.s3.list_objects_v2(Bucket=self.bucket_name)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        self.s3.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                
                # Delete bucket
                self.s3.delete_bucket(Bucket=self.bucket_name)
                print("✅ S3 bucket deleted")
            except Exception as e:
                print(f"⚠️  S3 cleanup warning: {e}")
            
            print("✅ Odin cleanup completed")
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return False

def main():
    """Main Odin function."""
    parser = argparse.ArgumentParser(description='Odin - The All-Knowing Father')
    parser.add_argument('command', choices=[
        'setup', 'run', 'status', 'cleanup'
    ], help='Odin command to execute')
    parser.add_argument('--config', default='odin.yaml', 
                       help='Configuration file (default: odin.yaml)')
    parser.add_argument('--input', default='test_data',
                       help='Input data directory (default: test_data)')
    parser.add_argument('--stages', nargs='+', 
                       choices=['stage0', 'stage1', 'stage2', 'stage3'],
                       help='Pipeline stages to run')
    
    args = parser.parse_args()
    
    # Initialize Odin
    odin = Odin(args.config)
    
    try:
        if args.command == 'setup':
            success = odin.setup_infrastructure()
        elif args.command == 'run':
            success = odin.run_pipeline(args.input, args.stages)
        elif args.command == 'status':
            odin.get_status()
            success = True
        elif args.command == 'cleanup':
            success = odin.cleanup()
        else:
            print(f"❌ Unknown command: {args.command}")
            success = False
        
        return success
        
    except KeyboardInterrupt:
        print("\n⏹️  Odin interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Odin failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
