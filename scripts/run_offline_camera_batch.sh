#!/bin/bash
"""
Offline Camera Batch Processing Script

This script runs cost-optimized batch processing for offline camera data:
- Perfect for processing data from offline cameras
- Cost optimization is always enabled (time is not a factor)
- Spot instances with fallback to on-demand
- Automatic infrastructure setup/teardown
- Optional local Stage 3 output download
"""

set -e

# Default configuration
PROFILE="cloud"
REGION="eu-north-1"
SPOT_BID_PERCENTAGE=70
MAX_VCPUS=100
GPU_REQUIRED=true
PRIORITY="normal"
COMPRESSION_WINDOW=10
MIN_CONFIDENCE=0.5
MIN_DURATION=5.0

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
    echo "Offline Camera Batch Processing"
    echo ""
    echo "Usage: $0 [OPTIONS] INPUT_PATH OUTPUT_PATH"
    echo ""
    echo "Arguments:"
    echo "  INPUT_PATH              Input path (file://, s3://, gs://)"
    echo "  OUTPUT_PATH              Output path (file://, s3://, gs://)"
    echo ""
    echo "Options:"
    echo "  --profile PROFILE        Configuration profile (default: cloud)"
    echo "  --region REGION          AWS region (default: eu-north-1)"
    echo "  --local-output PATH      Local output directory for Stage 3 results"
    echo "  --model PATH             Model path override"
    echo "  --conf-threshold FLOAT   Confidence threshold"
    echo "  --spot-bid-percentage INT Spot bid percentage (default: 70)"
    echo "  --max-vcpus INT          Maximum vCPUs (default: 100)"
    echo "  --no-gpu                 Disable GPU requirement"
    echo "  --priority PRIORITY      Job priority: low, normal, high (default: normal)"
    echo "  --compression-window INT Stage 3 compression window in minutes (default: 10)"
    echo "  --min-confidence FLOAT   Minimum confidence for observations (default: 0.5)"
    echo "  --min-duration FLOAT     Minimum duration in seconds (default: 5.0)"
    echo "  --download-stage3        Download Stage 3 output locally"
    echo "  --cost-report            Generate cost optimization report"
    echo "  --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 file:///data/camera1 s3://bucket/output"
    echo "  $0 --local-output ./results --download-stage3 file:///data/camera1 s3://bucket/output"
    echo "  $0 --spot-bid-percentage 80 --cost-report file:///data/camera1 s3://bucket/output"
}

# Parse command line arguments
LOCAL_OUTPUT=""
MODEL=""
CONF_THRESHOLD=""
NO_GPU=false
DOWNLOAD_STAGE3=false
COST_REPORT=false
INPUT_PATH=""
OUTPUT_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --local-output)
            LOCAL_OUTPUT="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --conf-threshold)
            CONF_THRESHOLD="$2"
            shift 2
            ;;
        --spot-bid-percentage)
            SPOT_BID_PERCENTAGE="$2"
            shift 2
            ;;
        --max-vcpus)
            MAX_VCPUS="$2"
            shift 2
            ;;
        --no-gpu)
            NO_GPU=true
            shift
            ;;
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --compression-window)
            COMPRESSION_WINDOW="$2"
            shift 2
            ;;
        --min-confidence)
            MIN_CONFIDENCE="$2"
            shift 2
            ;;
        --min-duration)
            MIN_DURATION="$2"
            shift 2
            ;;
        --download-stage3)
            DOWNLOAD_STAGE3=true
            shift
            ;;
        --cost-report)
            COST_REPORT=true
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
            if [[ -z "$INPUT_PATH" ]]; then
                INPUT_PATH="$1"
            elif [[ -z "$OUTPUT_PATH" ]]; then
                OUTPUT_PATH="$1"
            else
                print_error "Too many arguments"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$INPUT_PATH" || -z "$OUTPUT_PATH" ]]; then
    print_error "INPUT_PATH and OUTPUT_PATH are required"
    show_usage
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "src/munin/cloud/cli.py" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Set GPU requirement
if [[ "$NO_GPU" == true ]]; then
    GPU_REQUIRED=false
fi

print_info "Starting offline camera batch processing"
print_info "Profile: $PROFILE"
print_info "Region: $REGION"
print_info "Input: $INPUT_PATH"
print_info "Output: $OUTPUT_PATH"
print_info "Spot bid percentage: $SPOT_BID_PERCENTAGE%"
print_info "GPU required: $GPU_REQUIRED"
print_info "Priority: $PRIORITY"

if [[ "$DOWNLOAD_STAGE3" == true && -n "$LOCAL_OUTPUT" ]]; then
    print_info "Local Stage 3 output: $LOCAL_OUTPUT"
fi

# Build command
CMD="python src/munin/cloud/cli.py --profile $PROFILE batch --input $INPUT_PATH --output $OUTPUT_PATH"

# Add optional arguments
if [[ -n "$LOCAL_OUTPUT" ]]; then
    CMD="$CMD --local-output $LOCAL_OUTPUT"
fi

if [[ -n "$MODEL" ]]; then
    CMD="$CMD --model $MODEL"
fi

if [[ -n "$CONF_THRESHOLD" ]]; then
    CMD="$CMD --conf-threshold $CONF_THRESHOLD"
fi

CMD="$CMD --spot-bid-percentage $SPOT_BID_PERCENTAGE"
CMD="$CMD --max-vcpus $MAX_VCPUS"
CMD="$CMD --priority $PRIORITY"
CMD="$CMD --compression-window $COMPRESSION_WINDOW"
CMD="$CMD --min-confidence $MIN_CONFIDENCE"
CMD="$CMD --min-duration $MIN_DURATION"

if [[ "$NO_GPU" == true ]]; then
    CMD="$CMD --no-gpu"
fi

if [[ "$DOWNLOAD_STAGE3" == true ]]; then
    CMD="$CMD --download-stage3"
fi

if [[ "$COST_REPORT" == true ]]; then
    CMD="$CMD --cost-report"
fi

# Run the command
print_info "Running cost-optimized batch processing..."
print_info "Command: $CMD"

eval $CMD

if [[ $? -eq 0 ]]; then
    print_success "Offline camera batch processing completed successfully!"
    print_info "Results saved to: $OUTPUT_PATH"
    
    if [[ "$DOWNLOAD_STAGE3" == true && -n "$LOCAL_OUTPUT" ]]; then
        print_info "Local Stage 3 output: $LOCAL_OUTPUT"
        print_info "Check the following files:"
        print_info "  - $LOCAL_OUTPUT/compressed_observations.json"
        print_info "  - $LOCAL_OUTPUT/report.json"
        print_info "  - $LOCAL_OUTPUT/run_stage3_local.py"
    fi
    
    if [[ "$COST_REPORT" == true ]]; then
        print_info "Cost optimization report generated"
    fi
    
else
    print_error "Offline camera batch processing failed!"
    exit 1
fi
