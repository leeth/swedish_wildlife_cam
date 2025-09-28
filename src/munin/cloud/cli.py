"""
Cloud-optional CLI for wildlife detection pipeline.
"""

from __future__ import annotations

import argparse
import builtins
import contextlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ..logging_config import get_logger
from .config import CloudConfig
from .interfaces import ManifestEntry, Stage2Entry
from .stage3_reporting import Stage3Reporter

# Initialize logger for cloud CLI
logger = get_logger("wildlife_pipeline.cloud.cli")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(description="Cloud-optional wildlife detection pipeline")

    # Global options
    parser.add_argument("--profile", choices=["local", "cloud"], default="local",
                       help="Configuration profile to use")
    parser.add_argument("--config", help="Path to configuration file")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Stage-1 command
    stage1_parser = subparsers.add_parser("stage1", help="Run Stage-1 processing")
    stage1_parser.add_argument("--input", required=True, help="Input prefix (file://, s3://, gs://)")
    stage1_parser.add_argument("--output", required=True, help="Output prefix (file://, s3://, gs://)")
    stage1_parser.add_argument("--model", help="Stage-1 model path")
    stage1_parser.add_argument("--conf-threshold", type=float, help="Confidence threshold")
    stage1_parser.add_argument("--min-rel-area", type=float, help="Minimum relative area")
    stage1_parser.add_argument("--max-rel-area", type=float, help="Maximum relative area")
    stage1_parser.add_argument("--min-aspect", type=float, help="Minimum aspect ratio")
    stage1_parser.add_argument("--max-aspect", type=float, help="Maximum aspect ratio")
    stage1_parser.add_argument("--edge-margin", type=int, help="Edge margin in pixels")
    stage1_parser.add_argument("--crop-padding", type=float, help="Crop padding ratio")

    # Stage-2 command
    stage2_parser = subparsers.add_parser("stage2", help="Run Stage-2 processing")
    stage2_parser.add_argument("--manifest", required=True, help="Stage-1 manifest file")
    stage2_parser.add_argument("--output", required=True, help="Output prefix")
    stage2_parser.add_argument("--model", help="Stage-2 model path")
    stage2_parser.add_argument("--conf-threshold", type=float, help="Confidence threshold")

    # Materialize command
    materialize_parser = subparsers.add_parser("materialize", help="Materialize results to final format")
    materialize_parser.add_argument("--manifest", required=True, help="Stage-1 manifest file")
    materialize_parser.add_argument("--predictions", help="Stage-2 predictions file")
    materialize_parser.add_argument("--output", required=True, help="Output file (CSV/Parquet)")
    materialize_parser.add_argument("--format", choices=["csv", "parquet"], default="parquet")

    # Stage-3 command
    stage3_parser = subparsers.add_parser("stage3", help="Run Stage-3 reporting and compression")
    stage3_parser.add_argument("--manifest", required=True, help="Stage-1 manifest file")
    stage3_parser.add_argument("--predictions", required=True, help="Stage-2 predictions file")
    stage3_parser.add_argument("--output", required=True, help="Output prefix")
    stage3_parser.add_argument("--compression-window", type=int, default=10,
                              help="Compression window in minutes (default: 10)")
    stage3_parser.add_argument("--min-confidence", type=float, default=0.5,
                              help="Minimum confidence for observations (default: 0.5)")
    stage3_parser.add_argument("--min-duration", type=float, default=5.0,
                              help="Minimum duration in seconds (default: 5.0)")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("--output", required=True, help="Output prefix to check")

    # Cost-optimized batch processing command
    batch_parser = subparsers.add_parser("batch", help="Run cost-optimized batch processing")
    batch_parser.add_argument("--input", required=True, help="Input prefix (file://, s3://, gs://)")
    batch_parser.add_argument("--output", required=True, help="Output prefix (file://, s3://, gs://)")
    batch_parser.add_argument("--local-output", help="Local output directory for Stage 3 results")
    batch_parser.add_argument("--model", help="Model path override")
    batch_parser.add_argument("--conf-threshold", type=float, help="Confidence threshold")
    batch_parser.add_argument("--compression-window", type=int, default=10,
                              help="Stage 3 compression window in minutes (default: 10)")
    batch_parser.add_argument("--min-confidence", type=float, default=0.5,
                              help="Minimum confidence for observations (default: 0.5)")
    batch_parser.add_argument("--min-duration", type=float, default=5.0,
                              help="Minimum duration in seconds (default: 5.0)")
    batch_parser.add_argument("--spot-bid-percentage", type=int, default=70,
                              help="Spot instance bid percentage (default: 70)")
    batch_parser.add_argument("--max-vcpus", type=int, default=100,
                              help="Maximum vCPUs for compute environment (default: 100)")
    batch_parser.add_argument("--gpu-required", action="store_true", default=True,
                              help="Require GPU instances (default: True)")
    batch_parser.add_argument("--priority", choices=["low", "normal", "high"], default="normal",
                              help="Job priority (default: normal)")
    batch_parser.add_argument("--download-stage3", action="store_true",
                              help="Download Stage 3 output locally")
    batch_parser.add_argument("--cost-report", action="store_true",
                              help="Generate cost optimization report")

    # Cost optimization management commands
    cost_parser = subparsers.add_parser("cost", help="Cost optimization management")
    cost_subparsers = cost_parser.add_subparsers(dest="cost_command", help="Cost optimization commands")

    # Setup infrastructure
    setup_parser = cost_subparsers.add_parser("setup", help="Setup cost-optimized infrastructure")
    setup_parser.add_argument("--job-count", type=int, default=1, help="Number of jobs to process")
    setup_parser.add_argument("--gpu-required", action="store_true", default=True, help="Require GPU instances")

    # Teardown infrastructure
    cost_subparsers.add_parser("teardown", help="Teardown infrastructure")

    # Status and costs
    cost_subparsers.add_parser("status", help="Check infrastructure status")
    cost_subparsers.add_parser("costs", help="Get cost metrics")

    # Download Stage 3 output
    download_parser = cost_subparsers.add_parser("download-stage3", help="Download Stage 3 output locally")
    download_parser.add_argument("--cloud-path", required=True, help="Cloud output path")
    download_parser.add_argument("--local-path", required=True, help="Local output directory")
    download_parser.add_argument("--summary", action="store_true", help="Show download summary")
    download_parser.add_argument("--create-runner", action="store_true", help="Create local Stage 3 runner")

    return parser


