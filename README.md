# 🐦‍⬛ Odins Ravne - Swedish Wildlife Intelligence System

**Munin** (Memory Keeper) samler og bevarer vildtdata fra kameraer, mens **Hugin** (Thought Bringer) giver dyb indsigt og forståelse af dyrelivet.

## 🎯 Project Overview

Odins Ravne er et omfattende system til svensk vildtmonitorering der kombinerer:
- **Munin**: Data ingestion, processing og storage (Stage 0-2)
- **Hugin**: Analytics, insights og visualization (Stage 2+)

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.9+
pip install -r requirements.txt

# For GPU support (optional)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Local Development
```bash
# Munin - Data Ingestion
cd munin/
pip install -e .
munin ingest /path/to/images /path/to/output

# Hugin - Analytics
cd hugin/
pip install -e .
hugin analyze /path/to/data
```

### Cloud Deployment
```bash
# AWS Setup
./scripts/infrastructure/deploy_aws_infrastructure.py
./scripts/infrastructure/create_aws_test_user.py

# Deploy to AWS Batch
aws batch submit-job --job-definition wildlife-pipeline
```

## 📁 Project Structure

```
├── munin/                    # Memory Keeper (Data Ingestion)
│   ├── src/munin/           # Core Munin modules
│   ├── pyproject.toml      # Munin dependencies
│   └── README.md           # Munin documentation
├── hugin/                   # Thought Bringer (Analytics)
│   ├── src/hugin/          # Core Hugin modules
│   ├── pyproject.toml      # Hugin dependencies
│   └── README.md           # Hugin documentation
├── scripts/                 # Utility scripts
│   ├── infrastructure/     # AWS/cloud setup
│   ├── image_tools/        # Image processing utilities
│   └── data_upload/        # Cloud data management
└── docs/                   # Documentation
    ├── ROADMAP.md          # Development roadmap
    ├── INFRASTRUCTURE.md   # Setup and deployment
    ├── CLOUD_OPTIMIZATION.md # AWS/cloud optimization
    └── UTILITIES.md        # Tools and utilities
```

## 🐦‍⬛ Munin (Memory Keeper)

**Purpose**: Data ingestion, processing, and storage

**Key Features**:
- Swedish wildlife detection (moose, boar, roedeer, fox, badger)
- Video frame extraction and analysis
- EXIF metadata processing
- GPS location classification
- Cloud-optional architecture

### 🎥 Video Processing
- **Frame Extraction**: Extract frames from MP4, AVI, MOV, MKV videos
- **Sampling Rate**: Configurable frame sampling (default: 0.3 seconds)
- **Batch Processing**: Parallel video processing with multiprocessing
- **GPU Acceleration**: CUDA-accelerated video decoding
- **Format Support**: MP4, AVI, MOV, MKV, WebM, FLV, WMV

### 🦌 Wildlife Detection Models

#### **Swedish Wildlife Detector**
- **Optimized for Swedish species**: Moose, wild boar, roedeer, red fox, badger
- **Misclassification correction**: Automatically corrects common COCO misclassifications
- **Species mapping**: Maps generic detections to Swedish wildlife
- **Confidence scoring**: Calibrated confidence scores for Swedish species

#### **Wildlife Detector (Generic)**
- **YOLO-based detection**: Standard YOLOv8 object detection
- **COCO dataset support**: All 80 COCO classes
- **Custom model support**: Load custom trained models
- **Batch processing**: Efficient batch inference

#### **Detection Pipeline**
```python
# Swedish Wildlife Detection
detector = SwedishWildlifeDetector(model_path="yolov8n.pt")
detections = detector.predict(image_path)

# Generic Wildlife Detection  
detector = WildlifeDetector(model_path="custom_model.pt")
detections = detector.predict(image_path)
```

**CLI Commands**:
```bash
munin ingest /input /output --extensions jpg,mp4
munin process /data --stage1 --stage2
munin upload /data --cloud aws
```

## 🧠 Hugin (Thought Bringer)

**Purpose**: Analytics, insights, and visualization

**Key Features**:
- Wildlife behavior analysis
- Population trend prediction
- Conservation reporting
- Interactive dashboards
- Research data export

**CLI Commands**:
```bash
hugin analyze /data --species moose
hugin report /data --format pdf
hugin dashboard /data --web
```

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.9+**: Main development language
- **PyTorch**: Machine learning framework
- **YOLOv8**: Object detection models
- **OpenCV**: Image/video processing
- **FastAPI**: Web API framework

### Video Processing Technologies
- **PyAV**: High-performance video frame extraction
- **Decord**: GPU-accelerated video decoding
- **FFmpeg**: Video format conversion and processing
- **CUDA**: GPU acceleration for video processing
- **Multiprocessing**: Parallel video processing

### Wildlife Detection Technologies
- **YOLOv8**: State-of-the-art object detection
- **Swedish Wildlife Detector**: Custom species mapping
- **COCO Dataset**: 80-class object detection
- **TensorRT**: GPU inference optimization
- **ONNX**: Cross-platform model deployment

### Cloud Technologies
- **AWS**: S3, Batch, ECR, CloudFormation
- **Docker**: Containerization
- **Terraform**: Infrastructure as Code

### Data Formats
- **Parquet**: Columnar data storage
- **JSONL**: Manifest files
- **SQLite**: Local database
- **CSV**: Export format

## 📊 Current Status

### ✅ Completed (Munin)
- Core pipeline implementation (Stage 0-2)
- Swedish wildlife detection optimization
- Video processing with frame extraction
- Multiple wildlife detector models
- Cloud-optional architecture
- AWS infrastructure setup
- Security implementation
- Comprehensive testing

### 🚧 In Progress (Hugin)
- Analytics framework
- Data models and validation
- Basic reporting capabilities

### 📋 Roadmap
See [ROADMAP.md](docs/ROADMAP.md) for detailed development plan.

## 🔧 Setup & Deployment

- **Local Setup**: [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
- **Cloud Optimization**: [CLOUD_OPTIMIZATION.md](docs/CLOUD_OPTIMIZATION.md)
- **Utilities & Tools**: [UTILITIES.md](docs/UTILITIES.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐦‍⬛ Odins Ravne Team

- **Munin**: Memory Keeper - Data ingestion and processing
- **Hugin**: Thought Bringer - Analytics and insights
- **Odin**: All-Father - Overall system architecture

---

**Odins Ravne** - Bringing wisdom to wildlife conservation through technology.