#!/usr/bin/env python3
"""
Create ICO file from PNG logo for OilBoy Standalone Controller
This script creates the icon file needed for proper Windows taskbar display.

Author: Colin Monks, PhD
Company: Intelligent Imaging Innovations, Inc.
Version: V1.0.1
Date: 2025
"""

import os
import sys
from PIL import Image

def create_icon():
    """Create ICO file from PNG logo"""
    logo_path = "OilBoy_software logo.png"
    ico_path = "oilboy_icon.ico"
    
    print("OilBoy Icon Creator")
    print("==================")
    
    if not os.path.exists(logo_path):
        print(f"❌ Logo file not found: {logo_path}")
        return False
    
    try:
        # Load the logo image
        print(f"📖 Loading logo: {logo_path}")
        image = Image.open(logo_path)
        
        # Convert to RGBA for proper transparency
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create multiple icon sizes for Windows
        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        print(f"🔄 Creating icon sizes: {sizes}")
        
        # Create resized images
        icon_images = []
        for size in sizes:
            resized = image.resize(size, Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO file with multiple sizes
        print(f"💾 Saving ICO file: {ico_path}")
        icon_images[0].save(
            ico_path, 
            format='ICO', 
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        # Verify the file was created
        if os.path.exists(ico_path):
            size_kb = os.path.getsize(ico_path) / 1024
            print(f"✅ ICO file created successfully: {ico_path} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"❌ Failed to create ICO file: {ico_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating icon: {e}")
        return False

if __name__ == "__main__":
    success = create_icon()
    sys.exit(0 if success else 1)