def run_stage1(args, config: CloudConfig) -> list[ManifestEntry]:
    """Run Stage-1 processing."""
    logger.log_stage_start("stage1", profile=config.profile, input=args.input, output=args.output)

    try:
        # Get configuration
        stage1_config = config.get_stage1_config()

        # Override with command line arguments
        if args.model:
            stage1_config['model'] = args.model
        if args.conf_threshold:
            stage1_config['conf_threshold'] = args.conf_threshold
        if args.min_rel_area:
            stage1_config['min_rel_area'] = args.min_rel_area
        if args.max_rel_area:
            stage1_config['max_rel_area'] = args.max_rel_area
        if args.min_aspect:
            stage1_config['min_aspect'] = args.min_aspect
        if args.max_aspect:
            stage1_config['max_aspect'] = args.max_aspect
        if args.edge_margin:
            stage1_config['edge_margin'] = args.edge_margin
        if args.crop_padding:
            stage1_config['crop_padding'] = args.crop_padding

        # Run Stage-1
        manifest_entries = config.runner.run_stage1(args.input, args.output, stage1_config)

        logger.log_stage_complete("stage1", crops_generated=len(manifest_entries))
        logger.info(f"✅ Stage-1 completed: {len(manifest_entries)} crops generated")

        return manifest_entries

    except Exception as e:
        logger.log_stage_error("stage1", e, input=args.input, output=args.output)
        raise


def run_stage2(args, config: CloudConfig) -> list[Stage2Entry]:
    """Run Stage-2 processing."""
    logger.log_stage_start("stage2", profile=config.profile, manifest=args.manifest, output=args.output)

    try:
        # Load manifest entries
        manifest_entries = load_manifest_entries(args.manifest, config)

        if not manifest_entries:
            logger.warning("No manifest entries found", manifest_path=args.manifest)
            return []

        # Get configuration
        stage2_config = config.get_stage2_config()

        # Override with command line arguments
        if args.model:
            stage2_config['model'] = args.model
        if args.conf_threshold:
            stage2_config['conf_threshold'] = args.conf_threshold

        # Run Stage-2
        stage2_entries = config.runner.run_stage2(manifest_entries, args.output, stage2_config)

        logger.log_stage_complete("stage2", predictions_generated=len(stage2_entries))
        logger.info(f"✅ Stage-2 completed: {len(stage2_entries)} predictions generated")

        return stage2_entries

    except Exception as e:
        logger.log_stage_error("stage2", e, manifest=args.manifest, output=args.output)
        raise


