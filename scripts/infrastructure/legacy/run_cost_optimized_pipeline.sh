#!/bin/bash
"""
Cost-Optimized Pipeline Runner

This script provides an easy way to run the cost-optimized pipeline:
- Sets up infrastructure with spot instances
- Processes batch jobs with cost optimization
- Downloads Stage 3 output locally
- Tears down infrastructure when complete
"""

set -e

# Default configuration
REGION="eu-north-1"
ENVIRONMENT="production"
LOCAL_OUTPUT="./stage3_output"
JOB_TYPE="image_processing"
PRIORITY="normal"

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

# Function to show usage
show_usage() {
    echo "Cost-Optimized Pipeline Runner"
    echo ""
    echo "Usage: $0 [OPTIONS] INPUT_DATA..."
    echo ""
    echo "Options:"
    echo "  --region REGION           AWS region (default: eu-north-1)"
    echo "  --environment ENV         Environment name (default: production)"
    echo "  --local-output PATH       Local output directory (default: ./stage3_output)"
    echo "  --job-type TYPE           Job type (default: image_processing)"
    echo "  --priority PRIORITY       Job priority: low, normal, high (default: normal)"
    echo "  --download-only           Only download existing Stage 3 output"
    echo "  --analyze-only            Only analyze local Stage 3 output"
    echo "  --status                  Show infrastructure status"
    echo "  --costs                   Show cost metrics"
    echo "  --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/images/*.jpg"
    echo "  $0 --local-output ./results /path/to/videos/*.mp4"
    echo "  $0 --download-only --cloud-path s3://bucket/output --local-output ./results"
    echo "  $0 --analyze-only --local-output ./results"
}

# Parse command line arguments
DOWNLOAD_ONLY=false
ANALYZE_ONLY=false
SHOW_STATUS=false
SHOW_COSTS=false
INPUT_DATA=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --local-output)
            LOCAL_OUTPUT="$2"
            shift 2
            ;;
        --job-type)
            JOB_TYPE="$2"
            shift 2
            ;;
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --download-only)
            DOWNLOAD_ONLY=true
            shift
            ;;
        --analyze-only)
            ANALYZE_ONLY=true
            shift
            ;;
        --status)
            SHOW_STATUS=true
            shift
            ;;
        --costs)
            SHOW_COSTS=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        --*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            INPUT_DATA+=("$1")
            shift
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "scripts/infrastructure/cost_optimized_pipeline.py" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Show status
if [[ "$SHOW_STATUS" == true ]]; then
    print_info "Checking infrastructure status..."
    python scripts/infrastructure/cost_optimized_pipeline.py \
        --region "$REGION" \
        --environment "$ENVIRONMENT" \
        --action status
    exit 0
fi

# Show costs
if [[ "$SHOW_COSTS" == true ]]; then
    print_info "Getting cost metrics..."
    python scripts/infrastructure/cost_optimized_pipeline.py \
        --region "$REGION" \
        --environment "$ENVIRONMENT" \
        --action costs
    exit 0
fi

# Analyze local data only
if [[ "$ANALYZE_ONLY" == true ]]; then
    if [[ -z "$LOCAL_OUTPUT" ]]; then
        print_error "--local-output is required for --analyze-only"
        exit 1
    fi
    
    print_info "Analyzing local Stage 3 output..."
    python scripts/infrastructure/cost_optimized_pipeline.py \
        --region "$REGION" \
        --environment "$ENVIRONMENT" \
        --action analyze-local \
        --local-output "$LOCAL_OUTPUT"
    exit 0
fi

# Download only
if [[ "$DOWNLOAD_ONLY" == true ]]; then
    if [[ -z "$LOCAL_OUTPUT" ]]; then
        print_error "--local-output is required for --download-only"
        exit 1
    fi
    
    print_info "Downloading Stage 3 output..."
    python scripts/infrastructure/cost_optimized_pipeline.py \
        --region "$REGION" \
        --environment "$ENVIRONMENT" \
        --action download-stage3 \
        --cloud-path "s3://wildlife-detection-$ENVIRONMENT-output/output" \
        --local-output "$LOCAL_OUTPUT"
    exit 0
fi

# Full pipeline
if [[ ${#INPUT_DATA[@]} -eq 0 ]]; then
    print_error "No input data provided"
    show_usage
    exit 1
fi

print_info "Starting cost-optimized pipeline..."
print_info "Region: $REGION"
print_info "Environment: $ENVIRONMENT"
print_info "Local output: $LOCAL_OUTPUT"
print_info "Job type: $JOB_TYPE"
print_info "Priority: $PRIORITY"
print_info "Input data: ${#INPUT_DATA[@]} items"

# Create local output directory
mkdir -p "$LOCAL_OUTPUT"

# Run the pipeline
print_info "Running cost-optimized pipeline..."
python scripts/infrastructure/cost_optimized_pipeline.py \
    --region "$REGION" \
    --environment "$ENVIRONMENT" \
    --action run-pipeline \
    --input-data "${INPUT_DATA[@]}" \
    --local-output "$LOCAL_OUTPUT" \
    --job-type "$JOB_TYPE" \
    --priority "$PRIORITY" \
    --output "$LOCAL_OUTPUT/pipeline_result.json"

if [[ $? -eq 0 ]]; then
    print_success "Cost-optimized pipeline completed successfully!"
    print_info "Results saved to: $LOCAL_OUTPUT"
    
    # Show summary if available
    if [[ -f "$LOCAL_OUTPUT/pipeline_result.json" ]]; then
        print_info "Pipeline summary:"
        python -c "
import json
with open('$LOCAL_OUTPUT/pipeline_result.json', 'r') as f:
    result = json.load(f)
    print(f'  Status: {result.get(\"status\", \"unknown\")}')
    if 'cost_report' in result:
        cost = result['cost_report']
        print(f'  Total cost: ${cost.get(\"total_costs\", {}).get(\"total_cost\", 0):.2f}')
        print(f'  Savings: ${cost.get(\"pipeline_costs\", {}).get(\"savings\", 0):.2f}')
        print(f'  Jobs processed: {cost.get(\"efficiency_metrics\", {}).get(\"jobs_processed\", 0)}')
"
    fi
    
    # Run local analysis
    print_info "Running local Stage 3 analysis..."
    python scripts/infrastructure/cost_optimized_pipeline.py \
        --region "$REGION" \
        --environment "$ENVIRONMENT" \
        --action analyze-local \
        --local-output "$LOCAL_OUTPUT"
    
    print_success "Pipeline and analysis completed!"
    print_info "Check the following files:"
    print_info "  - $LOCAL_OUTPUT/compressed_observations.json"
    print_info "  - $LOCAL_OUTPUT/report.json"
    print_info "  - $LOCAL_OUTPUT/run_stage3_local.py"
    print_info "  - $LOCAL_OUTPUT/pipeline_result.json"
    
else
    print_error "Pipeline failed!"
    exit 1
fi
