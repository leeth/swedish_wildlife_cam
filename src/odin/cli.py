"""
Odin CLI - All-Father Infrastructure Management

This module provides the main CLI interface for Odin.
It dispatches commands to either local or AWS implementations.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Main CLI entry point for Odin."""
    parser = argparse.ArgumentParser(
        description="Odin - All-Father Infrastructure Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m odin.cli local infrastructure setup
  python -m odin.cli local pipeline run
  python -m odin.cli aws infrastructure setup
  python -m odin.cli aws pipeline run
  python -m odin.cli aws cost report
        """
    )
    
    subparsers = parser.add_subparsers(dest='environment', help='Environment to use')
    
    # Local environment
    local_parser = subparsers.add_parser('local', help='Local development commands')
    local_parser.add_argument('command', nargs='*', help='Local command to execute')
    
    # AWS environment
    aws_parser = subparsers.add_parser('aws', help='AWS production commands')
    aws_parser.add_argument('command', nargs='*', help='AWS command to execute')

    args = parser.parse_args()

    if not args.environment:
        parser.print_help()
        return
    
    try:
        if args.environment == 'local':
            # Import and run local CLI
            from odin.cli_local import main as local_main
            # Reconstruct sys.argv for local CLI
            sys.argv = ['odin.cli_local'] + args.command
            local_main()
            
        elif args.environment == 'aws':
            # Import and run AWS CLI
            from odin.cli_aws import main as aws_main
            # Reconstruct sys.argv for AWS CLI
            sys.argv = ['odin.cli_aws'] + args.command
            aws_main()
            
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()