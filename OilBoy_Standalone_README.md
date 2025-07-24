# OilBoy Standalone Application

A specialized Tkinter application for OilBoy management with SlideBook integration. This application provides a dedicated interface for OilBoy operations with two main operational modes.

## Features

### Connection Management
- **SlideBook Socket Connection**: Connects to SlideBook via socket to read and control objectives and Z-stage position
- **OilBoy BLE Connection**: Manages Bluetooth Low Energy connection to OilBoy device
- **OilBoy Configuration**: Enter and save OilBoy serial numbers with automatic MAC address caching
- **Known Devices**: Dropdown to quickly switch between previously connected OilBoy devices
- **Persistent Configuration**: Remembers OilBoy serial number and MAC address for quick connection

### Settings Management
- **Stage Offset**: Configurable offset in microns for stage positioning
- **OilBoy Objective Position**: Objective turret position for OilBoy (dropdown selection)
- **OilBoy Offset**: Amount the stage needs to raise for oil application
- **Oil Amount**: Configurable oil dispensing amount in steps

### Operational Modes

#### Mode 1: Low Power → High Power
1. Find sample in low power objective
2. Press "Execute Mode 1" button
3. Application automatically:
   - Switches to OilBoy objective
   - Pumps appropriate amount of oil
   - Raises stage for oil application
   - Lowers stage
   - Switches to selected high power objective

#### Mode 2: Re-oil High Power
1. Press "Execute Mode 2" button
2. Application automatically:
   - Switches to OilBoy objective
   - Pumps oil
   - Raises stage for oil application
   - Lowers stage
   - Returns to original high power objective

## Installation

### Prerequisites
- Python 3.7 or higher
- SlideBook 2025 running and listening on port 65432
- OilBoy device with BLE capability
- Windows 10/11 (for BLE support)

### Dependencies
Install required packages:
```bash
pip install -r oilboy_requirements.txt
```

### SBAccess Module
The application requires the SBAccess module from SlideBook. This should be available in your SlideBook installation directory.

## Configuration

The application uses a JSON configuration file (`oilboy_config.json`) that is automatically created on first run:

```json
{
    "slidebook": {
        "host": "127.0.0.1",
        "port": 65432
    },
    "oilboy": {
        "serial_number": "A002",
        "known_devices": {
            "A002": "DC:54:75:EB:81:B1",
            "A003": "DC:54:75:EB:6F:2D"
        }
    },
    "settings": {
        "stage_offset_microns": 100.0,
        "oilboy_objective_location": 0.0,
        "oilboy_offset_microns": 50.0,
        "default_oil_amount": 50,
        "default_z_drop": 50.0
    }
}
```

### Configuration Parameters

#### SlideBook Settings
- `host`: SlideBook server IP address (default: 127.0.0.1)
- `port`: SlideBook server port (default: 65432)

#### OilBoy Settings
- `serial_number`: OilBoy device serial number
- `known_devices`: Dictionary mapping serial numbers to MAC addresses for quick connection

#### Operation Settings
- `stage_offset_microns`: General stage offset in microns
- `oilboy_objective_location`: Objective turret position for OilBoy (integer)
- `oilboy_offset_microns`: Distance to raise stage for oil application
- `default_oil_amount`: Default oil dispensing amount in steps
- `default_z_drop`: Default Z-stage drop distance

## Usage

### Starting the Application
```bash
python oilboy_standalone_app.py
```

### Connection Setup
1. **Connect to SlideBook**:
   - Ensure SlideBook is running and listening on the configured port
   - Click "Connect SlideBook" button
   - Verify connection status shows "Connected"

2. **Connect to OilBoy**:
   - Enter the OilBoy serial number (e.g., "A002", "A003")
   - Optionally select from known devices dropdown for quick access
   - Click "Connect OilBoy" button
   - The application will scan for the device and connect automatically
   - MAC addresses are automatically saved for future quick connections

### Configuration
1. **OilBoy Configuration**: 
   - Enter OilBoy serial number in the "OilBoy Serial" field
   - Use "Known Devices" dropdown to select previously connected devices
   - Click "Save OilBoy Config" to save the serial number
2. **Operation Settings**: Modify the values in the Settings section as needed
3. **Save Settings**: Click "Save Settings" to persist changes to the configuration file

### Operation
1. **Mode 1 (Low → High Power)**:
   - Select destination objective from dropdown
   - Click "Execute Mode 1"
   - Monitor progress in the log window

2. **Mode 2 (Re-oil High Power)**:
   - Click "Execute Mode 2"
   - Application will return to current objective after oiling

## Troubleshooting

### Connection Issues
- **SlideBook Connection Failed**: Verify SlideBook is running and port 65432 is open
- **OilBoy Connection Failed**: Check device is powered on and advertising, verify serial number in config

### Operation Issues
- **Objective Switching Failed**: Verify objective names match those in SlideBook
- **Stage Movement Failed**: Check Z-stage is enabled and accessible in SlideBook
- **Oil Application Failed**: Verify OilBoy is connected and responding to commands

### Log Messages
The application provides detailed logging in the log window. Common messages:
- `[HH:MM:SS] SlideBook connected successfully`
- `[HH:MM:SS] OilBoy connected successfully`
- `[HH:MM:SS] Battery: 3.86V (USB)`
- `[HH:MM:SS] Applied 50 steps of oil`

## Technical Details

### BLE Communication
- Uses Nordic UART Service (NUS) for communication
- Supports automatic reconnection
- Battery voltage monitoring
- Command/response protocol

### SlideBook Integration
- Socket-based communication
- Hardware component control
- Microscope state monitoring
- Objective turret control

### Threading
- Asyncio event loop for BLE operations
- Background threads for long-running operations
- Non-blocking UI updates

### Graceful Shutdown
- Automatic disconnection from both SlideBook and OilBoy on application close
- Proper cleanup of asyncio event loops
- Logged shutdown process for debugging

## File Structure
```
oilboy_standalone_app.py      # Main application
oilboy_config.json           # Configuration file (auto-generated)
oilboy_requirements.txt      # Python dependencies
OilBoy_Standalone_README.md  # This documentation
```

## Support

For technical support or questions about the OilBoy Standalone Application, please contact:
- **Author**: Colin Monks
- **Company**: Intelligent Imaging Innovations, Inc.

## Version History

### v1.0.0
- Initial release
- SlideBook socket integration
- OilBoy BLE management
- Two operational modes
- Configuration management
- Logging and status monitoring 