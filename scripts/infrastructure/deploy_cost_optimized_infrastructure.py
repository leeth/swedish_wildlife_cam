#!/usr/bin/env python3
"""
Cost-Optimized AWS Infrastructure Deployment Script

This script deploys cost-optimized AWS infrastructure for the wildlife pipeline:
- Spot instances with fallback to on-demand
- Infrastructure lifecycle management
- Batch-oriented resource management
- Cost optimization strategies
"""

import boto3
import json
import time
import subprocess
from pathlib import Path
import sys
import argparse
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_cost_optimized_cloudformation_stack(region: str = "eu-north-1"):
    """Create cost-optimized CloudFormation stack."""
    print("☁️  Creating cost-optimized CloudFormation stack...")
    
    try:
        cf = boto3.client('cloudformation', region_name=region)
        
        stack_name = "wildlife-pipeline-cost-optimized"
        
        # Load cost-optimized CloudFormation template
        template_path = Path(__file__).parent.parent.parent / "aws" / "cloudformation-template-cost-optimized.yaml"
        
        if not template_path.exists():
            print(f"❌ Cost-optimized CloudFormation template not found: {template_path}")
            return False
        
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        # Stack parameters for cost optimization
        parameters = [
            {
                'ParameterKey': 'Environment',
                'ParameterValue': 'production'
            },
            {
                'ParameterKey': 'VpcId',
                'ParameterValue': 'vpc-12345678'  # Replace with actual VPC ID
            },
            {
                'ParameterKey': 'SubnetIds',
                'ParameterValue': 'subnet-12345678,subnet-87654321'  # Replace with actual subnet IDs
            },
            {
                'ParameterKey': 'MaxVCpus',
                'ParameterValue': '100'
            },
            {
                'ParameterKey': 'SpotBidPercentage',
                'ParameterValue': '70'
            },
            {
                'ParameterKey': 'MinVCpus',
                'ParameterValue': '0'
            },
            {
                'ParameterKey': 'DesiredVCpus',
                'ParameterValue': '0'
            }
        ]
        
        try:
            response = cf.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Project', 'Value': 'WildlifePipeline'},
                    {'Key': 'Environment', 'Value': 'Production'},
                    {'Key': 'CostOptimization', 'Value': 'Enabled'},
                    {'Key': 'SpotInstances', 'Value': 'Enabled'}
                ]
            )
            print(f"✅ Created cost-optimized CloudFormation stack: {stack_name}")
            print(f"📋 Stack ID: {response['StackId']}")
            
            # Wait for stack creation
            print("⏳ Waiting for stack creation to complete...")
            waiter = cf.get_waiter('stack_create_complete')
            waiter.wait(StackName=stack_name)
            print("✅ Stack creation completed")
            
            return True
            
        except cf.exceptions.AlreadyExistsException:
            print(f"✅ Cost-optimized CloudFormation stack already exists: {stack_name}")
            return True
        
    except Exception as e:
        print(f"❌ Error creating cost-optimized CloudFormation stack: {e}")
        return False


def create_spot_fleet_role(region: str = "eu-north-1"):
    """Create IAM role for spot fleet operations."""
    print("🔐 Creating spot fleet role...")
    
    try:
        iam = boto3.client('iam')
        
        # Spot fleet role
        spot_fleet_role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "spotfleet.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            iam.create_role(
                RoleName='aws-ec2-spot-fleet-role',
                AssumeRolePolicyDocument=json.dumps(spot_fleet_role),
                Description='Role for AWS EC2 Spot Fleet'
            )
            print("✅ Created spot fleet role")
        except iam.exceptions.EntityAlreadyExistsException:
            print("✅ Spot fleet role already exists")
        
        # Attach spot fleet service role policy
        try:
            iam.attach_role_policy(
                RoleName='aws-ec2-spot-fleet-role',
                PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetRole'
            )
            print("✅ Attached spot fleet service role policy")
        except Exception as e:
            print(f"⚠️  Error attaching spot fleet policy: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating spot fleet role: {e}")
        return False


