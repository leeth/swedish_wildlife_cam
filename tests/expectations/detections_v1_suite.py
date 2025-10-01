"""
Great Expectations test suite for detections_v1 data contract.

Tests data quality and schema compliance for detections.parquet files.
"""

import great_expectations as ge
from great_expectations.core import ExpectationSuite
from great_expectations.dataset import PandasDataset
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any


def create_detections_v1_suite() -> ExpectationSuite:
    """Create Great Expectations suite for detections_v1 data contract."""
    
    suite = ExpectationSuite(
        expectation_suite_name="detections_v1_suite",
        data_asset_type="PandasDataset"
    )
    
    # Column set and types validation
    suite.add_expectation(
        ge.expectations.ExpectColumnSetToEqualSet(
            column_set=[
                'detection_id', 'event_id', 'session_id', 'camera_id',
                'timestamp_utc', 'timestamp_original',
                'label', 'confidence', 'bounding_box',
                'image_path', 'image_width', 'image_height',
                'gps_latitude', 'gps_longitude', 'location_zone',
                'species', 'species_confidence', 'age_class', 'sex',
                'detection_method', 'model_version', 'processing_version', 'contract_version',
                'quality_score', 'blur_detected', 'occlusion_level',
                'rule_id', 'map_version'
            ]
        )
    )
    
    # Required columns exist
    required_columns = [
        'detection_id', 'event_id', 'session_id', 'camera_id',
        'timestamp_utc', 'timestamp_original',
        'label', 'confidence',
        'image_path', 'image_width', 'image_height',
        'detection_method', 'model_version', 'processing_version', 'contract_version'
    ]
    
    for col in required_columns:
        suite.add_expectation(
            ge.expectations.ExpectColumnToExist(column=col)
        )
    
    # Data type validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='detection_id', type_='str')
    )
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
        ge.expectations.ExpectColumnValuesToBeOfType(column='label', type_='str')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='confidence', type_='float')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='image_width', type_='int')
    )
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeOfType(column='image_height', type_='int')
    )
    
    # Timestamp validations (UTC)
    timestamp_columns = ['timestamp_utc', 'timestamp_original']
    for col in timestamp_columns:
        suite.add_expectation(
            ge.expectations.ExpectColumnValuesToMatchRegex(
                column=col,
                regex=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
            )
        )
    
    # Confidence validation [0,1]
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='confidence',
            min_value=0,
            max_value=1
        )
    )
    
    # Species confidence validation [0,1]
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='species_confidence',
            min_value=0,
            max_value=1,
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Quality score validation [0,1]
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='quality_score',
            min_value=0,
            max_value=1,
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Occlusion level validation [0,1]
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeBetween(
            column='occlusion_level',
            min_value=0,
            max_value=1,
            mostly=0.95  # Allow some missing values
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
    
    # Label whitelist validation
    allowed_labels = {
        'deer', 'roe_deer', 'red_deer', 'moose', 'elk',
        'boar', 'wild_boar', 'bear', 'wolf', 'lynx',
        'fox', 'red_fox', 'badger', 'otter', 'beaver',
        'bird', 'eagle', 'owl', 'crow', 'raven',
        'human', 'vehicle', 'bicycle', 'motorcycle',
        'unknown', 'other'
    }
    
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeInSet(
            column='label',
            value_set=list(allowed_labels)
        )
    )
    
    # Age class validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeInSet(
            column='age_class',
            value_set=['adult', 'juvenile', 'subadult', 'unknown'],
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Sex validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeInSet(
            column='sex',
            value_set=['male', 'female', 'unknown'],
            mostly=0.95  # Allow some missing values
        )
    )
    
    # Detection method validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeInSet(
            column='detection_method',
            value_set=['yolo', 'manual', 'automated', 'hybrid']
        )
    )
    
    # Contract version validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToEqual(
            column='contract_version',
            value='detections_v1'
        )
    )
    
    # Uniqueness validations
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToBeUnique(column='detection_id')
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
    
    # Bounding box validation (assuming bounding_box is a JSON string)
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToMatchRegex(
            column='bounding_box',
            regex=r'^\{"x_min":\d+\.?\d*,"y_min":\d+\.?\d*,"x_max":\d+\.?\d*,"y_max":\d+\.?\d*\}$'
        )
    )
    
    # Model version format validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToMatchRegex(
            column='model_version',
            regex=r'^v\d+\.\d+\.\d+$'  # v1.0.0, v2.1.3, etc.
        )
    )
    
    # Processing version format validation
    suite.add_expectation(
        ge.expectations.ExpectColumnValuesToMatchRegex(
            column='processing_version',
            regex=r'^v\d+\.\d+\.\d+$'  # v1.0.0, v2.1.3, etc.
        )
    )
    
    return suite


def validate_detections_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate detections DataFrame against detections_v1 suite."""
    
    # Convert DataFrame to Great Expectations dataset
    ge_df = PandasDataset(df)
    
    # Create and run suite
    suite = create_detections_v1_suite()
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


def create_detections_checkpoint() -> str:
    """Create checkpoint configuration for detections validation."""
    
    checkpoint_config = {
        "name": "detections_v1_checkpoint",
        "config_version": 1,
        "class_name": "SimpleCheckpoint",
        "validations": [
            {
                "batch_request": {
                    "datasource_name": "detections_datasource",
                    "data_connector_name": "default_inferred_data_connector_name",
                    "data_asset_name": "detections_data"
                },
                "expectation_suite_name": "detections_v1_suite"
            }
        ]
    }
    
    return checkpoint_config


def validate_bounding_boxes_within_image(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate that bounding boxes are within image bounds."""
    
    results = []
    
    for idx, row in df.iterrows():
        try:
            import json
            bbox = json.loads(row['bounding_box'])
            
            x_min = bbox['x_min']
            y_min = bbox['y_min']
            x_max = bbox['x_max']
            y_max = bbox['y_max']
            
            image_width = row['image_width']
            image_height = row['image_height']
            
            # Check if bounding box is within image bounds
            within_bounds = (
                x_min >= 0 and x_max <= image_width and
                y_min >= 0 and y_max <= image_height
            )
            
            results.append({
                'detection_id': row['detection_id'],
                'within_bounds': within_bounds,
                'bbox': bbox,
                'image_dimensions': (image_width, image_height)
            })
            
        except Exception as e:
            results.append({
                'detection_id': row['detection_id'],
                'within_bounds': False,
                'error': str(e)
            })
    
    return {
        'total_detections': len(results),
        'within_bounds': sum(1 for r in results if r.get('within_bounds', False)),
        'out_of_bounds': sum(1 for r in results if not r.get('within_bounds', False)),
        'results': results
    }
