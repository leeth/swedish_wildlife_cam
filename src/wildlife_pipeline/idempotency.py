"""
Idempotency management for wildlife detection pipeline.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum


class OperationStatus(Enum):
    """Operation status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IdempotencyManager(ABC):
    """Abstract idempotency manager for operation tracking."""
    
    @abstractmethod
    def start_operation(self, operation_id: str, operation_type: str, 
                       input_hash: str, metadata: Dict[str, Any] = None) -> bool:
        """Start an operation if not already in progress."""
        pass
    
    @abstractmethod
    def complete_operation(self, operation_id: str, result: Dict[str, Any] = None) -> None:
        """Mark an operation as completed."""
        pass
    
    @abstractmethod
    def fail_operation(self, operation_id: str, error: str) -> None:
        """Mark an operation as failed."""
        pass
    
    @abstractmethod
    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """Get the status of an operation."""
        pass
    
    @abstractmethod
    def get_operation_result(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed operation."""
        pass
    
    @abstractmethod
    def cleanup_old_operations(self, max_age_hours: int = 24) -> int:
        """Clean up old completed operations."""
        pass


class FileIdempotencyManager(IdempotencyManager):
    """File-based idempotency manager."""
    
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_operation_file(self, operation_id: str) -> Path:
        """Get the file path for an operation."""
        return self.state_dir / f"{operation_id}.json"
    
    def _load_operation_state(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Load operation state from file."""
        operation_file = self._get_operation_file(operation_id)
        if not operation_file.exists():
            return None
        
        try:
            with open(operation_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def _save_operation_state(self, operation_id: str, state: Dict[str, Any]) -> None:
        """Save operation state to file."""
        operation_file = self._get_operation_file(operation_id)
        with open(operation_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def start_operation(self, operation_id: str, operation_type: str, 
                       input_hash: str, metadata: Dict[str, Any] = None) -> bool:
        """Start an operation if not already in progress."""
        existing_state = self._load_operation_state(operation_id)
        
        if existing_state:
            status = OperationStatus(existing_state['status'])
            if status in [OperationStatus.IN_PROGRESS, OperationStatus.COMPLETED]:
                return False  # Operation already exists
        
        # Create new operation state
        state = {
            'operation_id': operation_id,
            'operation_type': operation_type,
            'input_hash': input_hash,
            'status': OperationStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self._save_operation_state(operation_id, state)
        return True
    
    def complete_operation(self, operation_id: str, result: Dict[str, Any] = None) -> None:
        """Mark an operation as completed."""
        state = self._load_operation_state(operation_id)
        if not state:
            raise ValueError(f"Operation {operation_id} not found")
        
        state['status'] = OperationStatus.COMPLETED.value
        state['completed_at'] = datetime.now().isoformat()
        state['result'] = result or {}
        
        self._save_operation_state(operation_id, state)
    
    def fail_operation(self, operation_id: str, error: str) -> None:
        """Mark an operation as failed."""
        state = self._load_operation_state(operation_id)
        if not state:
            raise ValueError(f"Operation {operation_id} not found")
        
        state['status'] = OperationStatus.FAILED.value
        state['failed_at'] = datetime.now().isoformat()
        state['error'] = error
        
        self._save_operation_state(operation_id, state)
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """Get the status of an operation."""
        state = self._load_operation_state(operation_id)
        if not state:
            return None
        
        return OperationStatus(state['status'])
    
    def get_operation_result(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed operation."""
        state = self._load_operation_state(operation_id)
        if not state or state['status'] != OperationStatus.COMPLETED.value:
            return None
        
        return state.get('result', {})
    
    def cleanup_old_operations(self, max_age_hours: int = 24) -> int:
        """Clean up old completed operations."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for operation_file in self.state_dir.glob("*.json"):
            try:
                with open(operation_file, 'r') as f:
                    state = json.load(f)
                
                # Check if operation is old and completed/failed
                if state['status'] in [OperationStatus.COMPLETED.value, OperationStatus.FAILED.value]:
                    created_at = datetime.fromisoformat(state['created_at'])
                    if created_at < cutoff_time:
                        operation_file.unlink()
                        cleaned_count += 1
                        
            except (json.JSONDecodeError, KeyError, ValueError):
                # Remove corrupted files
                operation_file.unlink()
                cleaned_count += 1
        
        return cleaned_count


class IdempotencyError(Exception):
    """Idempotency operation error."""
    pass


def generate_operation_id(operation_type: str, input_data: Dict[str, Any]) -> str:
    """Generate a unique operation ID based on input data."""
    # Create a hash of the input data
    input_str = json.dumps(input_data, sort_keys=True)
    input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
    
    # Combine with operation type and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{operation_type}_{timestamp}_{input_hash}"


def create_idempotency_manager(manager_type: str = "file", **kwargs) -> IdempotencyManager:
    """Factory function to create idempotency managers."""
    if manager_type == "file":
        return FileIdempotencyManager(**kwargs)
    else:
        raise ValueError(f"Unsupported idempotency manager type: {manager_type}")