def create_cost_optimization_lambda(region: str = "eu-north-1"):
    """Create Lambda function for cost optimization."""
    print("⚡ Creating cost optimization Lambda function...")
    
    try:
        lambda_client = boto3.client('lambda', region_name=region)
        
        # Lambda function code
        lambda_code = '''
import boto3
import json
import time
from datetime import datetime, timedelta

def lambda_handler(event, context):
    batch = boto3.client('batch')
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    action = event.get('action', 'status')
    compute_env = event.get('compute_environment')
    
    if action == 'start':
        # Scale up compute environment
        response = batch.update_compute_environment(
            computeEnvironment=compute_env,
            desiredvCpus=event.get('desired_vcpus', 10)
        )
        return {'statusCode': 200, 'body': 'Infrastructure started'}
    
    elif action == 'stop':
        # Scale down compute environment
        response = batch.update_compute_environment(
            computeEnvironment=compute_env,
            desiredvCpus=0
        )
        return {'statusCode': 200, 'body': 'Infrastructure stopped'}
    
    elif action == 'optimize':
        # Cost optimization logic
        try:
            # Get current spot pricing
            spot_prices = ec2.describe_spot_price_history(
                InstanceTypes=['g4dn.xlarge', 'g4dn.2xlarge', 'p3.2xlarge'],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=10
            )
            
            # Select optimal instance type
            best_instance = None
            best_price = float('inf')
            
            for price in spot_prices['SpotPriceHistory']:
                if float(price['SpotPrice']) < best_price:
                    best_price = float(price['SpotPrice'])
                    best_instance = price['InstanceType']
            
            # Update compute environment with optimal instance type
            if best_instance:
                response = batch.update_compute_environment(
                    computeEnvironment=compute_env,
                    computeResources={
                        'instanceTypes': [best_instance]
                    }
                )
                return {
                    'statusCode': 200,
                    'body': f'Optimized to {best_instance} at ${best_price:.4f}/hour'
                }
            
        except Exception as e:
            return {'statusCode': 500, 'body': f'Optimization failed: {str(e)}'}
    
    elif action == 'status':
        # Check compute environment status
        response = batch.describe_compute_environments(
            computeEnvironments=[compute_env]
        )
        return {
            'statusCode': 200,
            'body': json.dumps(response['computeEnvironments'][0])
        }
    
    return {'statusCode': 400, 'body': 'Invalid action'}
'''
        
        # Create Lambda function
        try:
            response = lambda_client.create_function(
                FunctionName='wildlife-cost-optimization',
                Runtime='python3.9',
                Role='arn:aws:iam::123456789012:role/lambda-execution-role',  # Replace with actual role
                Handler='index.lambda_handler',
                Code={'ZipFile': lambda_code.encode()},
                Description='Cost optimization function for wildlife pipeline',
                Timeout=300,
                Environment={
                    'Variables': {
                        'COMPUTE_ENVIRONMENT': 'wildlife-detection-compute-production'
                    }
                }
            )
            print("✅ Created cost optimization Lambda function")
            return True
            
        except lambda_client.exceptions.ResourceConflictException:
            print("✅ Cost optimization Lambda function already exists")
            return True
        
    except Exception as e:
        print(f"❌ Error creating cost optimization Lambda function: {e}")
        return False


def create_cost_monitoring_dashboard(region: str = "eu-north-1"):
    """Create CloudWatch dashboard for cost monitoring."""
    print("📊 Creating cost monitoring dashboard...")
    
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        # Dashboard body
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Batch", "RunningJobs", "ServiceName", "AWS Batch"],
                            [".", "PendingJobs", ".", "."],
                            [".", "FailedJobs", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": region,
                        "title": "Batch Job Metrics",
                        "period": 300
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "i-1234567890abcdef0"],
                            [".", "NetworkIn", ".", "."],
                            [".", "NetworkOut", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": region,
                        "title": "EC2 Instance Metrics",
                        "period": 300
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/S3", "BucketSizeBytes", "BucketName", "wildlife-detection-data"],
                            [".", "NumberOfObjects", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": region,
                        "title": "S3 Storage Metrics",
                        "period": 300
                    }
                }
            ]
        }
        
        try:
            cloudwatch.put_dashboard(
                DashboardName='wildlife-pipeline-cost-monitoring',
                DashboardBody=json.dumps(dashboard_body)
            )
            print("✅ Created cost monitoring dashboard")
            return True
            
        except Exception as e:
            print(f"❌ Error creating cost monitoring dashboard: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error creating cost monitoring dashboard: {e}")
        return False


