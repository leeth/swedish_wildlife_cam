#!/usr/bin/env python3
"""
Training script for custom wildlife detection model.
This script helps you train a YOLO model specifically for moose, boar, and roedeer.
"""

import argparse
import sys
from pathlib import Path
import yaml

def create_dataset_structure(base_path: Path):
    """Create the standard YOLO dataset directory structure"""
    dirs = [
        base_path / "images" / "train",
        base_path / "images" / "val", 
        base_path / "images" / "test",
        base_path / "labels" / "train",
        base_path / "labels" / "val",
        base_path / "labels" / "test"
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

def create_dataset_config(base_path: Path, output_path: str = "wildlife_dataset.yaml"):
    """Create YAML configuration file for the dataset"""
    
    # Wildlife classes
    classes = ["moose", "boar", "roedeer"]
    
    config = {
        'path': str(base_path.absolute()),  # dataset root directory
        'train': 'images/train',  # train images (relative to 'path')
        'val': 'images/val',      # val images (relative to 'path')
        'test': 'images/test',    # test images (optional)
        
        'nc': len(classes),       # number of classes
        'names': classes          # class names
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Dataset configuration saved to {output_path}")
    print(f"Classes: {classes}")
    return config

def train_model(dataset_config: str, epochs: int = 100, imgsz: int = 640):
    """Train the YOLO model using the dataset configuration"""
    try:
        from ultralytics import YOLO
        
        # Load a base model
        model = YOLO('yolov8n.pt')  # start with nano model
        
        # Train the model
        results = model.train(
            data=dataset_config,
            epochs=epochs,
            imgsz=imgsz,
            batch=16,
            name='wildlife_model',
            project='wildlife_training'
        )
        
        print(f"Training completed! Model saved to: {results.save_dir}")
        return results
        
    except ImportError:
        print("Error: ultralytics not installed. Please run: pip install ultralytics")
        return None
    except Exception as e:
        print(f"Training error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Train custom wildlife detection model")
    parser.add_argument("--dataset-path", type=str, default="./dataset", 
                       help="Path to dataset directory")
    parser.add_argument("--create-structure", action="store_true",
                       help="Create dataset directory structure")
    parser.add_argument("--train", action="store_true",
                       help="Start training the model")
    parser.add_argument("--epochs", type=int, default=100,
                       help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="Input image size")
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset_path)
    
    if args.create_structure:
        print("Creating dataset directory structure...")
        create_dataset_structure(dataset_path)
        create_dataset_config(dataset_path)
        
        print("\n" + "="*50)
        print("DATASET SETUP COMPLETE")
        print("="*50)
        print("Next steps:")
        print("1. Add your training images to:")
        print(f"   - {dataset_path}/images/train/")
        print(f"   - {dataset_path}/images/val/")
        print("2. Add corresponding YOLO format labels to:")
        print(f"   - {dataset_path}/labels/train/")
        print(f"   - {dataset_path}/labels/val/")
        print("3. Run: python scripts/train_wildlife_model.py --train")
        print("\nLabel format: <class_id> <x_center> <y_center> <width> <height>")
        print("Class IDs: 0=moose, 1=boar, 2=roedeer")
        
    elif args.train:
        config_file = "wildlife_dataset.yaml"
        if not Path(config_file).exists():
            print(f"Error: {config_file} not found. Run with --create-structure first.")
            sys.exit(1)
            
        print("Starting model training...")
        results = train_model(config_file, args.epochs, args.imgsz)
        
        if results:
            print("\n" + "="*50)
            print("TRAINING COMPLETE")
            print("="*50)
            print(f"Model saved to: {results.save_dir}")
            print("You can now use this model with your pipeline:")
            print(f"python -m wildlife_pipeline.run_pipeline --model {results.save_dir}/weights/best.pt")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
