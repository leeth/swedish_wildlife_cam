#!/usr/bin/env python3
"""
Simple test script for weather integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_weather_imports():
    """Test weather module imports."""
    try:
        # Test direct import without going through __init__.py
        from src.munin.observation_weather_enricher import ObservationWeatherEnricher
        print("✅ ObservationWeatherEnricher imported successfully")
        
        from src.munin.weather_enricher import WeatherEnricher
        print("✅ YRWeatherEnricher imported successfully")
        
        # Test initialization
        from pathlib import Path
        db_path = Path("test_weather.db")
        
        enricher = ObservationWeatherEnricher(db_path)
        print("✅ ObservationWeatherEnricher initialized successfully")
        
        yr_enricher = YRWeatherEnricher(db_path)
        print("✅ YRWeatherEnricher initialized successfully")
        
        # Clean up test database
        if db_path.exists():
            db_path.unlink()
            print("✅ Test database cleaned up")
        
        print("\n🎉 All weather integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Weather integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_weather_imports()
    sys.exit(0 if success else 1)
