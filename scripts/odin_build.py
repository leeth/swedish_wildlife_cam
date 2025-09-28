#!/usr/bin/env python3
"""
Odin Build - Infrastructure Setup

This script handles complete build-up of AWS infrastructure:
- CloudFormation stack deployment
- AWS Batch compute environments
- S3 buckets and permissions
- IAM roles and policies
"""

import boto3
import time
import sys
import yaml
from pathlib import Path
import argparse

class OdinBuild:
    def __init__(self, region='eu-north-1', config_path='odin.yaml'):
        """Initialize build manager."""
        self.region = region
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        
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
    
    def get_default_vpc(self):
        """Get default VPC and subnets."""
        print("🌐 Getting Default VPC")
        print("=" * 25)
        
        try:
            # Get default VPC
            vpcs = self.ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
            if not vpcs['Vpcs']:
                print("❌ No default VPC found")
                return None, None
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            print(f"✅ Found default VPC: {vpc_id}")
            
            # Get subnets
            subnets = self.ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
            print(f"✅ Found {len(subnet_ids)} subnets")
            
            return vpc_id, subnet_ids
            
        except Exception as e:
            print(f"❌ Error getting VPC: {e}")
            return None, None
    
    def generate_cloudformation_template(self):
        """Generate CloudFormation template from odin.yaml."""
        print("📋 Generating CloudFormation Template")
        print("=" * 40)
        
        # Get infrastructure config
        infra = self.config['infrastructure']
        batch = infra['batch']
        storage = self.config['storage']
        
        template = f"""
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Odin Wildlife Infrastructure - {self.config["name"]}'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC ID for the compute environment
  SubnetIds:
    Type: CommaDelimitedList
    Description: Subnet IDs for the compute environment
  BucketName:
    Type: String
    Description: S3 bucket name for data storage
    Default: {storage['s3_bucket']}

Resources:
  # S3 Bucket for data
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  # IAM Role for Batch Jobs
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
                  - s3:GetObject
                  - s3:PutObject
                  - s3:DeleteObject
                  - s3:ListBucket
                Resource:
                  - !GetAtt DataBucket.Arn
                  - !Sub '${{DataBucket.Arn}}/*'
        - PolicyName: CloudWatchLogs
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: '*'

  # IAM Role for EC2 Instances
  BatchInstanceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: wildlife-batch-instance-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:DeleteObject
                  - s3:ListBucket
                Resource:
                  - !GetAtt DataBucket.Arn
                  - !Sub '${{DataBucket.Arn}}/*'

  # Instance Profile for EC2
  BatchInstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref BatchInstanceRole

  # Security Group
  SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: wildlife-batch-sg
      GroupDescription: Security group for wildlife batch processing
      VpcId: !Ref VpcId
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0

  # Batch Service Role
  BatchServiceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: wildlife-batch-service-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: batch.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole

  # Batch Compute Environment
  ComputeEnvironment:
    Type: AWS::Batch::ComputeEnvironment
    Properties:
      ComputeEnvironmentName: {batch['compute_environment']['name']}
      Type: {batch['compute_environment']['type']}
      State: ENABLED
      ServiceRole: !GetAtt BatchServiceRole.Arn
      ComputeResources:
        Type: EC2
        MinvCpus: {batch['compute_environment']['min_vcpus']}
        MaxvCpus: {batch['compute_environment']['max_vcpus']}
        DesiredvCpus: {batch['compute_environment']['desired_vcpus']}
        InstanceTypes: {batch['compute_environment']['instance_types']}
        SecurityGroupIds:
          - !Ref SecurityGroup
        Subnets: !Ref SubnetIds
        InstanceRole: !GetAtt BatchInstanceProfile.Arn
        Tags:
          Environment: production
          Application: wildlife-detection
          ManagedBy: odin

  # Batch Job Queue
  JobQueue:
    Type: AWS::Batch::JobQueue
    Properties:
      JobQueueName: {batch['job_queue']['name']}
      State: ENABLED
      Priority: {batch['job_queue']['priority']}
      ComputeEnvironmentOrder:
        - Order: 1
          ComputeEnvironment: !Ref ComputeEnvironment

Outputs:
  DataBucket:
    Description: S3 bucket for wildlife data
    Value: !Ref DataBucket
    Export:
      Name: !Sub '${{AWS::StackName}}-DataBucket'
  
  ComputeEnvironment:
    Description: Batch compute environment
    Value: !Ref ComputeEnvironment
    Export:
      Name: !Sub '${{AWS::StackName}}-ComputeEnvironment'
  
  JobQueue:
    Description: Batch job queue
    Value: !Ref JobQueue
    Export:
      Name: !Sub '${{AWS::StackName}}-JobQueue'
"""
        
        print("✅ CloudFormation template generated")
        return template
    
    def deploy_stack(self, stack_name, template):
        """Deploy CloudFormation stack."""
        print(f"\n🚀 Deploying Stack: {stack_name}")
        print("=" * 35)
        
        try:
            # Get VPC info
            vpc_id, subnet_ids = self.get_default_vpc()
            if not vpc_id:
                return False
            
            # Deploy stack
            print(f"📋 Deploying stack: {stack_name}")
            response = self.cloudformation.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=[
                    {'ParameterKey': 'VpcId', 'ParameterValue': vpc_id},
                    {'ParameterKey': 'SubnetIds', 'ParameterValue': ','.join(subnet_ids)},
                    {'ParameterKey': 'BucketName', 'ParameterValue': self.config['storage']['s3_bucket']}
                ],
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Environment', 'Value': 'production'},
                    {'Key': 'Application', 'Value': 'wildlife-detection'},
                    {'Key': 'ManagedBy', 'Value': 'odin'}
                ]
            )
            
            print(f"✅ Stack creation initiated: {response['StackId']}")
            
            # Wait for completion
            print("⏳ Waiting for stack creation to complete...")
            waiter = self.cloudformation.get_waiter('stack_create_complete')
            waiter.wait(StackName=stack_name)
            
            print("✅ Stack deployment completed!")
            return True
            
        except Exception as e:
            print(f"❌ Stack deployment failed: {e}")
            return False
    
    def verify_deployment(self, stack_name):
        """Verify deployment is working."""
        print(f"\n✅ Verifying Deployment: {stack_name}")
        print("=" * 40)
        
        try:
            # Get stack outputs
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            outputs = stack.get('Outputs', [])
            
            print("📊 Stack Outputs:")
            for output in outputs:
                print(f"   {output['OutputKey']}: {output['OutputValue']}")
            
            # Test AWS Batch
            batch = boto3.client('batch', region_name=self.region)
            
            # Check compute environment
            ce_response = batch.describe_compute_environments()
            wildlife_ces = [ce for ce in ce_response['computeEnvironments'] 
                          if 'wildlife' in ce['computeEnvironmentName'].lower()]
            
            print(f"\n⚙️  Compute Environments: {len(wildlife_ces)}")
            for ce in wildlife_ces:
                print(f"   {ce['computeEnvironmentName']}: {ce['status']}")
            
            # Check job queue
            jq_response = batch.describe_job_queues()
            wildlife_jqs = [jq for jq in jq_response['jobQueues'] 
                          if 'wildlife' in jq['jobQueueName'].lower()]
            
            print(f"📋 Job Queues: {len(wildlife_jqs)}")
            for jq in wildlife_jqs:
                print(f"   {jq['jobQueueName']}: {jq['state']}")
            
            print("\n✅ Deployment verification completed!")
            return True
            
        except Exception as e:
            print(f"❌ Deployment verification failed: {e}")
            return False
    
    def build_all(self, stack_name='wildlife-odin-infrastructure'):
        """Build complete infrastructure."""
        print("🏗️  Odin Complete Build")
        print("=" * 25)
        print("Building complete wildlife infrastructure from odin.yaml")
        print()
        
        try:
            # 1. Generate template
            template = self.generate_cloudformation_template()
            
            # 2. Deploy stack
            if not self.deploy_stack(stack_name, template):
                return False
            
            # 3. Verify deployment
            if not self.verify_deployment(stack_name):
                return False
            
            print("\n🎉 Infrastructure build completed successfully!")
            print("✅ CloudFormation stack deployed")
            print("✅ AWS Batch compute environment ready")
            print("✅ S3 bucket created")
            print("✅ IAM roles and policies configured")
            
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Odin Infrastructure Build')
    parser.add_argument('--region', default='eu-north-1', 
                       help='AWS region (default: eu-north-1)')
    parser.add_argument('--config', default='odin.yaml',
                       help='Configuration file (default: odin.yaml)')
    parser.add_argument('--stack-name', default='wildlife-odin-infrastructure',
                       help='CloudFormation stack name')
    
    args = parser.parse_args()
    
    builder = OdinBuild(region=args.region, config_path=args.config)
    
    try:
        return builder.build_all(stack_name=args.stack_name)
        
    except KeyboardInterrupt:
        print("\n⏹️  Build interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
