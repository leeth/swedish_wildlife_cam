#!/usr/bin/env python3
"""
AWS Test User Creation Script

This script creates an AWS IAM user for testing the wildlife pipeline with minimal required permissions.
It creates a user with programmatic access and the necessary policies for:
- S3 storage operations
- AWS Batch job submission
- CloudFormation stack management
- Basic monitoring
"""

import boto3
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse


def create_test_user_policy():
    """Create a minimal policy for the test user."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3WildlifePipelineAccess",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "Resource": [
                    "arn:aws:s3:::wildlife-pipeline-*",
                    "arn:aws:s3:::wildlife-pipeline-*/*"
                ]
            },
            {
                "Sid": "BatchJobSubmission",
                "Effect": "Allow",
                "Action": [
                    "batch:SubmitJob",
                    "batch:DescribeJobs",
                    "batch:ListJobs",
                    "batch:TerminateJob"
                ],
                "Resource": "*"
            },
            {
                "Sid": "ECRImageAccess",
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudFormationStackManagement",
                "Effect": "Allow",
                "Action": [
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:DescribeStacks",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:DescribeStackResources",
                    "cloudformation:GetTemplate",
                    "cloudformation:ListStacks",
                    "cloudformation:UpdateStack"
                ],
                "Resource": "*"
            },
            {
                "Sid": "IAMRoleManagement",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:GetRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PassRole",
                    "iam:ListAttachedRolePolicies"
                ],
                "Resource": [
                    "arn:aws:iam::*:role/wildlife-pipeline-*"
                ]
            },
            {
                "Sid": "VPCManagement",
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateVpc",
                    "ec2:DeleteVpc",
                    "ec2:DescribeVpcs",
                    "ec2:CreateSubnet",
                    "ec2:DeleteSubnet",
                    "ec2:DescribeSubnets",
                    "ec2:CreateSecurityGroup",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DescribeSecurityGroups",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:AuthorizeSecurityGroupEgress"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams"
                ],
                "Resource": "*"
            }
        ]
    }
    return policy


def create_aws_test_user(username: str = "wildlife-pipeline-test", 
                        region: str = "eu-north-1",
                        output_file: str = "aws-test-credentials.json"):
    """Create an AWS test user with minimal permissions."""
    
    print(f"🔧 Creating AWS test user: {username}")
    print(f"🌍 Region: {region}")
    
    try:
        # Initialize IAM client
        iam = boto3.client('iam', region_name=region)
        
        # Check if user already exists
        try:
            iam.get_user(UserName=username)
            print(f"⚠️  User {username} already exists")
            
            # Get existing access keys
            try:
                response = iam.list_access_keys(UserName=username)
                if response['AccessKeyMetadata']:
                    print(f"✅ User {username} already has access keys")
                    return True
            except Exception as e:
                print(f"❌ Error checking access keys: {e}")
                return False
                
        except iam.exceptions.NoSuchEntityException:
            # User doesn't exist, create it
            print(f"👤 Creating new user: {username}")
            
            # Create user
            iam.create_user(UserName=username)
            print(f"✅ Created user: {username}")
        
        # Create and attach policy
        policy_name = f"{username}-policy"
        policy_document = create_test_user_policy()
        
        try:
            # Try to get existing policy
            iam.get_policy(PolicyArn=f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:policy/{policy_name}")
            print(f"📋 Policy {policy_name} already exists")
        except iam.exceptions.NoSuchEntityException:
            # Create policy
            iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document, indent=2)
            )
            print(f"✅ Created policy: {policy_name}")
        
        # Attach policy to user
        account_id = boto3.client('sts').get_caller_identity()['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        
        iam.attach_user_policy(
            UserName=username,
            PolicyArn=policy_arn
        )
        print(f"✅ Attached policy to user: {username}")
        
        # Create access key
        response = iam.create_access_key(UserName=username)
        access_key = response['AccessKey']
        
        # Save credentials to file
        credentials = {
            "username": username,
            "access_key_id": access_key['AccessKeyId'],
            "secret_access_key": access_key['SecretAccessKey'],
            "region": region,
            "created_at": datetime.now().isoformat(),
            "policy_arn": policy_arn
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"✅ Access key created and saved to: {output_path}")
        print(f"🔑 Access Key ID: {access_key['AccessKeyId']}")
        print(f"🔐 Secret Access Key: {access_key['SecretAccessKey']}")
        
        # Create AWS credentials file
        aws_credentials_path = Path.home() / ".aws" / "credentials"
        aws_credentials_path.parent.mkdir(exist_ok=True)
        
        # Read existing credentials or create new
        credentials_content = ""
        if aws_credentials_path.exists():
            with open(aws_credentials_path, 'r') as f:
                credentials_content = f.read()
        
        # Add test user profile
        test_profile = f"""
