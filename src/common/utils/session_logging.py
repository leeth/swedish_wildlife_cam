"""
Session-based logging utilities for wildlife pipeline.
Provides session ID generation and session-specific logging.
Integrates with AWS Step Functions execution context.
"""

import logging
import logging.handlers
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json


class SessionLogger:
    """Session-based logger with automatic session ID generation."""

    def __init__(self, session_id: Optional[str] = None, log_dir: str = "logs"):
        """
        Initialize session logger.

        Args:
            session_id: Optional session ID. If None, generates a new one.
            log_dir: Base directory for log files
        """
        self.session_id = session_id or self._generate_session_id()
        self.log_dir = Path(log_dir)
        self._aws_context = self._detect_aws_context()
        self._setup_session_logging()

    def _detect_aws_context(self) -> Dict[str, Any]:
        """Detect if running in AWS Step Functions or Lambda context."""
        aws_context = {}

        # Check for Step Functions execution context
        if os.getenv('AWS_STEP_FUNCTIONS_EXECUTION_NAME'):
            aws_context['execution_name'] = os.getenv('AWS_STEP_FUNCTIONS_EXECUTION_NAME')
            aws_context['execution_arn'] = os.getenv('AWS_STEP_FUNCTIONS_EXECUTION_ARN')
            aws_context['state_machine_name'] = os.getenv('AWS_STEP_FUNCTIONS_STATE_MACHINE_NAME')
            aws_context['context_type'] = 'step_functions'

        # Check for Lambda context
        elif os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            aws_context['function_name'] = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
            aws_context['function_version'] = os.getenv('AWS_LAMBDA_FUNCTION_VERSION')
            aws_context['context_type'] = 'lambda'

        # Check for Batch context
        elif os.getenv('AWS_BATCH_JOB_ID'):
            aws_context['job_id'] = os.getenv('AWS_BATCH_JOB_ID')
            aws_context['job_queue'] = os.getenv('AWS_BATCH_JOB_QUEUE')
            aws_context['context_type'] = 'batch'

        return aws_context

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        # Use AWS execution context if available
        if self._aws_context.get('execution_name'):
            return self._aws_context['execution_name']
        elif self._aws_context.get('function_name'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{self._aws_context['function_name']}_{timestamp}"
        elif self._aws_context.get('job_id'):
            return f"batch_{self._aws_context['job_id']}"

        # Fallback to local generation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _setup_session_logging(self):
        """Setup session-specific logging directories and handlers."""
        # Create session-specific directories
        self.session_dir = self.log_dir / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Create session log file path
        self.session_log_file = self.session_dir / f"session_{self.session_id}.log"

        # Setup session logger
        self.logger = logging.getLogger(f"session_{self.session_id}")
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create session-specific file handler
        session_handler = logging.handlers.RotatingFileHandler(
            self.session_log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )

        # Create formatter with session ID and AWS context
        aws_context_str = ""
        if self._aws_context:
            aws_context_str = f" [AWS:{self._aws_context.get('context_type', 'unknown')}]"

        formatter = logging.Formatter(
            f'%(asctime)s - %(name)s - %(levelname)s - [SESSION:%(session_id)s]{aws_context_str} - %(message)s'
        )
        session_handler.setFormatter(formatter)

        # Add session ID to log records
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.session_id = self.session_id
            return record
        logging.setLogRecordFactory(record_factory)

        self.logger.addHandler(session_handler)

        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Log session start with AWS context
        self.logger.info(f"🚀 Session started: {self.session_id}")
        if self._aws_context:
            self.logger.info(f"☁️  AWS Context: {json.dumps(self._aws_context, indent=2)}")
        self.logger.info(f"📁 Session logs: {self.session_log_file}")

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific component within this session."""
        component_logger = logging.getLogger(f"session_{self.session_id}.{name}")
        component_logger.setLevel(logging.INFO)

        # Add session handler if not already present
        if not any(isinstance(h, logging.handlers.RotatingFileHandler)
                  for h in component_logger.handlers):
            session_handler = logging.handlers.RotatingFileHandler(
                self.session_log_file,
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=3,
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [SESSION:%(session_id)s] - %(message)s'
            )
            session_handler.setFormatter(formatter)
            component_logger.addHandler(session_handler)

        return component_logger

    def log_session_info(self, info: Dict[str, Any]):
        """Log session information."""
        self.logger.info(f"📊 Session Info: {info}")

    def log_session_error(self, error: Exception, context: str = ""):
        """Log session error with context."""
        self.logger.error(f"❌ Session Error {context}: {error}")

    def log_session_success(self, message: str):
        """Log session success."""
        self.logger.info(f"✅ Session Success: {message}")

    def log_s3_path(self, stage: str, s3_path: str, description: str = ""):
        """Log S3 path for data tracking."""
        self.logger.info(f"📁 S3 {stage}: {s3_path} {description}")

    def log_data_flow(self, from_stage: str, to_stage: str, data_path: str):
        """Log data flow between stages."""
        self.logger.info(f"🔄 Data Flow: {from_stage} → {to_stage} via {data_path}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary information."""
        return {
            "session_id": self.session_id,
            "session_log_file": str(self.session_log_file),
            "session_start": datetime.now().isoformat(),
            "log_file_size": self.session_log_file.stat().st_size if self.session_log_file.exists() else 0
        }


def get_session_logger(session_id: Optional[str] = None,
                      component: str = "main",
                      log_dir: str = "logs") -> logging.Logger:
    """
    Get a session-based logger.

    Args:
        session_id: Optional session ID. If None, creates a new session.
        component: Component name for the logger
        log_dir: Base directory for log files

    Returns:
        Configured logger instance
    """
    session_logger = SessionLogger(session_id, log_dir)
    return session_logger.get_logger(component)


def cleanup_old_sessions(log_dir: str = "logs", days_to_keep: int = 30):
    """
    Clean up old session log files.

    Args:
        log_dir: Base directory for log files
        days_to_keep: Number of days to keep session logs
    """
    sessions_dir = Path(log_dir) / "sessions"
    if not sessions_dir.exists():
        return

    cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

    for log_file in sessions_dir.glob("session_*.log*"):
        if log_file.stat().st_mtime < cutoff_date:
            log_file.unlink()
            print(f"🗑️  Cleaned up old session log: {log_file}")


def list_active_sessions(log_dir: str = "logs") -> list:
    """
    List active session log files.

    Args:
        log_dir: Base directory for log files

    Returns:
        List of active session information
    """
    sessions_dir = Path(log_dir) / "sessions"
    if not sessions_dir.exists():
        return []

    sessions = []
    for log_file in sessions_dir.glob("session_*.log"):
        session_info = {
            "session_id": log_file.stem.replace("session_", ""),
            "log_file": str(log_file),
            "size": log_file.stat().st_size,
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        }
        sessions.append(session_info)

    return sorted(sessions, key=lambda x: x["modified"], reverse=True)
