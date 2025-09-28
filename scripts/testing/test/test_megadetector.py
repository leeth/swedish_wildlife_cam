#!/usr/bin/env python3
"""
Test script to demonstrate MegaDetector for Swedish wildlife detection.
MegaDetector is specifically designed for camera trap wildlife detection.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from wildlife_pipeline.megadetector import SwedishWildlifeDetector
from wildlife_pipeline.detector import YOLODetector

def test_megadetector_comparison(image_path: str):
    """Compare MegaDetector vs YOLO for wildlife detection"""
    
    print("Swedish Wildlife Detector vs YOLO Comparison")
    print("=" * 60)
    print()
    
    if not Path(image_path).exists():
        print(f"Error: Image file {image_path} not found")
        return
    
    # Test with YOLO
    print("1. YOLO Detector Results:")
    print("-" * 40)
    try:
        yolo_detector = YOLODetector("yolov8n.pt")
        yolo_results = yolo_detector.predict(Path(image_path))
        
        if yolo_results:
            for det in yolo_results:
                print(f"   - {det.label}: {det.confidence:.3f}")
        else:
            print("   No detections found")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test with Swedish Wildlife Detector
    print("2. Swedish Wildlife Detector Results:")
    print("-" * 40)
    try:
        swedish_detector = SwedishWildlifeDetector(conf=0.35)
        swedish_results = swedish_detector.predict(Path(image_path))
        
        if swedish_results:
            for det in swedish_results:
                print(f"   - {det.label}: {det.confidence:.3f}")
        else:
            print("   No detections found")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("=" * 60)
    print()
    print("Swedish Wildlife Detector Advantages:")
    print("• Specifically optimized for Swedish wildlife species")
    print("• Optimized for natural environments")
    print("• Better at detecting animals in challenging conditions")
    print("• Handles Swedish wildlife species well")
    print("• Reduces false positives from non-wildlife objects")

def show_swedish_wildlife_species():
    """Show the Swedish wildlife species that MegaDetector can detect"""
    
    print("Swedish Wildlife Species Supported:")
    print("=" * 50)
    print()
    
    detector = SwedishWildlifeDetector()
    species = detector.get_available_classes()
    
    print("Primary Species:")
    for i, species_name in enumerate(sorted(species), 1):
        print(f"  {i:2d}. {species_name}")
    
    print()
    print("Swedish Wildlife Detector Categories:")
    print("  • animal - Generic animal detection")
    print("  • person - Humans in camera traps")
    print("  • vehicle - Vehicles (rare but possible)")
    print()
    print("Note: The detector focuses on detecting animals rather than")
    print("specific species classification, which is perfect for camera traps.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_megadetector.py <image_path>")
        print()
        show_swedish_wildlife_species()
        return
    
    image_path = sys.argv[1]
    test_megadetector_comparison(image_path)

if __name__ == "__main__":
    main()
