"""
Runners for executing pipeline stages locally and in cloud.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tqdm import tqdm
from PIL import Image

from .interfaces import Runner, ManifestEntry, Stage2Entry, StorageLocation
from .storage import create_storage_adapter
from .queue import create_queue_adapter
from .models import create_model_provider


class LocalRunner(Runner):
    """Local runner for batch processing."""
    
    def __init__(self, storage_adapter, model_provider, max_workers: int = 4):
        self.storage = storage_adapter
        self.model_provider = model_provider
        self.max_workers = max_workers
    
    def run_stage1(self, input_prefix: str, output_prefix: str, config: Dict[str, Any]) -> List[ManifestEntry]:
        """Run Stage-1 processing locally."""
        print(f"Running Stage-1 locally: {input_prefix} -> {output_prefix}")
        
        # Load Stage-1 model
        model_path = config.get('stage1_model', 'megadetector')
        model = self.model_provider.load_model(model_path)
        
        # Get input files
        input_location = StorageLocation.from_url(input_prefix)
        image_files = self.storage.list(input_location, "*.jpg")
        image_files.extend(self.storage.list(input_location, "*.jpeg"))
        image_files.extend(self.storage.list(input_location, "*.png"))
        
        print(f"Found {len(image_files)} images to process")
        
        # Process images
        manifest_entries = []
        crops_location = StorageLocation.from_url(f"{output_prefix}/stage1/crops")
        
        for image_file in tqdm(image_files, desc="Processing Stage-1"):
            try:
                # Load image
                image_content = self.storage.get(image_file)
                image = Image.open(io.BytesIO(image_content))
                
                # Run detection
                detections = model.predict(image)
                
                # Process detections
                for i, detection in enumerate(detections):
                    if detection.confidence >= config.get('conf_threshold', 0.3):
                        # Create crop
                        crop_path = f"crops/{image_file.path.stem}_{i}.jpg"
                        crop_location = StorageLocation.from_url(f"{output_prefix}/stage1/{crop_path}")
                        
                        # Save crop
                        crop_image = image.crop(detection.bbox)
                        crop_bytes = self._image_to_bytes(crop_image)
                        self.storage.put(crop_location, crop_bytes)
                        
                        # Create manifest entry
                        manifest_entry = ManifestEntry(
                            source_path=image_file.url,
                            crop_path=crop_location.url,
                            camera_id=self._extract_camera_id(image_file.path),
                            timestamp=self._extract_timestamp(image_file.path),
                            bbox=detection.bbox,
                            det_score=detection.confidence,
                            stage1_model=model_path,
                            config_hash=self._get_config_hash(config)
                        )
                        manifest_entries.append(manifest_entry)
                        
            except Exception as e:
                print(f"Error processing {image_file.url}: {e}")
                continue
        
        # Save manifest
        self._save_manifest(manifest_entries, f"{output_prefix}/stage1/manifest.jsonl")
        
        return manifest_entries
    
    def run_stage2(self, manifest_entries: List[ManifestEntry], output_prefix: str, config: Dict[str, Any]) -> List[Stage2Entry]:
        """Run Stage-2 processing locally."""
        print(f"Running Stage-2 locally on {len(manifest_entries)} crops")
        
        # Load Stage-2 model
        model_path = config.get('stage2_model', 'yolo_cls')
        model = self.model_provider.load_model(model_path)
        
        stage2_entries = []
        
        for manifest_entry in tqdm(manifest_entries, desc="Processing Stage-2"):
            try:
                # Load crop
                crop_location = StorageLocation.from_url(manifest_entry.crop_path)
                crop_content = self.storage.get(crop_location)
                crop_image = Image.open(io.BytesIO(crop_content))
                
                # Run classification
                prediction = model.predict(crop_image)
                
                # Create Stage-2 entry
                stage2_entry = Stage2Entry(
                    crop_path=manifest_entry.crop_path,
                    label=prediction.label,
                    confidence=prediction.confidence,
                    auto_ok=prediction.confidence >= config.get('conf_threshold', 0.5),
                    stage2_model=model_path,
                    stage1_model=manifest_entry.stage1_model,
                    config_hash=manifest_entry.config_hash
                )
                stage2_entries.append(stage2_entry)
                
            except Exception as e:
                print(f"Error processing {manifest_entry.crop_path}: {e}")
                continue
        
        # Save predictions
        self._save_predictions(stage2_entries, f"{output_prefix}/stage2/predictions.jsonl")
        
        return stage2_entries
    
    def _image_to_bytes(self, image: Image.Image, format: str = "JPEG") -> bytes:
        """Convert PIL Image to bytes."""
        import io
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=90)
        return buffer.getvalue()
    
    def _extract_camera_id(self, path: str) -> str:
        """Extract camera ID from path."""
        path_parts = Path(path).parts
        return path_parts[0] if path_parts else "unknown"
    
    def _extract_timestamp(self, path: str) -> str:
        """Extract timestamp from path or use current time."""
        # This would extract from EXIF or filename
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _get_config_hash(self, config: Dict[str, Any]) -> str:
        """Get hash of configuration."""
        import hashlib
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def _save_manifest(self, entries: List[ManifestEntry], manifest_path: str):
        """Save manifest to storage."""
        manifest_location = StorageLocation.from_url(manifest_path)
        manifest_content = "\n".join(json.dumps(entry.to_dict()) for entry in entries)
        self.storage.put(manifest_location, manifest_content.encode('utf-8'))
    
    def _save_predictions(self, entries: List[Stage2Entry], predictions_path: str):
        """Save predictions to storage."""
        predictions_location = StorageLocation.from_url(predictions_path)
        predictions_content = "\n".join(json.dumps(entry.to_dict()) for entry in entries)
        self.storage.put(predictions_location, predictions_content.encode('utf-8'))


class CloudBatchRunner(Runner):
    """Cloud batch runner for AWS Batch/Cloud Run Jobs with GPU optimization."""
    
    def __init__(self, storage_adapter, model_provider, job_definition: str = "wildlife-detection-job", 
                 vcpu: int = 4, memory: int = 8192, gpu_count: int = 1, gpu_type: str = "g4dn.xlarge"):
        self.storage = storage_adapter
        self.model_provider = model_provider
        self.job_definition = job_definition
        self.vcpu = vcpu
        self.memory = memory
        self.gpu_count = gpu_count
        self.gpu_type = gpu_type
    
    def run_stage1(self, input_prefix: str, output_prefix: str, config: Dict[str, Any]) -> List[ManifestEntry]:
        """Run Stage-1 in cloud batch job."""
        print(f"Submitting Stage-1 cloud batch job: {input_prefix} -> {output_prefix}")
        
        # Submit batch job
        job_id = self._submit_batch_job("stage1", {
            'input_prefix': input_prefix,
            'output_prefix': output_prefix,
            'config': config
        })
        
        # Wait for completion
        self._wait_for_job_completion(job_id)
        
        # Load results
        manifest_location = StorageLocation.from_url(f"{output_prefix}/stage1/manifest.jsonl")
        if self.storage.exists(manifest_location):
            manifest_content = self.storage.get(manifest_location)
            entries = []
            for line in manifest_content.decode('utf-8').strip().split('\n'):
                if line:
                    entries.append(ManifestEntry.from_dict(json.loads(line)))
            return entries
        
        return []
    
    def run_stage2(self, manifest_entries: List[ManifestEntry], output_prefix: str, config: Dict[str, Any]) -> List[Stage2Entry]:
        """Run Stage-2 in cloud batch job."""
        print(f"Submitting Stage-2 cloud batch job on {len(manifest_entries)} crops")
        
        # Submit batch job
        job_id = self._submit_batch_job("stage2", {
            'manifest_entries': [entry.to_dict() for entry in manifest_entries],
            'output_prefix': output_prefix,
            'config': config
        })
        
        # Wait for completion
        self._wait_for_job_completion(job_id)
        
        # Load results
        predictions_location = StorageLocation.from_url(f"{output_prefix}/stage2/predictions.jsonl")
        if self.storage.exists(predictions_location):
            predictions_content = self.storage.get(predictions_location)
            entries = []
            for line in predictions_content.decode('utf-8').strip().split('\n'):
                if line:
                    entries.append(Stage2Entry.from_dict(json.loads(line)))
            return entries
        
        return []
    
    def _submit_batch_job(self, stage: str, job_data: Dict[str, Any]) -> str:
        """Submit batch job to cloud provider with GPU optimization."""
        print(f"Submitting {stage} batch job with GPU optimization...")
        
        # Enhanced job configuration for image processing
        job_config = {
            'jobName': f'wildlife-{stage}-{hash(str(job_data))}',
            'jobQueue': 'wildlife-detection-queue',
            'jobDefinition': self.job_definition,
            'parameters': {
                'stage': stage,
                'input_prefix': job_data.get('input_prefix', ''),
                'output_prefix': job_data.get('output_prefix', ''),
                'config': json.dumps(job_data.get('config', {}))
            },
            'containerOverrides': {
                'vcpus': self.vcpu,
                'memory': self.memory,
                'resourceRequirements': [
                    {
                        'type': 'GPU',
                        'value': str(self.gpu_count)
                    }
                ],
                'environment': [
                    {'name': 'CUDA_VISIBLE_DEVICES', 'value': '0'},
                    {'name': 'PYTORCH_CUDA_ALLOC_CONF', 'value': 'max_split_size_mb:512'},
                    {'name': 'OPENCV_GPU_ENABLED', 'value': '1'},
                    {'name': 'BATCH_SIZE', 'value': str(job_data.get('config', {}).get('batch_size', 16))},
                    {'name': 'IMAGE_SIZE', 'value': str(job_data.get('config', {}).get('image_size', 640))}
                ]
            },
            'retryStrategy': {
                'attempts': 3,
                'evaluateOnExit': [
                    {
                        'action': 'RETRY',
                        'onStatusReason': 'GPU_ERROR'
                    }
                ]
            },
            'timeout': {
                'attemptDurationSeconds': 3600  # 1 hour timeout
            }
        }
        
        print(f"Job configuration: {json.dumps(job_config, indent=2)}")
        return f"job_{stage}_{hash(str(job_data))}"
    
    def _wait_for_job_completion(self, job_id: str):
        """Wait for batch job completion."""
        print(f"Waiting for job {job_id} to complete...")
        # This would poll the job status
        import time
        time.sleep(2)  # Simulate job completion


class EventDrivenRunner(Runner):
    """Event-driven runner for queue-based processing."""
    
    def __init__(self, storage_adapter, queue_adapter, model_provider):
        self.storage = storage_adapter
        self.queue = queue_adapter
        self.model_provider = model_provider
    
    def run_stage1(self, input_prefix: str, output_prefix: str, config: Dict[str, Any]) -> List[ManifestEntry]:
        """Run Stage-1 in event-driven mode."""
        print(f"Starting event-driven Stage-1: {input_prefix} -> {output_prefix}")
        
        # Process images and send to queue
        input_location = StorageLocation.from_url(input_prefix)
        image_files = self.storage.list(input_location, "*.jpg")
        
        for image_file in image_files:
            message = {
                'stage': 'stage1',
                'input_path': image_file.url,
                'output_prefix': output_prefix,
                'config': config
            }
            self.queue.send_message('stage1-queue', message)
        
        print(f"Sent {len(image_files)} messages to stage1-queue")
        return []  # Results will be collected via queue
    
    def run_stage2(self, manifest_entries: List[ManifestEntry], output_prefix: str, config: Dict[str, Any]) -> List[Stage2Entry]:
        """Run Stage-2 in event-driven mode."""
        print(f"Starting event-driven Stage-2 on {len(manifest_entries)} crops")
        
        # Send manifest entries to queue
        for manifest_entry in manifest_entries:
            message = {
                'stage': 'stage2',
                'manifest_entry': manifest_entry.to_dict(),
                'output_prefix': output_prefix,
                'config': config
            }
            self.queue.send_message('stage2-queue', message)
        
        print(f"Sent {len(manifest_entries)} messages to stage2-queue")
        return []  # Results will be collected via queue


def create_runner(runner_type: str, storage_adapter, model_provider, queue_adapter=None, **kwargs) -> Runner:
    """Factory function to create runners."""
    if runner_type == "local":
        return LocalRunner(storage_adapter, model_provider, **kwargs)
    elif runner_type == "cloud_batch":
        return CloudBatchRunner(storage_adapter, model_provider, **kwargs)
    elif runner_type == "event_driven":
        if queue_adapter is None:
            raise ValueError("queue_adapter required for event_driven runner")
        return EventDrivenRunner(storage_adapter, queue_adapter, model_provider)
    else:
        raise ValueError(f"Unknown runner type: {runner_type}")
