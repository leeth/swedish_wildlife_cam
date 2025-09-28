#!/usr/bin/env python3
"""
Test Odin Pipeline Execution

This script tests Odin's pipeline execution with different scenarios:
- Small dataset (3 files)
- Medium dataset (10 files)
- Full dataset (all files)
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.append(str(Path(__file__).parent))

from odin import Odin

def test_small_pipeline():
    """Test pipeline with small dataset."""
    print("🧪 Test 1: Small Pipeline (3 files)")
    print("=" * 40)
    
    odin = Odin()
    
    # Create small test dataset
    test_data_dir = Path("test_data_small")
    test_data_dir.mkdir(exist_ok=True)
    
    # Copy first 3 files
    import shutil
    source_dir = Path("test_data")
    files_copied = 0
    for file_path in source_dir.iterdir():
        if files_copied >= 3:
            break
        if file_path.is_file():
            shutil.copy2(file_path, test_data_dir)
            files_copied += 1
    
    print(f"📁 Created small test dataset: {files_copied} files")
    
    # Run pipeline
    success = odin.run_pipeline("test_data_small", ["stage0", "stage1", "stage2"])
    
    # Cleanup
    shutil.rmtree(test_data_dir, ignore_errors=True)
    
    if success:
        print("✅ Small pipeline test passed")
    else:
        print("❌ Small pipeline test failed")
    
    return success

def test_medium_pipeline():
    """Test pipeline with medium dataset."""
    print("\n🧪 Test 2: Medium Pipeline (10 files)")
    print("=" * 42)
    
    odin = Odin()
    
    # Create medium test dataset
    test_data_dir = Path("test_data_medium")
    test_data_dir.mkdir(exist_ok=True)
    
    # Copy first 10 files
    import shutil
    source_dir = Path("test_data")
    files_copied = 0
    for file_path in source_dir.iterdir():
        if files_copied >= 10:
            break
        if file_path.is_file():
            shutil.copy2(file_path, test_data_dir)
            files_copied += 1
    
    print(f"📁 Created medium test dataset: {files_copied} files")
    
    # Run pipeline
    success = odin.run_pipeline("test_data_medium", ["stage0", "stage1", "stage2"])
    
    # Cleanup
    shutil.rmtree(test_data_dir, ignore_errors=True)
    
    if success:
        print("✅ Medium pipeline test passed")
    else:
        print("❌ Medium pipeline test failed")
    
    return success

def test_full_pipeline():
    """Test pipeline with full dataset."""
    print("\n🧪 Test 3: Full Pipeline (all files)")
    print("=" * 42)
    
    odin = Odin()
    
    # Run pipeline with all data
    success = odin.run_pipeline("test_data", ["stage0", "stage1", "stage2"])
    
    if success:
        print("✅ Full pipeline test passed")
    else:
        print("❌ Full pipeline test failed")
    
    return success

def test_pipeline_stages():
    """Test individual pipeline stages."""
    print("\n🧪 Test 4: Individual Pipeline Stages")
    print("=" * 42)
    
    odin = Odin()
    
    # Test each stage individually
    stages = ["stage0", "stage1", "stage2"]
    results = []
    
    for stage in stages:
        print(f"\n🔍 Testing {stage}...")
        try:
            success = odin.run_pipeline("test_data", [stage])
            results.append((stage, success))
            if success:
                print(f"✅ {stage} test passed")
            else:
                print(f"❌ {stage} test failed")
        except Exception as e:
            print(f"❌ {stage} test failed with exception: {e}")
            results.append((stage, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 Stage Results: {passed}/{total} stages passed")
    
    return passed == total

def main():
    """Run all pipeline tests."""
    print("⚡ Odin Pipeline Tests ⚡")
    print("=" * 30)
    print("Testing Odin's pipeline execution capabilities")
    print()
    
    tests = [
        ("Small Pipeline", test_small_pipeline),
        ("Medium Pipeline", test_medium_pipeline),
        ("Full Pipeline", test_full_pipeline),
        ("Individual Stages", test_pipeline_stages)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Pipeline Test Results Summary")
    print("=" * 35)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All pipeline tests passed!")
        return True
    else:
        print("⚠️  Some pipeline tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
