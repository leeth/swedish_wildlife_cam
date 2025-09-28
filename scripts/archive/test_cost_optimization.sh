#!/bin/bash
"""
Test Cost Optimization with Real Trailcam Data

This script tests the cost optimization functionality with real trailcam data:
- 25 random images
- 5 random videos
- Cost-optimized batch processing
- Local Stage 3 output download
"""

set -e

# Configuration
TEST_DATA_DIR="/home/asbjorn/projects/wildlife_pipeline_starter/test_data"
LOCAL_OUTPUT_DIR="/home/asbjorn/projects/wildlife_pipeline_starter/test_results"
REGION="eu-north-1"
ENVIRONMENT="production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info "🧪 Testing Cost Optimization with Real Trailcam Data"
print_info "Test data directory: $TEST_DATA_DIR"
print_info "Local output directory: $LOCAL_OUTPUT_DIR"
print_info "Region: $REGION"
print_info "Environment: $ENVIRONMENT"

# Check if test data exists
if [[ ! -d "$TEST_DATA_DIR" ]]; then
    print_error "Test data directory not found: $TEST_DATA_DIR"
    exit 1
fi

# Count files
IMAGE_COUNT=$(find "$TEST_DATA_DIR" -name "*.jpg" | wc -l)
VIDEO_COUNT=$(find "$TEST_DATA_DIR" -name "*.mp4" | wc -l)
TOTAL_FILES=$((IMAGE_COUNT + VIDEO_COUNT))

print_info "Found $IMAGE_COUNT images and $VIDEO_COUNT videos (total: $TOTAL_FILES files)"

# Create local output directory
mkdir -p "$LOCAL_OUTPUT_DIR"

# Check if we're in the right directory
if [[ ! -f "src/cost_optimization/cli.py" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Test 1: Basic cost optimization setup
print_info "Test 1: Setting up cost-optimized infrastructure"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    infra setup \
    --job-count 1 \
    --gpu-required

if [[ $? -eq 0 ]]; then
    print_success "Infrastructure setup completed"
else
    print_error "Infrastructure setup failed"
    exit 1
fi

# Test 2: Check infrastructure status
print_info "Test 2: Checking infrastructure status"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    infra status

# Test 3: Get cost metrics
print_info "Test 3: Getting cost metrics"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    infra costs

# Test 4: Run cost-optimized batch processing
print_info "Test 4: Running cost-optimized batch processing"
print_info "Processing $TOTAL_FILES files from trailcam data..."

python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    batch \
    --input "file://$TEST_DATA_DIR" \
    --output "s3://wildlife-detection-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/test_output" \
    --local-output "$LOCAL_OUTPUT_DIR" \
    --job-count 1 \
    --gpu-required \
    --priority normal \
    --spot-bid-percentage 70 \
    --max-vcpus 100 \
    --download-stage3 \
    --cost-report

if [[ $? -eq 0 ]]; then
    print_success "Cost-optimized batch processing completed"
else
    print_error "Cost-optimized batch processing failed"
    exit 1
fi

# Test 5: Download Stage 3 output (if not already downloaded)
print_info "Test 5: Downloading Stage 3 output"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    stage3 download \
    --cloud-path "s3://wildlife-detection-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)/test_output" \
    --local-path "$LOCAL_OUTPUT_DIR" \
    --summary \
    --create-runner

# Test 6: Analyze local Stage 3 data
print_info "Test 6: Analyzing local Stage 3 data"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    stage3 analyze \
    --local-path "$LOCAL_OUTPUT_DIR"

# Test 7: Run local Stage 3 runner (if created)
if [[ -f "$LOCAL_OUTPUT_DIR/run_stage3_local.py" ]]; then
    print_info "Test 7: Running local Stage 3 analysis"
    cd "$LOCAL_OUTPUT_DIR"
    python run_stage3_local.py
    cd - > /dev/null
else
    print_warning "Local Stage 3 runner not found, skipping local analysis"
fi

# Test 8: Teardown infrastructure
print_info "Test 8: Tearing down infrastructure"
python src/cost_optimization/cli.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --verbose \
    infra teardown

if [[ $? -eq 0 ]]; then
    print_success "Infrastructure teardown completed"
else
    print_warning "Infrastructure teardown failed (this is often expected)"
fi

# Show results
print_success "🎉 Cost Optimization Test Completed!"
print_info "Results saved to: $LOCAL_OUTPUT_DIR"
print_info "Check the following files:"
print_info "  - $LOCAL_OUTPUT_DIR/compressed_observations.json"
print_info "  - $LOCAL_OUTPUT_DIR/report.json"
print_info "  - $LOCAL_OUTPUT_DIR/run_stage3_local.py"

# Show file sizes
if [[ -d "$LOCAL_OUTPUT_DIR" ]]; then
    print_info "Local output directory contents:"
    ls -la "$LOCAL_OUTPUT_DIR"
    
    print_info "Total size: $(du -sh "$LOCAL_OUTPUT_DIR" | cut -f1)"
fi

print_success "Test completed successfully! 🚀💰"
