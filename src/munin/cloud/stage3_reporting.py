"""
Stage 3: Reporting and Compression

This module handles the final reporting stage that compresses video observations
to avoid duplicate logging of the same animal over extended periods.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

from .interfaces import Stage2Entry, ManifestEntry
from ..logging_config import get_logger

# Initialize logger for Stage 3 reporting
logger = get_logger("wildlife_pipeline.stage3_reporting")


@dataclass
class CompressedObservation:
    """Represents a compressed observation after Stage 3 processing."""
    camera_id: str
    species: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    max_confidence: float
    avg_confidence: float
    frame_count: int
    detection_timeline: List[Dict[str, Any]]
    source_video: Optional[str] = None
    needs_review: bool = False


class Stage3Reporter:
    """
    Stage 3 reporter that compresses video observations to avoid duplicate logging.
    
    This class takes Stage 2 results and compresses them into meaningful observations
    where each animal is logged only once per 10-minute window, preventing bloated
    logs from animals that stay in frame for extended periods.
    """
    
    def __init__(self, compression_window_minutes: int = 10, 
                 min_confidence: float = 0.5, min_duration_seconds: float = 5.0):
        """
        Initialize Stage 3 reporter.
        
        Args:
            compression_window_minutes: Compress observations within this window (default: 10 minutes)
            min_confidence: Minimum confidence for observations to be included
            min_duration_seconds: Minimum duration for an observation to be logged
        """
        self.compression_window = timedelta(minutes=compression_window_minutes)
        self.min_confidence = min_confidence
        self.min_duration_seconds = min_duration_seconds
    
    def process_stage2_results(self, stage2_entries: List[Stage2Entry], 
                             manifest_entries: List[ManifestEntry]) -> List[CompressedObservation]:
        """
        Process Stage 2 results and compress them into meaningful observations.
        
        Args:
            stage2_entries: List of Stage 2 classification results
            manifest_entries: List of Stage 1 manifest entries
            
        Returns:
            List of compressed observations
        """
        logger.log_stage_start("stage3_reporting", 
                              stage2_entries=len(stage2_entries), 
                              manifest_entries=len(manifest_entries),
                              compression_window_minutes=self.compression_window.total_seconds() / 60,
                              min_confidence=self.min_confidence,
                              min_duration_seconds=self.min_duration_seconds)
        
        # Group entries by camera and species
        grouped_observations = self._group_observations_by_camera_species(
            stage2_entries, manifest_entries
        )
        
        logger.info(f"📊 Grouped observations: {len(grouped_observations)} camera-species combinations", 
                   grouped_count=len(grouped_observations))
        
        # Compress observations within time windows
        compressed_observations = []
        
        for (camera_id, species), observations in grouped_observations.items():
            logger.debug(f"🔄 Compressing {len(observations)} observations for {camera_id}-{species}", 
                       camera_id=camera_id, species=species, observation_count=len(observations))
            
            compressed = self._compress_observations_for_species(
                camera_id, species, observations
            )
            compressed_observations.extend(compressed)
            
            logger.debug(f"✅ Compressed to {len(compressed)} observations", 
                        camera_id=camera_id, species=species, compressed_count=len(compressed))
        
        # Sort by start time
        compressed_observations.sort(key=lambda x: x.start_time)
        
        # Log compression statistics
        original_count = len(stage2_entries)
        compressed_count = len(compressed_observations)
        compression_ratio = original_count / compressed_count if compressed_count > 0 else 0
        
        logger.log_compression_stats(
            original_count=original_count,
            compressed_count=compressed_count,
            compression_ratio=compression_ratio
        )
        
        logger.log_stage_complete("stage3_reporting", 
                                compressed_observations=len(compressed_observations))
        
        return compressed_observations
    
    def _group_observations_by_camera_species(self, 
                                            stage2_entries: List[Stage2Entry],
                                            manifest_entries: List[ManifestEntry]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """Group observations by camera and species."""
        # Create lookup for manifest entries
        manifest_lookup = {entry.crop_path: entry for entry in manifest_entries}
        
        grouped = {}
        
        for stage2_entry in stage2_entries:
            if stage2_entry.confidence < self.min_confidence:
                continue
                
            # Find corresponding manifest entry
            manifest_entry = manifest_lookup.get(stage2_entry.crop_path)
            if not manifest_entry:
                continue
            
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(manifest_entry.timestamp.replace('Z', '+00:00'))
            except:
                continue
            
            # Determine if this is from a video (has frame info in crop path)
            is_video = '_frame_' in stage2_entry.crop_path
            
            key = (manifest_entry.camera_id, stage2_entry.label)
            if key not in grouped:
                grouped[key] = []
            
            grouped[key].append({
                'timestamp': timestamp,
                'confidence': stage2_entry.confidence,
                'crop_path': stage2_entry.crop_path,
                'source_path': manifest_entry.source_path,
                'is_video': is_video,
                'frame_number': self._extract_frame_number(stage2_entry.crop_path) if is_video else None
            })
        
        return grouped
    
    def _extract_frame_number(self, crop_path: str) -> Optional[int]:
        """Extract frame number from crop path if it's from a video."""
        try:
            # Extract frame number from path like "video_frame_000123.jpg"
            filename = Path(crop_path).stem
            if '_frame_' in filename:
                frame_part = filename.split('_frame_')[1]
                return int(frame_part)
        except:
            pass
        return None
    
    def _compress_observations_for_species(self, camera_id: str, species: str, 
                                         observations: List[Dict[str, Any]]) -> List[CompressedObservation]:
        """Compress observations for a specific camera and species."""
        if not observations:
            return []
        
        # Sort by timestamp
        observations.sort(key=lambda x: x['timestamp'])
        
        compressed = []
        current_observation = None
        
        for obs in observations:
            if current_observation is None:
                # Start new observation
                current_observation = {
                    'start_time': obs['timestamp'],
                    'end_time': obs['timestamp'],
                    'confidences': [obs['confidence']],
                    'frames': [obs],
                    'source_video': obs['source_path'] if obs['is_video'] else None
                }
            else:
                # Check if this observation is within the compression window
                time_diff = obs['timestamp'] - current_observation['start_time']
                
                if time_diff <= self.compression_window:
                    # Extend current observation
                    current_observation['end_time'] = obs['timestamp']
                    current_observation['confidences'].append(obs['confidence'])
                    current_observation['frames'].append(obs)
                else:
                    # Finalize current observation and start new one
                    compressed_obs = self._finalize_observation(
                        camera_id, species, current_observation
                    )
                    if compressed_obs:
                        compressed.append(compressed_obs)
                    
                    # Start new observation
                    current_observation = {
                        'start_time': obs['timestamp'],
                        'end_time': obs['timestamp'],
                        'confidences': [obs['confidence']],
                        'frames': [obs],
                        'source_video': obs['source_path'] if obs['is_video'] else None
                    }
        
        # Finalize last observation
        if current_observation:
            compressed_obs = self._finalize_observation(
                camera_id, species, current_observation
            )
            if compressed_obs:
                compressed.append(compressed_obs)
        
        return compressed
    
    def _finalize_observation(self, camera_id: str, species: str, 
                            observation_data: Dict[str, Any]) -> Optional[CompressedObservation]:
        """Finalize an observation and create CompressedObservation."""
        duration = (observation_data['end_time'] - observation_data['start_time']).total_seconds()
        
        # Check minimum duration
        if duration < self.min_duration_seconds:
            return None
        
        max_confidence = max(observation_data['confidences'])
        avg_confidence = sum(observation_data['confidences']) / len(observation_data['confidences'])
        
        # Create detection timeline
        timeline = []
        for frame in observation_data['frames']:
            timeline.append({
                'timestamp': frame['timestamp'].isoformat(),
                'confidence': frame['confidence'],
                'frame_number': frame.get('frame_number'),
                'crop_path': frame['crop_path']
            })
        
        return CompressedObservation(
            camera_id=camera_id,
            species=species,
            start_time=observation_data['start_time'],
            end_time=observation_data['end_time'],
            duration_seconds=duration,
            max_confidence=max_confidence,
            avg_confidence=avg_confidence,
            frame_count=len(observation_data['frames']),
            detection_timeline=timeline,
            source_video=observation_data['source_video'],
            needs_review=max_confidence < 0.8  # Flag for review if confidence is low
        )
    
    def generate_report(self, compressed_observations: List[CompressedObservation]) -> Dict[str, Any]:
        """
        Generate a summary report from compressed observations.
        
        Args:
            compressed_observations: List of compressed observations
            
        Returns:
            Summary report dictionary
        """
        if not compressed_observations:
            return {
                'total_observations': 0,
                'species_summary': {},
                'camera_summary': {},
                'time_range': None,
                'video_observations': 0,
                'image_observations': 0
            }
        
        # Calculate statistics
        species_summary = {}
        camera_summary = {}
        video_observations = 0
        image_observations = 0
        
        start_time = min(obs.start_time for obs in compressed_observations)
        end_time = max(obs.end_time for obs in compressed_observations)
        
        for obs in compressed_observations:
            # Species summary
            if obs.species not in species_summary:
                species_summary[obs.species] = {
                    'count': 0,
                    'total_duration': 0,
                    'max_confidence': 0,
                    'avg_confidence': 0
                }
            
            species_summary[obs.species]['count'] += 1
            species_summary[obs.species]['total_duration'] += obs.duration_seconds
            species_summary[obs.species]['max_confidence'] = max(
                species_summary[obs.species]['max_confidence'], obs.max_confidence
            )
            species_summary[obs.species]['avg_confidence'] = (
                species_summary[obs.species]['avg_confidence'] + obs.avg_confidence
            ) / 2
            
            # Camera summary
            if obs.camera_id not in camera_summary:
                camera_summary[obs.camera_id] = {
                    'count': 0,
                    'species': set()
                }
            
            camera_summary[obs.camera_id]['count'] += 1
            camera_summary[obs.camera_id]['species'].add(obs.species)
            
            # Video vs image
            if obs.source_video:
                video_observations += 1
            else:
                image_observations += 1
        
        # Convert sets to lists for JSON serialization
        for camera_id in camera_summary:
            camera_summary[camera_id]['species'] = list(camera_summary[camera_id]['species'])
        
        return {
            'total_observations': len(compressed_observations),
            'species_summary': species_summary,
            'camera_summary': camera_summary,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'video_observations': video_observations,
            'image_observations': image_observations,
            'compression_stats': {
                'compression_window_minutes': self.compression_window.total_seconds() / 60,
                'min_confidence': self.min_confidence,
                'min_duration_seconds': self.min_duration_seconds
            }
        }
    
    def save_compressed_observations(self, compressed_observations: List[CompressedObservation], 
                                   output_path: Path) -> None:
        """
        Save compressed observations to a JSON file.
        
        Args:
            compressed_observations: List of compressed observations
            output_path: Path to save the observations
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        serializable_observations = []
        for obs in compressed_observations:
            serializable_observations.append({
                'camera_id': obs.camera_id,
                'species': obs.species,
                'start_time': obs.start_time.isoformat(),
                'end_time': obs.end_time.isoformat(),
                'duration_seconds': obs.duration_seconds,
                'max_confidence': obs.max_confidence,
                'avg_confidence': obs.avg_confidence,
                'frame_count': obs.frame_count,
                'detection_timeline': obs.detection_timeline,
                'source_video': obs.source_video,
                'needs_review': obs.needs_review
            })
        
        # Use storage adapter for file operations
        if hasattr(self, 'storage_adapter') and self.storage_adapter:
            from .interfaces import StorageLocation
            location = StorageLocation.from_url(str(output_path))
            content = json.dumps(serializable_observations, indent=2)
            self.storage_adapter.put(location, content.encode('utf-8'))
        else:
            # Fallback to direct file I/O
            with open(output_path, 'w') as f:
                json.dump(serializable_observations, f, indent=2)
        
        print(f"Saved {len(compressed_observations)} compressed observations to {output_path}")
