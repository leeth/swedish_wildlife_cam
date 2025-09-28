#!/usr/bin/env python3
"""
Test script to demonstrate fox and badger detection capabilities.
This script shows how the Swedish Wildlife Detector handles fox and badger detection.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from wildlife_pipeline.megadetector import SwedishWildlifeDetector

def test_fox_badger_mapping():
    """Test the fox and badger mapping capabilities"""
    
    print("Fox and Badger Detection Test")
    print("=" * 50)
    print()
    
    # Create detector instance
    detector = SwedishWildlifeDetector(conf=0.25)
    
    # Test common misclassifications for fox and badger
    test_cases = [
        ("cat", "fox"),
        ("kitten", "fox"),
        ("red_fox", "fox"),
        ("vulpes_vulpes", "fox"),
        ("marten", "badger"),
        ("weasel", "badger"),
        ("meles_meles", "badger"),
        ("fox", "fox"),
        ("badger", "badger"),
    ]
    
    print("Fox and Badger Mapping Test:")
    print("-" * 40)
    
    for original_label, expected_mapping in test_cases:
        mapped_label = detector._map_to_swedish_wildlife(original_label)
        status = "✅" if mapped_label == expected_mapping else "❌"
        print(f"{status} {original_label:15} → {mapped_label or 'no mapping'}")
    
    print()
    print("Swedish Wildlife Species Supported:")
    print("-" * 40)
    species = detector.get_available_classes()
    for i, species_name in enumerate(sorted(species), 1):
        print(f"  {i:2d}. {species_name}")
    
    print()
    print("Fox and Badger Detection Notes:")
    print("-" * 40)
    print("• Foxes are often misclassified as 'cat' or 'kitten'")
    print("• Badgers are sometimes misclassified as 'marten' or 'weasel'")
    print("• The detector maps these misclassifications to correct species")
    print("• Lower confidence threshold (0.25) may help detect smaller animals")
    print()
    print("If fox/badger are not detected, they might be:")
    print("• Too small in the image")
    print("• Partially obscured")
    print("• In poor lighting conditions")
    print("• Not present in the current image set")

def show_detection_tips():
    """Show tips for better fox and badger detection"""
    
    print("Tips for Better Fox and Badger Detection:")
    print("=" * 50)
    print()
    print("1. Use lower confidence threshold:")
    print("   --conf-thres 0.25")
    print()
    print("2. Check for misclassifications:")
    print("   - Look for 'cat' detections that might be foxes")
    print("   - Look for 'marten' or 'weasel' that might be badgers")
    print()
    print("3. Fox characteristics to look for:")
    print("   - Reddish-brown color")
    print("   - Pointed ears")
    print("   - Bushy tail")
    print("   - Often active at night")
    print()
    print("4. Badger characteristics to look for:")
    print("   - Black and white striped face")
    print("   - Stocky body")
    print("   - Short legs")
    print("   - Often active at night")
    print()
    print("5. Camera trap settings for small mammals:")
    print("   - Lower camera height")
    print("   - Higher resolution")
    print("   - Good lighting")
    print("   - Motion sensitivity")

def main():
    test_fox_badger_mapping()
    print()
    show_detection_tips()

if __name__ == "__main__":
    main()
