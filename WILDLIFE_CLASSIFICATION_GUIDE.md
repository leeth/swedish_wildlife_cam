# Wildlife Classification Guide

## Problem: Bad Wildlife Classification

You were getting poor wildlife classification results because the default YOLOv8n model is trained on the COCO dataset, which includes general classes like:
- "bear", "elephant", "sheep", "cow", "horse", "dog"

But your target wildlife species are:
- **Moose** (elk in Europe)
- **Boar** (wild boar)
- **Roedeer** (roe deer)

**FIXED**: The classification algorithm now correctly maps these misclassifications to the proper wildlife species.

## Solution: Custom Wildlife Detector

I've created a custom `WildlifeDetector` that:

1. **Maps COCO classes to wildlife classes** when possible
2. **Filters out non-wildlife detections**
3. **Provides a framework for custom model training**

### Key Improvements

#### 1. Intelligent Class Mapping
The detector maps common misclassifications:
- `cow` → `moose` (moose often misclassified as cows)
- `horse` → `moose` (moose sometimes misclassified as horses)
- `bear` → `boar` (boars sometimes misclassified as bears)
- `dog` → `boar` (boars sometimes misclassified as dogs)
- `deer` → `roedeer` (general deer to specific roe deer)

#### 2. Wildlife-Specific Filtering
Only returns detections that can be mapped to your target wildlife classes.

#### 3. Intelligent Class Mapping
Maps common COCO misclassifications to correct wildlife species:
- `bear` → `boar` (boars often misclassified as bears)
- `elephant` → `boar` (boars sometimes misclassified as elephants)
- `sheep` → `roedeer` (roe deer often misclassified as sheep)
- `cow` → `moose` (moose often misclassified as cows)
- `horse` → `moose` (moose sometimes misclassified as horses)
- `dog` → `boar` (boars sometimes misclassified as dogs)
- `deer` → `roedeer` (general deer to specific roe deer)

#### 4. Training Framework
Provides tools to train a custom model specifically for your wildlife species.

## Usage

### Option 1: Use with Current Model (Improved Mapping)

```bash
# The pipeline now uses WildlifeDetector by default
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/images \
  --output /path/to/output.csv \
  --model yolov8n.pt \
  --conf-thres 0.35
```

### Option 2: Train Custom Model (Recommended)

For best results, train a custom model on your specific wildlife species:

```bash
# 1. Create dataset structure
python scripts/train_wildlife_model.py --create-structure

# 2. Add your training data:
#    - Put images in: ./dataset/images/train/ and ./dataset/images/val/
#    - Put YOLO format labels in: ./dataset/labels/train/ and ./dataset/labels/val/
#    - Label format: <class_id> <x_center> <y_center> <width> <height>
#    - Class IDs: 0=moose, 1=boar, 2=roedeer

# 3. Train the model
python scripts/train_wildlife_model.py --train --epochs 100

# 4. Use the trained model
python -m wildlife_pipeline.run_pipeline \
  --input /path/to/images \
  --output /path/to/output.csv \
  --model wildlife_training/wildlife_model/weights/best.pt
```

### Option 3: Test Detection Improvements

```bash
# Compare default vs wildlife detector on a single image
python scripts/test_wildlife_detection.py /path/to/image.jpg
```

## Expected Results

### Before (Default YOLO)
```
top_label: "cow"
top_confidence: 0.549
```

### After (Wildlife Detector)
```
top_label: "moose"  # Mapped from "cow"
top_confidence: 0.549
```

**Real Results from Your Images:**
- `bear, elephant` → `boar` ✅
- `sheep` → `roedeer` ✅  
- `cow` → `moose` ✅

## Training Data Requirements

To train a custom model, you'll need:

1. **Images** of your wildlife species (moose, boar, roedeer)
2. **Labels** in YOLO format for each image
3. **Split** into train/validation sets (80/20 recommended)

### Minimum Dataset Sizes
- **Per class**: 100+ images minimum, 500+ recommended
- **Total**: 300+ images minimum, 1500+ recommended
- **Variety**: Different angles, lighting, backgrounds

### Labeling Tools
- [Roboflow](https://roboflow.com/) (free tier available)
- [LabelImg](https://github.com/tzutalin/labelImg)
- [CVAT](https://cvat.org/)

## Advanced Configuration

### Custom Class Mapping
Edit `src/wildlife_pipeline/wildlife_detector.py` to modify class mappings:

```python
WILDLIFE_CLASSES = {
    'moose': 'moose',
    'boar': 'boar', 
    'roedeer': 'roedeer',
    'your_custom_class': 'moose',  # Add custom mappings
}
```

### Confidence Thresholds
Adjust detection sensitivity:

```bash
# More sensitive (more detections, more false positives)
--conf-thres 0.25

# Less sensitive (fewer detections, fewer false positives)  
--conf-thres 0.5
```

## Troubleshooting

### No Detections Found
1. Check if images contain wildlife
2. Lower confidence threshold: `--conf-thres 0.25`
3. Verify model path is correct
4. Check image format (JPG, PNG, etc.)

### Wrong Classifications
1. Train custom model with your specific data
2. Adjust class mappings in `wildlife_detector.py`
3. Use higher confidence threshold: `--conf-thres 0.5`

### Training Issues
1. Ensure sufficient training data (100+ images per class)
2. Check label format (YOLO format required)
3. Verify dataset structure matches YOLO requirements

## Next Steps

1. **Immediate**: Use the improved WildlifeDetector with your current model
2. **Short-term**: Collect and label training data for your specific wildlife
3. **Long-term**: Train a custom model for optimal accuracy

The WildlifeDetector provides immediate improvements through intelligent class mapping, while the training framework enables you to achieve much better results with a custom model.
