"""
Munin CLI - The Memory Keeper

Munin brings memories home by processing wildlife detection data.
"""

import click
from pathlib import Path
from typing import Optional

from .data_ingestion import OptimizedFileWalker, OptimizedExifExtractor
from .wildlife_detector import WildlifeDetector
from .swedish_wildlife_detector import SwedishWildlifeDetector
from .video_processor import OptimizedVideoProcessor
from .detection_filter import filter_bboxes, crop_with_padding
from .classification_engine import YOLOClassifier
from .storage_manager import WildlifeDatabase
from .model_optimizer import ModelOptimizer


@click.group()
@click.version_option()
def cli():
    """Munin - The Memory Keeper
    
    Munin brings memories home by processing wildlife detection data.
    """
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--extensions', default='jpg,jpeg,png,tiff,webp,mp4,avi,mov', 
              help='File extensions to process')
@click.option('--max-depth', type=int, help='Maximum directory depth')
@click.option('--workers', type=int, help='Number of parallel workers')
@click.option('--extract-exif', is_flag=True, help='Extract EXIF data')
@click.option('--compute-hashes', is_flag=True, help='Compute file hashes')
def ingest(input_path: str, output_path: str, extensions: str, 
           max_depth: Optional[int], workers: Optional[int], 
           extract_exif: bool, compute_hashes: bool):
    """Ingest and process wildlife data files.
    
    INPUT_PATH: Directory containing images and videos
    OUTPUT_PATH: Directory to save processed data
    """
    click.echo("🐦‍⬛ Munin - The Memory Keeper")
    click.echo("Bringing memories home...")
    
    # Initialize file walker
    walker = OptimizedFileWalker(max_workers=workers)
    extensions_list = [ext.strip() for ext in extensions.split(',')]
    
    # Walk files
    files = walker.walk_files_parallel(
        root_path=Path(input_path),
        extensions=extensions_list,
        max_depth=max_depth
    )
    
    click.echo(f"📁 Found {len(files)} files to process")
    
    # Extract EXIF if requested
    if extract_exif:
        image_files = [f for f in files if f.is_image]
        if image_files:
            extractor = OptimizedExifExtractor()
            exif_results = extractor.extract_exif_batch([f.path for f in image_files])
            click.echo(f"📸 Extracted EXIF from {len(exif_results)} images")
    
    # Compute hashes if requested
    if compute_hashes:
        processor = OptimizedImageProcessor()
        hashes = processor.compute_hashes_parallel([f.path for f in files])
        click.echo(f"🔐 Computed hashes for {len(hashes)} files")
    
    click.echo("✅ Data ingestion completed!")


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--model', default='yolov8n.pt', help='Model path or name')
@click.option('--confidence', default=0.3, help='Detection confidence threshold')
@click.option('--min-area', default=0.003, help='Minimum relative area')
@click.option('--max-area', default=0.8, help='Maximum relative area')
@click.option('--edge-margin', default=12, help='Edge margin in pixels')
@click.option('--crop-padding', default=0.15, help='Crop padding ratio')
@click.option('--save-crops', is_flag=True, help='Save cropped images')
@click.option('--workers', type=int, help='Number of parallel workers')
def stage1(input_path: str, output_path: str, model: str, confidence: float,
           min_area: float, max_area: float, edge_margin: int, 
           crop_padding: float, save_crops: bool, workers: Optional[int]):
    """Stage 1: Detect wildlife and crop regions of interest.
    
    INPUT_PATH: Directory containing images and videos
    OUTPUT_PATH: Directory to save results
    """
    click.echo("🐦‍⬛ Munin Stage 1 - Detection")
    click.echo("Detecting wildlife and cropping regions...")
    
    # Initialize detector
    if model in ['megadetector', 'md', 'mega', 'swedish']:
        detector = SwedishWildlifeDetector()
    else:
        detector = WildlifeDetector(model)
    
    # Process files
    # TODO: Implement stage1 processing logic
    
    click.echo("✅ Stage 1 detection completed!")


@cli.command()
@click.argument('manifest_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--model', default='yolov8n-cls.pt', help='Classification model path')
@click.option('--confidence', default=0.5, help='Classification confidence threshold')
@click.option('--workers', type=int, help='Number of parallel workers')
def stage2(manifest_path: str, output_path: str, model: str, 
           confidence: float, workers: Optional[int]):
    """Stage 2: Classify detected wildlife.
    
    MANIFEST_PATH: Path to Stage 1 manifest file
    OUTPUT_PATH: Directory to save results
    """
    click.echo("🐦‍⬛ Munin Stage 2 - Classification")
    click.echo("Classifying detected wildlife...")
    
    # Initialize classifier
    classifier = YOLOClassifier(model, confidence)
    
    # Process manifest
    # TODO: Implement stage2 processing logic
    
    click.echo("✅ Stage 2 classification completed!")


@cli.command()
@click.argument('manifest_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--format', default='parquet', help='Output format (parquet, csv)')
@click.option('--table', default='observations', help='Table name for database')
def materialize(manifest_path: str, output_path: str, format: str, table: str):
    """Materialize results to final output format.
    
    MANIFEST_PATH: Path to Stage 1 manifest file
    OUTPUT_PATH: Path to save final results
    """
    click.echo("🐦‍⬛ Munin - Materialization")
    click.echo("Materializing results...")
    
    # Initialize storage manager
    storage = WildlifeDatabase()
    
    # Process manifest
    # TODO: Implement materialization logic
    
    click.echo("✅ Materialization completed!")


@cli.command()
@click.argument('video_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--interval', default=0.3, help='Frame sampling interval (seconds)')
@click.option('--max-frames', type=int, help='Maximum frames to extract')
@click.option('--batch-size', type=int, default=32, help='Batch size for processing')
@click.option('--gpu', is_flag=True, help='Enable GPU acceleration')
@click.option('--workers', type=int, help='Number of parallel workers')
def video(video_path: str, output_path: str, interval: float, 
          max_frames: Optional[int], batch_size: int, gpu: bool, 
          workers: Optional[int]):
    """Process video files for wildlife detection.
    
    VIDEO_PATH: Path to video file
    OUTPUT_PATH: Directory to save results
    """
    click.echo("🐦‍⬛ Munin - Video Processing")
    click.echo("Processing video for wildlife detection...")
    
    # Initialize video processor
    processor = OptimizedVideoProcessor()
    
    # Process video
    # TODO: Implement video processing logic
    
    click.echo("✅ Video processing completed!")


@cli.command()
@click.argument('model_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--format', default='onnx', help='Export format (onnx, tensorrt)')
@click.option('--precision', default='fp16', help='Precision (fp32, fp16, int8)')
@click.option('--batch-size', type=int, default=32, help='Batch size for optimization')
@click.option('--benchmark', is_flag=True, help='Run performance benchmark')
def optimize(model_path: str, output_path: str, format: str, 
             precision: str, batch_size: int, benchmark: bool):
    """Optimize models for high-performance inference.
    
    MODEL_PATH: Path to model file
    OUTPUT_PATH: Directory to save optimized model
    """
    click.echo("🐦‍⬛ Munin - Model Optimization")
    click.echo("Optimizing model for high-performance inference...")
    
    # Initialize optimizer
    optimizer = ModelOptimizer(model_path)
    
    # Optimize model
    # TODO: Implement model optimization logic
    
    click.echo("✅ Model optimization completed!")


if __name__ == '__main__':
    cli()
