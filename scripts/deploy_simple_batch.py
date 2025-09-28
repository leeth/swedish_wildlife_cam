#!/usr/bin/env python3
"""
Deploy Simple AWS Batch Infrastructure

This script deploys a simple AWS Batch setup for testing.
"""

import boto3
import time
import json
from pathlib import Path

def get_default_vpc():
    """Get default VPC and subnets."""
    ec2 = boto3.client('ec2', region_name='eu-north-1')
    
    # Get default VPC
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
    if not vpcs['Vpcs']:
        print("❌ No default VPC found")
        return None, None
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    print(f"✅ Found default VPC: {vpc_id}")
    
    # Get subnets
    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
    print(f"✅ Found {len(subnet_ids)} subnets: {subnet_ids}")
    
    return vpc_id, subnet_ids

def deploy_simple_batch():
    """Deploy simple batch infrastructure."""
    print("🚀 Deploying Simple AWS Batch Infrastructure")
    print("=" * 50)
    
    # Get VPC and subnets
    vpc_id, subnet_ids = get_default_vpc()
    if not vpc_id:
        return False
    
    # Create CloudFormation client
    cf = boto3.client('cloudformation', region_name='eu-north-1')
    
    # Read template
    template_path = Path(__file__).parent.parent / "aws" / "simple-batch-template.yaml"
    with open(template_path, 'r') as f:
        template_body = f.read()
    
    # Deploy stack
    stack_name = "wildlife-simple-batch"
    print(f"📋 Deploying stack: {stack_name}")
    
    try:
        response = cf.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=[
                {
                    'ParameterKey': 'Environment',
                    'ParameterValue': 'production'
                },
                {
                    'ParameterKey': 'VpcId',
                    'ParameterValue': vpc_id
                },
                {
                    'ParameterKey': 'SubnetIds',
                    'ParameterValue': ','.join(subnet_ids)
                }
            ],
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        
        print(f"✅ Stack creation initiated: {response['StackId']}")
        
        # Wait for completion
        print("⏳ Waiting for stack creation to complete...")
        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        
        print("✅ Stack creation completed!")
        
        # Get outputs
        stack = cf.describe_stacks(StackName=stack_name)
        outputs = stack['Stacks'][0].get('Outputs', [])
        
        print("\n📊 Stack Outputs:")
        for output in outputs:
            print(f"   {output['OutputKey']}: {output['OutputValue']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Stack creation failed: {e}")
        return False

def test_batch_job():
    """Test running a batch job."""
    print("\n🧪 Testing Batch Job")
    print("=" * 30)
    
    batch = boto3.client('batch', region_name='eu-north-1')
    
    # Get job queue and definition
    try:
        queues = batch.describe_job_queues()
        if not queues['jobQueues']:
            print("❌ No job queues found")
            return False
        
        queue_name = queues['jobQueues'][0]['jobQueueName']
        print(f"✅ Found job queue: {queue_name}")
        
        definitions = batch.describe_job_definitions()
        if not definitions['jobDefinitions']:
            print("❌ No job definitions found")
            return False
        
        job_def_name = definitions['jobDefinitions'][0]['jobDefinitionName']
        print(f"✅ Found job definition: {job_def_name}")
        
        # Submit test job
        print("📋 Submitting test job...")
        response = batch.submit_job(
            jobName='wildlife-test-job',
            jobQueue=queue_name,
            jobDefinition=job_def_name
        )
        
        job_id = response['jobId']
        print(f"✅ Job submitted: {job_id}")
        
        # Monitor job
        print("⏳ Monitoring job...")
        for i in range(10):  # Check for 5 minutes
            time.sleep(30)
            job = batch.describe_jobs(jobs=[job_id])
            status = job['jobs'][0]['status']
            print(f"   Job status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                break
        
        if status == 'SUCCEEDED':
            print("✅ Job completed successfully!")
            return True
        else:
            print(f"❌ Job failed with status: {status}")
            return False
            
    except Exception as e:
        print(f"❌ Batch job test failed: {e}")
        return False

def main():
    """Main function."""
    print("🧪 Simple AWS Batch Test")
    print("=" * 40)
    
    # Deploy infrastructure
    if not deploy_simple_batch():
        print("❌ Infrastructure deployment failed")
        return False
    
    # Test batch job
    if not test_batch_job():
        print("❌ Batch job test failed")
        return False
    
    print("\n🎉 Simple AWS Batch test completed successfully!")
    print("✅ Infrastructure deployed and tested")
    print("✅ Batch job executed successfully")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ Test failed!")
        exit(1)
    print("\n🚀 Ready for real processing! 💰")
