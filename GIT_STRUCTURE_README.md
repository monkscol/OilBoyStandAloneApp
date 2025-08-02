# OilBoy Standalone Controller - Git Structure

## Overview
This repository has been restructured to keep only the essential source code in git, while excluding large build artifacts and generated files.

## Files Tracked in Git (Essential Source Code)

### Core Application Files
- `oilboy_standalone_app.py` - Main application script
- `SBAccess.py` - SlideBook integration module
- `CSBPoint.py` - SlideBook point utilities
- `CMetadataLib.py` - Metadata library
- `ByteUtil.py` - Byte utilities
- `BaseDecoder.py` - Base decoder implementation

### Configuration and Assets
- `oilboy_config.json` - Application configuration
- `OilBoy_software logo.png` - Application logo (1.1MB, but essential for branding)
- `requirements.txt` - Python dependencies

### Documentation
- `OilBoy_Standalone_README.md` - Main application documentation
- `BUILD_README.md` - Build process documentation
- `GIT_STRUCTURE_README.md` - This file

### Git Configuration
- `.gitignore` - Git ignore rules

## Files Excluded from Git (Local Only)

### Build Artifacts (Large Files)
- `dist/` - PyInstaller output directory (~71MB total)
  - `OilBoy_Standalone_Controller.exe` (36MB)
  - `OilBoy_Standalone_Controller.zip` (35MB)
- `build/` - PyInstaller build cache
- `installer/` - Installer directory (~242MB total)
  - `OilBoy_Standalone_Controller.exe` (240MB)

### Generated Files
- `oilboy_icon.ico` - Generated icon file
- `oilboy_debug.log` - Debug log file
- `__pycache__/` - Python cache files
- `*.spec` - PyInstaller spec files

### Build Scripts (Local Development)
- `build_oilboy.py` - Build script
- `build_oilboy.bat` - Build batch file
- `cleanup.bat` - Cleanup script

## Local Build Process

### Prerequisites
1. Install PyInstaller: `pip install pyinstaller`
2. Install required dependencies: `pip install -r requirements.txt`

### Building the Application
Use the local build scripts (not tracked in git):

**Option 1: Python Script**
```bash
python build_local.py
```

**Option 2: Batch File**
```bash
build_local.bat
```

### What the Build Process Does
1. Cleans up previous build artifacts
2. Runs PyInstaller with all necessary hidden imports
3. Creates a standalone Windows executable in `dist/`
4. Includes the logo and configuration files

## Repository Size Reduction

### Before Restructuring
- Total size: ~350MB+ (including build artifacts)
- Large executable files tracked in git
- Build cache and temporary files included

### After Restructuring
- Total size: ~2MB (source code only)
- Only essential source files tracked
- Build artifacts generated locally as needed

## Benefits of This Structure

1. **Smaller Repository**: Much faster cloning and pushing
2. **Cleaner History**: No large binary files cluttering git history
3. **Faster Operations**: Git operations are much faster
4. **Better Collaboration**: Easier to share and collaborate
5. **Local Flexibility**: Build artifacts can be regenerated locally

## Important Notes

- **Never commit build artifacts**: The `.gitignore` ensures build files stay local
- **Regenerate as needed**: Build the executable locally when needed
- **Keep build scripts local**: The `build_local.py` and `build_local.bat` files are for local use only
- **Logo file**: The PNG logo is kept in git as it's essential for the application branding

## Troubleshooting

If you need to rebuild the application:
1. Ensure PyInstaller is installed: `pip install pyinstaller`
2. Run the local build script: `python build_local.py`
3. Check the `dist/` directory for the generated executable

If you encounter permission errors during build:
1. Close any running instances of the application
2. Run the cleanup script: `cleanup.bat`
3. Try building again 