#!/usr/bin/env python3
"""
Stage 3 Output Downloader

This script downloads Stage 3 output from cloud storage to local filesystem:
- Downloads compressed observations (compressed_observations.json)
- Downloads report (report.json)
- Supports both S3 and local storage
- Implements cost optimization by downloading only when needed
"""

import boto3
import json
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stage3OutputDownloader:
    """Downloads Stage 3 output from cloud storage to local filesystem."""
    
    def __init__(self, region: str = "eu-north-1", profile: str = "cloud"):
        self.region = region
        self.profile = profile
        self.s3 = boto3.client('s3', region_name=region)
        
    def download_stage3_output(self, 
                             cloud_output_path: str, 
                             local_output_path: str,
                             include_observations: bool = True,
                             include_report: bool = True) -> Dict:
        """Download Stage 3 output from cloud to local storage."""
        try:
            logger.info(f"Downloading Stage 3 output from {cloud_output_path} to {local_output_path}")
            
            # Ensure local output directory exists
            local_path = Path(local_output_path)
            local_path.mkdir(parents=True, exist_ok=True)
            
            results = {
                'downloaded_files': [],
                'failed_downloads': [],
                'total_size_bytes': 0,
                'download_time': None
            }
            
            start_time = datetime.now()
            
            # Download compressed observations
            if include_observations:
                observations_result = self._download_file(
                    f"{cloud_output_path}/stage3/compressed_observations.json",
                    local_path / "compressed_observations.json"
                )
                if observations_result['success']:
                    results['downloaded_files'].append(observations_result['local_path'])
                    results['total_size_bytes'] += observations_result['size_bytes']
                else:
                    results['failed_downloads'].append(observations_result['error'])
            
            # Download report
            if include_report:
                report_result = self._download_file(
                    f"{cloud_output_path}/stage3/report.json",
                    local_path / "report.json"
                )
                if report_result['success']:
                    results['downloaded_files'].append(report_result['local_path'])
                    results['total_size_bytes'] += report_result['size_bytes']
                else:
                    results['failed_downloads'].append(report_result['error'])
            
            # Download additional Stage 3 files if they exist
            additional_files = self._discover_additional_files(cloud_output_path)
            for file_path in additional_files:
                file_result = self._download_file(
                    file_path,
                    local_path / Path(file_path).name
                )
                if file_result['success']:
                    results['downloaded_files'].append(file_result['local_path'])
                    results['total_size_bytes'] += file_result['size_bytes']
                else:
                    results['failed_downloads'].append(file_result['error'])
            
            end_time = datetime.now()
            results['download_time'] = (end_time - start_time).total_seconds()
            
            # Generate summary
            logger.info(f"✅ Stage 3 output download completed:")
            logger.info(f"  📁 Downloaded files: {len(results['downloaded_files'])}")
            logger.info(f"  📊 Total size: {results['total_size_bytes'] / 1024 / 1024:.2f} MB")
            logger.info(f"  ⏱️  Download time: {results['download_time']:.2f} seconds")
            
            if results['failed_downloads']:
                logger.warning(f"  ❌ Failed downloads: {len(results['failed_downloads'])}")
                for error in results['failed_downloads']:
                    logger.warning(f"    - {error}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error downloading Stage 3 output: {e}")
            return {'error': str(e)}
    
    def _download_file(self, cloud_path: str, local_path: Path) -> Dict:
        """Download a single file from cloud storage."""
        try:
            # Parse cloud path to determine storage type
            if cloud_path.startswith('s3://'):
                return self._download_from_s3(cloud_path, local_path)
            elif cloud_path.startswith('file://') or not cloud_path.startswith(('http://', 'https://')):
                return self._download_from_local(cloud_path, local_path)
            else:
                return {'success': False, 'error': f'Unsupported cloud path format: {cloud_path}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _download_from_s3(self, s3_path: str, local_path: Path) -> Dict:
        """Download file from S3."""
        try:
            # Parse S3 path
            if not s3_path.startswith('s3://'):
                return {'success': False, 'error': 'Invalid S3 path format'}
            
            s3_path = s3_path[5:]  # Remove 's3://' prefix
            if '/' not in s3_path:
                return {'success': False, 'error': 'Invalid S3 path format'}
            
            bucket_name, key = s3_path.split('/', 1)
            
            # Download file
            self.s3.download_file(bucket_name, key, str(local_path))
            
            # Get file size
            file_size = local_path.stat().st_size
            
            logger.info(f"✅ Downloaded from S3: {s3_path} -> {local_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'cloud_path': f"s3://{s3_path}",
                'size_bytes': file_size
            }
            
        except Exception as e:
            return {'success': False, 'error': f'S3 download failed: {str(e)}'}
    
    def _download_from_local(self, source_path: str, local_path: Path) -> Dict:
        """Copy file from local source to local destination."""
        try:
            source_path = Path(source_path)
            
            if not source_path.exists():
                return {'success': False, 'error': f'Source file does not exist: {source_path}'}
            
            # Copy file
            import shutil
            shutil.copy2(source_path, local_path)
            
            # Get file size
            file_size = local_path.stat().st_size
            
            logger.info(f"✅ Copied from local: {source_path} -> {local_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'cloud_path': str(source_path),
                'size_bytes': file_size
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Local copy failed: {str(e)}'}
    
    def _discover_additional_files(self, cloud_output_path: str) -> List[str]:
        """Discover additional Stage 3 files that might exist."""
        additional_files = []
        
        try:
            if cloud_output_path.startswith('s3://'):
                # List S3 objects in stage3 directory
                s3_path = cloud_output_path[5:]  # Remove 's3://' prefix
                if '/' not in s3_path:
                    return additional_files
                
                bucket_name, prefix = s3_path.split('/', 1)
                stage3_prefix = f"{prefix}/stage3/"
                
                response = self.s3.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=stage3_prefix
                )
                
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('.json') and key not in [
                        f"{stage3_prefix}compressed_observations.json",
                        f"{stage3_prefix}report.json"
                    ]:
                        additional_files.append(f"s3://{bucket_name}/{key}")
            
            elif cloud_output_path.startswith('file://') or not cloud_output_path.startswith(('http://', 'https://')):
                # List local files in stage3 directory
                stage3_dir = Path(cloud_output_path) / "stage3"
                if stage3_dir.exists():
                    for file_path in stage3_dir.glob("*.json"):
                        if file_path.name not in ['compressed_observations.json', 'report.json']:
                            additional_files.append(str(file_path))
            
        except Exception as e:
            logger.warning(f"Error discovering additional files: {e}")
        
        return additional_files
    
    def get_stage3_summary(self, local_output_path: str) -> Dict:
        """Get summary of downloaded Stage 3 output."""
        try:
            local_path = Path(local_output_path)
            
            summary = {
                'local_path': str(local_path),
                'files': [],
                'total_size_bytes': 0,
                'observations_count': 0,
                'species_detected': [],
                'cameras': [],
                'time_range': None
            }
            
            # Check for compressed observations
            observations_file = local_path / "compressed_observations.json"
            if observations_file.exists():
                with open(observations_file, 'r') as f:
                    observations = json.load(f)
                
                summary['files'].append({
                    'name': 'compressed_observations.json',
                    'size_bytes': observations_file.stat().st_size,
                    'observations_count': len(observations)
                })
                summary['total_size_bytes'] += observations_file.stat().st_size
                summary['observations_count'] = len(observations)
                
                # Extract species and cameras from observations
                species_set = set()
                cameras_set = set()
                timestamps = []
                
                for obs in observations:
                    if 'species' in obs:
                        species_set.add(obs['species'])
                    if 'camera' in obs:
                        cameras_set.add(obs['camera'])
                    if 'timestamp' in obs:
                        timestamps.append(obs['timestamp'])
                
                summary['species_detected'] = list(species_set)
                summary['cameras'] = list(cameras_set)
                
                if timestamps:
                    timestamps.sort()
                    summary['time_range'] = {
                        'start': timestamps[0],
                        'end': timestamps[-1]
                    }
            
            # Check for report
            report_file = local_path / "report.json"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    report = json.load(f)
                
                summary['files'].append({
                    'name': 'report.json',
                    'size_bytes': report_file.stat().st_size,
                    'report_data': report
                })
                summary['total_size_bytes'] += report_file.stat().st_size
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting Stage 3 summary: {e}")
            return {'error': str(e)}
    
    def create_local_stage3_runner(self, local_output_path: str) -> str:
        """Create a local script to run Stage 3 processing."""
        try:
            local_path = Path(local_output_path)
            script_path = local_path / "run_stage3_local.py"
            
            script_content = f'''#!/usr/bin/env python3
"""
Local Stage 3 Runner

This script runs Stage 3 processing locally using downloaded data.
Generated by Stage3OutputDownloader on {datetime.now().isoformat()}
"""

import json
import sys
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

def run_stage3_local():
    """Run Stage 3 processing locally."""
    print("🐦‍⬛ Running Stage 3 locally...")
    
    # Load compressed observations
    observations_file = Path(__file__).parent / "compressed_observations.json"
    if not observations_file.exists():
        print("❌ compressed_observations.json not found")
        return False
    
    with open(observations_file, 'r') as f:
        observations = json.load(f)
    
    print(f"📊 Loaded {{len(observations)}} compressed observations")
    
    # Load report if available
    report_file = Path(__file__).parent / "report.json"
    if report_file.exists():
        with open(report_file, 'r') as f:
            report = json.load(f)
        print(f"📈 Report loaded: {{report.get('total_observations', 'unknown')}} total observations")
    
    # Process observations
    species_count = {{}}
    camera_count = {{}}
    
    for obs in observations:
        species = obs.get('species', 'unknown')
        camera = obs.get('camera', 'unknown')
        
        species_count[species] = species_count.get(species, 0) + 1
        camera_count[camera] = camera_count.get(camera, 0) + 1
    
    print("\\n📊 Local Stage 3 Results:")
    print(f"  Total observations: {{len(observations)}}")
    print(f"  Species detected: {{list(species_count.keys())}}")
    print(f"  Cameras: {{list(camera_count.keys())}}")
    
    print("\\n🦌 Species breakdown:")
    for species, count in species_count.items():
        print(f"  {{species}}: {{count}} observations")
    
    print("\\n📷 Camera breakdown:")
    for camera, count in camera_count.items():
        print(f"  {{camera}}: {{count}} observations")
    
    print("\\n✅ Local Stage 3 processing completed!")
    return True

if __name__ == "__main__":
    run_stage3_local()
'''
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            script_path.chmod(0o755)
            
            logger.info(f"✅ Created local Stage 3 runner: {script_path}")
            return str(script_path)
            
        except Exception as e:
            logger.error(f"Error creating local Stage 3 runner: {e}")
            return None


def main():
    """Main CLI for Stage 3 output downloader."""
    parser = argparse.ArgumentParser(description="Download Stage 3 output from cloud to local storage")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument("--profile", default="cloud", help="Configuration profile")
    parser.add_argument("--cloud-path", required=True, help="Cloud output path (e.g., s3://bucket/path or /local/path)")
    parser.add_argument("--local-path", required=True, help="Local output directory")
    parser.add_argument("--observations-only", action="store_true", help="Download only compressed observations")
    parser.add_argument("--report-only", action="store_true", help="Download only report")
    parser.add_argument("--summary", action="store_true", help="Show summary of downloaded files")
    parser.add_argument("--create-runner", action="store_true", help="Create local Stage 3 runner script")
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = Stage3OutputDownloader(args.region, args.profile)
    
    try:
        # Determine what to download
        include_observations = not args.report_only
        include_report = not args.observations_only
        
        # Download Stage 3 output
        result = downloader.download_stage3_output(
            cloud_output_path=args.cloud_path,
            local_output_path=args.local_path,
            include_observations=include_observations,
            include_report=include_report
        )
        
        if 'error' in result:
            print(f"❌ Download failed: {result['error']}")
            sys.exit(1)
        
        # Show summary if requested
        if args.summary:
            summary = downloader.get_stage3_summary(args.local_path)
            print(f"\\n📊 Stage 3 Summary:")
            print(f"  Local path: {summary['local_path']}")
            print(f"  Files: {len(summary['files'])}")
            print(f"  Total size: {summary['total_size_bytes'] / 1024 / 1024:.2f} MB")
            print(f"  Observations: {summary['observations_count']}")
            print(f"  Species: {summary['species_detected']}")
            print(f"  Cameras: {summary['cameras']}")
            if summary['time_range']:
                print(f"  Time range: {summary['time_range']['start']} to {summary['time_range']['end']}")
        
        # Create local runner if requested
        if args.create_runner:
            runner_path = downloader.create_local_stage3_runner(args.local_path)
            if runner_path:
                print(f"\\n🚀 Local Stage 3 runner created: {runner_path}")
                print(f"Run with: python {runner_path}")
        
        print(f"\\n✅ Stage 3 output download completed!")
        print(f"📁 Local files: {args.local_path}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
