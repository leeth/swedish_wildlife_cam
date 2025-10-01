# Schema Directory

This directory contains auto-generated JSON Schema files from Pydantic models.

## Generated Schemas

- `events_v1.json` - Events data contract schema
- `detections_v1.json` - Detections data contract schema
- `metadata_v1.json` - Metadata contract schema

## Generation

Run `make schema` to generate all schemas from Pydantic models.

## CI Integration

Schemas are automatically generated and uploaded as artifacts in PR workflows.
