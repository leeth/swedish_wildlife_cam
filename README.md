# 🐦‍⬛ Odins Ravne - Swedish Wildlife Intelligence System

**Munin** (Memory Keeper) samler og bevarer vildtdata fra kameraer, mens **Hugin** (Thought Bringer) giver dyb indsigt og forståelse af dyrelivet.

## 🎯 Projekt Oversigt

Odins Ravne er et omfattende system til svensk vildtmonitorering der kombinerer:
- **Munin**: Data indtagelse, procesering og lagring (Stage 0-2)
- **Hugin**: Analyse, indsigt og visualisering (Stage 2+)

## 🚀 Hurtig Start

### Forudsætninger
```bash
# Python 3.9+
pip install -r requirements.txt

# For GPU support (valgfrit)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Lokal Udvikling
```bash
# Munin - Data Indtagelse
cd munin/
pip install -e .
munin ingest /path/to/images /path/to/output

# Hugin - Analyse
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

## 📁 Projekt Struktur

```
├── munin/                    # Memory Keeper (Data Indtagelse)
│   ├── src/munin/           # Core Munin moduler
│   ├── pyproject.toml      # Munin dependencies
│   └── README.md           # Munin dokumentation
├── hugin/                   # Thought Bringer (Analyse)
│   ├── src/hugin/          # Core Hugin moduler
│   ├── pyproject.toml      # Hugin dependencies
│   └── README.md           # Hugin dokumentation
├── scripts/                 # Utility scripts
│   ├── infrastructure/     # AWS/cloud setup
│   ├── image_tools/        # Billedbehandling utilities
│   └── data_upload/        # Cloud data management
└── docs/                   # Dokumentation
    ├── ROADMAP.md          # Udviklings roadmap
    ├── INFRASTRUCTURE.md   # Setup og deployment
    ├── CLOUD_OPTIMIZATION.md # AWS/cloud optimering
    └── UTILITIES.md        # Tools og utilities
```

## 🐦‍⬛ Munin (Memory Keeper)

**Formål**: Data indtagelse, procesering og lagring

**Nøglefunktioner**:
- Svensk vildt detektion (elg, vildsvin, rådyr, ræv, grævling)
- Video frame ekstraktion og analyse
- EXIF metadata procesering
- GPS lokationsklassifikation
- Cloud-optional arkitektur

### 🎥 Video Procesering
- **Frame Ekstraktion**: Ekstraher frames fra MP4, AVI, MOV, MKV videoer
- **Sampling Rate**: Konfigurerbar frame sampling (standard: 0.3 sekunder)
- **Batch Procesering**: Parallel video procesering med multiprocessing
- **GPU Acceleration**: CUDA-accelereret video dekodning
- **Format Support**: MP4, AVI, MOV, MKV, WebM, FLV, WMV

### 🦌 Vildt Detektion Modeller

#### **Swedish Wildlife Detector**
- **Optimeret til svenske arter**: Elg, vildsvin, rådyr, ræv, grævling
- **Misklassifikations korrektion**: Korrigerer automatisk almindelige COCO misklassifikationer
- **Art mapping**: Mapper generiske detektioner til svensk vildt
- **Confidence scoring**: Kalibrerede confidence scores for svenske arter

#### **Wildlife Detector (Generisk)**
- **YOLO-baseret detektion**: Standard YOLOv8 objekt detektion
- **COCO dataset support**: Alle 80 COCO klasser
- **Custom model support**: Indlæs custom trænede modeller
- **Batch processing**: Effektiv batch inference

#### **Detektion Pipeline**
```python
# Svensk Vildt Detektion
detector = SwedishWildlifeDetector(model_path="yolov8n.pt")
detections = detector.predict(image_path)

# Generisk Vildt Detektion  
detector = WildlifeDetector(model_path="custom_model.pt")
detections = detector.predict(image_path)
```

**CLI Kommandoer**:
```bash
munin ingest /input /output --extensions jpg,mp4
munin process /data --stage1 --stage2
munin upload /data --cloud aws
```

## 🧠 Hugin (Thought Bringer)

**Formål**: Analyse, indsigt og visualisering

**Nøglefunktioner**:
- Vildt adfærdsanalyse
- Populationstrends forudsigelse
- Naturbeskyttelses rapportering
- Interaktive dashboards
- Forskningsdata eksport

**CLI Kommandoer**:
```bash
hugin analyze /data --species moose
hugin report /data --format pdf
hugin dashboard /data --web
```

## 🛠️ Teknologi Stack

### Core Teknologier
- **Python 3.9+**: Hovedudviklingssprog
- **PyTorch**: Machine learning framework
- **YOLOv8**: Objekt detektion modeller
- **OpenCV**: Billed/video procesering
- **FastAPI**: Web API framework

### Video Procesering Teknologier
- **PyAV**: Højydelses video frame ekstraktion
- **Decord**: GPU-accelereret video dekodning
- **FFmpeg**: Video format konvertering og procesering
- **CUDA**: GPU acceleration til video procesering
- **Multiprocessing**: Parallel video procesering

### Vildt Detektion Teknologier
- **YOLOv8**: State-of-the-art objekt detektion
- **Swedish Wildlife Detector**: Custom art mapping
- **COCO Dataset**: 80-klasse objekt detektion
- **TensorRT**: GPU inference optimering
- **ONNX**: Cross-platform model deployment

### Cloud Teknologier
- **AWS**: S3, Batch, ECR, CloudFormation
- **Docker**: Containerisering
- **Terraform**: Infrastructure as Code

### Data Formater
- **Parquet**: Kolonne data lagring
- **JSONL**: Manifest filer
- **SQLite**: Lokal database
- **CSV**: Eksport format

## 📊 Nuværende Status

### ✅ Completed (Munin)
- Core pipeline implementering (Stage 0-2)
- Svensk vildt detektion optimering
- Video procesering med frame ekstraktion
- Flere vildt detektor modeller
- Cloud-optional arkitektur
- AWS infrastruktur setup
- Sikkerhed implementering
- Omfattende testning

### 🚧 I Gang (Hugin)
- Analyse framework
- Data modeller og validering
- Grundlæggende rapporterings funktioner

### 📋 Roadmap
Se [ROADMAP.md](docs/ROADMAP.md) for detaljeret udviklingsplan.

## 🔧 Setup & Deployment

- **Lokal Setup**: [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
- **Cloud Optimering**: [CLOUD_OPTIMIZATION.md](docs/CLOUD_OPTIMIZATION.md)
- **Utilities & Tools**: [UTILITIES.md](docs/UTILITIES.md)

## 🤝 Bidrag

1. Fork repository
2. Opret feature branch
3. Lav dine ændringer
4. Tilføj tests
5. Submit pull request

## 📄 Licens

Dette projekt er licenseret under MIT License - se LICENSE filen for detaljer.

## 🐦‍⬛ Odins Ravne Team

- **Munin**: Memory Keeper - Data indtagelse og procesering
- **Hugin**: Thought Bringer - Analyse og indsigt
- **Odin**: All-Father - Overordnet system arkitektur

---

**Odins Ravne** - Bringer visdom til vildtbeskyttelse gennem teknologi.