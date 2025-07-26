import time
import subprocess
import json
import os
import sys
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageWin
import win32print
import win32ui
import win32con

# --- CONFIGURATION ---
CONFIG_FILE = "printer-config.json"
DEFAULT_CONFIG_FILE = "printer-config.json.default"

# Minimal defaults if no config files exist
MINIMAL_DEFAULTS = {
    "default_printer": None,
    "date_format": "%B %d, %Y",
    "font_path": "C:/Windows/Fonts/arialbd.ttf",
    "max_retries": 6,
    "wait_between_tries": 5,
    "printers": {}
}

def load_config():
    """Load configuration from JSON file with defaults"""
    config = None
    
    # Try to load user config first
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {CONFIG_FILE}: {e}")
    
    # If no user config, try to load default config
    if config is None and os.path.exists(DEFAULT_CONFIG_FILE):
        try:
            with open(DEFAULT_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print(f"Loaded default configuration from {DEFAULT_CONFIG_FILE}")
        except Exception as e:
            print(f"Warning: Could not load {DEFAULT_CONFIG_FILE}: {e}")
    
    # If still no config, use minimal defaults
    if config is None:
        config = MINIMAL_DEFAULTS.copy()
        print("Using minimal built-in defaults")
    
    # Ensure required keys exist
    for key in ['printers', 'month_size_ratios']:
        if key not in config:
            config[key] = {}
    
    return config

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
            "bluetooth_device_name": "",
            "bluetooth_wait_time": 3
        }
    return config["printers"][printer_name]

def list_printers():
    print("Available Printers:")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    for i, printer in enumerate(printers):
        print(f"{i+1}: {printer[2]}")
    return printers

def reconnect_bluetooth_device(device_name):
    """
    Attempts to reconnect the Bluetooth device using PowerShell (best effort).
    """
    print(f"Trying to reconnect Bluetooth device: {device_name}")
    connect_cmd = f'''
    $device = Get-PnpDevice | Where-Object {{ $_.FriendlyName -like "*{device_name}*" }}
    if ($device) {{
        $deviceId = $device.InstanceId
        & "C:\\Windows\\System32\\DevicePairingWizard.exe" /connect $deviceId
    }}'''
    try:
        subprocess.run(["powershell", "-Command", connect_cmd], check=True)
        print("Bluetooth reconnect command sent.")
    except Exception as e:
        print("Bluetooth reconnect attempt failed or not supported. Error:", e)

def generate_label_image(date_str, date_obj, config, printer_config):
    # Create image based on printer-specific settings
    width_px = int(printer_config['label_width_in'] * printer_config['dpi'])
    height_px = int(printer_config['label_height_in'] * printer_config['dpi'])
    image = Image.new('L', (width_px, height_px), 255)
    draw = ImageDraw.Draw(image)

    # Get month-specific size ratio
    month_name = date_obj.strftime("%B")
    text_height_ratio = config.get('month_size_ratios', {}).get(month_name, config.get('default_text_height_ratio', 0.15))
    
    # Calculate maximum dimensions
    max_text_height = int(height_px * text_height_ratio)
    max_text_width = int(width_px * config.get('max_text_width_ratio', 0.85))
    
    # Find the right font size
    min_font = config.get('min_font_size', 10)
    max_font = config.get('max_font_size', 500)
    font_size = min_font
    for size in range(min_font, max_font):
        font = ImageFont.truetype(config['font_path'], size)
        # Use textbbox to get accurate text dimensions
        bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if text_height > max_text_height or text_width > max_text_width:
            font_size = size - 1
            break
        font_size = size
    
    # Use the determined font size
    font = ImageFont.truetype(config['font_path'], font_size)
    
    # Get text dimensions using textbbox
    # textbbox returns absolute coordinates of the bounding box
    bbox = draw.textbbox((0, 0), date_str, font=font)
    
    # Calculate actual text width and height
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # For horizontal centering, we need to center the text within the label
    # Since bbox[0] might be negative (for characters extending left), we account for it
    x = (width_px - text_width) // 2
    
    # For vertical positioning at bottom with margin
    # We want the bottom of the text to be bottom_margin pixels from the bottom
    y = height_px - printer_config['bottom_margin'] - text_height
    
    # Calculate the actual drawing position
    draw_x = x - bbox[0]
    draw_y = y - bbox[1]
    
    # Add safety check to prevent left cutoff
    if draw_x < 0:
        print(f"WARNING: Text would be cut off on left! Adjusting from {draw_x} to 0")
        draw_x = 0
    
    # Draw the text at the calculated position
    draw.text((draw_x, draw_y), date_str, font=font, fill=0)
    
    # Debug info
    print(f"\n=== Debug Info ===")
    print(f"Date string: '{date_str}'")
    print(f"Font size: {font_size}, Text dimensions: {text_width}x{text_height}")
    print(f"BBox: left={bbox[0]}, top={bbox[1]}, right={bbox[2]}, bottom={bbox[3]}")
    print(f"Logical center position: x={x}, y={y}")
    print(f"Final draw position: ({draw_x}, {draw_y})")
    print(f"Label dimensions: {width_px}x{height_px}")
    print(f"Text will occupy: x={draw_x} to x={draw_x + text_width}")
    print(f"Bottom margin: {printer_config['bottom_margin']}px")
    
    image.save("label_preview.png")  # Optional preview
    return image


