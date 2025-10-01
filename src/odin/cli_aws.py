"""
Odin AWS CLI - AWS production commands

This module provides CLI commands for AWS production:
- AWS infrastructure management
- AWS pipeline execution
- Cost optimization
- Batch workflows
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import OdinConfig
from .aws import InfrastructureManager, PipelineManager, CostOptimizationManager


def setup_parser():
    """Setup argument parser for AWS commands."""
    parser = argparse.ArgumentParser(
        description="Odin AWS - AWS production commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m odin.cli_aws infrastructure setup
  python -m odin.cli_aws infrastructure status
  python -m odin.cli_aws pipeline run
  python -m odin.cli_aws cost report
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Infrastructure commands
    infra_parser = subparsers.add_parser('infrastructure', help='Infrastructure management')
    infra_subparsers = infra_parser.add_subparsers(dest='infra_action')

    infra_subparsers.add_parser('setup', help='Setup AWS infrastructure')
    infra_subparsers.add_parser('status', help='Check infrastructure status')
    infra_subparsers.add_parser('teardown', help='Teardown AWS infrastructure')

    # Pipeline commands
    pipeline_parser = subparsers.add_parser('pipeline', help='Pipeline execution')
    pipeline_subparsers = pipeline_parser.add_subparsers(dest='pipeline_action')

    pipeline_subparsers.add_parser('run', help='Run complete pipeline')
    pipeline_subparsers.add_parser('stage1', help='Run stage 1 only')
    pipeline_subparsers.add_parser('stage2', help='Run stage 2 only')
    pipeline_subparsers.add_parser('stage3', help='Run stage 3 only')

    # Cost commands
    cost_parser = subparsers.add_parser('cost', help='Cost management')
    cost_subparsers = cost_parser.add_subparsers(dest='cost_action')

    cost_subparsers.add_parser('report', help='Generate cost report')
    cost_subparsers.add_parser('optimize', help='Optimize costs')

    # Data commands
    data_parser = subparsers.add_parser('data', help='Data management')
    data_subparsers = data_parser.add_subparsers(dest='data_action')

    data_subparsers.add_parser('upload', help='Upload data to S3')
    data_subparsers.add_parser('download', help='Download data from S3')
    data_subparsers.add_parser('list', help='List S3 data')

    return parser


def main():
    """Main CLI entry point for AWS commands."""
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load configuration
    config_path = "conf/profiles/cloud.yaml"
    config = OdinConfig.from_file(config_path)

    try:
        if args.command == 'infrastructure':
            handle_infrastructure_command(args, config)
        elif args.command == 'pipeline':
            handle_pipeline_command(args, config)
        elif args.command == 'cost':
            handle_cost_command(args, config)
        elif args.command == 'data':
            handle_data_command(args, config)
        else:
            parser.print_help()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def handle_infrastructure_command(args, config):
    """Handle infrastructure commands."""
    infra_manager = InfrastructureManager(config)

    if args.infra_action == 'setup':
        print("🏗️ Setting up AWS infrastructure...")
        infra_manager.setup()
        print("✅ AWS infrastructure setup completed!")

    elif args.infra_action == 'status':
        print("📊 Checking AWS infrastructure status...")
        status = infra_manager.get_status()
        print(f"✅ Infrastructure status: {status}")

    elif args.infra_action == 'teardown':
        print("🧹 Tearing down AWS infrastructure...")
        infra_manager.teardown()
        print("✅ AWS infrastructure teardown completed!")

    else:
        print("❌ Unknown infrastructure action")


def handle_pipeline_command(args, config):
    """Handle pipeline commands."""
    pipeline_manager = PipelineManager(config)

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


def handle_cost_command(args, config):
    """Handle cost commands."""
    cost_manager = CostOptimizationManager(config)

    if args.cost_action == 'report':
        print("💰 Generating cost report...")
        report = cost_manager.get_cost_report()
        print(f"✅ Cost report: {report}")

    elif args.cost_action == 'optimize':
        print("🔧 Optimizing costs...")
        cost_manager.optimize_costs()
        print("✅ Cost optimization completed!")

    else:
        print("❌ Unknown cost action")


def handle_data_command(args, config):
    """Handle data commands."""
    print(f"📁 Data command: {args.data_action}")
    # TODO: Implement data management commands
    print("⚠️ Data management not yet implemented")


if __name__ == '__main__':
    main()

