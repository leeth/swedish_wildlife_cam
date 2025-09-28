#!/usr/bin/env python3
"""
Odin CLI - The All-Knowing Infrastructure Manager

Odin manages the entire wildlife processing world.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .infrastructure import InfrastructureManager
from .pipeline import PipelineManager
from .local_infrastructure import LocalInfrastructureManager
from .local_pipeline import LocalPipelineManager
from .config import OdinConfig


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


if __name__ == "__main__":
    main()