[wildlife-pipeline-test]
aws_access_key_id = {access_key['AccessKeyId']}
aws_secret_access_key = {access_key['SecretAccessKey']}
region = {region}
"""
        
        with open(aws_credentials_path, 'a') as f:
            f.write(test_profile)
        
        print(f"✅ Added profile to AWS credentials file: {aws_credentials_path}")
        print(f"📝 Profile name: wildlife-pipeline-test")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating AWS test user: {e}")
        return False


def test_aws_credentials(credentials_file: str = "aws-test-credentials.json"):
    """Test the created AWS credentials."""
    print(f"\n🧪 Testing AWS credentials...")
    
    try:
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)
        
        # Test S3 access
        s3 = boto3.client(
            's3',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials['region']
        )
        
        # List buckets
        response = s3.list_buckets()
        print(f"✅ S3 access working - found {len(response['Buckets'])} buckets")
        
        # Test IAM access
        iam = boto3.client(
            'iam',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials['region']
        )
        
        # Get user info
        user_info = iam.get_user()
        print(f"✅ IAM access working - user: {user_info['User']['UserName']}")
        
        # Test Batch access
        batch = boto3.client(
            'batch',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials['region']
        )
        
        # List job queues
        response = batch.describe_job_queues()
        print(f"✅ Batch access working - found {len(response['jobQueues'])} job queues")
        
        print(f"\n🎉 All AWS services accessible with test credentials!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False


def cleanup_test_user(username: str = "wildlife-pipeline-test"):
    """Clean up the test user and resources."""
    print(f"🧹 Cleaning up test user: {username}")
    
    try:
        iam = boto3.client('iam')
        
        # Delete access keys
        try:
            response = iam.list_access_keys(UserName=username)
            for key in response['AccessKeyMetadata']:
                iam.delete_access_key(
                    UserName=username,
                    AccessKeyId=key['AccessKeyId']
                )
                print(f"✅ Deleted access key: {key['AccessKeyId']}")
        except Exception as e:
            print(f"⚠️  Error deleting access keys: {e}")
        
        # Detach policies
        try:
            response = iam.list_attached_user_policies(UserName=username)
            for policy in response['AttachedPolicies']:
                iam.detach_user_policy(
                    UserName=username,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"✅ Detached policy: {policy['PolicyName']}")
        except Exception as e:
            print(f"⚠️  Error detaching policies: {e}")
        
        # Delete user
        try:
            iam.delete_user(UserName=username)
            print(f"✅ Deleted user: {username}")
        except Exception as e:
            print(f"⚠️  Error deleting user: {e}")
        
        print(f"🧹 Cleanup completed for user: {username}")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


def main():
    """Main CLI for AWS test user creation."""
    parser = argparse.ArgumentParser(description="Create AWS test user for wildlife pipeline")
    parser.add_argument("--username", default="wildlife-pipeline-test", help="Username for test user")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--output", default="aws-test-credentials.json", help="Output credentials file")
    parser.add_argument("--test", action="store_true", help="Test the created credentials")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test user")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_user(args.username)
        return
    
    # Create test user
    success = create_aws_test_user(
        username=args.username,
        region=args.region,
        output_file=args.output
    )
    
    if success and args.test:
        test_aws_credentials(args.output)
    
    if success:
        print(f"\n📋 Next Steps:")
        print(f"1. Use credentials from: {args.output}")
        print(f"2. Set AWS profile: export AWS_PROFILE=wildlife-pipeline-test")
        print(f"3. Test pipeline: python -m src.wildlife_pipeline.cloud.cli stage1 --profile cloud")
        print(f"4. Clean up when done: python {__file__} --cleanup")


if __name__ == "__main__":
    main()
