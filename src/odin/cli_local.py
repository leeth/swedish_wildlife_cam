"""
Odin Local CLI - Local development commands

This module provides CLI commands for local development:
- LocalStack management
- Local pipeline execution
- Development utilities
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import OdinConfig
from .local import LocalInfrastructureManager, LocalPipelineManager


def setup_parser():
    """Setup argument parser for local commands."""
    parser = argparse.ArgumentParser(
        description="Odin Local - Local development commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m odin.cli_local infrastructure setup
  python -m odin.cli_local infrastructure status
  python -m odin.cli_local pipeline run
  python -m odin.cli_local pipeline stage1
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Infrastructure commands
    infra_parser = subparsers.add_parser('infrastructure', help='Infrastructure management')
    infra_subparsers = infra_parser.add_subparsers(dest='infra_action')
    
    infra_subparsers.add_parser('setup', help='Setup local infrastructure')
    infra_subparsers.add_parser('status', help='Check infrastructure status')
    infra_subparsers.add_parser('teardown', help='Teardown local infrastructure')
    
    # Pipeline commands
    pipeline_parser = subparsers.add_parser('pipeline', help='Pipeline execution')
    pipeline_subparsers = pipeline_parser.add_subparsers(dest='pipeline_action')
    
    pipeline_subparsers.add_parser('run', help='Run complete pipeline')
    pipeline_subparsers.add_parser('stage1', help='Run stage 1 only')
    pipeline_subparsers.add_parser('stage2', help='Run stage 2 only')
    pipeline_subparsers.add_parser('stage3', help='Run stage 3 only')
    
    # Data commands
    data_parser = subparsers.add_parser('data', help='Data management')
    data_subparsers = data_parser.add_subparsers(dest='data_action')
    
    data_subparsers.add_parser('upload', help='Upload data to local storage')
    data_subparsers.add_parser('download', help='Download data from local storage')
    data_subparsers.add_parser('list', help='List local data')
    
    return parser


def main():
    """Main CLI entry point for local commands."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config_path = "conf/profiles/local.yaml"
    config = OdinConfig.from_file(config_path)
    
    try:
        if args.command == 'infrastructure':
            handle_infrastructure_command(args, config)
        elif args.command == 'pipeline':
            handle_pipeline_command(args, config)
        elif args.command == 'data':
            handle_data_command(args, config)
        else:
            parser.print_help()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def handle_infrastructure_command(args, config):
    """Handle infrastructure commands."""
    infra_manager = LocalInfrastructureManager(config)
    
    if args.infra_action == 'setup':
        print("🏗️ Setting up local infrastructure...")
        infra_manager.setup()
        print("✅ Local infrastructure setup completed!")
        
    elif args.infra_action == 'status':
        print("📊 Checking local infrastructure status...")
        status = infra_manager.get_status()
        print(f"✅ Infrastructure status: {status}")
        
    elif args.infra_action == 'teardown':
        print("🧹 Tearing down local infrastructure...")
        infra_manager.teardown()
        print("✅ Local infrastructure teardown completed!")
        
    else:
        print("❌ Unknown infrastructure action")


def handle_pipeline_command(args, config):
    """Handle pipeline commands."""
    pipeline_manager = LocalPipelineManager(config)
    
    if args.pipeline_action == 'run':
        print("🚀 Running complete pipeline...")
        pipeline_manager.run_complete_pipeline()
        print("✅ Pipeline execution completed!")
        
    elif args.pipeline_action == 'stage1':
        print("🎬 Running stage 1...")
        pipeline_manager.run_stage1()
        print("✅ Stage 1 completed!")
        
    elif args.pipeline_action == 'stage2':
        print("🎬 Running stage 2...")
        pipeline_manager.run_stage2()
        print("✅ Stage 2 completed!")
        
    elif args.pipeline_action == 'stage3':
        print("🎬 Running stage 3...")
        pipeline_manager.run_stage3()
        print("✅ Stage 3 completed!")
        
    else:
        print("❌ Unknown pipeline action")


def handle_data_command(args, config):
    """Handle data commands."""
    print(f"📁 Data command: {args.data_action}")
    # TODO: Implement data management commands
    print("⚠️ Data management not yet implemented")


if __name__ == '__main__':
    main()