def deploy_cost_optimized_infrastructure(region: str = "eu-north-1"):
    """Deploy complete cost-optimized AWS infrastructure."""
    print("🚀 Deploying Cost-Optimized AWS Infrastructure")
    print("=" * 60)
    
    try:
        # Step 1: Create spot fleet role
        print("\n🔐 Step 1: Creating spot fleet role")
        if not create_spot_fleet_role(region):
            print("❌ Failed to create spot fleet role")
            return False
        
        # Step 2: Create cost-optimized CloudFormation stack
        print("\n☁️  Step 2: Creating cost-optimized CloudFormation stack")
        if not create_cost_optimized_cloudformation_stack(region):
            print("❌ Failed to create cost-optimized CloudFormation stack")
            return False
        
        # Step 3: Create cost optimization Lambda function
        print("\n⚡ Step 3: Creating cost optimization Lambda function")
        if not create_cost_optimization_lambda(region):
            print("❌ Failed to create cost optimization Lambda function")
            return False
        
        # Step 4: Create cost monitoring dashboard
        print("\n📊 Step 4: Creating cost monitoring dashboard")
        if not create_cost_monitoring_dashboard(region):
            print("❌ Failed to create cost monitoring dashboard")
            return False
        
        print("\n🎉 Cost-Optimized AWS Infrastructure Deployment Completed!")
        print("=" * 60)
        print("📋 Created Resources:")
        print("  ✅ Spot Fleet Role")
        print("  ✅ Cost-Optimized CloudFormation Stack")
        print("  ✅ Cost Optimization Lambda Function")
        print("  ✅ Cost Monitoring Dashboard")
        print("\n💰 Cost Optimization Features:")
        print("  • Spot instances with 70% bid percentage")
        print("  • Automatic infrastructure scaling")
        print("  • Cost monitoring and optimization")
        print("  • Batch-oriented resource management")
        print("  • Fallback to on-demand instances")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost-optimized infrastructure deployment failed: {e}")
        return False


def main():
    """Main CLI for cost-optimized AWS infrastructure deployment."""
    parser = argparse.ArgumentParser(description="Deploy cost-optimized AWS infrastructure for wildlife pipeline")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--complete", action="store_true", help="Deploy complete cost-optimized infrastructure")
    parser.add_argument("--spot-role", action="store_true", help="Create spot fleet role only")
    parser.add_argument("--cf", action="store_true", help="Create cost-optimized CloudFormation stack only")
    parser.add_argument("--lambda-func", action="store_true", help="Create cost optimization Lambda function only")
    parser.add_argument("--dashboard", action="store_true", help="Create cost monitoring dashboard only")
    
    args = parser.parse_args()
    
    if args.complete:
        deploy_cost_optimized_infrastructure(args.region)
    elif args.spot_role:
        create_spot_fleet_role(args.region)
    elif args.cf:
        create_cost_optimized_cloudformation_stack(args.region)
    elif args.lambda_func:
        create_cost_optimization_lambda(args.region)
    elif args.dashboard:
        create_cost_monitoring_dashboard(args.region)
    else:
        print("🔧 Cost-Optimized AWS Infrastructure Deployment")
        print("Use --complete to deploy all cost-optimized resources")
        print("Use --spot-role, --cf, --lambda, or --dashboard for specific resources")


if __name__ == "__main__":
    main()
