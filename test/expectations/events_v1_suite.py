"""
Great Expectations test suite for events_v1 data contract.

Tests data quality and schema compliance for events.parquet files.
"""

import great_expectations as ge
from great_expectations.core import ExpectationSuite
from great_expectations.dataset import PandasDataset
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any


def create_events_v1_suite() -> ExpectationSuite:
    """Create Great Expectations suite for events_v1 data contract."""
    
    suite = ExpectationSuite(
        expectation_suite_name="events_v1_suite",
        data_asset_type="PandasDataset"
    )
    
    # Column set and types validation
    suite.add_expectation(
        ge.expectations.ExpectColumnSetToEqualSet(
            column_set=[
                'event_id', 'session_id', 'camera_id',
                'timestamp_utc', 'timestamp_original', 'timestamp_corrected',
                'gps_latitude', 'gps_longitude', 'gps_accuracy', 'location_zone',
                'image_path', 'image_width', 'image_height', 'image_format', 'file_size_bytes',
                'detection_count', 'observation_any',
                'temperature_celsius', 'humidity_percent', 'precipitation_mm', 'wind_speed_ms',
                'processing_version', 'contract_version',
                'rule_id', 'map_version',
                'quality_score', 'blur_detected', 'motion_detected'
            ]
        )
    )
    
    # Required columns exist
    required_columns = [
        'event_id', 'session_id', 'camera_id',
        'timestamp_utc', 'timestamp_original', 'timestamp_corrected',
        'image_path', 'image_width', 'image_height', 'image_format', 'file_size_bytes',
        'detection_count', 'observation_any',
        'processing_version', 'contract_version'
    ]
    
    for col in required_columns:
        suite.add_expectation(
            ge.expectations.ExpectColumnToExist(column=col)
        )
    
    # Data type validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='event_id', type_='str')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='session_id', type_='str')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='camera_id', type_='str')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='detection_count', type_='int')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='observation_any', type_='bool')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='image_width', type_='int')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='image_height', type_='int')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='file_size_bytes', type_='int')
    )
    
    # Timestamp validations (UTC)
    timestamp_columns = ['timestamp_utc', 'timestamp_original', 'timestamp_corrected']
    for col in timestamp_columns:
        suite.add_expectation(
            ge.expectations.ExpectColumnValuesToMatchRegex(
                column=col,
                regex=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
            )
        )
    
    # Detection count validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='detection_count',
            min_value=0,
            max_value=1000  # Reasonable upper bound
        )
    )
    
    # Observation logic validation
    suite.add_expectation(
        ge.expectations.ExpectColumnPairValuesToBeEqual(
            column_A='observation_any',
            column_B='detection_count',
            or_equal=False,
            ignore_row_if='both_values_are_missing'
        )
    )
    
    # Image dimensions validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='image_width',
            min_value=1,
            max_value=10000  # Reasonable upper bound
        )
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='image_height',
            min_value=1,
            max_value=10000  # Reasonable upper bound
        )
    )
    
    # File size validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='file_size_bytes',
            min_value=1,
            max_value=100_000_000  # 100MB upper bound
        )
    )
    
    # GPS coordinate validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='gps_latitude',
            min_value=-90,
            max_value=90,
            mostly=0.95  # Allow some missing values
        )
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='gps_longitude',
            min_value=-180,
            max_value=180,
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Weather data validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='humidity_percent',
            min_value=0,
            max_value=100,
            mostly=0.95  # Allow some missing values
        )
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='precipitation_mm',
            min_value=0,
            max_value=1000,  # 1 meter of rain
            mostly=0.95  # Allow some missing values
        )
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='wind_speed_ms',
            min_value=0,
            max_value=100,  # 100 m/s = 360 km/h
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Quality score validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='quality_score',
            min_value=0,
            max_value=1,
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Contract version validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToEqual(
            column='contract_version',
            value='events_v1'
        )
    )
    
    # Uniqueness validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeUnique(column='event_id')
    )
    
    # Image format validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeInSet(
            column='image_format',
            value_set=['JPEG', 'PNG', 'TIFF', 'BMP', 'WEBP']
        )
    )
    
    # Camera ID format validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToMatchRegex(
            column='camera_id',
            regex=r'^cam\d{2}$'  # cam01, cam02, etc.
        )
    )
    
    # Session ID format validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToMatchRegex(
            column='session_id',
            regex=r'^session-\d{4}-\d{2}-\d{2}-\d{6}$'  # session-2024-01-15-143022
        )
    )
    
    return suite


def validate_events_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate events DataFrame against events_v1 suite."""
    
    # Convert DataFrame to Great Expectations dataset
    ge_df = PandasDataset(df)
    
    # Create and run suite
    suite = create_events_v1_suite()
    ge_df.expectation_suite = suite
    
    # Run validations
    results = ge_df.validate()
    
    return {
        'success': results.success,
        'statistics': results.statistics,
        'results': [
            {
                'expectation_type': result.expectation_config.expectation_type,
                'success': result.success,
                'result': result.result
            }
            for result in results.results
        ]
    }


def create_events_checkpoint() -> str:
    """Create checkpoint configuration for events validation."""
    
    checkpoint_config = {
        "name": "events_v1_checkpoint",
        "config_version": 1,
        "class_name": "SimpleCheckpoint",
        "validations": [
            {
                "batch_request": {
                    "datasource_name": "events_datasource",
                    "data_connector_name": "default_inferred_data_connector_name",
                    "data_asset_name": "events_data"
                },
                "expectation_suite_name": "events_v1_suite"
            }
        ]
    }
    
    return checkpoint_config
