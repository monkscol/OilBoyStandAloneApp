# OilBoy Standalone Controller - Build Instructions

**Author:** Colin Monks, PhD  
**Company:** Intelligent Imaging Innovations, Inc.  
**Version:** V1.0  
**Date:** 2025

## Overview

This document explains how to compile the OilBoy Standalone Controller application into a standalone Windows executable that can be distributed to end users.

## Prerequisites

### System Requirements
- **Operating System:** Windows 11 or Windows 10
- **Python:** Version 3.8 or later
- **Memory:** At least 4GB RAM (8GB recommended)
- **Disk Space:** At least 2GB free space for build process

### Required Files
Before building, ensure you have all the necessary files in your project directory:
- `oilboy_standalone_app.py` - Main application
- `SBAccess.py` - SlideBook integration module
- `BaseDecoder.py` - Base decoder module
- `ByteUtil.py` - Byte utilities module
- `CMetadataLib.py` - Metadata library module
- `CSBPoint.py` - CSB point module
- `OilBoy_software logo.png` - Application logo
- `oilboy_config.json` - Configuration file (will be created if missing)

## Build Methods

### Method 1: Automated Build (Recommended)

1. **Double-click** `build.bat` in Windows Explorer
   - This will automatically check dependencies and build the application
   - Follow the on-screen prompts

### Method 2: Manual Build

1. **Open Command Prompt** in your project directory
2. **Run the build script:**
   ```cmd
   python build_app.py
   ```

### Method 3: Direct PyInstaller

1. **Install PyInstaller:**
   ```cmd
   pip install pyinstaller
   ```

2. **Run PyInstaller:**
   ```cmd
   pyinstaller --onefile --windowed --icon=oilboy_icon.ico --name="OilBoy_Standalone_Controller" oilboy_standalone_app.py
   ```

## Build Process

The build process will:

1. **Check Dependencies** - Verify PyInstaller, Pillow, and Bleak are installed
2. **Create Spec File** - Generate PyInstaller configuration
3. **Build Application** - Compile Python code into executable
4. **Create Installer Package** - Package files for distribution

## Output Files

After successful build, you'll find:

### Build Artifacts
- `dist/OilBoy_Standalone_Controller.exe` - Main executable
- `build/` - Build cache directory
- `oilboy_app.spec` - PyInstaller specification file

### Distribution Package
- `installer/` - Directory containing distribution files:
  - `OilBoy_Standalone_Controller.exe` - Main application
  - `oilboy_config.json` - Configuration file
  - `OilBoy_software logo.png` - Application logo
  - `README.txt` - Installation instructions

## Troubleshooting

### Common Issues

**"Python not found"**
- Install Python 3.8+ from python.org
- Ensure Python is added to PATH during installation

**"PyInstaller not found"**
- Run: `pip install pyinstaller`
- Or use the automated build script

**"Missing module errors"**
- Run: `pip install -r requirements.txt`
- Ensure all required files are in the project directory

**"Large executable size"**
- This is normal for PyInstaller applications
- The executable includes Python runtime and all dependencies
- Typical size: 50-100MB

**"Bluetooth not working"**
- Ensure Windows Bluetooth service is enabled
- Check device permissions in Windows Settings
- Verify OilBoy device is in range and advertising

### Build Errors

**ImportError: No module named 'bleak'**
```cmd
pip install bleak
```

**ImportError: No module named 'PIL'**
```cmd
pip install Pillow
```

**FileNotFoundError: Missing required files**
- Ensure all Python modules and assets are in the project directory
- Check file names match exactly (case-sensitive)

## Distribution

### For End Users
1. **Copy** the entire `installer/` folder
2. **Extract** to target computer
3. **Run** `OilBoy_Standalone_Controller.exe`

### System Requirements for End Users
- Windows 11 or Windows 10
- Bluetooth support (for OilBoy communication)
- Network connection (for SlideBook integration)
- No Python installation required

### Installation Notes
- The application is completely self-contained
- No system-wide installation required
- Configuration files are created in the same directory as the executable
- Users can run from any location (USB drive, network share, etc.)

## Security Considerations

### Code Signing
For production distribution, consider code signing the executable:
1. Obtain a code signing certificate
2. Sign the executable before distribution
3. This prevents Windows SmartScreen warnings

### Antivirus Software
- Some antivirus software may flag PyInstaller executables
- This is a false positive due to the packaging method
- Consider submitting to antivirus vendors for whitelisting

## Performance Optimization

### Build Optimization
- Use `--onefile` for single executable
- Use `--windowed` to hide console window
- Use `--upx-dir` for additional compression (requires UPX)

### Runtime Optimization
- The application uses asyncio for efficient BLE communication
- Threading is used for UI responsiveness
- Memory usage is optimized for typical microscope workflows

## Support

For technical support or questions about the build process:
- **Contact:** Colin Monks, PhD
- **Company:** Intelligent Imaging Innovations, Inc.
- **Application Version:** V1.0

## Version History

- **V1.0 (2025):** Initial release with PyInstaller build system 