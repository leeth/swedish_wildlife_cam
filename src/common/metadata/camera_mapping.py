"""
Camera mapping management for wildlife pipeline.

Handles stable camera identification with versioning and effective date ranges.
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


class CameraMappingManager:
    """Manages camera mappings with versioning and effective date ranges."""
    
    def __init__(self, s3_bucket: str, s3_prefix: str = "metadata/camera_mapping"):
        """Initialize camera mapping manager."""
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3')
        self.mappings_cache = {}
        self.current_version = None
    
    def add_mapping(
        self,
        camera_id: str,
        physical_serial: str,
        alias: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        map_version: str = "1.0.0"
    ) -> str:
        """Add a new camera mapping record."""
        
        if effective_from is None:
            effective_from = datetime.now(timezone.utc)
        
        mapping_id = f"mapping_{camera_id}_{int(effective_from.timestamp())}"
        
        mapping = {
            'mapping_id': mapping_id,
            'camera_id': camera_id,
            'physical_serial': physical_serial,
            'alias': alias,
            'effective_from': effective_from.isoformat(),
            'effective_to': effective_to.isoformat() if effective_to else None,
            'map_version': map_version,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Load current mappings
        mappings = self._load_mappings()
        mappings.append(mapping)
        
        # Save updated mappings
        version = self._save_mappings(mappings)
        
        logger.info(f"Added camera mapping: {camera_id} -> {physical_serial}")
        return version
    
    def get_camera_id(
        self,
        physical_serial: str,
        timestamp: datetime,
        version: Optional[str] = None
    ) -> Optional[str]:
        """Get camera_id for physical serial at given timestamp."""
        
        mappings = self._load_mappings(version)
        
        # Find applicable mapping
        applicable_mappings = []
        for mapping in mappings:
            if mapping['physical_serial'] != physical_serial:
                continue
                
            effective_from = datetime.fromisoformat(mapping['effective_from'])
            effective_to = (
                datetime.fromisoformat(mapping['effective_to'])
                if mapping['effective_to']
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            if effective_from <= timestamp <= effective_to:
                applicable_mappings.append(mapping)
        
        if not applicable_mappings:
            return None
        
        # Return the most recent applicable mapping
        latest_mapping = max(applicable_mappings, key=lambda x: x['created_at'])
        return latest_mapping['camera_id']
    
    def get_physical_serial(
        self,
        camera_id: str,
        timestamp: datetime,
        version: Optional[str] = None
    ) -> Optional[str]:
        """Get physical serial for camera_id at given timestamp."""
        
        mappings = self._load_mappings(version)
        
        # Find applicable mapping
        applicable_mappings = []
        for mapping in mappings:
            if mapping['camera_id'] != camera_id:
                continue
                
            effective_from = datetime.fromisoformat(mapping['effective_from'])
            effective_to = (
                datetime.fromisoformat(mapping['effective_to'])
                if mapping['effective_to']
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            if effective_from <= timestamp <= effective_to:
                applicable_mappings.append(mapping)
        
        if not applicable_mappings:
            return None
        
        # Return the most recent applicable mapping
        latest_mapping = max(applicable_mappings, key=lambda x: x['created_at'])
        return latest_mapping['physical_serial']
    
    def get_mapping_info(
        self,
        camera_id: str,
        timestamp: datetime,
        version: Optional[str] = None
    ) -> Optional[Dict]:
        """Get complete mapping information for camera_id at timestamp."""
        
        mappings = self._load_mappings(version)
        
        # Find applicable mapping
        applicable_mappings = []
        for mapping in mappings:
            if mapping['camera_id'] != camera_id:
                continue
                
            effective_from = datetime.fromisoformat(mapping['effective_from'])
            effective_to = (
                datetime.fromisoformat(mapping['effective_to'])
                if mapping['effective_to']
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            if effective_from <= timestamp <= effective_to:
                applicable_mappings.append(mapping)
        
        if not applicable_mappings:
            return None
        
        # Return the most recent applicable mapping
        latest_mapping = max(applicable_mappings, key=lambda x: x['created_at'])
        
        return {
            'camera_id': latest_mapping['camera_id'],
            'physical_serial': latest_mapping['physical_serial'],
            'alias': latest_mapping['alias'],
            'map_version': latest_mapping['map_version'],
            'mapping_id': latest_mapping['mapping_id']
        }
    
    def list_active_cameras(
        self,
        timestamp: Optional[datetime] = None,
        version: Optional[str] = None
    ) -> List[Dict]:
        """List all active cameras at given timestamp."""
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        mappings = self._load_mappings(version)
        active_cameras = []
        
        for mapping in mappings:
            effective_from = datetime.fromisoformat(mapping['effective_from'])
            effective_to = (
                datetime.fromisoformat(mapping['effective_to'])
                if mapping['effective_to']
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            if effective_from <= timestamp <= effective_to:
                active_cameras.append({
                    'camera_id': mapping['camera_id'],
                    'physical_serial': mapping['physical_serial'],
                    'alias': mapping['alias'],
                    'map_version': mapping['map_version']
                })
        
        return active_cameras
    
    def _load_mappings(self, version: Optional[str] = None) -> List[Dict]:
        """Load camera mappings from S3."""
        
        if version:
            cache_key = f"mappings_{version}"
        else:
            cache_key = "mappings_current"
        
        if cache_key in self.mappings_cache:
            return self.mappings_cache[cache_key]
        
        try:
            if version:
                s3_key = f"{self.s3_prefix}/v{version}/mapping.json"
            else:
                s3_key = f"{self.s3_prefix}/current/mapping.json"
            
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            mappings = json.loads(response['Body'].read().decode('utf-8'))
            
            self.mappings_cache[cache_key] = mappings
            return mappings
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"No camera mappings found for version {version or 'current'}")
                return []
            raise
    
    def _save_mappings(self, mappings: List[Dict]) -> str:
        """Save camera mappings to S3 with versioning."""
        
        # Generate new version
        version = f"{int(datetime.now().timestamp())}"
        
        # Save to versioned location
        s3_key = f"{self.s3_prefix}/v{version}/mapping.json"
        mappings_json = json.dumps(mappings, indent=2)
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=mappings_json,
            ContentType='application/json'
        )
        
        # Update current version
        current_key = f"{self.s3_prefix}/current/mapping.json"
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=current_key,
            Body=mappings_json,
            ContentType='application/json'
        )
        
        # Update manifest
        self._update_manifest(version, s3_key, mappings_json)
        
        # Clear cache
        self.mappings_cache.clear()
        
        logger.info(f"Saved camera mappings version {version}")
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
                "current_exif_corrections": "1",
                "current_camera_mapping": version,
                "exif_corrections_file": f"{self.s3_prefix}/current/corrections.json",
                "camera_mapping_file": s3_key,
                "exif_corrections_checksum": "",
                "camera_mapping_checksum": hashlib.sha256(content.encode()).hexdigest(),
                "processing_version": "1.0.0"
            }
        
        manifest['current_camera_mapping'] = version
        manifest['camera_mapping_file'] = s3_key
        manifest['camera_mapping_checksum'] = hashlib.sha256(content.encode()).hexdigest()
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
                if obj['Key'].endswith('/mapping.json'):
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
        """Export mappings to Parquet format."""
        
        mappings = self._load_mappings(version)
        
        if not mappings:
            raise ValueError("No mappings found to export")
        
        # Convert to DataFrame
        df = pd.DataFrame(mappings)
        
        # Convert timestamp columns
        df['effective_from'] = pd.to_datetime(df['effective_from'])
        df['effective_to'] = pd.to_datetime(df['effective_to'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Save to S3 as Parquet
        version_suffix = f"_v{version}" if version else ""
        parquet_key = f"{self.s3_prefix}/exports/mappings{version_suffix}.parquet"
        
        # Convert to Parquet bytes
        parquet_buffer = df.to_parquet(index=False)
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=parquet_key,
            Body=parquet_buffer,
            ContentType='application/octet-stream'
        )
        
        logger.info(f"Exported mappings to {parquet_key}")
        return parquet_key
