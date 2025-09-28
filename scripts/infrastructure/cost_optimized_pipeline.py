#!/usr/bin/env python3
"""
Cost-Optimized Pipeline Manager

This script manages the complete cost-optimized pipeline:
- Sets up infrastructure when starting
- Processes batch jobs with spot instances
- Downloads Stage 3 output locally
- Tears down infrastructure when complete
- Implements hyper batch-oriented processing
"""

import boto3
import json
import time
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import our cost optimization modules
from cost_optimization_manager import CostOptimizationManager
from batch_workflow_manager import BatchWorkflowManager
from stage3_output_downloader import Stage3OutputDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CostOptimizedPipeline:
    """Manages complete cost-optimized pipeline with Stage 3 output download."""
    
    def __init__(self, region: str = "eu-north-1", environment: str = "production"):
        self.region = region
        self.environment = environment
        self.cost_manager = CostOptimizationManager(region, environment)
        self.batch_manager = BatchWorkflowManager(region, environment)
        self.downloader = Stage3OutputDownloader(region, "cloud")
        
        # Pipeline configuration
        self.pipeline_config = {
            'max_parallel_jobs': 10,
            'gpu_required': True,
            'spot_preferred': True,
            'fallback_timeout': 300,  # 5 minutes
            'cost_threshold': 0.5  # 50% savings threshold
        }
    
    def run_cost_optimized_pipeline(self, 
                                   input_data: List[str],
                                   local_output_path: str,
                                   job_type: str = "image_processing",
                                   priority: str = "normal") -> Dict:
        """Run complete cost-optimized pipeline with local Stage 3 output."""
        try:
            logger.info("🚀 Starting cost-optimized pipeline")
            logger.info(f"Input data: {len(input_data)} items")
            logger.info(f"Local output: {local_output_path}")
            logger.info(f"Job type: {job_type}")
            logger.info(f"Priority: {priority}")
            
            # Step 1: Create batch configuration
            logger.info("Step 1: Creating batch configuration")
            batch_config = self.batch_manager.create_batch_config(
                input_data=input_data,
                job_type=job_type,
                gpu_required=self.pipeline_config['gpu_required'],
                priority=priority
            )
            
            # Step 2: Setup infrastructure with cost optimization
            logger.info("Step 2: Setting up cost-optimized infrastructure")
            if not self.cost_manager.setup_infrastructure(
                job_count=len(input_data),
                gpu_required=self.pipeline_config['gpu_required']
            ):
                return {'status': 'failed', 'error': 'Infrastructure setup failed'}
            
            # Step 3: Process batch with cost optimization
            logger.info("Step 3: Processing batch with cost optimization")
            batch_result = self.batch_manager.process_batch(batch_config)
            
            if batch_result.get('status') != 'completed':
                logger.error("Batch processing failed")
                return batch_result
            
            # Step 4: Download Stage 3 output locally
            logger.info("Step 4: Downloading Stage 3 output locally")
            download_result = self._download_stage3_output_locally(
                batch_result, local_output_path
            )
            
            # Step 5: Teardown infrastructure
            logger.info("Step 5: Tearing down infrastructure")
            self.cost_manager.teardown_infrastructure()
            
            # Step 6: Generate cost report
            logger.info("Step 6: Generating cost report")
            cost_report = self._generate_cost_report(batch_result, download_result)
            
            return {
                'status': 'completed',
                'batch_result': batch_result,
                'download_result': download_result,
                'cost_report': cost_report,
                'local_output_path': local_output_path
            }
            
        except Exception as e:
            logger.error(f"Error in cost-optimized pipeline: {e}")
            # Ensure infrastructure is torn down on error
            try:
                self.cost_manager.teardown_infrastructure()
            except:
                pass
            return {'status': 'failed', 'error': str(e)}
    
    def _download_stage3_output_locally(self, batch_result: Dict, local_output_path: str) -> Dict:
        """Download Stage 3 output from cloud to local storage."""
        try:
            # Determine cloud output path from batch result
            cloud_output_path = self._extract_cloud_output_path(batch_result)
            if not cloud_output_path:
                return {'status': 'failed', 'error': 'Could not determine cloud output path'}
            
            # Download Stage 3 output
            download_result = self.downloader.download_stage3_output(
                cloud_output_path=cloud_output_path,
                local_output_path=local_output_path,
                include_observations=True,
                include_report=True
            )
            
            if 'error' in download_result:
                return {'status': 'failed', 'error': download_result['error']}
            
            # Create local Stage 3 runner
            runner_path = self.downloader.create_local_stage3_runner(local_output_path)
            if runner_path:
                download_result['local_runner'] = runner_path
            
            return {
                'status': 'completed',
                'download_result': download_result,
                'local_path': local_output_path
            }
            
        except Exception as e:
            logger.error(f"Error downloading Stage 3 output: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _extract_cloud_output_path(self, batch_result: Dict) -> Optional[str]:
        """Extract cloud output path from batch result."""
        try:
            # This would typically come from the batch job configuration
            # For now, we'll construct it based on the environment
            if self.environment == "production":
                return f"s3://wildlife-detection-{self.environment}-{boto3.client('sts').get_caller_identity()['Account']}/output"
            else:
                return f"s3://wildlife-detection-{self.environment}-{boto3.client('sts').get_caller_identity()['Account']}/output"
        except Exception as e:
            logger.error(f"Error extracting cloud output path: {e}")
            return None
    
    def _generate_cost_report(self, batch_result: Dict, download_result: Dict) -> Dict:
        """Generate comprehensive cost report."""
        try:
            # Get cost metrics from batch result
            cost_metrics = batch_result.get('cost_report', {})
            
            # Get download metrics
            download_metrics = download_result.get('download_result', {})
            
            # Calculate total costs
            estimated_hours = cost_metrics.get('processing_time_hours', 1)
            spot_cost = cost_metrics.get('estimated_spot_cost', 0)
            on_demand_cost = cost_metrics.get('estimated_ondemand_cost', 0)
            savings = cost_metrics.get('estimated_savings', 0)
            
            # Calculate download costs (minimal for S3)
            download_size_mb = download_metrics.get('total_size_bytes', 0) / 1024 / 1024
            download_cost = download_size_mb * 0.0004  # S3 download cost per GB
            
            return {
                'pipeline_costs': {
                    'spot_cost': spot_cost,
                    'ondemand_cost': on_demand_cost,
                    'savings': savings,
                    'savings_percentage': (savings / on_demand_cost * 100) if on_demand_cost > 0 else 0
                },
                'download_costs': {
                    'size_mb': download_size_mb,
                    'estimated_cost': download_cost
                },
                'total_costs': {
                    'pipeline_cost': spot_cost,
                    'download_cost': download_cost,
                    'total_cost': spot_cost + download_cost
                },
                'efficiency_metrics': {
                    'jobs_processed': cost_metrics.get('total_jobs', 0),
                    'success_rate': cost_metrics.get('success_rate', 0),
                    'processing_time_hours': estimated_hours,
                    'cost_per_job': (spot_cost + download_cost) / max(cost_metrics.get('total_jobs', 1), 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating cost report: {e}")
            return {'error': str(e)}
    
    def run_local_stage3_analysis(self, local_output_path: str) -> Dict:
        """Run local Stage 3 analysis on downloaded data."""
        try:
            logger.info(f"Running local Stage 3 analysis on {local_output_path}")
            
            # Get summary of downloaded data
            summary = self.downloader.get_stage3_summary(local_output_path)
            
            if 'error' in summary:
                return {'status': 'failed', 'error': summary['error']}
            
            # Run local Stage 3 runner if it exists
            local_path = Path(local_output_path)
            runner_path = local_path / "run_stage3_local.py"
            
            if runner_path.exists():
                logger.info("Running local Stage 3 runner...")
                result = subprocess.run(
                    [sys.executable, str(runner_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(local_path)
                )
                
                if result.returncode == 0:
                    logger.info("✅ Local Stage 3 analysis completed successfully")
                    return {
                        'status': 'completed',
                        'summary': summary,
                        'runner_output': result.stdout,
                        'runner_path': str(runner_path)
                    }
                else:
                    logger.error(f"❌ Local Stage 3 analysis failed: {result.stderr}")
                    return {
                        'status': 'failed',
                        'error': result.stderr,
                        'summary': summary
                    }
            else:
                logger.warning("Local Stage 3 runner not found, showing summary only")
                return {
                    'status': 'completed',
                    'summary': summary,
                    'note': 'Local runner not found'
                }
            
        except Exception as e:
            logger.error(f"Error running local Stage 3 analysis: {e}")
            return {'status': 'failed', 'error': str(e)}


def main():
    """Main CLI for cost-optimized pipeline."""
    parser = argparse.ArgumentParser(description="Cost-Optimized Pipeline Manager")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--environment", default="production", help="Environment name")
    parser.add_argument("--action", required=True,
                       choices=['run-pipeline', 'download-stage3', 'analyze-local', 'status', 'costs'],
                       help="Action to perform")
    parser.add_argument("--input-data", nargs='+', help="Input data paths")
    parser.add_argument("--local-output", help="Local output directory")
    parser.add_argument("--job-type", default="image_processing", help="Job type")
    parser.add_argument("--priority", default="normal", choices=['low', 'normal', 'high'],
                       help="Job priority")
    parser.add_argument("--cloud-path", help="Cloud output path for download")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = CostOptimizedPipeline(args.region, args.environment)
    
    try:
        if args.action == 'run-pipeline':
            if not args.input_data or not args.local_output:
                print("❌ --input-data and --local-output are required for run-pipeline")
                sys.exit(1)
            
            # Run complete cost-optimized pipeline
            result = pipeline.run_cost_optimized_pipeline(
                input_data=args.input_data,
                local_output_path=args.local_output,
                job_type=args.job_type,
                priority=args.priority
            )
            
            # Save results
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
            
            print(f"Pipeline result: {json.dumps(result, indent=2)}")
        
        elif args.action == 'download-stage3':
            if not args.cloud_path or not args.local_output:
                print("❌ --cloud-path and --local-output are required for download-stage3")
                sys.exit(1)
            
            # Download Stage 3 output
            result = pipeline.downloader.download_stage3_output(
                cloud_output_path=args.cloud_path,
                local_output_path=args.local_output
            )
            
            print(f"Download result: {json.dumps(result, indent=2)}")
        
        elif args.action == 'analyze-local':
            if not args.local_output:
                print("❌ --local-output is required for analyze-local")
                sys.exit(1)
            
            # Run local Stage 3 analysis
            result = pipeline.run_local_stage3_analysis(args.local_output)
            print(f"Local analysis result: {json.dumps(result, indent=2)}")
        
        elif args.action == 'status':
            status = pipeline.cost_manager.get_compute_environment_status()
            print(f"Compute Environment Status: {json.dumps(status, indent=2)}")
        
        elif args.action == 'costs':
            metrics = pipeline.cost_manager.get_cost_metrics()
            print(f"Cost Metrics: {json.dumps(metrics, indent=2)}")
    
    except Exception as e:
        logger.error(f"Error executing action {args.action}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
