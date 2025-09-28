#!/usr/bin/env python3
"""
AWS Infrastructure Deployment Script

This script deploys the complete AWS infrastructure for the wildlife pipeline:
- S3 buckets for storage
- AWS Batch compute environment with GPU support
- ECR repository for Docker images
- CloudFormation stack with all resources
- IAM roles and policies
- VPC and security groups
"""

import boto3
import json
import time
import subprocess
from pathlib import Path
import sys
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_s3_buckets(region: str = "eu-north-1"):
    """Create S3 buckets for the wildlife pipeline."""
    print("🪣 Creating S3 buckets...")
    
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # Bucket names
        buckets = {
            "wildlife-pipeline-data": "Raw images and processed data",
            "wildlife-pipeline-results": "Pipeline outputs and results",
            "wildlife-pipeline-models": "Model artifacts and weights",
            "wildlife-pipeline-logs": "Pipeline logs and monitoring data"
        }
        
        created_buckets = []
        
        for bucket_name, description in buckets.items():
            try:
                # Create bucket
                if region == "us-east-1":
                    s3.create_bucket(Bucket=bucket_name)
                else:
                    s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                
                print(f"✅ Created bucket: {bucket_name}")
                
                # Configure bucket for versioning
                s3.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Configure bucket for logging
                s3.put_bucket_logging(
                    Bucket=bucket_name,
                    BucketLoggingStatus={
                        'LoggingEnabled': {
                            'TargetBucket': 'wildlife-pipeline-logs',
                            'TargetPrefix': f'{bucket_name}/'
                        }
                    }
                )
                
                created_buckets.append(bucket_name)
                
            except s3.exceptions.BucketAlreadyOwnedByYou:
                print(f"✅ Bucket already exists: {bucket_name}")
                created_buckets.append(bucket_name)
            except Exception as e:
                print(f"❌ Error creating bucket {bucket_name}: {e}")
        
        return created_buckets
        
    except Exception as e:
        print(f"❌ Error creating S3 buckets: {e}")
        return []


def create_ecr_repository(region: str = "eu-north-1"):
    """Create ECR repository for Docker images."""
    print("🐳 Creating ECR repository...")
    
    try:
        ecr = boto3.client('ecr', region_name=region)
        
        repository_name = "wildlife-pipeline"
        
        try:
            response = ecr.create_repository(
                repositoryName=repository_name,
                imageTagMutability='MUTABLE',
                imageScanningConfiguration={
                    'scanOnPush': True
                }
            )
            print(f"✅ Created ECR repository: {repository_name}")
            return response['repository']['repositoryUri']
            
        except ecr.exceptions.RepositoryAlreadyExistsException:
            print(f"✅ ECR repository already exists: {repository_name}")
            return f"{boto3.client('sts').get_caller_identity()['Account']}.dkr.ecr.{region}.amazonaws.com/{repository_name}"
        
    except Exception as e:
        print(f"❌ Error creating ECR repository: {e}")
        return None


