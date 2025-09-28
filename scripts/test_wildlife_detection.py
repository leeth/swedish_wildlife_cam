#!/usr/bin/env python3
"""
Test script to demonstrate wildlife detection improvements.
This script shows the difference between the default YOLO model and the wildlife-specific detector.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from wildlife_pipeline.detector import YOLODetector
from wildlife_pipeline.wildlife_detector import WildlifeDetector

def test_detection_comparison(image_path: str, model_path: str = "yolov8n.pt"):
    """Compare detection results between default YOLO and wildlife detector"""
    
    print(f"Testing image: {image_path}")
    print("="*60)
    
    # Test with default YOLO detector
    print("1. Default YOLO Detector Results:")
    print("-" * 40)
    try:
        default_detector = YOLODetector(model_path)
        default_results = default_detector.predict(Path(image_path))
        
        if default_results:
            for det in default_results:
                print(f"   - {det.label}: {det.confidence:.3f}")
        else:
            print("   No detections found")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test with wildlife detector
    print("2. Wildlife Detector Results:")
    print("-" * 40)
    try:
        wildlife_detector = WildlifeDetector(model_path)
        wildlife_results = wildlife_detector.predict(Path(image_path))
        
        if wildlife_results:
            for det in wildlife_results:
                print(f"   - {det.label}: {det.confidence:.3f}")
        else:
            print("   No wildlife detections found")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("="*60)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_wildlife_detection.py <image_path> [model_path]")
        print("Example: python scripts/test_wildlife_detection.py ./data/sample/image.jpg yolov8n.pt")
        sys.exit(1)
    
    image_path = sys.argv[1]
    model_path = sys.argv[2] if len(sys.argv) > 2 else "yolov8n.pt"
    
    if not Path(image_path).exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    test_detection_comparison(image_path, model_path)

if __name__ == "__main__":
    main()