def materialize_results(args, config: CloudConfig):
    """Materialize results to final format."""
    print(f"Materializing results with profile: {config.profile}")

    # Load manifest entries
    manifest_entries = load_manifest_entries(args.manifest, config)

    # Load predictions if available
    predictions_entries = []
    if args.predictions:
        predictions_entries = load_predictions_entries(args.predictions, config)

    # Create final results
    results = create_final_results(manifest_entries, predictions_entries)

    # Save results
    save_results(results, args.output, args.format)

    print(f"Results materialized to {args.output}")


def load_manifest_entries(manifest_path: str, config: CloudConfig) -> list[ManifestEntry]:
    """Load manifest entries from storage."""
    from .interfaces import StorageLocation

    manifest_location = StorageLocation.from_url(manifest_path)

    if not config.storage_adapter.exists(manifest_location):
        print(f"Manifest file not found: {manifest_path}")
        return []

    manifest_content = config.storage_adapter.get(manifest_location)
    entries = []

    for line in manifest_content.decode('utf-8').strip().split('\n'):
        if line:
            try:
                entry_data = json.loads(line)
                entries.append(ManifestEntry.from_dict(entry_data))
            except Exception as e:
                print(f"Error parsing manifest line: {e}")
                continue

    return entries


def load_predictions_entries(predictions_path: str, config: CloudConfig) -> list[Stage2Entry]:
    """Load predictions entries from storage."""
    from .interfaces import StorageLocation

    predictions_location = StorageLocation.from_url(predictions_path)

    if not config.storage_adapter.exists(predictions_location):
        print(f"Predictions file not found: {predictions_path}")
        return []

    predictions_content = config.storage_adapter.get(predictions_location)
    entries = []

    for line in predictions_content.decode('utf-8').strip().split('\n'):
        if line:
            try:
                entry_data = json.loads(line)
                entries.append(Stage2Entry.from_dict(entry_data))
            except Exception as e:
                print(f"Error parsing predictions line: {e}")
                continue

    return entries


def create_final_results(manifest_entries: list[ManifestEntry], predictions_entries: list[Stage2Entry]) -> list[dict[str, Any]]:
    """Create final results combining manifest and predictions."""
    # Create lookup for predictions
    predictions_lookup = {entry.crop_path: entry for entry in predictions_entries}

    results = []
    for manifest_entry in manifest_entries:
        result = {
            'source_path': manifest_entry.source_path,
            'camera_id': manifest_entry.camera_id,
            'timestamp': manifest_entry.timestamp,
            'latitude': manifest_entry.latitude,
            'longitude': manifest_entry.longitude,
            'image_width': manifest_entry.image_width,
            'image_height': manifest_entry.image_height,
            'bbox': manifest_entry.bbox,
            'det_score': manifest_entry.det_score,
            'stage1_model': manifest_entry.stage1_model,
            'config_hash': manifest_entry.config_hash,
            'crop_path': manifest_entry.crop_path,
            'stage2_label': None,
            'stage2_confidence': None,
            'auto_ok': None,
            'stage2_model': None
        }

        # Add Stage-2 results if available
        if manifest_entry.crop_path in predictions_lookup:
            prediction = predictions_lookup[manifest_entry.crop_path]
            result.update({
                'stage2_label': prediction.label,
                'stage2_confidence': prediction.confidence,
                'auto_ok': prediction.auto_ok,
                'stage2_model': prediction.stage2_model
            })

        results.append(result)

    return results


def save_results(results: list[dict[str, Any]], output_path: str, format: str):
    """Save results to file."""
    if format == "csv":
        import pandas as pd
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
    elif format == "parquet":
        import pandas as pd
        df = pd.DataFrame(results)
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")


def check_status(args, config: CloudConfig):
    """Check pipeline status."""
    print(f"Checking status for: {args.output}")

    from .interfaces import StorageLocation

    # Check Stage-1 status
    stage1_manifest = StorageLocation.from_url(f"{args.output}/stage1/manifest.jsonl")
    stage1_exists = config.storage_adapter.exists(stage1_manifest)

    # Check Stage-2 status
    stage2_predictions = StorageLocation.from_url(f"{args.output}/stage2/predictions.jsonl")
    stage2_exists = config.storage_adapter.exists(stage2_predictions)

    print(f"Stage-1 manifest: {'✓' if stage1_exists else '✗'}")
    print(f"Stage-2 predictions: {'✓' if stage2_exists else '✗'}")

    if stage1_exists:
        manifest_entries = load_manifest_entries(f"{args.output}/stage1/manifest.jsonl", config)
        print(f"Stage-1 crops: {len(manifest_entries)}")

    if stage2_exists:
        predictions_entries = load_predictions_entries(f"{args.output}/stage2/predictions.jsonl", config)
        print(f"Stage-2 predictions: {len(predictions_entries)}")


