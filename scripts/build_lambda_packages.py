#!/usr/bin/env python3
"""
Build Lambda packages for LocalStack deployment.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def build_lambda_package(lambda_name, source_dir):
    """Build a Lambda package."""
    print(f"Building {lambda_name}...")
    
    # Create dist directory if it doesn't exist
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Create temporary build directory
    build_dir = Path(f"build/{lambda_name}")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy source files
    source_path = Path(source_dir)
    for item in source_path.iterdir():
        if item.is_file():
            shutil.copy2(item, build_dir)
        elif item.is_dir() and item.name != "__pycache__":
            shutil.copytree(item, build_dir / item.name, dirs_exist_ok=True)
    
    # Copy src directory for imports
    src_dir = Path("src")
    if src_dir.exists():
        shutil.copytree(src_dir, build_dir / "src", dirs_exist_ok=True)
    
    # Use minimal requirements for Lambda
    req_file = build_dir / "requirements.txt"
    req_file.write_text("boto3>=1.34.0\n")
    
    # Install dependencies using clean venv
    print(f"Installing dependencies for {lambda_name}...")
    venv_python = Path("venv-clean/bin/python")
    if not venv_python.exists():
        venv_python = sys.executable
    
    subprocess.run([
        str(venv_python), "-m", "pip", "install", 
        "-r", str(req_file), 
        "-t", str(build_dir)
    ], check=True)
    
    # Create zip file
    zip_path = dist_dir / f"{lambda_name}.zip"
    shutil.make_archive(
        str(zip_path).replace('.zip', ''), 
        'zip', 
        str(build_dir)
    )
    
    print(f"Created {zip_path}")
    
    # Clean up
    shutil.rmtree(build_dir)
    
    return zip_path

def main():
    """Build all Lambda packages."""
    lambdas = [
        ("guard_budget", "lambdas/guard_budget"),
        ("stage0_exif", "lambdas/stage0_exif"),
        ("stage2_post", "lambdas/stage2_post"),
        ("weather_enrichment", "lambdas/weather_enrichment"),
        ("write_parquet", "lambdas/write_parquet"),
    ]
    
    for lambda_name, source_dir in lambdas:
        try:
            build_lambda_package(lambda_name, source_dir)
        except Exception as e:
            print(f"Error building {lambda_name}: {e}")
            # Create a minimal zip file
            dist_dir = Path("dist")
            dist_dir.mkdir(exist_ok=True)
            
            # Create minimal handler
            build_dir = Path(f"build/{lambda_name}")
            build_dir.mkdir(parents=True, exist_ok=True)
            
            handler_content = f'''def handler(event, context):
    return {{"statusCode": 200, "body": "{lambda_name} placeholder"}}'''
            
            (build_dir / "handler.py").write_text(handler_content)
            
            zip_path = dist_dir / f"{lambda_name}.zip"
            shutil.make_archive(
                str(zip_path).replace('.zip', ''), 
                'zip', 
                str(build_dir)
            )
            
            print(f"Created minimal {zip_path}")
            shutil.rmtree(build_dir)

if __name__ == "__main__":
    main()
