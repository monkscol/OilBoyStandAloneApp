#!/usr/bin/env python3
"""
Simple Build Script for OilBoy with Graphics

This script includes only the essential PIL modules that work.

Author: Colin Monks, PhD
Company: Intelligent Imaging Innovations, Inc.
Version: V1.0.1
Date: 2025
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """Main build process with graphics and icons"""
    print("OilBoy Standalone Controller - Simple Graphics Build")
    print("Author: Colin Monks, PhD")
    print("Company: Intelligent Imaging Innovations, Inc.")
    print("Version: V1.0.1")
    print("Date: 2025\n")
    
    # Create icon file first (only if missing)
    if not os.path.exists("oilboy_icon.ico"):
        print("Creating application icon...")
        try:
            result = subprocess.run([sys.executable, "create_icon.py"], check=True, capture_output=True, text=True)
            print("✓ Icon created successfully")
        except subprocess.CalledProcessError as e:
            print("⚠ Warning: Could not create icon file")
            print("  Icon will be created at runtime instead")
        except FileNotFoundError:
            print("⚠ Warning: create_icon.py not found")
    else:
        print("✓ Icon already exists, skipping creation")
    
    # Clean previous builds
    print("Cleaning previous builds...")
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✓ Removed {dir_name} directory")
            except Exception as e:
                print(f"⚠ Warning: Could not remove {dir_name}: {e}")
    
    # Build command with ONLY essential modules
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single executable
        "--windowed",                   # No console window
        "--clean",                      # Clean cache
        "--noconfirm",                  # Don't ask for confirmation
        "--name=OilBoy_Standalone_Controller",
        "--add-data=OilBoy_software logo.png;.",
        "--add-data=oilboy_config.json;.",
        "--add-data=SBAccess.py;.",
        "--add-data=BaseDecoder.py;.",
        "--add-data=ByteUtil.py;.",
        "--add-data=CMetadataLib.py;.",
        "--add-data=CSBPoint.py;.",
        # ONLY essential PIL imports that work
        "--hidden-import=PIL",
        "--hidden-import=PIL._imaging",
        "--hidden-import=PIL._imagingtk",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        # BLE-specific hidden imports (working ones)
        "--hidden-import=bleak",
        "--hidden-import=bleak.backends",
        "--hidden-import=bleak.backends.winrt",
        "--hidden-import=bleak.backends.winrt.scanner",
        "--hidden-import=bleak.backends.winrt.client",
        "--hidden-import=bleak.backends.winrt.characteristic",
        "--hidden-import=bleak.backends.winrt.service",
        "--hidden-import=bleak.backends.winrt.descriptor",
        "--hidden-import=asyncio",
        "--hidden-import=asyncio.windows_events",
        "--hidden-import=asyncio.windows_utils",
        "--hidden-import=asyncio.selector_events",
        "--hidden-import=asyncio.proactor_events",
        "--hidden-import=asyncio.base_events",
        "--hidden-import=asyncio.futures",
        "--hidden-import=asyncio.tasks",
        # Windows-specific imports (working ones)
        "--hidden-import=winrt",
        "--hidden-import=winrt.windows.devices.bluetooth",
        "--hidden-import=winrt.windows.devices.bluetooth.genericattributeprofile",
        "--hidden-import=winrt.windows.devices.enumeration",
        "--hidden-import=winrt.windows.foundation",
        "--hidden-import=winrt.windows.storage.streams",
        "oilboy_standalone_app.py"
    ]
    
    # Add icon if it exists
    if os.path.exists("oilboy_icon.ico"):
        cmd.extend(["--icon=oilboy_icon.ico"])
        print("✓ Using custom icon")
    
    print("\nBuilding application with essential graphics and BLE support...")
    
    try:
        subprocess.check_call(cmd)
        print("✓ Application built successfully!")
        
        # Check if executable was created
        exe_path = Path("dist/OilBoy_Standalone_Controller.exe")
        if exe_path.exists():
            print(f"✓ Executable created: {exe_path}")
            print(f"  Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
            
        else:
            print("✗ Executable not found in dist folder")
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed with error: {e}")
        return False
    
    print("\n=== Build Complete ===")
    print("✓ Application executable: dist/OilBoy_Standalone_Controller.exe")
    print("\nTry running the executable now!")
    
    return True

if __name__ == "__main__":
    main() 