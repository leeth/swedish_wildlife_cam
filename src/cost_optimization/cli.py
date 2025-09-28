"""
Cost Optimization CLI

This module provides a unified CLI for cost optimization features that can be used
by both Munin and Hugin for offline camera batch processing.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from .config import CostOptimizationConfig
from .manager import CostOptimizationManager
from .batch_workflow import BatchWorkflowManager
from .stage3_downloader import Stage3OutputDownloader

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser for cost optimization."""
    parser = argparse.ArgumentParser(description="Cost Optimization CLI for Wildlife Pipeline")
    
    # Global options
    parser.add_argument("--config", help="Path to cost optimization configuration file")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--environment", default="production", help="Environment name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Batch processing command
    batch_parser = subparsers.add_parser("batch", help="Run cost-optimized batch processing")
    batch_parser.add_argument("--input", required=True, help="Input path (file://, s3://, gs://)")
    batch_parser.add_argument("--output", required=True, help="Output path (file://, s3://, gs://)")
    batch_parser.add_argument("--local-output", help="Local output directory for Stage 3 results")
    batch_parser.add_argument("--job-count", type=int, default=1, help="Number of jobs to process")
    batch_parser.add_argument("--gpu-required", action="store_true", default=True, help="Require GPU instances")
    batch_parser.add_argument("--priority", choices=["low", "normal", "high"], default="normal", help="Job priority")
    batch_parser.add_argument("--spot-bid-percentage", type=int, default=70, help="Spot bid percentage")
    batch_parser.add_argument("--max-vcpus", type=int, default=100, help="Maximum vCPUs")
    batch_parser.add_argument("--download-stage3", action="store_true", help="Download Stage 3 output locally")
    batch_parser.add_argument("--cost-report", action="store_true", help="Generate cost optimization report")
    
    # Infrastructure management commands
    infra_parser = subparsers.add_parser("infra", help="Infrastructure management")
    infra_subparsers = infra_parser.add_subparsers(dest="infra_command", help="Infrastructure commands")
    
    # Setup infrastructure
    setup_parser = infra_subparsers.add_parser("setup", help="Setup cost-optimized infrastructure")
    setup_parser.add_argument("--job-count", type=int, default=1, help="Number of jobs to process")
    setup_parser.add_argument("--gpu-required", action="store_true", default=True, help="Require GPU instances")
    
    # Teardown infrastructure
    teardown_parser = infra_subparsers.add_parser("teardown", help="Teardown infrastructure")
    
    # Status and costs
    status_parser = infra_subparsers.add_parser("status", help="Check infrastructure status")
    costs_parser = infra_subparsers.add_parser("costs", help="Get cost metrics")
    
    # Stage 3 management commands
    stage3_parser = subparsers.add_parser("stage3", help="Stage 3 output management")
    stage3_subparsers = stage3_parser.add_subparsers(dest="stage3_command", help="Stage 3 commands")
    
    # Download Stage 3 output
    download_parser = stage3_subparsers.add_parser("download", help="Download Stage 3 output locally")
    download_parser.add_argument("--cloud-path", required=True, help="Cloud output path")
    download_parser.add_argument("--local-path", required=True, help="Local output directory")
    download_parser.add_argument("--summary", action="store_true", help="Show download summary")
    download_parser.add_argument("--create-runner", action="store_true", help="Create local Stage 3 runner")
    
    # Analyze local Stage 3 data
    analyze_parser = stage3_subparsers.add_parser("analyze", help="Analyze local Stage 3 data")
    analyze_parser.add_argument("--local-path", required=True, help="Local output directory")
    
    return parser


def load_config(args) -> CostOptimizationConfig:
    """Load cost optimization configuration."""
    if args.config:
        return CostOptimizationConfig.from_file(args.config)
    else:
        # Create default configuration
        config = CostOptimizationConfig(
            region=args.region,
            environment=args.environment
        )
        return config