def print_label(image, printer_name, config, printer_config):
    width_px, height_px = image.size
    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        
        # Get printer dimensions and DPI
        printer_width = hDC.GetDeviceCaps(110)  # PHYSICALWIDTH
        printer_height = hDC.GetDeviceCaps(111)  # PHYSICALHEIGHT
        printer_dpi_x = hDC.GetDeviceCaps(88)   # LOGPIXELSX
        printer_dpi_y = hDC.GetDeviceCaps(90)   # LOGPIXELSY
        
        # Calculate the actual printable area
        printable_width = hDC.GetDeviceCaps(8)   # HORZRES
        printable_height = hDC.GetDeviceCaps(10)  # VERTRES
        offset_x = hDC.GetDeviceCaps(112)  # PHYSICALOFFSETX
        offset_y = hDC.GetDeviceCaps(113)  # PHYSICALOFFSETY
        
        print(f"\n=== Printer Info ===")
        print(f"Printer DPI: {printer_dpi_x}x{printer_dpi_y}")
        print(f"Physical size: {printer_width}x{printer_height}")
        print(f"Printable area: {printable_width}x{printable_height}")
        print(f"Offsets: x={offset_x}, y={offset_y}")
        
        hDC.StartDoc('Label')
        hDC.StartPage()
        
        # Set mapping mode to match pixels 1:1
        hDC.SetMapMode(win32con.MM_TEXT)
        
        # Create the DIB from our image
        dib = ImageWin.Dib(image)
        
        # The printer is centering on the left edge, so we need to shift by half the label width
        # Calculate half the label width in pixels
        half_label_width = int(printer_config['label_width_in'] * printer_config['dpi'] / 2)
        
        # Draw with the image shifted right by half the label width
        dib.draw(hDC.GetHandleOutput(), 
                (half_label_width, 0, half_label_width + width_px, height_px))
        
        print(f"Applied horizontal offset: {half_label_width}px (half of {printer_config['label_width_in']}\" at {printer_config['dpi']} DPI)")
        
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        print(f"Label sent to printer: {printer_name}")
        print(f"Image size: {width_px}x{height_px} pixels (created at {printer_config['dpi']} DPI)")
        print(f"Drew at coordinates: ({half_label_width}, 0, {half_label_width + width_px}, {height_px})")
        print(f"Expected physical size: {printer_config['label_width_in']}x{printer_config['label_height_in']} inches")
        return True
    except Exception as e:
        print(f"Printing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Print date labels on a label printer')
    parser.add_argument('-l', '--list', action='store_true', help='Force printer selection menu')
    parser.add_argument('-c', '--count', type=int, default=1, help='Number of labels to print (default: 1)')
    parser.add_argument('-d', '--date', type=str, help='Specific date to print (format: YYYY-MM-DD)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Step 1: Get printer selection
    selected_printer = None
    
    # If we have a default and not forcing list, try to use it
    if config['default_printer'] and not args.list:
        # Get all printers to verify default still exists
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        printer_names = [p[2] for p in all_printers]
        
        if config['default_printer'] in printer_names:
            selected_printer = config['default_printer']
            print(f"Using default printer: {selected_printer}")
        else:
            print(f"Default printer '{config['default_printer']}' not found.")
            config['default_printer'] = None
    
    # If no valid default or forcing list, show selection menu
    if not selected_printer:
        printers = list_printers()
        
        if not printers:
            print("No printers found!")
            exit(1)
        while True:
            try:
                selection = input("\nEnter the number of the printer you want to use: ")
                selection_num = int(selection)
                if 1 <= selection_num <= len(printers):
                    selected_printer = printers[selection_num - 1][2]
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
    if printer_config['bluetooth_device_name']:
        reconnect_bluetooth_device(printer_config['bluetooth_device_name'])
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
    
    label_img = generate_label_image(date_str, date_obj, config, printer_config)
    print(f"Label image generated for: {date_str}")

    # Step 4: Print the requested number of labels
    print(f"\nPrinting {args.count} label(s)...")
    
    for label_num in range(1, args.count + 1):
        if args.count > 1:
            print(f"\nLabel {label_num} of {args.count}:")
        
        # Try printing with retries
        for attempt in range(config['max_retries']):
            print(f"  Print attempt {attempt + 1} of {config['max_retries']}...")
            success = print_label(label_img, selected_printer, config, printer_config)
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
