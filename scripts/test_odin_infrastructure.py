#!/usr/bin/env python3
"""
Test Odin Infrastructure Management

This script tests Odin's infrastructure management capabilities:
- Setup infrastructure
- Scale up/down
- Monitor status
- Run pipeline
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.append(str(Path(__file__).parent))

from odin import Odin

def test_odin_setup():
    """Test Odin infrastructure setup."""
    print("🧪 Test 1: Odin Infrastructure Setup")
    print("=" * 40)
    
    odin = Odin()
    
    # Test setup
    success = odin.setup_infrastructure()
    if success:
        print("✅ Infrastructure setup test passed")
    else:
        print("❌ Infrastructure setup test failed")
    
    return success

def test_odin_status():
    """Test Odin status reporting."""
    print("\n🧪 Test 2: Odin Status Reporting")
    print("=" * 35)
    
    odin = Odin()
    
    try:
        odin.get_status()
        print("✅ Status reporting test passed")
        return True
    except Exception as e:
        print(f"❌ Status reporting test failed: {e}")
        return False

def test_odin_pipeline():
    """Test Odin pipeline execution."""
    print("\n🧪 Test 3: Odin Pipeline Execution")
    print("=" * 38)
    
    odin = Odin()
    
    # Test with small dataset
    success = odin.run_pipeline("test_data", ["stage0", "stage1"])
    if success:
        print("✅ Pipeline execution test passed")
    else:
        print("❌ Pipeline execution test failed")
    
    return success

def main():
    """Run all Odin tests."""
    print("⚡ Odin Infrastructure Tests ⚡")
    print("=" * 35)
    print("Testing Odin's infrastructure management capabilities")
    print()
    
    tests = [
        ("Infrastructure Setup", test_odin_setup),
        ("Status Reporting", test_odin_status),
        ("Pipeline Execution", test_odin_pipeline)
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
    print("\n📊 Test Results Summary")
    print("=" * 25)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All Odin tests passed!")
        return True
    else:
        print("⚠️  Some Odin tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