def run_batch_processing(args, config: CostOptimizationConfig):
    """Run cost-optimized batch processing."""
    try:
        logger.info("🚀 Starting cost-optimized batch processing")
        logger.info(f"Input: {args.input}")
        logger.info(f"Output: {args.output}")
        logger.info(f"Job count: {args.job_count}")
        logger.info(f"GPU required: {args.gpu_required}")
        logger.info(f"Priority: {args.priority}")
        
        # Update config with command line arguments
        config.update(
            spot_bid_percentage=args.spot_bid_percentage,
            max_vcpus=args.max_vcpus,
            gpu_required=args.gpu_required,
            download_stage3=args.download_stage3
        )
        
        # Initialize components
        cost_manager = CostOptimizationManager(config)
        batch_manager = BatchWorkflowManager(config)
        downloader = Stage3OutputDownloader(config)
        
        # Create batch configuration
        batch_config = {
            'batch_id': f"offline-camera-{int(time.time())}",
            'jobs': [{
                'name': 'offline-camera-processing',
                'parameters': {
                    'input_path': args.input,
                    'output_path': args.output,
                    'cost_optimization': 'enabled',
                    'spot_instance_preferred': 'true',
                    'fallback_to_ondemand': 'true'
                },
                'gpu_required': args.gpu_required,
                'priority': args.priority
            }],
            'gpu_required': args.gpu_required,
            'max_parallel_jobs': 1,
            'created_at': datetime.now().isoformat()
        }
        
        # Process batch
        batch_result = batch_manager.process_batch(batch_config)
        
        if batch_result.get('status') != 'completed':
            logger.error(f"Batch processing failed: {batch_result.get('error', 'Unknown error')}")
            return False
        
        # Download Stage 3 output if requested
        if args.download_stage3 and args.local_output:
            logger.info("Downloading Stage 3 output locally")
            download_result = downloader.download_stage3_output(
                cloud_output_path=args.output,
                local_output_path=args.local_output,
                include_observations=True,
                include_report=True
            )
            
            if 'error' in download_result:
                logger.warning(f"Stage 3 download failed: {download_result['error']}")
            else:
                logger.info(f"✅ Stage 3 output downloaded to: {args.local_output}")
                
                # Create local Stage 3 runner
                if config.create_local_runner:
                    runner_path = downloader.create_local_stage3_runner(args.local_output)
                    if runner_path:
                        logger.info(f"✅ Local Stage 3 runner created: {runner_path}")
        
        # Generate cost report if requested
        if args.cost_report:
            logger.info("Generating cost optimization report")
            cost_metrics = cost_manager.get_cost_metrics()
            logger.info(f"💰 Cost metrics: {json.dumps(cost_metrics, indent=2)}")
        
        logger.info("✅ Cost-optimized batch processing completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return False


def run_infrastructure_management(args, config: CostOptimizationConfig):
    """Run infrastructure management commands."""
    try:
        cost_manager = CostOptimizationManager(config)
        
        if args.infra_command == "setup":
            logger.info("Setting up cost-optimized infrastructure")
            success = cost_manager.setup_infrastructure(
                job_count=args.job_count,
                gpu_required=args.gpu_required
            )
            if success:
                logger.info("✅ Infrastructure setup completed")
            else:
                logger.error("❌ Infrastructure setup failed")
            return success
        
        elif args.infra_command == "teardown":
            logger.info("Tearing down infrastructure")
            success = cost_manager.teardown_infrastructure()
            if success:
                logger.info("✅ Infrastructure teardown completed")
            else:
                logger.error("❌ Infrastructure teardown failed")
            return success
        
        elif args.infra_command == "status":
            status = cost_manager.get_compute_environment_status()
            logger.info(f"Infrastructure status: {json.dumps(status, indent=2)}")
            return True
        
        elif args.infra_command == "costs":
            metrics = cost_manager.get_cost_metrics()
            logger.info(f"Cost metrics: {json.dumps(metrics, indent=2)}")
            return True
        
        else:
            logger.error(f"Unknown infrastructure command: {args.infra_command}")
            return False
    
    except Exception as e:
        logger.error(f"Error in infrastructure management: {e}")
        return False


def run_stage3_management(args, config: CostOptimizationConfig):
    """Run Stage 3 management commands."""
    try:
        downloader = Stage3OutputDownloader(config)
        
        if args.stage3_command == "download":
            logger.info("Downloading Stage 3 output locally")
            result = downloader.download_stage3_output(
                cloud_output_path=args.cloud_path,
                local_output_path=args.local_path,
                include_observations=True,
                include_report=True
            )
            
            if 'error' in result:
                logger.error(f"Download failed: {result['error']}")
                return False
            else:
                logger.info(f"✅ Stage 3 output downloaded to: {args.local_path}")
                
                if args.summary:
                    summary = downloader.get_stage3_summary(args.local_path)
                    logger.info(f"Download summary: {json.dumps(summary, indent=2)}")
                
                if args.create_runner:
                    runner_path = downloader.create_local_stage3_runner(args.local_path)
                    if runner_path:
                        logger.info(f"✅ Local Stage 3 runner created: {runner_path}")
                return True
        
        elif args.stage3_command == "analyze":
            logger.info(f"Analyzing local Stage 3 data: {args.local_path}")
            summary = downloader.get_stage3_summary(args.local_path)
            
            if 'error' in summary:
                logger.error(f"Analysis failed: {summary['error']}")
                return False
            else:
                logger.info(f"Stage 3 analysis: {json.dumps(summary, indent=2)}")
                return True
        
        else:
            logger.error(f"Unknown Stage 3 command: {args.stage3_command}")
            return False
    
    except Exception as e:
        logger.error(f"Error in Stage 3 management: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = load_config(args)
    
    # Execute command
    success = False
    
    if args.command == "batch":
        success = run_batch_processing(args, config)
    elif args.command == "infra":
        success = run_infrastructure_management(args, config)
    elif args.command == "stage3":
        success = run_stage3_management(args, config)
    else:
        logger.error(f"Unknown command: {args.command}")
        return
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
