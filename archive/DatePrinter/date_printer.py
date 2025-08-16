import time
import json
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path to import LabelPrinter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LabelPrinter import LabelGenerator, LabelPrinter

# --- CONFIGURATION ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "printer-config.json")

def load_config():
    """Load configuration from JSON file, fail if missing"""
    if not os.path.exists(CONFIG_FILE):
        print(f"\nERROR: Configuration file '{CONFIG_FILE}' not found!")
        print("\nPlease create a printer-config.json file with the following structure:")
        print(json.dumps({
            "default_printer": "Your Printer Name",
            "date_format": "%B %d, %Y",
            "font_path": "C:\\Windows\\Fonts\\arial.ttf" if sys.platform == 'win32' else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
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
                    "bluetooth_device_name": "",
                    "bluetooth_wait_time": 3
                }
            }
        }, indent=2))
        print("\nSee README.md for detailed configuration documentation.")
        sys.exit(1)
    
    # Load the config file
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"\nERROR: Invalid JSON in {CONFIG_FILE}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Failed to load {CONFIG_FILE}: {e}")
        sys.exit(1)

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_printer_config(config, printer_name):
    """Get printer-specific configuration, creating default if needed"""
    if printer_name not in config.get("printers", {}):
        # Create default printer config
        if "printers" not in config:
            config["printers"] = {}
        config["printers"][printer_name] = {
            "label_width_in": 2.25,
            "label_height_in": 1.25,
            "dpi": 203,
            "bottom_margin": 15,
            "horizontal_offset": 0,
            "positioning_mode": "auto",
            "bluetooth_device_name": "",
            "bluetooth_wait_time": 3
        }
    return config["printers"][printer_name]

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Print date labels on a thermal label printer',
        epilog='Configuration is stored in printer-config.json (must be created manually)'
    )
    parser.add_argument('-l', '--list', action='store_true', 
                        help='Force printer selection menu (ignore default printer)')
    parser.add_argument('-c', '--count', type=int, default=1, 
                        help='Number of labels to print (default: 1)')
    parser.add_argument('-d', '--date', type=str, 
                        help='Specific date to print (format: YYYY-MM-DD, default: today)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize label printer
    label_printer = LabelPrinter(config)
    label_generator = LabelGenerator(config)
    
    # Step 1: Get printer selection
    selected_printer = None
    
    # If we have a default and not forcing list, try to use it
    if config.get('default_printer') and not args.list:
        # Get all printers to verify default still exists
        all_printers = label_printer.list_printers()
        printer_names = [p[1] for p in all_printers]
        
        if config['default_printer'] in printer_names:
            selected_printer = config['default_printer']
            print(f"Using default printer: {selected_printer}")
        else:
            print(f"Default printer '{config['default_printer']}' not found.")
            config['default_printer'] = None
    
    # If no valid default or forcing list, show selection menu
    if not selected_printer:
        printers = label_printer.list_printers()
        
        if not printers:
            print("No printers found!")
            exit(1)
            
        print("Available Printers:")
        for i, printer_name in printers:
            print(f"{i+1}: {printer_name}")
            
        while True:
            try:
                selection = input("\nEnter the number of the printer you want to use: ")
                selection_num = int(selection)
                if 1 <= selection_num <= len(printers):
                    selected_printer = printers[selection_num - 1][1]
                    print(f"Selected printer: {selected_printer}")
                    
                    # Save as new default
                    config["default_printer"] = selected_printer
                    save_config(config)
                    print(f"Saved '{selected_printer}' as default printer.")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(printers)}")
            except ValueError:
                print("Please enter a valid number")

    # Get printer-specific configuration
    printer_config = get_printer_config(config, selected_printer)
    
    # Step 2: Try to connect to Bluetooth printer (best effort)
    if printer_config.get('bluetooth_device_name'):
        label_printer.reconnect_bluetooth_device(printer_config['bluetooth_device_name'])
        print("Waiting for Bluetooth device to connect...")
        time.sleep(printer_config['bluetooth_wait_time'])

    # Step 3: Generate the label image
    if args.date:
        try:
            # Parse the provided date
            date_obj = datetime.strptime(args.date, "%Y-%m-%d")
            date_str = date_obj.strftime(config['date_format'])
            print(f"Using specified date: {date_str}")
        except ValueError:
            print(f"Invalid date format: {args.date}. Please use YYYY-MM-DD format.")
            exit(1)
    else:
        date_obj = datetime.now()
        date_str = date_obj.strftime(config['date_format'])
    
    # Get month-specific size ratio if available
    month_name = date_obj.strftime("%B")
    month_ratio = config.get('month_size_ratios', {}).get(month_name)
    
    custom_settings = {
        'debug': True,  # Enable debug output
        'text_height_ratio': month_ratio
    } if month_ratio else {'debug': True}
    
    label_img = label_generator.generate_label(date_str, printer_config, custom_settings)
    
    # Save preview
    preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "label_preview.png")
    label_img.save(preview_path)
    print(f"Label image generated for: {date_str}")
    print(f"Preview saved to: {preview_path}")

    # Step 4: Print the requested number of labels
    print(f"\nPrinting {args.count} label(s)...")
    
    for label_num in range(1, args.count + 1):
        if args.count > 1:
            print(f"\nLabel {label_num} of {args.count}:")
        
        # Try printing with retries
        for attempt in range(config['max_retries']):
            print(f"  Print attempt {attempt + 1} of {config['max_retries']}...")
            success = label_printer.print_label(label_img, selected_printer, printer_config)
            if success:
                if label_num < args.count:
                    time.sleep(config.get('pause_between_labels', 1))
                break
            else:
                print(f"  Retrying in {config['wait_between_tries']} seconds...")
                time.sleep(config['wait_between_tries'])
        else:
            print("Failed to print after multiple attempts. Is the printer powered on, paired, and connected?")
            exit(1)
    
    print(f"\nSuccessfully printed {args.count} label(s).")

if __name__ == "__main__":
    main()