def run_stage3(args, config: CloudConfig) -> None:
    """Run Stage-3 reporting and compression."""
    logger.log_stage_start("stage3", profile=config.profile,
                          manifest=args.manifest, predictions=args.predictions, output=args.output)

    try:
        # Load manifest entries
        manifest_entries = load_manifest_entries(args.manifest, config)
        logger.info(f"📋 Loaded {len(manifest_entries)} manifest entries")

        # Load Stage-2 predictions
        predictions_entries = load_predictions_entries(args.predictions, config)
        logger.info(f"🔮 Loaded {len(predictions_entries)} Stage-2 predictions")

        # Initialize Stage-3 reporter
        reporter = Stage3Reporter(
            compression_window_minutes=args.compression_window,
            min_confidence=args.min_confidence,
            min_duration_seconds=args.min_duration
        )

        # Process Stage-2 results
        print("Compressing observations...")
        compressed_observations = reporter.process_stage2_results(predictions_entries, manifest_entries)
        print(f"Compressed to {len(compressed_observations)} observations")

        # Generate report
        report = reporter.generate_report(compressed_observations)
        print(f"Generated report: {report['total_observations']} total observations")

        # Save results
        output_prefix = args.output
        if not output_prefix.endswith('/'):
            output_prefix += '/'

        # Save compressed observations
        observations_path = f"{output_prefix}stage3/compressed_observations.json"
        reporter.save_compressed_observations(compressed_observations, Path(observations_path))

        # Save report
        report_path = f"{output_prefix}stage3/report.json"
        config.storage_adapter.put(
            config.storage_adapter._create_location(report_path),
            json.dumps(report, indent=2).encode('utf-8')
        )

        logger.log_stage_complete("stage3",
                                compressed_observations=len(compressed_observations),
                                species_detected=list(report['species_summary'].keys()),
                                cameras=list(report['camera_summary'].keys()))

        logger.info("✅ Stage-3 completed:")
        logger.info(f"  📊 Compressed observations: {observations_path}")
        logger.info(f"  📈 Report: {report_path}")
        logger.info(f"  🦌 Species detected: {list(report['species_summary'].keys())}")

    except Exception as e:
        logger.log_stage_error("stage3", error=str(e), operation="compression")
        raise


