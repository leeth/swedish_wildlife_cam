#!/usr/bin/env python3
"""
Odin CLI - The All-Knowing Infrastructure Manager

Odin manages the entire wildlife processing world.
"""

import argparse
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .infrastructure import InfrastructureManager
from .pipeline import PipelineManager
from .local_infrastructure import LocalInfrastructureManager
from .local_pipeline import LocalPipelineManager
from .config import OdinConfig
from .manager import CostOptimizationManager
from .batch_workflow import BatchWorkflowManager
from .stage3_downloader import Stage3OutputDownloader


def main():
    """Main CLI entry point for Odin."""
    parser = argparse.ArgumentParser(
        description="Odin - The All-Knowing Infrastructure Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  odin setup                    # Setup infrastructure
  odin teardown                # Teardown infrastructure
  odin status                  # Check infrastructure status
  odin pipeline run           # Run complete pipeline
  odin pipeline stage1         # Run stage 1 only
  odin pipeline stage2         # Run stage 2 only
  odin pipeline stage3         # Run stage 3 only
  odin cost report             # Generate cost report
  odin cost optimize           # Optimize costs
        """
    )
    
    parser.add_argument(
        "--config", 
        type=str, 
        default="odin.yaml",
        help="Path to Odin configuration file (default: odin.yaml)"
    )
    
    parser.add_argument(
        "--region",
        type=str,
        help="AWS region (overrides config)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Main commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Infrastructure commands
    infra_parser = subparsers.add_parser("infrastructure", aliases=["infra"], help="Infrastructure management")
    infra_subparsers = infra_parser.add_subparsers(dest="infra_command")
    
    infra_subparsers.add_parser("setup", help="Setup infrastructure")
    infra_subparsers.add_parser("teardown", help="Teardown infrastructure")
    infra_subparsers.add_parser("status", help="Check infrastructure status")
    infra_subparsers.add_parser("scale-up", help="Scale up infrastructure")
    infra_subparsers.add_parser("scale-down", help="Scale down infrastructure")
    
    # Pipeline commands
    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline management")
    pipeline_subparsers = pipeline_parser.add_subparsers(dest="pipeline_command")
    
    pipeline_subparsers.add_parser("run", help="Run complete pipeline")
    pipeline_subparsers.add_parser("stage1", help="Run stage 1 (manifest)")
    pipeline_subparsers.add_parser("stage2", help="Run stage 2 (detection)")
    pipeline_subparsers.add_parser("stage3", help="Run stage 3 (reporting)")
    pipeline_subparsers.add_parser("status", help="Check pipeline status")
    
    # Cost commands
    cost_parser = subparsers.add_parser("cost", help="Cost management")
    cost_subparsers = cost_parser.add_subparsers(dest="cost_command")
    
    cost_subparsers.add_parser("report", help="Generate cost report")
    cost_subparsers.add_parser("optimize", help="Optimize costs")
    cost_subparsers.add_parser("monitor", help="Monitor costs")
    
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
    
    # Data commands
    data_parser = subparsers.add_parser("data", help="Data management")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    
    data_subparsers.add_parser("upload", help="Upload data to S3")
    data_subparsers.add_parser("download", help="Download data from S3")
    data_subparsers.add_parser("list", help="List data in S3")
    data_subparsers.add_parser("cleanup", help="Cleanup data")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    config = OdinConfig(config_path)
    
    # Override region if specified
    if args.region:
        config.set_region(args.region)
    
    # Initialize managers based on provider
    provider = config.get_provider()
    
    if provider == 'local':
        infra_manager = LocalInfrastructureManager(config)
        pipeline_manager = LocalPipelineManager(config)
    else:
        infra_manager = InfrastructureManager(config)
        pipeline_manager = PipelineManager(config)
    
    try:
        # Route commands
        if args.command in ["infrastructure", "infra"]:
            handle_infrastructure_command(infra_manager, args.infra_command, args.verbose)
        elif args.command == "pipeline":
            handle_pipeline_command(pipeline_manager, args.pipeline_command, args.verbose)
        elif args.command == "cost":
            handle_cost_command(infra_manager, args.cost_command, args.verbose)
        elif args.command == "batch":
            handle_batch_command(args, config, args.verbose)
        elif args.command == "stage3":
            handle_stage3_command(args, config, args.verbose)
        elif args.command == "data":
            handle_data_command(infra_manager, args.data_command, args.verbose)
        else:
            print(f"❌ Unknown command: {args.command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def handle_infrastructure_command(infra_manager: InfrastructureManager, command: str, verbose: bool):
    """Handle infrastructure commands."""
    if command == "setup":
        print("🏗️ Setting up infrastructure...")
        infra_manager.setup()
        print("✅ Infrastructure setup complete!")
    elif command == "teardown":
        print("🗑️ Tearing down infrastructure...")
        infra_manager.teardown()
        print("✅ Infrastructure teardown complete!")
    elif command == "status":
        print("📊 Checking infrastructure status...")
        status = infra_manager.get_status()
        print(f"Status: {status}")
    elif command == "scale-up":
        print("📈 Scaling up infrastructure...")
        infra_manager.scale_up()
        print("✅ Infrastructure scaled up!")
    elif command == "scale-down":
        print("📉 Scaling down infrastructure...")
        infra_manager.scale_down()
        print("✅ Infrastructure scaled down!")
    else:
        print(f"❌ Unknown infrastructure command: {command}")


def handle_pipeline_command(pipeline_manager: PipelineManager, command: str, verbose: bool):
    """Handle pipeline commands."""
    if command == "run":
        print("🚀 Running complete pipeline...")
        pipeline_manager.run_complete_pipeline()
        print("✅ Pipeline complete!")
    elif command == "stage1":
        print("📋 Running stage 1 (manifest)...")
        pipeline_manager.run_stage1()
        print("✅ Stage 1 complete!")
    elif command == "stage2":
        print("🔍 Running stage 2 (detection)...")
        pipeline_manager.run_stage2()
        print("✅ Stage 2 complete!")
    elif command == "stage3":
        print("📊 Running stage 3 (reporting)...")
        pipeline_manager.run_stage3()
        print("✅ Stage 3 complete!")
    elif command == "status":
        print("📊 Checking pipeline status...")
        status = pipeline_manager.get_status()
        print(f"Status: {status}")
    else:
        print(f"❌ Unknown pipeline command: {command}")


def handle_cost_command(infra_manager: InfrastructureManager, command: str, verbose: bool):
    """Handle cost commands."""
    if command == "report":
        print("💰 Generating cost report...")
        infra_manager.generate_cost_report()
        print("✅ Cost report generated!")
    elif command == "optimize":
        print("⚡ Optimizing costs...")
        infra_manager.optimize_costs()
        print("✅ Costs optimized!")
    elif command == "monitor":
        print("📊 Monitoring costs...")
        infra_manager.monitor_costs()
        print("✅ Cost monitoring started!")
    else:
        print(f"❌ Unknown cost command: {command}")


def handle_data_command(infra_manager: InfrastructureManager, command: str, verbose: bool):
    """Handle data commands."""
    if command == "upload":
        print("📤 Uploading data...")
        infra_manager.upload_data()
        print("✅ Data uploaded!")
    elif command == "download":
        print("📥 Downloading data...")
        infra_manager.download_data()
        print("✅ Data downloaded!")
    elif command == "list":
        print("📋 Listing data...")
        infra_manager.list_data()
        print("✅ Data listed!")
    elif command == "cleanup":
        print("🧹 Cleaning up data...")
        infra_manager.cleanup_data()
        print("✅ Data cleaned up!")
    else:
        print(f"❌ Unknown data command: {command}")


def handle_batch_command(args, config, verbose: bool):
    """Handle batch processing commands."""
    try:
        print("🚀 Starting cost-optimized batch processing")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Job count: {args.job_count}")
        print(f"GPU required: {args.gpu_required}")
        print(f"Priority: {args.priority}")
        
        # Initialize cost optimization components
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
            print(f"❌ Batch processing failed: {batch_result.get('error', 'Unknown error')}")
            return False
        
        # Download Stage 3 output if requested
        if args.download_stage3 and args.local_output:
            print("📥 Downloading Stage 3 output locally")
            download_result = downloader.download_stage3_output(
                cloud_output_path=args.output,
                local_output_path=args.local_output,
                include_observations=True,
                include_report=True
            )
            
            if 'error' in download_result:
                print(f"⚠️ Stage 3 download failed: {download_result['error']}")
            else:
                print(f"✅ Stage 3 output downloaded to: {args.local_output}")
        
        # Generate cost report if requested
        if args.cost_report:
            print("💰 Generating cost optimization report")
            cost_metrics = cost_manager.get_cost_metrics()
            print(f"Cost metrics: {json.dumps(cost_metrics, indent=2)}")
        
        print("✅ Cost-optimized batch processing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in batch processing: {e}")
        return False


def handle_stage3_command(args, config, verbose: bool):
    """Handle Stage 3 management commands."""
    try:
        downloader = Stage3OutputDownloader(config)
        
        if args.stage3_command == "download":
            print("📥 Downloading Stage 3 output locally")
            result = downloader.download_stage3_output(
                cloud_output_path=args.cloud_path,
                local_output_path=args.local_path,
                include_observations=True,
                include_report=True
            )
            
            if 'error' in result:
                print(f"❌ Download failed: {result['error']}")
                return False
            else:
                print(f"✅ Stage 3 output downloaded to: {args.local_path}")
                
                if args.summary:
                    summary = downloader.get_stage3_summary(args.local_path)
                    print(f"Download summary: {json.dumps(summary, indent=2)}")
                
                if args.create_runner:
                    runner_path = downloader.create_local_stage3_runner(args.local_path)
                    if runner_path:
                        print(f"✅ Local Stage 3 runner created: {runner_path}")
                return True
        
        elif args.stage3_command == "analyze":
            print(f"🔍 Analyzing local Stage 3 data: {args.local_path}")
            summary = downloader.get_stage3_summary(args.local_path)
            
            if 'error' in summary:
                print(f"❌ Analysis failed: {summary['error']}")
                return False
            else:
                print(f"Stage 3 analysis: {json.dumps(summary, indent=2)}")
                return True
        
        else:
            print(f"❌ Unknown Stage 3 command: {args.stage3_command}")
            return False
    
    except Exception as e:
        print(f"❌ Error in Stage 3 management: {e}")
        return False


if __name__ == "__main__":
    main()
