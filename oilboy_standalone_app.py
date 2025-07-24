#!/usr/bin/env python3
"""
OilBoy Standalone Application

A specialized Tkinter application for OilBoy management with SlideBook integration.
Supports two modes:
1. Low power to high power objective switching with oiling
2. Re-oiling high power objectives

Author: Colin Monks, PhD
Company: Intelligent Imaging Innovations, Inc.
Version: V1.0
Date: 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import threading
import json
import os
import logging
import socket
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient
from PIL import Image, ImageTk

# Import SBAccess for SlideBook integration
try:
    from SBAccess import SBAccess, MicroscopeHardwareComponent, MicroscopeStates
except ImportError:
    print("Warning: SBAccess not available. SlideBook integration will be disabled.")
    SBAccess = None

# OilBoy BLE UUIDs
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class OilBoyBLE:
    """OilBoy BLE communication handler"""
    
    def __init__(self, status_callback=None, connected_callback=None, battery_callback=None):
        self.client = None
        self.device_address = None
        self.command_characteristic = None
        self.tx_characteristic = None
        self.is_connected = False
        self.status_callback = status_callback
        self.connected_callback = connected_callback
        self.battery_callback = battery_callback
        self.loop = None

    def _emit_status(self, msg):
        if self.status_callback:
            self.status_callback(msg)

    def _emit_connected(self, connected):
        if self.connected_callback:
            self.connected_callback(connected)
    
    def _emit_battery(self, voltage, usb_power):
        if self.battery_callback:
            self.battery_callback(voltage, usb_power)

    def notification_handler(self, sender, data):
        try:
            text = data.decode('utf-8').strip()
            
            # Parse battery voltage responses
            if text.startswith("BATTERY_OK,"):
                try:
                    parts = text.split(',')
                    voltage_part = next((p for p in parts if p.startswith('VOLT_')), None)
                    usb_part = next((p for p in parts if p.startswith('USB_')), None)
                    if voltage_part and usb_part:
                        voltage = float(voltage_part.split('_')[1])
                        usb_power = usb_part.split('_')[1] == 'True'
                        self._emit_battery(voltage, usb_power)
                        return
                except Exception as parse_err:
                    self._emit_status(f"Battery parse error: {parse_err}")
            elif text.startswith("BATTERY:"):
                try:
                    vstr = text.split(":")[1].replace("V", "")
                    voltage = float(vstr)
                    self._emit_battery(voltage, False)
                    return
                except Exception as parse_err:
                    self._emit_status(f"Battery parse error: {parse_err}")
            
            # Handle other responses
            self._emit_status(f"OilBoy: {text}")
            
        except Exception as e:
            self._emit_status(f"BLE notification error: {e}")

    def scan_and_connect_with_serial(self, serial, burst_window=24):
        """Scan for OILBOY_<serial> and connect"""
        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                self._scan_and_connect_with_serial_async(serial, burst_window), self.loop)
            return future.result(timeout=burst_window+30)
        return False

    def connect_by_mac(self, mac):
        """Try to connect directly to a device by MAC address"""
        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                self._connect_by_mac_async(mac), self.loop)
            return future.result(timeout=5)
        return False

    async def _connect_by_mac_async(self, mac):
        self._emit_status(f"Trying direct connect to {mac}...")
        try:
            self.client = BleakClient(mac)
            await asyncio.wait_for(self.client.connect(), timeout=10.0)
            self._emit_status("Connected. Setting up services...")
            await self._setup_characteristics_async()
            if self.command_characteristic and self.tx_characteristic:
                self.is_connected = True
                self._emit_connected(True)
                self._emit_status("OilBoy is ready.")
                return True
            else:
                self._emit_status("ERROR: UART service characteristics not found.")
                await self._disconnect_async()
                return False
        except Exception as e:
            self._emit_status(f"Direct connect failed: {e}")
            await self._disconnect_async()
            return False

    async def _scan_and_connect_with_serial_async(self, serial, burst_window=24):
        target_name = f"OILBOY_{serial.strip().upper()}"
        self._emit_status(f"Scanning for {target_name} (up to {burst_window}s)...")
        start_time = asyncio.get_event_loop().time()
        attempt = 1
        while asyncio.get_event_loop().time() - start_time < burst_window:
            device = None
            try:
                self._emit_status(f"Scan attempt {attempt}...")
                devices = await BleakScanner.discover(timeout=1.0)
                for d in devices:
                    if d.name and d.name.upper() == target_name:
                        device = d
                        break
            except Exception as e:
                self._emit_status(f"Scan error: {e}")
            if device:
                self._emit_status(f"Found {target_name} at {device.address}. Connecting...")
                for connect_try in range(3):
                    try:
                        self.client = BleakClient(device)
                        await asyncio.wait_for(self.client.connect(), timeout=10.0)
                        self._emit_status("Connected. Setting up services...")
                        await self._setup_characteristics_async()
                        if self.command_characteristic and self.tx_characteristic:
                            self.is_connected = True
                            self._emit_connected(True)
                            self._emit_status("OilBoy is ready.")
                            return True
                        else:
                            self._emit_status("ERROR: UART service characteristics not found.")
                            await self._disconnect_async()
                            return False
                    except asyncio.TimeoutError:
                        self._emit_status(f"Connection attempt {connect_try+1} timed out.")
                    except Exception as e:
                        self._emit_status(f"Connection attempt {connect_try+1} failed: {e}")
                        await self._disconnect_async()
                self._emit_status(f"All connection attempts failed for this burst. Waiting for next burst...")
                await asyncio.sleep(7)
            else:
                await asyncio.sleep(0.5)
            attempt += 1
        self._emit_status(f"{target_name} not found after {burst_window}s.")
        return False

    async def _disconnect_async(self):
        if self.client and self.client.is_connected:
            try:
                if self.tx_characteristic:
                    await self.client.stop_notify(self.tx_characteristic)
            except Exception:
                pass
            try:
                await self.client.disconnect()
            except Exception as e:
                self._emit_status(f"Error during disconnect: {str(e)}")
        
        self.client = None
        self.is_connected = False
        self._emit_connected(False)
        self._emit_status("Disconnected from OilBoy.")

    async def _setup_characteristics_async(self):
        """Discover and configure UART characteristics"""
        self.command_characteristic = None
        self.tx_characteristic = None
        try:
            for service in self.client.services:
                if service.uuid.lower() == UART_SERVICE_UUID.lower():
                    for char in service.characteristics:
                        if char.uuid.lower() == UART_TX_CHAR_UUID.lower():
                            self.command_characteristic = char
                        elif char.uuid.lower() == UART_RX_CHAR_UUID.lower():
                            self.tx_characteristic = char
            
            if self.tx_characteristic and "notify" in self.tx_characteristic.properties:
                await self.client.start_notify(self.tx_characteristic, self.notification_handler)
            else:
                self._emit_status("RX characteristic does not support notifications.")

        except Exception as e:
            self._emit_status(f"Error setting up characteristics: {e}")

    def disconnect(self):
        """Public method to disconnect"""
        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(self._disconnect_async(), self.loop)
            return future.result(timeout=5)
        return False

    async def send_command_async(self, command, timeout=3.0):
        """Send command to OilBoy and wait for response"""
        if not self.is_connected or not self.command_characteristic:
            self._emit_status("Not connected to OilBoy")
            return False
        
        try:
            command_bytes = f"{command}\n".encode('utf-8')
            await asyncio.wait_for(
                self.client.write_gatt_char(self.command_characteristic, command_bytes),
                timeout=timeout
            )
            self._emit_status(f"Command sent: {command}")
            return True
        except Exception as e:
            self._emit_status(f"Error sending command: {e}")
            return False

    def send_command(self, command, timeout=3.0):
        """Synchronous wrapper for send_command_async"""
        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                self.send_command_async(command, timeout), self.loop)
            return future.result(timeout=timeout+1)
        return False

class OilBoyStandaloneApp:
    """Main OilBoy Standalone Application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OilBoy Standalone Controller")
        self.root.geometry("800x700")
        
        # Configuration
        self.config_file = "oilboy_config.json"
        self.config = self.load_config()
        
        # Apply dark mode styling
        self.setup_dark_mode()
        
        # Set window geometry from config
        self.set_window_geometry()
        
        # SlideBook connection
        self.slidebook_socket = None
        self.sb_access = None
        self.slidebook_connected = False
        
        # OilBoy BLE connection
        self.oilboy = None
        self.oilboy_connected = False
        self.asyncio_loop = None
        self.ble_thread = None
        
        # Current state
        self.current_objective = "Unknown"
        self.current_z_position = 0.0
        self.objectives_list = []
        
        # Shutdown flag
        self.shutting_down = False
        
        # Setup UI
        self.setup_ui()
        
        # Start asyncio thread for BLE
        self.start_asyncio_thread()
        
        # Try to connect to SlideBook on startup
        self.root.after(1000, self.connect_to_slidebook)
        
        # Bind window close event for graceful shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_logo(self, parent_frame):
        """Load and display the OilBoy logo"""
        try:
            # Load the logo image
            logo_path = "OilBoy_software logo.png"
            if os.path.exists(logo_path):
                # Open and resize the image
                image = Image.open(logo_path)
                # Resize to a reasonable size for the UI (e.g., 100x100 pixels)
                image = image.resize((100, 100), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(image)
                
                # Create and place the logo label (right side of header)
                logo_label = ttk.Label(parent_frame, image=self.logo_photo)
                logo_label.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
                
                # Set the logo as the application icon
                self.set_application_icon(logo_path)
                
                self.log_message("OilBoy logo loaded successfully")
            else:
                self.log_message(f"Warning: Logo file not found at {logo_path}")
        except Exception as e:
            self.log_message(f"Error loading logo: {e}")

    def set_application_icon(self, logo_path):
        """Set the OilBoy logo as the application window icon"""
        try:
            # Load the image for the icon
            image = Image.open(logo_path)
            
            # Create different sizes for the icon (Windows typically uses 16x16, 32x32, 48x48)
            icon_sizes = [(16, 16), (32, 32), (48, 48)]
            icon_images = []
            
            for size in icon_sizes:
                resized_image = image.resize(size, Image.Resampling.LANCZOS)
                icon_images.append(resized_image)
            
            # Convert to PhotoImage for Tkinter
            icon_photo = ImageTk.PhotoImage(icon_images[1])  # Use 32x32 for the main icon
            
            # Set the window icon for title bar
            self.root.iconphoto(True, icon_photo)
            
            # Store the icon photo to prevent garbage collection
            self.icon_photo = icon_photo
            
            # Create and save ICO file for taskbar icon
            self.create_ico_file(logo_path)
            
            self.log_message("Application icon set successfully")
            
        except Exception as e:
            self.log_message(f"Error setting application icon: {e}")

    def create_ico_file(self, logo_path):
        """Create an ICO file from the logo and set it as the taskbar icon"""
        try:
            # Create ICO file path
            ico_path = "oilboy_icon.ico"
            
            # Check if ICO file already exists
            if os.path.exists(ico_path):
                self.log_message(f"ICO file already exists: {ico_path}")
            else:
                # Load the image
                image = Image.open(logo_path)
                
                # Convert to RGBA if not already (ICO files need alpha channel)
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                # Create different sizes for the ICO file
                icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
                icon_images = []
                
                for size in icon_sizes:
                    resized_image = image.resize(size, Image.Resampling.LANCZOS)
                    icon_images.append(resized_image)
                
                # Save as ICO file with all sizes
                icon_images[0].save(ico_path, format='ICO', sizes=[(size[0], size[1]) for size in icon_sizes])
                self.log_message(f"ICO file created successfully: {ico_path}")
            
            # Set the ICO file as the window icon (this affects taskbar)
            try:
                self.root.iconbitmap(ico_path)
                self.log_message("Taskbar icon set successfully")
                
                # Force refresh the taskbar icon
                self.root.after(1000, self.force_taskbar_icon_refresh)
                
            except Exception as icon_error:
                self.log_message(f"Error setting taskbar icon: {icon_error}")
                # Try alternative method
                self.set_icon_alternative(ico_path)
            
        except Exception as e:
            self.log_message(f"Error with ICO file: {e}")
            # Try alternative method without ICO file
            self.set_icon_alternative(logo_path)

    def set_icon_alternative(self, image_path):
        """Alternative method to set the application icon"""
        try:
            # Load the image
            image = Image.open(image_path)
            
            # Convert to RGBA if needed
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Create a 32x32 version for the icon
            icon_image = image.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            icon_photo = ImageTk.PhotoImage(icon_image)
            
            # Set both iconphoto and try to set as default icon
            self.root.iconphoto(True, icon_photo)
            
            # Store to prevent garbage collection
            self.icon_photo = icon_photo
            
            # Try to set the window icon using wm_iconphoto
            self.root.wm_iconphoto(True, icon_photo)
            
            self.log_message("Alternative icon method applied")
            
        except Exception as e:
            self.log_message(f"Error in alternative icon method: {e}")

    def force_taskbar_icon_refresh(self):
        """Force refresh the taskbar icon on Windows"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get the window handle
            hwnd = self.root.winfo_id()
            
            # Windows API constants
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            
            # Load the ICO file using Windows API
            if os.path.exists("oilboy_icon.ico"):
                # Use LoadImage to load the icon
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                
                # Load the icon
                icon_handle = user32.LoadImageW(
                    None, 
                    "oilboy_icon.ico", 
                    1,  # IMAGE_ICON
                    32, 32,  # width, height
                    0x00000010  # LR_LOADFROMFILE
                )
                
                if icon_handle:
                    # Set the icon for the window
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_handle)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon_handle)
                    self.log_message("Taskbar icon refreshed using Windows API")
                else:
                    self.log_message("Failed to load icon using Windows API")
            
        except Exception as e:
            self.log_message(f"Error refreshing taskbar icon: {e}")

    def setup_dark_mode(self):
        """Apply dark mode styling to the application"""
        try:
            # Configure dark theme colors
            style = ttk.Style()
            
            # Dark color scheme
            bg_color = "#2b2b2b"           # Dark background
            fg_color = "#ffffff"           # White text
            accent_color = "#4a9eff"       # Blue accent
            button_bg = "#404040"          # Button background
            button_fg = "#ffffff"          # Button text
            entry_bg = "#404040"           # Entry background
            entry_fg = "#ffffff"           # Entry text
            frame_bg = "#363636"           # Frame background
            label_bg = "#2b2b2b"           # Label background
            
            # Configure ttk styles
            style.theme_use('clam')  # Use clam theme as base
            
            # Configure main window
            self.root.configure(bg=bg_color)
            
            # Configure ttk styles
            style.configure('TFrame', background=frame_bg)
            style.configure('TLabel', background=label_bg, foreground=fg_color)
            style.configure('TButton', 
                          background=button_bg, 
                          foreground=button_fg,
                          bordercolor=accent_color,
                          focuscolor=accent_color)
            style.map('TButton',
                     background=[('active', accent_color), ('pressed', accent_color)],
                     foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])
            
            style.configure('TEntry', 
                          fieldbackground=entry_bg,
                          foreground=entry_fg,
                          bordercolor=accent_color,
                          focuscolor=accent_color)
            
            style.configure('TCombobox', 
                          fieldbackground=entry_bg,
                          background=entry_bg,
                          foreground=entry_fg,
                          bordercolor=accent_color,
                          focuscolor=accent_color)
            style.map('TCombobox',
                     fieldbackground=[('readonly', entry_bg)],
                     selectbackground=[('readonly', accent_color)])
            
            style.configure('TLabelframe', 
                          background=frame_bg,
                          bordercolor=accent_color)
            style.configure('TLabelframe.Label', 
                          background=frame_bg,
                          foreground=fg_color)
            
            # Configure scrolled text widget
            self.root.option_add('*Text.background', entry_bg)
            self.root.option_add('*Text.foreground', fg_color)
            self.root.option_add('*Text.insertBackground', fg_color)
            self.root.option_add('*Text.selectBackground', accent_color)
            
        except Exception as e:
            print(f"Warning: Could not apply dark mode styling: {e}")

    def set_window_geometry(self):
        """Set window geometry and position from config"""
        try:
            geometry = self.config.get("window", {}).get("geometry", "800x700+100+100")
            self.root.geometry(geometry)
            
        except Exception as e:
            print(f"Warning: Could not set window geometry: {e}")

    def save_window_geometry(self):
        """Save current window geometry to config"""
        try:
            geometry = self.root.geometry()
            self.config["window"]["geometry"] = geometry
            self.log_message(f"Window geometry saved: {geometry}")
        except Exception as e:
            self.log_message(f"Error saving window geometry: {e}")

    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
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
                "oilboy_objective_location": "",
                "oilboy_offset_microns": 50.0,
                "default_oil_amount": 50,
                "default_z_drop": 50.0
            },
            "window": {
                "geometry": "800x700+100+100"
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    self.merge_config(default_config, config)
                    return default_config
            else:
                # Save default config
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def merge_config(self, default, loaded):
        """Recursively merge loaded config with defaults"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self.merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.log_message(f"Error saving config: {e}")

    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Header row with logo and author info
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        # Author Info (left side, stacked vertically)
        author_frame = ttk.Frame(header_frame)
        author_frame.grid(row=0, column=0, sticky=tk.W)
        
        version_label = ttk.Label(author_frame, text="V1.0", font=("Arial", 10))
        version_label.grid(row=0, column=0, sticky=tk.W)
        
        author_label = ttk.Label(author_frame, text="Colin Monks, PhD", font=("Arial", 10))
        author_label.grid(row=1, column=0, sticky=tk.W)
        
        company_label = ttk.Label(author_frame, text="Intelligent Imaging Innovations, Inc.", font=("Arial", 10))
        company_label.grid(row=2, column=0, sticky=tk.W)
        
        year_label = ttk.Label(author_frame, text="2025", font=("Arial", 10))
        year_label.grid(row=3, column=0, sticky=tk.W)
        
        # Load and display logo (right side)
        self.load_logo(header_frame)
        
        # Connection Status Frame
        status_frame = ttk.LabelFrame(main_frame, text="Connection Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        # SlideBook Status
        ttk.Label(status_frame, text="SlideBook:").grid(row=0, column=0, sticky=tk.W)
        self.slidebook_status_var = tk.StringVar(value="Disconnected")
        self.slidebook_status_label = ttk.Label(status_frame, textvariable=self.slidebook_status_var, 
                                               foreground="#ff6b6b")  # Red for disconnected
        self.slidebook_status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # OilBoy Configuration
        oilboy_config_frame = ttk.Frame(status_frame)
        oilboy_config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        oilboy_config_frame.columnconfigure(1, weight=1)
        
        ttk.Label(oilboy_config_frame, text="OilBoy Serial:").grid(row=0, column=0, sticky=tk.W)
        self.oilboy_serial_var = tk.StringVar(value=self.config["oilboy"]["serial_number"])
        self.oilboy_serial_entry = ttk.Entry(oilboy_config_frame, textvariable=self.oilboy_serial_var, width=15)
        self.oilboy_serial_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Known devices dropdown
        ttk.Label(oilboy_config_frame, text="Known Devices:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.known_devices_var = tk.StringVar()
        self.known_devices_combo = ttk.Combobox(oilboy_config_frame, textvariable=self.known_devices_var, 
                                               state="readonly", width=15)
        self.known_devices_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        self.known_devices_combo.bind('<<ComboboxSelected>>', self.on_known_device_selected)
        
        # Populate known devices dropdown
        self.populate_known_devices()
        
        # OilBoy Status
        ttk.Label(status_frame, text="OilBoy:").grid(row=2, column=0, sticky=tk.W)
        self.oilboy_status_var = tk.StringVar(value="Disconnected")
        self.oilboy_status_label = ttk.Label(status_frame, textvariable=self.oilboy_status_var,
                                             foreground="#ff6b6b")  # Red for disconnected
        self.oilboy_status_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Battery Status
        ttk.Label(status_frame, text="Battery:").grid(row=3, column=0, sticky=tk.W)
        self.battery_var = tk.StringVar(value="--")
        self.battery_label = ttk.Label(status_frame, textvariable=self.battery_var)
        self.battery_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        # Connection Buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.grid(row=0, column=2, rowspan=4, padx=(20, 0))
        
        self.slidebook_connect_btn = ttk.Button(button_frame, text="Connect SlideBook", 
                                               command=self.connect_to_slidebook, width=15)
        self.slidebook_connect_btn.grid(row=0, column=0, pady=2)
        
        self.oilboy_connect_btn = ttk.Button(button_frame, text="Connect OilBoy", 
                                            command=self.connect_to_oilboy, width=15)
        self.oilboy_connect_btn.grid(row=1, column=0, pady=2)
        
        self.save_oilboy_config_btn = ttk.Button(button_frame, text="Save OilBoy Config", 
                                                command=self.save_oilboy_config, width=15)
        self.save_oilboy_config_btn.grid(row=2, column=0, pady=2)
        
        self.check_battery_btn = ttk.Button(button_frame, text="Check Battery", 
                                           command=self.check_battery, width=15)
        self.check_battery_btn.grid(row=3, column=0, pady=2)
        
        self.test_connection_btn = ttk.Button(button_frame, text="Test Connection", 
                                             command=self.test_oilboy_connection_ui, width=15)
        self.test_connection_btn.grid(row=4, column=0, pady=2)
        

        
        # Settings Frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Settings Grid - 3 columns
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        # OilBoy Objective Location
        ttk.Label(settings_frame, text="OilBoy Objective:").grid(row=0, column=0, sticky=tk.W)
        self.oilboy_obj_loc_var = tk.StringVar(value=self.config["settings"]["oilboy_objective_location"])
        self.oilboy_obj_loc_combo = ttk.Combobox(settings_frame, textvariable=self.oilboy_obj_loc_var, 
                                                state="readonly", width=15)
        self.oilboy_obj_loc_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 20))
        
        # Oil Amount
        ttk.Label(settings_frame, text="Oil Amount (steps):").grid(row=0, column=2, sticky=tk.W)
        self.oil_amount_var = tk.IntVar(value=self.config["settings"]["default_oil_amount"])
        self.oil_amount_entry = ttk.Entry(settings_frame, textvariable=self.oil_amount_var, width=15)
        self.oil_amount_entry.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        
        # OilBoy Offset
        ttk.Label(settings_frame, text="OilBoy Offset (μm):").grid(row=1, column=0, sticky=tk.W)
        self.oilboy_offset_var = tk.DoubleVar(value=self.config["settings"]["oilboy_offset_microns"])
        self.oilboy_offset_entry = ttk.Entry(settings_frame, textvariable=self.oilboy_offset_var, width=15)
        self.oilboy_offset_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 20))
        
        # Save Settings Button
        save_btn = ttk.Button(settings_frame, text="Save Settings", command=self.save_settings, width=15)
        save_btn.grid(row=1, column=2, columnspan=2, sticky=tk.E, padx=(10, 0))
        
        # Operation Modes Frame
        modes_frame = ttk.LabelFrame(main_frame, text="Operation Modes", padding="10")
        modes_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        modes_frame.columnconfigure(1, weight=1)
        
        # Mode 1: Low to High Power
        mode1_frame = ttk.Frame(modes_frame)
        mode1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mode1_frame.columnconfigure(1, weight=1)
        
        ttk.Label(mode1_frame, text="Mode 1: Low Power → High Power", 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(mode1_frame, text="Find sample in low power, then switch to OilBoy, apply oil, and switch to high power").grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Destination Objective for Mode 1
        ttk.Label(mode1_frame, text="Destination Objective:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.dest_objective_var = tk.StringVar()
        self.dest_objective_combo = ttk.Combobox(mode1_frame, textvariable=self.dest_objective_var, state="readonly")
        self.dest_objective_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(10, 0))
        
        # Mode 2: Re-oil High Power
        mode2_frame = ttk.Frame(modes_frame)
        mode2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mode2_frame.columnconfigure(1, weight=1)
        
        ttk.Label(mode2_frame, text="Mode 2: Re-oil High Power", 
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(mode2_frame, text="Switch to OilBoy, apply oil, and return to current high power objective").grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Execute buttons in right column
        buttons_frame = ttk.Frame(modes_frame)
        buttons_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.N, tk.E), padx=(20, 0))
        
        # Create custom styled buttons for modes
        style = ttk.Style()
        style.configure('Mode.TButton', 
                       background="#4a9eff",
                       foreground="#ffffff",
                       font=("Arial", 10, "bold"))
        style.map('Mode.TButton',
                 background=[('active', '#3a8eef'), ('pressed', '#2a7edf')])
        
        self.mode1_btn = ttk.Button(buttons_frame, text="Execute Mode 1", command=self.execute_mode1, style='Mode.TButton', width=15)
        self.mode1_btn.grid(row=0, column=0, pady=(0, 10))
        
        self.mode2_btn = ttk.Button(buttons_frame, text="Execute Mode 2", command=self.execute_mode2, style='Mode.TButton', width=15)
        self.mode2_btn.grid(row=1, column=0)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Create scrolled text with dark mode styling
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=10, 
            width=80,
            bg="#404040",      # Dark background
            fg="#ffffff",      # White text
            insertbackground="#ffffff",  # White cursor
            selectbackground="#4a9eff",  # Blue selection
            font=("Consolas", 9)  # Monospace font for better log readability
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear Log Button
        clear_log_btn = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        clear_log_btn.grid(row=1, column=0, pady=(10, 0))

    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        log_entry = f"{timestamp} {message}\n"
        
        try:
            # Check if the log_text widget still exists and is valid
            if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                self.log_text.insert(tk.END, log_entry)
                self.log_text.see(tk.END)
            else:
                # Fallback to print if widget is destroyed
                print(log_entry.strip())
        except Exception:
            # Fallback to print if any Tkinter error occurs
            print(log_entry.strip())

    def clear_log(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)

    def start_asyncio_thread(self):
        """Start asyncio event loop in a separate thread"""
        def run_asyncio():
            self.asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.asyncio_loop)
            self.asyncio_loop.run_forever()
        
        self.ble_thread = threading.Thread(target=run_asyncio, daemon=True)
        self.ble_thread.start()

    def connect_to_slidebook(self):
        """Connect to SlideBook via socket"""
        if not SBAccess:
            self.log_message("Error: SBAccess not available")
            return
        
        try:
            host = self.config["slidebook"]["host"]
            port = self.config["slidebook"]["port"]
            
            self.log_message(f"Connecting to SlideBook at {host}:{port}...")
            
            self.slidebook_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.slidebook_socket.connect((host, port))
            self.sb_access = SBAccess(self.slidebook_socket)
            
            self.slidebook_connected = True
            self.slidebook_status_var.set("Connected")
            self.slidebook_status_label.configure(foreground="#51cf66")  # Green for connected
            self.log_message("SlideBook connected successfully")
            
            # Update current state
            self.update_slidebook_state()
            
            # Populate objectives dropdown
            self.populate_objectives()
            
        except Exception as e:
            self.log_message(f"Failed to connect to SlideBook: {e}")
            self.slidebook_status_var.set("Connection Failed")
            self.slidebook_status_label.configure(foreground="#ff6b6b")  # Red for failed

    def update_slidebook_state(self):
        """Update current objective and Z position from SlideBook"""
        if not self.slidebook_connected or not self.sb_access:
            return
        
        try:
            # Get current objective
            try:
                current_obj = self.sb_access.GetMicroscopeState(MicroscopeStates.CurrentObjective)
                if current_obj:
                    self.current_objective = current_obj.strip()
            except Exception as e:
                self.log_message(f"Error getting current objective: {e}")
            
            # Get current Z position
            try:
                z_pos_data = self.sb_access.GetHardwareComponentLocationMicrons(MicroscopeHardwareComponent.ZStage)
                if z_pos_data and len(z_pos_data) >= 3:
                    self.current_z_position = z_pos_data[2]
            except Exception as e:
                self.log_message(f"Error getting Z position: {e}")
                
        except Exception as e:
            self.log_message(f"Error updating SlideBook state: {e}")

    def populate_objectives(self):
        """Populate objectives dropdown from SlideBook"""
        if not self.slidebook_connected or not self.sb_access:
            return
        
        try:
            objectives = self.sb_access.GetObjectives()
            self.objectives_list = [obj.mName for obj in objectives]
            self.dest_objective_combo['values'] = self.objectives_list
            
            # Also populate OilBoy objective dropdown with actual objective names
            self.oilboy_obj_loc_combo['values'] = self.objectives_list
            
            if self.objectives_list:
                self.dest_objective_combo.set(self.objectives_list[0])
                self.log_message(f"Loaded {len(self.objectives_list)} objectives")
            
            # Set OilBoy objective to first available objective if not already set
            if self.objectives_list:
                current_value = self.oilboy_obj_loc_var.get()
                if not current_value or current_value not in self.objectives_list:
                    # Set to first objective if no value or value not in current list
                    self.oilboy_obj_loc_var.set(self.objectives_list[0])
                    self.log_message(f"Set OilBoy objective to first available: {self.objectives_list[0]}")
            
        except Exception as e:
            self.log_message(f"Error loading objectives: {e}")

    def populate_known_devices(self):
        """Populate known devices dropdown"""
        try:
            known_devices = list(self.config["oilboy"]["known_devices"].keys())
            self.known_devices_combo['values'] = known_devices
            if known_devices:
                self.known_devices_combo.set(known_devices[0])
        except Exception as e:
            self.log_message(f"Error populating known devices: {e}")

    def on_known_device_selected(self, event):
        """Handle selection from known devices dropdown"""
        try:
            selected_serial = self.known_devices_var.get()
            if selected_serial:
                self.oilboy_serial_var.set(selected_serial)
                self.log_message(f"Selected OilBoy: {selected_serial}")
        except Exception as e:
            self.log_message(f"Error selecting known device: {e}")

    def connect_to_oilboy(self):
        """Connect to OilBoy via BLE"""
        if not self.asyncio_loop:
            self.log_message("Error: Asyncio loop not ready")
            return
        
        try:
            # Get serial number from UI
            serial = self.oilboy_serial_var.get().strip()
            if not serial:
                self.log_message("Error: Please enter OilBoy serial number")
                return
            
            # Update config with current serial number
            self.config["oilboy"]["serial_number"] = serial
            
            # Check if we have a known MAC address for this serial
            known_mac = self.config["oilboy"]["known_devices"].get(serial)
            
            # Create OilBoy BLE object if not exists
            if not self.oilboy:
                self.oilboy = OilBoyBLE(
                    status_callback=self.log_message,
                    connected_callback=self.on_oilboy_connected,
                    battery_callback=self.on_battery_update
                )
                self.oilboy.loop = self.asyncio_loop
            
            # Try direct MAC connect first with retries
            if known_mac:
                self.log_message(f"Trying MAC connection to {known_mac}...")
                for attempt in range(3):
                    self.log_message(f"MAC connection attempt {attempt + 1}/3...")
                    success = self.oilboy.connect_by_mac(known_mac)
                    if success:
                        self.log_message("MAC connection successful!")
                        self._safe_battery_request()
                        return
                    elif attempt < 2:
                        self.log_message("MAC connection failed, retrying...")
                        import time
                        time.sleep(2)
            
            # Fallback to scan and connect with retries
            self.log_message(f"Scanning for OilBoy {serial}...")
            for attempt in range(3):
                self.log_message(f"Scan attempt {attempt + 1}/3...")
                success = self.oilboy.scan_and_connect_with_serial(serial)
                if success:
                    self.log_message("Scan connection successful!")
                    self._safe_battery_request()
                    return
                elif attempt < 2:
                    self.log_message("Scan failed, retrying...")
                    import time
                    time.sleep(2)
            
            self.log_message("Failed to connect to OilBoy after all attempts")
                
        except Exception as e:
            self.log_message(f"Error connecting to OilBoy: {e}")

    def on_oilboy_connected(self, connected):
        """Callback when OilBoy connection status changes"""
        self.oilboy_connected = connected
        if connected:
            self.oilboy_status_var.set("Connected")
            self.oilboy_status_label.configure(foreground="#51cf66")  # Green for connected
            self.log_message("OilBoy connected successfully")
            
            # Request battery status after connection is established
            self.root.after(1000, self._request_battery_after_connection)
            
            # Save the MAC address for future quick connections
            if self.oilboy and self.oilboy.device_address:
                serial = self.oilboy_serial_var.get().strip()
                if serial:
                    self.config["oilboy"]["known_devices"][serial] = self.oilboy.device_address
                    self.save_config()
                    self.log_message(f"Saved MAC address {self.oilboy.device_address} for serial {serial}")
        else:
            self.oilboy_status_var.set("Disconnected")
            self.oilboy_status_label.configure(foreground="#ff6b6b")  # Red for disconnected
            self.log_message("OilBoy disconnected")

    def _request_battery_after_connection(self):
        """Request battery status after connection is established"""
        if self.oilboy_connected and self.oilboy:
            try:
                self.log_message("Requesting battery status after connection...")
                success = self.oilboy.send_command("BATTERY")
                if success:
                    self.log_message("Battery status request sent successfully")
                else:
                    self.log_message("Battery status request failed")
            except TimeoutError:
                self.log_message("Battery status request timed out - OilBoy may not be responding")
            except Exception as e:
                self.log_message(f"Error requesting battery status: {e}")

    def on_battery_update(self, voltage, usb_power):
        """Callback for battery voltage updates"""
        status = f"{voltage:.2f}V"
        if usb_power:
            status += " (USB)"
        self.battery_var.set(status)

    def save_settings(self):
        """Save current settings to config"""
        try:
            self.config["settings"]["oilboy_objective_location"] = self.oilboy_obj_loc_var.get()
            self.config["settings"]["oilboy_offset_microns"] = self.oilboy_offset_var.get()
            self.config["settings"]["default_oil_amount"] = self.oil_amount_var.get()
            
            # Save window geometry
            self.save_window_geometry()
            
            self.save_config()
            self.log_message("Settings saved successfully")
            
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")

    def save_oilboy_config(self):
        """Save OilBoy configuration to config"""
        try:
            serial = self.oilboy_serial_var.get().strip()
            if not serial:
                self.log_message("Error: Please enter OilBoy serial number")
                return
            
            self.config["oilboy"]["serial_number"] = serial
            self.save_config()
            self.log_message(f"OilBoy configuration saved: Serial {serial}")
            
        except Exception as e:
            self.log_message(f"Error saving OilBoy configuration: {e}")

    def execute_mode1(self):
        """Execute Mode 1: Low Power → High Power"""
        if self.shutting_down:
            self.log_message("Cannot execute mode - application is shutting down")
            return
            
        if not self.slidebook_connected:
            messagebox.showerror("Error", "SlideBook not connected")
            return
        
        if not self.oilboy_connected:
            messagebox.showerror("Error", "OilBoy not connected")
            return
        
        dest_objective = self.dest_objective_var.get()
        if not dest_objective:
            messagebox.showerror("Error", "Please select destination objective")
            return
        
        self.log_message(f"Starting Mode 1: Switching to {dest_objective}")
        
        # Run in separate thread to avoid blocking UI
        threading.Thread(target=self._execute_mode1_thread, args=(dest_objective,), daemon=True).start()

    def _execute_mode1_thread(self, dest_objective):
        """Execute Mode 1 in background thread"""
        try:
            # Check shutdown flag before each step
            if self.shutting_down:
                self.log_message("Mode 1 cancelled - application shutting down")
                return
                
            # Step 1: Switch to OilBoy objective
            oilboy_objective = self.oilboy_obj_loc_var.get()
            self.log_message(f"Step 1: Switching to OilBoy objective ({oilboy_objective})...")
            self.switch_to_objective(oilboy_objective)
            time.sleep(2)
            
            # Step 2: Apply oil
            if self.shutting_down:
                self.log_message("Mode 1 cancelled - application shutting down")
                return
            self.log_message("Step 2: Applying oil...")
            self.apply_oil()
            time.sleep(1)
            
            # Step 3: Raise stage for oil application
            if self.shutting_down:
                self.log_message("Mode 1 cancelled - application shutting down")
                return
            self.log_message("Step 3: Raising stage for oil application...")
            self.raise_stage_for_oil()
            time.sleep(2)
            
            # Step 4: Lower stage
            if self.shutting_down:
                self.log_message("Mode 1 cancelled - application shutting down")
                return
            self.log_message("Step 4: Lowering stage...")
            self.lower_stage()
            time.sleep(2)
            
            # Step 5: Switch to destination objective
            if self.shutting_down:
                self.log_message("Mode 1 cancelled - application shutting down")
                return
            self.log_message(f"Step 5: Switching to {dest_objective}...")
            self.switch_to_objective(dest_objective)
            
            self.log_message("Mode 1 completed successfully")
            
        except Exception as e:
            self.log_message(f"Error in Mode 1: {e}")

    def execute_mode2(self):
        """Execute Mode 2: Re-oil High Power"""
        if self.shutting_down:
            self.log_message("Cannot execute mode - application is shutting down")
            return
            
        if not self.slidebook_connected:
            messagebox.showerror("Error", "SlideBook not connected")
            return
        
        if not self.oilboy_connected:
            messagebox.showerror("Error", "OilBoy not connected")
            return
        
        self.log_message("Starting Mode 2: Re-oiling current high power objective")
        
        # Run in separate thread to avoid blocking UI
        threading.Thread(target=self._execute_mode2_thread, daemon=True).start()

    def _execute_mode2_thread(self):
        """Execute Mode 2 in background thread"""
        try:
            # Check shutdown flag before starting
            if self.shutting_down:
                self.log_message("Mode 2 cancelled - application shutting down")
                return
                
            # Store current objective
            current_obj = self.current_objective
            
            # Step 1: Switch to OilBoy objective
            oilboy_objective = self.oilboy_obj_loc_var.get()
            self.log_message(f"Step 1: Switching to OilBoy objective ({oilboy_objective})...")
            self.switch_to_objective(oilboy_objective)
            time.sleep(2)
            
            # Step 2: Apply oil
            if self.shutting_down:
                self.log_message("Mode 2 cancelled - application shutting down")
                return
            self.log_message("Step 2: Applying oil...")
            self.apply_oil()
            time.sleep(1)
            
            # Step 3: Raise stage for oil application
            if self.shutting_down:
                self.log_message("Mode 2 cancelled - application shutting down")
                return
            self.log_message("Step 3: Raising stage for oil application...")
            self.raise_stage_for_oil()
            time.sleep(2)
            
            # Step 4: Lower stage
            if self.shutting_down:
                self.log_message("Mode 2 cancelled - application shutting down")
                return
            self.log_message("Step 4: Lowering stage...")
            self.lower_stage()
            time.sleep(2)
            
            # Step 5: Return to original objective
            if self.shutting_down:
                self.log_message("Mode 2 cancelled - application shutting down")
                return
            self.log_message(f"Step 5: Returning to {current_obj}...")
            self.switch_to_objective(current_obj)
            
            self.log_message("Mode 2 completed successfully")
            
        except Exception as e:
            self.log_message(f"Error in Mode 2: {e}")

    def switch_to_objective(self, objective_name):
        """Switch to specified objective via SlideBook"""
        if self.shutting_down:
            raise Exception("Cannot switch objective - application is shutting down")
            
        if not self.slidebook_connected or not self.sb_access:
            raise Exception("SlideBook not connected")
        
        try:
            # Find objective by name
            objectives = self.sb_access.GetObjectives()
            target_position = None
            
            for obj in objectives:
                if obj.mName == objective_name:
                    target_position = obj.mTurretPosition
                    break
            
            if target_position is None:
                raise Exception(f"Objective '{objective_name}' not found")
            
            # Switch to objective
            self.sb_access.SetHardwareComponentPosition(
                MicroscopeHardwareComponent.ObjectiveTurret, target_position)
            
            self.log_message(f"Switched to objective: {objective_name}")
            
            # Update current state
            self.update_slidebook_state()
            
        except Exception as e:
            raise Exception(f"Error switching to objective: {e}")

    def apply_oil(self):
        """Apply oil using OilBoy"""
        if self.shutting_down:
            raise Exception("Cannot apply oil - application is shutting down")
            
        if not self.oilboy_connected:
            raise Exception("OilBoy not connected")
        
        # Test connection with PING before sending OIL command
        if not self.test_oilboy_connection():
            self.log_message("OilBoy connection test failed, attempting reconnection...")
            if not self.reconnect_oilboy():
                raise Exception("Failed to reconnect to OilBoy")
            # Test connection again after reconnection
            if not self.test_oilboy_connection():
                raise Exception("OilBoy connection still failed after reconnection")
        
        oil_amount = self.oil_amount_var.get()
        self.oilboy.send_command(f"OIL:{oil_amount}")
        self.log_message(f"Applied {oil_amount} steps of oil")

    def test_oilboy_connection(self):
        """Test OilBoy connection with PING command"""
        if not self.oilboy_connected or not self.oilboy:
            return False
        
        try:
            self.log_message("Testing OilBoy connection with PING...")
            # Send PING and wait for PONG response
            success = self.oilboy.send_command("PING")
            if success:
                self.log_message("OilBoy PING successful")
                return True
            else:
                self.log_message("OilBoy PING failed")
                return False
        except Exception as e:
            self.log_message(f"Error testing OilBoy connection: {e}")
            return False

    def reconnect_oilboy(self):
        """Attempt to reconnect to OilBoy with simple retries"""
        try:
            self.log_message("Attempting OilBoy reconnection...")
            
            # Disconnect first if connected
            if self.oilboy_connected and self.oilboy:
                try:
                    self.oilboy.disconnect()
                except Exception as e:
                    self.log_message(f"Error during disconnect: {e}")
                finally:
                    self.oilboy_connected = False
            
            # Wait a moment before reconnecting
            import time
            time.sleep(1)
            
            # Try to reconnect using the same method as original connection
            serial = self.oilboy_serial_var.get().strip()
            if not serial:
                self.log_message("No OilBoy serial number available for reconnection")
                return False
            
            # Check if we have a known MAC address for this serial
            known_mac = self.config["oilboy"]["known_devices"].get(serial)
            
            if known_mac:
                self.log_message(f"Trying MAC reconnection to {known_mac}...")
                for attempt in range(3):
                    self.log_message(f"MAC reconnection attempt {attempt + 1}/3...")
                    success = self.oilboy.connect_by_mac(known_mac)
                    if success:
                        self.oilboy_connected = True
                        self.log_message("OilBoy reconnected via MAC address")
                        self._safe_battery_request()
                        return True
                    elif attempt < 2:
                        self.log_message("MAC reconnection failed, retrying...")
                        time.sleep(2)
            
            # Fallback to scan and connect
            self.log_message(f"Scanning for OilBoy {serial} for reconnection...")
            for attempt in range(3):
                self.log_message(f"Scan reconnection attempt {attempt + 1}/3...")
                success = self.oilboy.scan_and_connect_with_serial(serial)
                if success:
                    self.oilboy_connected = True
                    self.log_message("OilBoy reconnected via scan")
                    self._safe_battery_request()
                    return True
                elif attempt < 2:
                    self.log_message("Scan reconnection failed, retrying...")
                    time.sleep(2)
            
            self.log_message("OilBoy reconnection failed after all attempts")
            return False
                
        except Exception as e:
            self.log_message(f"Error during OilBoy reconnection: {e}")
            return False

    def raise_stage_for_oil(self):
        """Raise stage by offset amount for oil application"""
        if self.shutting_down:
            raise Exception("Cannot raise stage - application is shutting down")
            
        if not self.slidebook_connected or not self.sb_access:
            raise Exception("SlideBook not connected")
        
        try:
            # Get current Z position
            current_z_data = self.sb_access.GetHardwareComponentLocationMicrons(MicroscopeHardwareComponent.ZStage)
            if not current_z_data or len(current_z_data) < 3:
                raise Exception("Failed to read current Z position")
            
            current_z = current_z_data[2]
            self.log_message(f"Current Z position: {current_z:.2f} μm")
            
            # Store original position for later restoration
            self.original_z_position = current_z
            
            # Calculate new position with offset
            offset = float(self.oilboy_offset_var.get())
            target_z = current_z + offset
            
            # Move to new position
            success = self.sb_access.SetHardwareComponentLocationMicrons(
                MicroscopeHardwareComponent.ZStage, 0.0, 0.0, target_z)
            
            if success:
                self.log_message(f"Raised stage from {current_z:.2f} to {target_z:.2f} μm")
            else:
                raise Exception("Failed to raise stage")
                
        except Exception as e:
            self.log_message(f"Error raising stage: {e}")
            raise

    def lower_stage(self):
        """Lower stage back to original position"""
        if self.shutting_down:
            raise Exception("Cannot lower stage - application is shutting down")
            
        if not self.slidebook_connected or not self.sb_access:
            raise Exception("SlideBook not connected")
        
        try:
            # Use stored original position
            if not hasattr(self, 'original_z_position'):
                raise Exception("No original Z position stored")
            
            target_z = self.original_z_position
            
            # Move to original position
            success = self.sb_access.SetHardwareComponentLocationMicrons(
                MicroscopeHardwareComponent.ZStage, 0.0, 0.0, target_z)
            
            if success:
                self.log_message(f"Lowered stage to {target_z:.2f} μm")
            else:
                raise Exception("Failed to lower stage")
                
        except Exception as e:
            self.log_message(f"Error lowering stage: {e}")
            raise

    def check_battery(self):
        """Manually check and display battery status from OilBoy"""
        if not self.oilboy_connected:
            messagebox.showwarning("Warning", "OilBoy not connected. Cannot check battery.")
            return
        
        try:
            self.log_message("Requesting battery status from OilBoy...")
            success = self.oilboy.send_command("BATTERY")
            if success:
                self.log_message("Battery status request sent successfully")
            else:
                self.log_message("Battery status request failed")
        except TimeoutError:
            self.log_message("Battery status request timed out - OilBoy may not be responding")
            messagebox.showwarning("Warning", "Battery status request timed out. OilBoy may not be responding.")
        except Exception as e:
            self.log_message(f"Error requesting battery status: {e}")
            messagebox.showerror("Error", f"Error requesting battery status: {e}")

    def test_oilboy_connection_ui(self):
        """Manually test OilBoy connection via UI button"""
        if not self.oilboy_connected:
            messagebox.showwarning("Warning", "OilBoy not connected. Cannot test connection.")
            return
        
        if self.test_oilboy_connection():
            messagebox.showinfo("Success", "OilBoy connection is successful!")
        else:
            messagebox.showerror("Error", "OilBoy connection failed. Please check logs.")

    def on_closing(self):
        """Handle application closing with graceful disconnection"""
        # Prevent multiple shutdown attempts
        if hasattr(self, '_shutdown_in_progress') and self._shutdown_in_progress:
            return
        self._shutdown_in_progress = True
        
        try:
            # Set shutdown flag to prevent any new operations
            self.shutting_down = True
            self.log_message("Application shutdown initiated...")
            
            # Disconnect from OilBoy first
            if self.oilboy and self.oilboy_connected:
                self.log_message("Disconnecting from OilBoy...")
                try:
                    success = self.oilboy.disconnect()
                    if success:
                        self.log_message("OilBoy disconnected successfully")
                    else:
                        self.log_message("OilBoy disconnect returned False")
                except Exception as e:
                    self.log_message(f"Error disconnecting OilBoy: {e}")
                finally:
                    self.oilboy_connected = False
                    if hasattr(self, 'oilboy_status_label') and self.oilboy_status_label.winfo_exists():
                        self.oilboy_status_label.configure(foreground="#ff6b6b")  # Red for disconnected
            
            # Disconnect from SlideBook with proper socket shutdown
            if self.slidebook_connected:
                self.log_message("Disconnecting from SlideBook...")
                try:
                    # Mark as disconnected first to prevent any new API calls
                    self.slidebook_connected = False
                    
                    # Proper TCP shutdown sequence
                    if self.slidebook_socket:
                        try:
                            # Shutdown the socket properly
                            self.slidebook_socket.shutdown(socket.SHUT_RDWR)
                        except (OSError, socket.error):
                            # Socket might already be closed or in error state
                            pass
                        finally:
                            try:
                                self.slidebook_socket.close()
                                self.log_message("SlideBook socket closed cleanly")
                            except Exception as e:
                                self.log_message(f"Error closing SlideBook socket: {e}")
                            self.slidebook_socket = None
                    
                    # Clear the SBAccess object
                    self.sb_access = None
                    
                except Exception as e:
                    self.log_message(f"Error during SlideBook disconnect: {e}")
                finally:
                    if hasattr(self, 'slidebook_status_label') and self.slidebook_status_label.winfo_exists():
                        self.slidebook_status_label.configure(foreground="#ff6b6b")  # Red for disconnected
            
            # Stop asyncio loop
            if self.asyncio_loop and not self.asyncio_loop.is_closed():
                try:
                    self.asyncio_loop.call_soon_threadsafe(self.asyncio_loop.stop)
                    self.log_message("Asyncio loop stopped")
                except Exception as e:
                    self.log_message(f"Error stopping asyncio loop: {e}")
            
            # Save configuration
            try:
                # Save window geometry before saving config
                self.save_window_geometry()
                self.save_config()
                self.log_message("Configuration saved")
            except Exception as e:
                self.log_message(f"Error saving configuration: {e}")
            
            self.log_message("Application shutdown complete")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            # Destroy the window only if it still exists
            try:
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.destroy()
            except Exception:
                pass

    def _optimized_mac_connection(self, mac_address):
        """Optimized MAC connection for deep sleep/burst pattern"""
        try:
            # Try multiple connection attempts during expected wake windows
            max_attempts = 3
            for attempt in range(max_attempts):
                self.log_message(f"MAC connection attempt {attempt + 1}/{max_attempts}...")
                
                success = self.oilboy.connect_by_mac(mac_address)
                if success:
                    self.log_message("MAC connection successful!")
                    # Request battery status on successful connection
                    self._safe_battery_request()
                    return True
                
                # Wait for next wake window (10.1 second cycle)
                if attempt < max_attempts - 1:
                    self.log_message("MAC connection failed, waiting for next wake window...")
                    import time
                    time.sleep(10.5)  # Slightly longer than cycle to ensure we catch next window
            
            return False
            
        except Exception as e:
            self.log_message(f"Error in optimized MAC connection: {e}")
            return False

    def _optimized_scan_and_connect(self, serial):
        """Optimized scan and connect for deep sleep/burst pattern"""
        try:
            # Use longer scan window to catch multiple burst cycles
            self.log_message("Starting optimized scan for burst advertising...")
            
            # Scan for multiple wake cycles to increase chances of detection
            max_scan_cycles = 2
            for cycle in range(max_scan_cycles):
                self.log_message(f"Scan cycle {cycle + 1}/{max_scan_cycles}...")
                
                success = self.oilboy.scan_and_connect_with_serial(serial, burst_window=12)
                if success:
                    self.log_message("Optimized scan connection successful!")
                    # Request battery status on successful connection
                    self._safe_battery_request()
                    return True
                
                # Wait between scan cycles if not the last attempt
                if cycle < max_scan_cycles - 1:
                    self.log_message("Scan cycle failed, waiting for next wake window...")
                    import time
                    time.sleep(10.5)  # Wait for next wake cycle
            
            return False
            
        except Exception as e:
            self.log_message(f"Error in optimized scan and connect: {e}")
            return False

    def _safe_battery_request(self):
        """Safely request battery status with error handling"""
        try:
            # Add a delay to let OilBoy fully wake up before requesting battery
            import time
            time.sleep(3)  # Wait 3 seconds for OilBoy to be ready
            
            self.log_message("Requesting battery status...")
            success = self.oilboy.send_command("BATTERY")
            if success:
                self.log_message("Battery status request sent successfully")
            else:
                self.log_message("Battery status request failed")
        except TimeoutError:
            self.log_message("Battery status request timed out - OilBoy may not be responding")
        except Exception as e:
            self.log_message(f"Error requesting battery status: {e}")

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.log_message("Application interrupted by user")
        except Exception as e:
            self.log_message(f"Application error: {e}")
        finally:
            # Ensure cleanup happens even if mainloop exits unexpectedly
            self.on_closing()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create and run application
    app = OilBoyStandaloneApp()
    app.run() 