#!/usr/bin/env python3
"""
OilBoy Standalone Controller - Local Build Script
Author: Colin Monks, PhD
Company: Intelligent Imaging Innovations, Inc.
Version: V1.0
Date: 2025

This script builds the OilBoy Standalone Controller into a Windows executable.
Keep this file locally - it's not tracked in git.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("OilBoy Standalone Controller - Build Script")
    print("=" * 50)
    
    # Clean up previous builds
    print("Cleaning up previous builds...")
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  Removed {dir_name}/")
            except PermissionError:
                print(f"  Warning: Could not remove {dir_name}/ (may be in use)")
    
    # Remove spec file if it exists
    spec_file = "OilBoy_Standalone_Controller.spec"
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"  Removed {spec_file}")
        except PermissionError:
            print(f"  Warning: Could not remove {spec_file}")
    
    # Build the application
    print("\nBuilding application...")
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=OilBoy_Standalone_Controller',
        '--add-data=OilBoy_software logo.png;.',
        '--add-data=oilboy_config.json;.',
        '--hidden-import=bleak',
        '--hidden-import=winrt',
        '--hidden-import=asyncio',
        '--hidden-import=asyncio.windows_events',
        '--hidden-import=asyncio.windows_utils',
        '--hidden-import=winrt.windows.devices.bluetooth',
        '--hidden-import=winrt.windows.devices.bluetooth.advertisement',
        '--hidden-import=winrt.windows.devices.enumeration',
        '--hidden-import=winrt.windows.foundation',
        '--hidden-import=winrt.windows.storage.streams',
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageTk',
        'oilboy_standalone_app.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        
        # Check if executable was created
        exe_path = Path("dist/OilBoy_Standalone_Controller.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Executable created: {exe_path} ({size_mb:.1f} MB)")
        else:
            print("Warning: Executable not found in dist/")
            
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code {e.returncode}")
        print("Error output:")
        print(e.stderr)
        return 1
    except FileNotFoundError:
        print("Error: PyInstaller not found. Please install it with:")
        print("pip install pyinstaller")
        return 1
    
    print("\nBuild process completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 