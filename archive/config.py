#!/usr/bin/env python3
"""Configuration module for DatePrinter"""

import json
import os
import sys

CONFIG_FILE = "printer-config.json"

# Minimal defaults for test scripts
TEST_DEFAULTS = {
    "default_printer": None,
    "date_format": "%B %d, %Y",
    "font_path": "C:\\Windows\\Fonts\\arial.ttf",
    "printers": {}
}

def load_config(require_full_config=True):
    """
    Load configuration from JSON file
    
    Args:
        require_full_config: If True, exit if config missing (for main script)
                           If False, return defaults (for test scripts)
    """
    if not os.path.exists(CONFIG_FILE):
        if require_full_config:
            print(f"\nERROR: Configuration file '{CONFIG_FILE}' not found!")
            print("\nPlease create a printer-config.json file with the following structure:")
            print(json.dumps({
                "default_printer": "Your Printer Name",
                "date_format": "%B %d, %Y",
                "font_path": "C:\\Windows\\Fonts\\arial.ttf",
                "max_retries": 3,
                "wait_between_tries": 2,
                "pause_between_labels": 1,
                "month_size_ratios": {
                    "January": 0.15,
                    "February": 0.15
                    # ... add other months as needed
                },
                "windows_device_caps": {
                    "PHYSICALWIDTH": 110,
                    "PHYSICALHEIGHT": 111,
                    "LOGPIXELSX": 88,
                    "LOGPIXELSY": 90,
                    "HORZRES": 8,
                    "VERTRES": 10,
                    "PHYSICALOFFSETX": 112,
                    "PHYSICALOFFSETY": 113
                },
                "printers": {
                    "Your Printer Name": {
                        "label_width_in": 2.25,
                        "label_height_in": 1.25,
                        "dpi": 203,
                        "bottom_margin": 15,
                        "positioning_mode": "auto",
                        "horizontal_offset": 0,
                        "bluetooth_device_name": "",
                        "bluetooth_wait_time": 3
                    }
                }
            }, indent=2))
            print("\nSee README.md for detailed configuration documentation.")
            sys.exit(1)
        else:
            # Return minimal defaults for test scripts
            print(f"Warning: {CONFIG_FILE} not found, using test defaults")
            return TEST_DEFAULTS.copy()
    
    # Load the config file
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"\nERROR: Invalid JSON in {CONFIG_FILE}: {e}")
        if require_full_config:
            sys.exit(1)
        return TEST_DEFAULTS.copy()
    except Exception as e:
        print(f"\nERROR: Failed to load {CONFIG_FILE}: {e}")
        if require_full_config:
            sys.exit(1)
        return TEST_DEFAULTS.copy()

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_printer_config(config, printer_name):
    """Get printer-specific configuration, with safe defaults"""
    default_printer_config = {
        "label_width_in": 2.25,
        "label_height_in": 1.25,
        "dpi": 203,
        "bottom_margin": 15,
        "positioning_mode": "auto",
        "horizontal_offset": 0,
        "bluetooth_device_name": "",
        "bluetooth_wait_time": 3
    }
    
    if printer_name not in config.get("printers", {}):
        # Create default printer config
        if "printers" not in config:
            config["printers"] = {}
        config["printers"][printer_name] = default_printer_config.copy()
    
    # Merge with defaults to ensure all keys exist
    printer_config = config["printers"][printer_name]
    for key, value in default_printer_config.items():
        if key not in printer_config:
            printer_config[key] = value
    
    return printer_config

def get_default_printer(config):
    """Get the default printer name, or prompt for selection"""
    return config.get("default_printer", None)

def get_available_printers():
    """Get list of available printers from Windows"""
    try:
        import win32print
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        return [(p[2], p) for p in printers]  # Return list of (name, full_info) tuples
    except Exception as e:
        print(f"Error enumerating printers: {e}")
        return []