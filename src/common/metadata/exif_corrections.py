"""
EXIF corrections management for wildlife pipeline.

Handles time correction tables with versioning and effective date ranges.
"""

import pandas as pd
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class EXIFCorrectionsManager:
    """Manages EXIF corrections with versioning and effective date ranges."""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "metadata/exif_corrections"):
        """Initialize EXIF corrections manager."""
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
        self.corrections_cache = {}
        self.current_version = None
    
    def add_correction(
        self,
        camera_id: str,
        delta_seconds: int,
        effective_from: datetime,
        effective_to: Optional[datetime] = None,
        rule_id: str = "manual_correction"
    ) -> str:
        """Add a new EXIF correction record."""
        
        correction_id = f"correction_{camera_id}_{int(effective_from.timestamp())}"
        
        correction = {
            'correction_id': correction_id,
            'camera_id': camera_id,
            'delta_seconds': delta_seconds,
            'effective_from': effective_from.isoformat(),
            'effective_to': effective_to.isoformat() if effective_to else None,
            'rule_id': rule_id,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Load current corrections
        corrections = self._load_corrections()
        corrections.append(correction)
        
        # Save updated corrections
        version = self._save_corrections(corrections)
        
        logger.info(f"Added EXIF correction for camera {camera_id}: {delta_seconds}s from {effective_from}")
        return version
    
    def get_correction(
        self,
        camera_id: str,
        timestamp: datetime,
        version: Optional[str] = None
    ) -> Optional[Dict]:
        """Get applicable EXIF correction for camera and timestamp."""
        
        corrections = self._load_corrections(version)
        
        # Find applicable correction
        applicable_corrections = []
        for correction in corrections:
            if correction['camera_id'] != camera_id:
                continue
                
            effective_from = datetime.fromisoformat(correction['effective_from'])
            effective_to = (
                datetime.fromisoformat(correction['effective_to'])
                if correction['effective_to']
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            if effective_from <= timestamp <= effective_to:
                applicable_corrections.append(correction)
        
        if not applicable_corrections:
            return None
        
        # Return the most recent applicable correction
        latest_correction = max(applicable_corrections, key=lambda x: x['created_at'])
        
        return {
            'delta_seconds': latest_correction['delta_seconds'],
            'rule_id': latest_correction['rule_id'],
            'correction_id': latest_correction['correction_id']
        }
    
    def apply_correction(
        self,
        camera_id: str,
        original_timestamp: datetime,
        version: Optional[str] = None
    ) -> Tuple[datetime, Optional[Dict]]:
        """Apply EXIF correction to timestamp."""
        
        correction = self.get_correction(camera_id, original_timestamp, version)
        
        if not correction:
            return original_timestamp, None
        
        corrected_timestamp = original_timestamp + pd.Timedelta(seconds=correction['delta_seconds'])
        
        return corrected_timestamp, correction
    
    def _load_corrections(self, version: Optional[str] = None) -> List[Dict]:
        """Load EXIF corrections from S3."""
        
        if version:
            cache_key = f"corrections_{version}"
        else:
            cache_key = "corrections_current"
        
        if cache_key in self.corrections_cache:
            return self.corrections_cache[cache_key]
        
        try:
            if version:
                s3_key = f"{self.s3_prefix}/v{version}/corrections.json"
            else:
                s3_key = f"{self.s3_prefix}/current/corrections.json"
            
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            corrections = json.loads(response['Body'].read().decode('utf-8'))
            
            self.corrections_cache[cache_key] = corrections
            return corrections
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"No EXIF corrections found for version {version or 'current'}")
                return []
            raise
    
    def _save_corrections(self, corrections: List[Dict]) -> str:
        """Save EXIF corrections to S3 with versioning."""
        
        # Generate new version
        version = f"{int(datetime.now().timestamp())}"
        
        # Save to versioned location
        s3_key = f"{self.s3_prefix}/v{version}/corrections.json"
        corrections_json = json.dumps(corrections, indent=2)
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=corrections_json,
            ContentType='application/json'
        )
        
        # Update current version
        current_key = f"{self.s3_prefix}/current/corrections.json"
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=current_key,
            Body=corrections_json,
            ContentType='application/json'
        )
        
        # Update manifest
        self._update_manifest(version, s3_key, corrections_json)
        
        # Clear cache
        self.corrections_cache.clear()
        
        logger.info(f"Saved EXIF corrections version {version}")
        return version
    
    def _update_manifest(self, version: str, s3_key: str, content: str) -> None:
        """Update metadata manifest with new version."""
        
        manifest_key = f"{self.s3_prefix}/manifest.json"
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=manifest_key)
            manifest = json.loads(response['Body'].read().decode('utf-8'))
        except ClientError:
            manifest = {
                "manifest_version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "current_exif_corrections": version,
                "current_camera_mapping": "1",
                "exif_corrections_file": s3_key,
                "camera_mapping_file": f"{self.s3_prefix}/current/mapping.json",
                "exif_corrections_checksum": hashlib.sha256(content.encode()).hexdigest(),
                "camera_mapping_checksum": "",
                "processing_version": "1.0.0"
            }
        
        manifest['current_exif_corrections'] = version
        manifest['exif_corrections_file'] = s3_key
        manifest['exif_corrections_checksum'] = hashlib.sha256(content.encode()).hexdigest()
        manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType='application/json'
        )
    
    def get_manifest(self) -> Dict:
        """Get current metadata manifest."""
        
        manifest_key = f"{self.s3_prefix}/manifest.json"
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=manifest_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError:
            return {}
    
    def list_versions(self) -> List[Dict]:
        """List all available versions."""
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=f"{self.s3_prefix}/v"
            )
            
            versions = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('/corrections.json'):
                    version = obj['Key'].split('/')[-2].replace('v', '')
                    versions.append({
                        'version': version,
                        'last_modified': obj['LastModified'],
                        'size': obj['Size']
                    })
            
            return sorted(versions, key=lambda x: x['version'], reverse=True)
            
        except ClientError:
            return []
    
    def export_to_parquet(self, version: Optional[str] = None) -> str:
        """Export corrections to Parquet format."""
        
        corrections = self._load_corrections(version)
        
        if not corrections:
            raise ValueError("No corrections found to export")
        
        # Convert to DataFrame
        df = pd.DataFrame(corrections)
        
        # Convert timestamp columns
        df['effective_from'] = pd.to_datetime(df['effective_from'])
        df['effective_to'] = pd.to_datetime(df['effective_to'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Save to S3 as Parquet
        version_suffix = f"_v{version}" if version else ""
        parquet_key = f"{self.s3_prefix}/exports/corrections{version_suffix}.parquet"
        
        # Convert to Parquet bytes
        parquet_buffer = df.to_parquet(index=False)
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=parquet_key,
            Body=parquet_buffer,
            ContentType='application/octet-stream'
        )
        
        logger.info(f"Exported corrections to {parquet_key}")
        return parquet_key