def create_iam_roles(region: str = "eu-north-1"):
    """Create IAM roles for the wildlife pipeline."""
    print("🔐 Creating IAM roles...")
    
    try:
        iam = boto3.client('iam')
        
        # Batch service role
        batch_service_role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "batch.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            iam.create_role(
                RoleName='wildlife-pipeline-batch-service-role',
                AssumeRolePolicyDocument=json.dumps(batch_service_role),
                Description='Service role for AWS Batch wildlife pipeline'
            )
            print("✅ Created Batch service role")
        except iam.exceptions.EntityAlreadyExistsException:
            print("✅ Batch service role already exists")
        
        # Batch instance role
        batch_instance_role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            iam.create_role(
                RoleName='wildlife-pipeline-batch-instance-role',
                AssumeRolePolicyDocument=json.dumps(batch_instance_role),
                Description='Instance role for AWS Batch wildlife pipeline'
            )
            print("✅ Created Batch instance role")
        except iam.exceptions.EntityAlreadyExistsException:
            print("✅ Batch instance role already exists")
        
        # Attach policies
        policies = [
            ('wildlife-pipeline-batch-service-role', 'arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole'),
            ('wildlife-pipeline-batch-instance-role', 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'),
            ('wildlife-pipeline-batch-instance-role', 'arn:aws:iam::aws:policy/CloudWatchLogsFullAccess'),
            ('wildlife-pipeline-batch-instance-role', 'arn:aws:iam::aws:policy/AmazonS3FullAccess')
        ]
        
        for role_name, policy_arn in policies:
            try:
                iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                print(f"✅ Attached policy to {role_name}")
            except Exception as e:
                print(f"⚠️  Error attaching policy to {role_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating IAM roles: {e}")
        return False


def create_batch_compute_environment(region: str = "eu-north-1"):
    """Create AWS Batch compute environment with GPU support."""
    print("⚡ Creating Batch compute environment...")
    
    try:
        batch = boto3.client('batch', region_name=region)
        
        # Get account ID
        account_id = boto3.client('sts').get_caller_identity()['Account']
        
        compute_environment_name = "wildlife-pipeline-compute"
        
        try:
            response = batch.create_compute_environment(
                computeEnvironmentName=compute_environment_name,
                type='MANAGED',
                state='ENABLED',
                computeResources={
                    'type': 'EC2',
                    'minvCpus': 0,
                    'maxvCpus': 256,
                    'desiredvCpus': 0,
                    'instanceTypes': ['g4dn.xlarge', 'g4dn.2xlarge', 'p3.2xlarge'],
                    'subnets': ['subnet-12345678'],  # Replace with actual subnet
                    'securityGroupIds': ['sg-12345678'],  # Replace with actual security group
                    'instanceRole': f'arn:aws:iam::{account_id}:role/wildlife-pipeline-batch-instance-role',
                    'tags': {
                        'Project': 'WildlifePipeline',
                        'Environment': 'Production'
                    }
                },
                serviceRole=f'arn:aws:iam::{account_id}:role/wildlife-pipeline-batch-service-role'
            )
            print(f"✅ Created compute environment: {compute_environment_name}")
            return response['computeEnvironmentArn']
            
        except batch.exceptions.ClientException as e:
            if "already exists" in str(e):
                print(f"✅ Compute environment already exists: {compute_environment_name}")
                return f"arn:aws:batch:{region}:{account_id}:compute-environment/{compute_environment_name}"
            else:
                raise e
        
    except Exception as e:
        print(f"❌ Error creating Batch compute environment: {e}")
        return None


def create_batch_job_queue(region: str = "eu-north-1"):
    """Create AWS Batch job queue."""
    print("📋 Creating Batch job queue...")
    
    try:
        batch = boto3.client('batch', region_name=region)
        
        job_queue_name = "wildlife-pipeline-queue"
        compute_environment_name = "wildlife-pipeline-compute"
        
        try:
            response = batch.create_job_queue(
                jobQueueName=job_queue_name,
                state='ENABLED',
                priority=1,
                computeEnvironmentOrder=[
                    {
                        'order': 1,
                        'computeEnvironment': compute_environment_name
                    }
                ]
            )
            print(f"✅ Created job queue: {job_queue_name}")
            return response['jobQueueArn']
            
        except batch.exceptions.ClientException as e:
            if "already exists" in str(e):
                print(f"✅ Job queue already exists: {job_queue_name}")
                return f"arn:aws:batch:{region}:{boto3.client('sts').get_caller_identity()['Account']}:job-queue/{job_queue_name}"
            else:
                raise e
        
    except Exception as e:
        print(f"❌ Error creating Batch job queue: {e}")
        return None


def create_batch_job_definition(region: str = "eu-north-1", ecr_uri: str = None):
    """Create AWS Batch job definition."""
    print("📝 Creating Batch job definition...")
    
    try:
        batch = boto3.client('batch', region_name=region)
        
        job_definition_name = "wildlife-pipeline-job"
        
        if not ecr_uri:
            account_id = boto3.client('sts').get_caller_identity()['Account']
            ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/wildlife-pipeline:latest"
        
        try:
            response = batch.register_job_definition(
                jobDefinitionName=job_definition_name,
                type='container',
                containerProperties={
                    'image': ecr_uri,
                    'vcpus': 4,
                    'memory': 16384,
                    'jobRoleArn': f'arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/wildlife-pipeline-batch-instance-role',
                    'environment': [
                        {'name': 'AWS_DEFAULT_REGION', 'value': region},
                        {'name': 'PYTHONPATH', 'value': '/app'},
                        {'name': 'CUDA_VISIBLE_DEVICES', 'value': '0'},
                        {'name': 'PYTORCH_CUDA_ALLOC_CONF', 'value': 'max_split_size_mb:512'}
                    ],
                    'resourceRequirements': [
                        {'type': 'GPU', 'value': '1'}
                    ],
                    'mountPoints': [],
                    'volumes': [],
                    'logConfiguration': {
                        'logDriver': 'awslogs',
                        'options': {
                            'awslogs-group': '/aws/batch/wildlife-pipeline',
                            'awslogs-region': region,
                            'awslogs-stream-prefix': 'batch'
                        }
                    }
                }
            )
            print(f"✅ Created job definition: {job_definition_name}")
            return response['jobDefinitionArn']
            
        except batch.exceptions.ClientException as e:
            if "already exists" in str(e):
                print(f"✅ Job definition already exists: {job_definition_name}")
                return f"arn:aws:batch:{region}:{boto3.client('sts').get_caller_identity()['Account']}:job-definition/{job_definition_name}"
            else:
                raise e
        
    except Exception as e:
        print(f"❌ Error creating Batch job definition: {e}")
        return None


def create_cloudformation_stack(region: str = "eu-north-1"):
    """Create CloudFormation stack with all resources."""
    print("☁️  Creating CloudFormation stack...")
    
    try:
        cf = boto3.client('cloudformation', region_name=region)
        
        stack_name = "wildlife-pipeline-stack"
        
        # Load CloudFormation template
        template_path = Path(__file__).parent.parent / "aws" / "cloudformation-template.yaml"
        
        if not template_path.exists():
            print(f"❌ CloudFormation template not found: {template_path}")
            return False
        
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        try:
            response = cf.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Project', 'Value': 'WildlifePipeline'},
                    {'Key': 'Environment', 'Value': 'Production'}
                ]
            )
            print(f"✅ Created CloudFormation stack: {stack_name}")
            print(f"📋 Stack ID: {response['StackId']}")
            
            # Wait for stack creation
            print("⏳ Waiting for stack creation to complete...")
            waiter = cf.get_waiter('stack_create_complete')
            waiter.wait(StackName=stack_name)
            print("✅ Stack creation completed")
            
            return True
            
        except cf.exceptions.AlreadyExistsException:
            print(f"✅ CloudFormation stack already exists: {stack_name}")
            return True
        
    except Exception as e:
        print(f"❌ Error creating CloudFormation stack: {e}")
        return False


