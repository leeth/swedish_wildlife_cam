# Data Contract Migrations

This document tracks changes to data contracts and schemas.

## Migration Rules

1. **Breaking changes** require a new contract version (e.g., `events_v1` → `events_v2`)
2. **Non-breaking changes** can be made to existing versions
3. **All changes** must be documented in this file
4. **Schema changes** must be validated in CI

## Migration History

### events_v1 (2024-01-15)
- Initial events data contract
- Core fields: event_id, session_id, camera_id, timestamps
- Detection summary: detection_count, observation_any
- Weather enrichment: temperature, humidity, precipitation, wind
- Quality indicators: quality_score, blur_detected, motion_detected

### detections_v1 (2024-01-15)
- Initial detections data contract
- Core fields: detection_id, event_id, bounding_box, confidence
- Species information: species, species_confidence, age_class, sex
- Quality indicators: quality_score, blur_detected, occlusion_level

### metadata_v1 (2024-01-15)
- Initial metadata contract
- EXIF corrections with effective date ranges
- Camera mapping with stable identifiers
- Version tracking and traceability

## Future Migrations

### Planned Changes
- Add new weather data fields (pressure, visibility)
- Extend species classification (subspecies, behavior)
- Add GPS accuracy validation
- Implement data lineage tracking

### Breaking Change Examples
- Renaming required fields
- Changing data types
- Removing required fields
- Changing validation rules

### Non-Breaking Change Examples
- Adding optional fields
- Extending enum values
- Adding new validation rules
- Improving documentation
