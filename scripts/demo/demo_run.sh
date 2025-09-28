#!/usr/bin/env bash
set -euo pipefail
python -m wildlife_pipeline.run_pipeline \
  --input ./data/sample \
  --output ./data/out.parquet \
  --model yolov8n.pt \
  --conf-thres 0.35 \
  --write parquet \
  --preview 10