def deploy_complete_infrastructure(region: str = "eu-north-1"):
    """Deploy complete AWS infrastructure."""
    print("🚀 Deploying Complete AWS Infrastructure")
    print("=" * 50)
    
    try:
        # Step 1: Create S3 buckets
        print("\n📦 Step 1: Creating S3 buckets")
        buckets = create_s3_buckets(region)
        if not buckets:
            print("❌ Failed to create S3 buckets")
            return False
        
        # Step 2: Create ECR repository
        print("\n🐳 Step 2: Creating ECR repository")
        ecr_uri = create_ecr_repository(region)
        if not ecr_uri:
            print("❌ Failed to create ECR repository")
            return False
        
        # Step 3: Create IAM roles
        print("\n🔐 Step 3: Creating IAM roles")
        if not create_iam_roles(region):
            print("❌ Failed to create IAM roles")
            return False
        
        # Step 4: Create Batch compute environment
        print("\n⚡ Step 4: Creating Batch compute environment")
        compute_env_arn = create_batch_compute_environment(region)
        if not compute_env_arn:
            print("❌ Failed to create Batch compute environment")
            return False
        
        # Step 5: Create Batch job queue
        print("\n📋 Step 5: Creating Batch job queue")
        job_queue_arn = create_batch_job_queue(region)
        if not job_queue_arn:
            print("❌ Failed to create Batch job queue")
            return False
        
        # Step 6: Create Batch job definition
        print("\n📝 Step 6: Creating Batch job definition")
        job_def_arn = create_batch_job_definition(region, ecr_uri)
        if not job_def_arn:
            print("❌ Failed to create Batch job definition")
            return False
        
        # Step 7: Create CloudFormation stack
        print("\n☁️  Step 7: Creating CloudFormation stack")
        if not create_cloudformation_stack(region):
            print("❌ Failed to create CloudFormation stack")
            return False
        
        print("\n🎉 AWS Infrastructure Deployment Completed!")
        print("=" * 50)
        print("📋 Created Resources:")
        print(f"  S3 Buckets: {', '.join(buckets)}")
        print(f"  ECR Repository: {ecr_uri}")
        print(f"  Batch Compute Environment: {compute_env_arn}")
        print(f"  Batch Job Queue: {job_queue_arn}")
        print(f"  Batch Job Definition: {job_def_arn}")
        
        return True
        
    except Exception as e:
        print(f"❌ Infrastructure deployment failed: {e}")
        return False


def main():
    """Main CLI for AWS infrastructure deployment."""
    parser = argparse.ArgumentParser(description="Deploy AWS infrastructure for wildlife pipeline")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--complete", action="store_true", help="Deploy complete infrastructure")
    parser.add_argument("--s3", action="store_true", help="Create S3 buckets only")
    parser.add_argument("--ecr", action="store_true", help="Create ECR repository only")
    parser.add_argument("--batch", action="store_true", help="Create Batch resources only")
    parser.add_argument("--cf", action="store_true", help="Create CloudFormation stack only")
    
    args = parser.parse_args()
    
    if args.complete:
        deploy_complete_infrastructure(args.region)
    elif args.s3:
        create_s3_buckets(args.region)
    elif args.ecr:
        create_ecr_repository(args.region)
    elif args.batch:
        create_iam_roles(args.region)
        create_batch_compute_environment(args.region)
        create_batch_job_queue(args.region)
        create_batch_job_definition(args.region)
    elif args.cf:
        create_cloudformation_stack(args.region)
    else:
        print("🔧 AWS Infrastructure Deployment")
        print("Use --complete to deploy all resources")
        print("Use --s3, --ecr, --batch, or --cf for specific resources")


if __name__ == "__main__":
    main()
