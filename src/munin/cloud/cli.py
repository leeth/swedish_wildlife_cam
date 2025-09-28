"""
Cloud-optional CLI for wildlife detection pipeline.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json

from .config import CloudConfig
from .interfaces import ManifestEntry, Stage2Entry
from .stage3_reporting import Stage3Reporter
from ..logging_config import get_logger

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
    
    return parser


def run_stage1(args, config: CloudConfig) -> List[ManifestEntry]:
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


def run_stage2(args, config: CloudConfig) -> List[Stage2Entry]:
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


def load_manifest_entries(manifest_path: str, config: CloudConfig) -> List[ManifestEntry]:
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


def load_predictions_entries(predictions_path: str, config: CloudConfig) -> List[Stage2Entry]:
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


def create_final_results(manifest_entries: List[ManifestEntry], predictions_entries: List[Stage2Entry]) -> List[Dict[str, Any]]:
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


def save_results(results: List[Dict[str, Any]], output_path: str, format: str):
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
        
        logger.info(f"✅ Stage-3 completed:")
        logger.info(f"  📊 Compressed observations: {observations_path}")
        logger.info(f"  📈 Report: {report_path}")
        logger.info(f"  🦌 Species detected: {list(report['species_summary'].keys())}")
    
    except Exception as e:
        logger.log_stage_error("stage3", error=str(e), operation="compression")
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
    else:
        print(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
