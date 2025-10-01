"""
Run Report Generator for Wildlife Pipeline

Generates report.json with pipeline execution statistics.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RunReportGenerator:
    """
    Generate run reports with execution statistics.

    Report includes:
    - estimated_cost_dkk
    - actual_runtime
    - weather_calls
    - cache_hits
    - top3_stands
    """

    def __init__(self, output_dir: str = "/tmp/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self,
                       run_id: str,
                       estimated_cost_dkk: float,
                       actual_runtime_seconds: float,
                       weather_calls: int = 0,
                       cache_hits: int = 0,
                       top3_stands: Optional[List[Dict[str, Any]]] = None,
                       additional_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate run report with execution statistics.

        Args:
            run_id: Unique run identifier
            estimated_cost_dkk: Estimated cost in Danish Kroner
            actual_runtime_seconds: Actual runtime in seconds
            weather_calls: Number of weather API calls
            cache_hits: Number of cache hits
            top3_stands: Top 3 camera stands with statistics
            additional_metrics: Additional metrics to include

        Returns:
            Report dictionary
        """
        try:
            # Calculate cost efficiency
            cost_efficiency = estimated_cost_dkk / actual_runtime_seconds if actual_runtime_seconds > 0 else 0

            # Calculate cache hit rate
            cache_hit_rate = cache_hits / weather_calls if weather_calls > 0 else 0

            # Generate report
            report = {
                'run_id': run_id,
                'generated_at': datetime.now().isoformat(),
                'execution_summary': {
                    'estimated_cost_dkk': round(estimated_cost_dkk, 2),
                    'actual_runtime_seconds': round(actual_runtime_seconds, 2),
                    'actual_runtime_human': self._format_duration(actual_runtime_seconds),
                    'cost_efficiency_dkk_per_second': round(cost_efficiency, 4)
                },
                'weather_statistics': {
                    'weather_calls': weather_calls,
                    'cache_hits': cache_hits,
                    'cache_hit_rate': round(cache_hit_rate, 3),
                    'api_calls_saved': cache_hits
                },
                'top3_stands': top3_stands or [],
                'additional_metrics': additional_metrics or {}
            }

            # Save report to file
            report_file = self.output_dir / f"report_{run_id}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Run report generated: {report_file}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate run report: {e}")
            return {}

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def get_report(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get existing report by run_id."""
        try:
            report_file = self.output_dir / f"report_{run_id}.json"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to get report {run_id}: {e}")
            return None

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all available reports."""
        try:
            reports = []
            for report_file in self.output_dir.glob("report_*.json"):
                try:
                    with open(report_file, 'r') as f:
                        report = json.load(f)
                    reports.append({
                        'run_id': report.get('run_id'),
                        'generated_at': report.get('generated_at'),
                        'file_path': str(report_file)
                    })
                except Exception as e:
                    logger.warning(f"Failed to read report {report_file}: {e}")

            return sorted(reports, key=lambda x: x.get('generated_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Failed to list reports: {e}")
            return []

    def cleanup_old_reports(self, days_to_keep: int = 30):
        """Clean up reports older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleaned_count = 0

            for report_file in self.output_dir.glob("report_*.json"):
                try:
                    file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        report_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old report: {report_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {report_file}: {e}")

            logger.info(f"Cleaned up {cleaned_count} old reports")
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup old reports: {e}")
            return 0
