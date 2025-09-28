#!/usr/bin/env python3
"""
Test script for cloud-optional architecture.
"""

import tempfile
from pathlib import Path
from PIL import Image
import json

def test_local_config():
    """Test local configuration."""
    print("Testing local configuration...")
    
    from src.wildlife_pipeline.cloud import CloudConfig
    
    config = CloudConfig(profile="local")
    
    print(f"Profile: {config.profile}")
    print(f"Storage adapter: {type(config.storage_adapter).__name__}")
    print(f"Queue adapter: {type(config.queue_adapter).__name__}")
    print(f"Model provider: {type(config.model_provider).__name__}")
    print(f"Runner: {type(config.runner).__name__}")
    
    # Test storage operations
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        from src.wildlife_pipeline.cloud.interfaces import StorageLocation
        
        location = StorageLocation.from_url(f"file://{test_file}")
        
        # Test storage adapter
        content = config.storage_adapter.get(location)
        print(f"Storage test: {content.decode('utf-8')}")
        
        # Test manifest creation
        from src.wildlife_pipeline.cloud.interfaces import ManifestEntry
        
        manifest_entry = ManifestEntry(
            source_path="file://test.jpg",
            crop_path="file://crop.jpg",
            camera_id="camera_1",
            timestamp="2025-09-07T10:30:00",
            bbox={"x1": 100, "y1": 200, "x2": 300, "y2": 400},
            det_score=0.85,
            stage1_model="megadetector",
            config_hash="abc123"
        )
        
        print(f"Manifest entry: {manifest_entry.to_dict()}")
    
    print("✅ Local configuration test passed")


def test_cloud_config():
    """Test cloud configuration."""
    print("\nTesting cloud configuration...")
    
    from src.wildlife_pipeline.cloud import CloudConfig
    
    config = CloudConfig(profile="cloud")
    
    print(f"Profile: {config.profile}")
    print(f"Storage adapter: {type(config.storage_adapter).__name__}")
    print(f"Queue adapter: {type(config.queue_adapter).__name__}")
    print(f"Model provider: {type(config.model_provider).__name__}")
    print(f"Runner: {type(config.runner).__name__}")
    
    # Test configuration values
    stage1_config = config.get_stage1_config()
    print(f"Stage-1 config: {stage1_config}")
    
    stage2_config = config.get_stage2_config()
    print(f"Stage-2 config: {stage2_config}")
    
    print("✅ Cloud configuration test passed")


def test_storage_adapters():
    """Test storage adapters."""
    print("\nTesting storage adapters...")
    
    from src.wildlife_pipeline.cloud.storage import LocalFSAdapter, S3Adapter, GCSAdapter
    from src.wildlife_pipeline.cloud.interfaces import StorageLocation
    
    # Test LocalFSAdapter
    with tempfile.TemporaryDirectory() as temp_dir:
        adapter = LocalFSAdapter(base_path=f"file://{temp_dir}")
        
        # Test put/get
        location = StorageLocation.from_url("file://test.txt")
        content = b"Hello, World!"
        adapter.put(location, content)
        
        retrieved = adapter.get(location)
        assert retrieved == content, "Storage content mismatch"
        
        # Test exists
        assert adapter.exists(location), "File should exist"
        
        # Test list
        files = adapter.list(StorageLocation.from_url("file://"))
        assert len(files) == 1, "Should find one file"
        
        # Test delete
        adapter.delete(location)
        assert not adapter.exists(location), "File should be deleted"
    
    print("✅ Storage adapters test passed")


def test_manifest_schema():
    """Test manifest schema."""
    print("\nTesting manifest schema...")
    
    from src.wildlife_pipeline.cloud.interfaces import ManifestEntry, Stage2Entry
    
    # Test ManifestEntry
    manifest_entry = ManifestEntry(
        source_path="s3://bucket/images/camera1/2025-09-07/image1.jpg",
        crop_path="s3://bucket/crops/camera1/2025-09-07/crop1.jpg",
        camera_id="camera_1",
        timestamp="2025-09-07T10:30:00",
        bbox={"x1": 100, "y1": 200, "x2": 300, "y2": 400},
        det_score=0.85,
        stage1_model="megadetector",
        config_hash="abc123",
        latitude=59.3293,
        longitude=18.0686,
        image_width=1920,
        image_height=1080
    )
    
    # Test serialization
    manifest_dict = manifest_entry.to_dict()
    print(f"Manifest entry: {json.dumps(manifest_dict, indent=2)}")
    
    # Test deserialization
    restored_entry = ManifestEntry.from_dict(manifest_dict)
    assert restored_entry.source_path == manifest_entry.source_path
    assert restored_entry.camera_id == manifest_entry.camera_id
    assert restored_entry.latitude == manifest_entry.latitude
    
    # Test Stage2Entry
    stage2_entry = Stage2Entry(
        crop_path="s3://bucket/crops/camera1/2025-09-07/crop1.jpg",
        label="moose",
        confidence=0.92,
        auto_ok=True,
        stage2_model="yolo_cls",
        stage1_model="megadetector",
        config_hash="abc123"
    )
    
    stage2_dict = stage2_entry.to_dict()
    print(f"Stage-2 entry: {json.dumps(stage2_dict, indent=2)}")
    
    print("✅ Manifest schema test passed")


def test_cli_interface():
    """Test CLI interface."""
    print("\nTesting CLI interface...")
    
    from src.wildlife_pipeline.cloud.cli import create_parser
    
    parser = create_parser()
    
    # Test help
    help_text = parser.format_help()
    assert "stage1" in help_text, "Should include stage1 command"
    assert "stage2" in help_text, "Should include stage2 command"
    assert "materialize" in help_text, "Should include materialize command"
    assert "status" in help_text, "Should include status command"
    
    # Test argument parsing
    args = parser.parse_args(["--profile", "local", "stage1", "--input", "file://./data", "--output", "file://./results"])
    assert args.profile == "local", "Profile should be local"
    assert args.command == "stage1", "Command should be stage1"
    assert args.input == "file://./data", "Input should be correct"
    assert args.output == "file://./results", "Output should be correct"
    
    print("✅ CLI interface test passed")


def main():
    """Run all tests."""
    print("Testing cloud-optional architecture...")
    
    try:
        test_local_config()
        test_cloud_config()
        test_storage_adapters()
        test_manifest_schema()
        test_cli_interface()
        
        print("\n🎉 All tests passed! Cloud-optional architecture is working correctly.")
        
        print("\n📋 Usage examples:")
        print("  # Local processing")
        print("  python -m src.wildlife_pipeline.cloud.cli stage1 --profile local --input file://./data --output file://./results")
        print("  python -m src.wildlife_pipeline.cloud.cli stage2 --profile local --manifest file://./results/stage1/manifest.jsonl --output file://./results")
        print("  python -m src.wildlife_pipeline.cloud.cli materialize --profile local --manifest file://./results/stage1/manifest.jsonl --output file://./results/final.parquet")
        
        print("\n  # Cloud processing")
        print("  python -m src.wildlife_pipeline.cloud.cli stage1 --profile cloud --input s3://bucket/data --output s3://bucket/results")
        print("  python -m src.wildlife_pipeline.cloud.cli stage2 --profile cloud --manifest s3://bucket/results/stage1/manifest.jsonl --output s3://bucket/results")
        print("  python -m src.wildlife_pipeline.cloud.cli materialize --profile cloud --manifest s3://bucket/results/stage1/manifest.jsonl --output s3://bucket/results/final.parquet")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