def run_cost_optimized_batch(args, config: CloudConfig):
    """Run cost-optimized batch processing for offline camera data."""
    logger.log_stage_start("cost_optimized_batch", profile=config.profile,
                          input=args.input, output=args.output)

    try:
        # Import cost optimization modules
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "infrastructure"))

        from batch_workflow_manager import BatchWorkflowManager
        from cost_optimization_manager import CostOptimizationManager
        from stage3_output_downloader import Stage3OutputDownloader

        # Initialize cost optimization components
        cost_manager = CostOptimizationManager(region="eu-north-1", environment="production")
        batch_manager = BatchWorkflowManager(region="eu-north-1", environment="production")
        downloader = Stage3OutputDownloader(region="eu-north-1", profile="cloud")

        logger.info("🚀 Starting cost-optimized batch processing for offline camera data")
        logger.info(f"Input: {args.input}")
        logger.info(f"Output: {args.output}")
        logger.info(f"Spot bid percentage: {args.spot_bid_percentage}%")
        logger.info(f"GPU required: {args.gpu_required}")

        # Step 1: Setup cost-optimized infrastructure
        logger.info("Step 1: Setting up cost-optimized infrastructure")
        if not cost_manager.setup_infrastructure(
            job_count=1,  # Will be determined by input data
            gpu_required=args.gpu_required
        ):
            raise Exception("Infrastructure setup failed")

        # Step 2: Run complete pipeline with cost optimization
        logger.info("Step 2: Running complete pipeline with cost optimization")

        # Create batch configuration for offline camera data
        batch_config = {
            'batch_id': f"offline-camera-{int(time.time())}",
            'jobs': [{
                'name': 'offline-camera-processing',
                'parameters': {
                    'input_path': args.input,
                    'output_path': args.output,
                    'model': args.model,
                    'conf_threshold': args.conf_threshold,
                    'compression_window': args.compression_window,
                    'min_confidence': args.min_confidence,
                    'min_duration': args.min_duration,
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

        # Process batch with cost optimization
        batch_result = batch_manager.process_batch(batch_config)

        if batch_result.get('status') != 'completed':
            raise Exception(f"Batch processing failed: {batch_result.get('error', 'Unknown error')}")

        # Step 3: Download Stage 3 output locally if requested
        if args.download_stage3 and args.local_output:
            logger.info("Step 3: Downloading Stage 3 output locally")
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
                runner_path = downloader.create_local_stage3_runner(args.local_output)
                if runner_path:
                    logger.info(f"✅ Local Stage 3 runner created: {runner_path}")

        # Step 4: Generate cost report if requested
        if args.cost_report:
            logger.info("Step 4: Generating cost optimization report")
            cost_metrics = cost_manager.get_cost_metrics()
            logger.info(f"💰 Cost metrics: {json.dumps(cost_metrics, indent=2)}")

        # Step 5: Teardown infrastructure
        logger.info("Step 5: Tearing down infrastructure")
        cost_manager.teardown_infrastructure()

        logger.log_stage_complete("cost_optimized_batch",
                                batch_result=batch_result,
                                cost_optimization=True,
                                spot_instances=True)

        logger.info("✅ Cost-optimized batch processing completed!")
        logger.info(f"📊 Results: {args.output}")
        if args.download_stage3 and args.local_output:
            logger.info(f"📁 Local Stage 3 output: {args.local_output}")

    except Exception as e:
        logger.log_stage_error("cost_optimized_batch", error=str(e),
                              input=args.input, output=args.output)
        # Ensure infrastructure is torn down on error
        with contextlib.suppress(builtins.BaseException):
            cost_manager.teardown_infrastructure()
        raise


def run_cost_management(args, config: CloudConfig):
    """Run cost optimization management commands."""
    try:
        # Import cost optimization modules
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "infrastructure"))

        from cost_optimization_manager import CostOptimizationManager
        from stage3_output_downloader import Stage3OutputDownloader

        # Initialize cost optimization components
        cost_manager = CostOptimizationManager(region="eu-north-1", environment="production")

        if args.cost_command == "setup":
            logger.info("Setting up cost-optimized infrastructure")
            success = cost_manager.setup_infrastructure(
                job_count=args.job_count,
                gpu_required=args.gpu_required
            )
            if success:
                logger.info("✅ Infrastructure setup completed")
            else:
                logger.error("❌ Infrastructure setup failed")

        elif args.cost_command == "teardown":
            logger.info("Tearing down infrastructure")
            success = cost_manager.teardown_infrastructure()
            if success:
                logger.info("✅ Infrastructure teardown completed")
            else:
                logger.error("❌ Infrastructure teardown failed")

        elif args.cost_command == "status":
            status = cost_manager.get_compute_environment_status()
            logger.info(f"Infrastructure status: {json.dumps(status, indent=2)}")

        elif args.cost_command == "costs":
            metrics = cost_manager.get_cost_metrics()
            logger.info(f"Cost metrics: {json.dumps(metrics, indent=2)}")

        elif args.cost_command == "download-stage3":
            logger.info("Downloading Stage 3 output locally")
            downloader = Stage3OutputDownloader(region="eu-north-1", profile="cloud")
            result = downloader.download_stage3_output(
                cloud_output_path=args.cloud_path,
                local_output_path=args.local_path,
                include_observations=True,
                include_report=True
            )

            if 'error' in result:
                logger.error(f"Download failed: {result['error']}")
            else:
                logger.info(f"✅ Stage 3 output downloaded to: {args.local_path}")

                if args.summary:
                    summary = downloader.get_stage3_summary(args.local_path)
                    logger.info(f"Download summary: {json.dumps(summary, indent=2)}")

                if args.create_runner:
                    runner_path = downloader.create_local_stage3_runner(args.local_path)
                    if runner_path:
                        logger.info(f"✅ Local Stage 3 runner created: {runner_path}")

        else:
            logger.error(f"Unknown cost command: {args.cost_command}")

    except Exception as e:
        logger.error(f"Cost management error: {e}")
        raise


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load configuration
    config = CloudConfig(profile=args.profile, config_path=args.config)

    # Execute command
    if args.command == "stage1":
        run_stage1(args, config)
    elif args.command == "stage2":
        run_stage2(args, config)
    elif args.command == "stage3":
        run_stage3(args, config)
    elif args.command == "materialize":
        materialize_results(args, config)
    elif args.command == "status":
        check_status(args, config)
    elif args.command == "batch":
        run_cost_optimized_batch(args, config)
    elif args.command == "cost":
        run_cost_management(args, config)
    else:
        print(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
