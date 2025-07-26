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

# --- USER SETTINGS ---
BLUETOOTH_DEVICE_NAME = "RW402B-20B0"  # As seen in Bluetooth Settings
PRINTER_NAME = "Munbyn RW402B(Bluetooth)"                     # As seen in printer list
LABEL_WIDTH_IN, LABEL_HEIGHT_IN = 2.25, 1.25                 # Inches
DPI = 300
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"                   # Bold font path
DATE_FORMAT = "%B %d, %Y"  # e.g., "January 26, 2025"
MAX_RETRIES = 6
WAIT_BETWEEN_TRIES = 5  # Seconds
CONFIG_FILE = "printer-config.json"
BOTTOM_MARGIN = 5  # Pixels from bottom of label

# Month-specific size ratios (longer month names get smaller text)
MONTH_SIZE_RATIOS = {
    "January": 0.15,
    "February": 0.14,
    "March": 0.18,
    "April": 0.18,
    "May": 0.20,
    "June": 0.19,
    "July": 0.19,
    "August": 0.16,
    "September": 0.13,
    "October": 0.15,
    "November": 0.14,
    "December": 0.14
}

def load_config():
    """Load configuration from JSON file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

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

def generate_label_image(date_str, date_obj):
    width_px = int(LABEL_WIDTH_IN * DPI)
    height_px = int(LABEL_HEIGHT_IN * DPI)
    image = Image.new('L', (width_px, height_px), 255)
    draw = ImageDraw.Draw(image)

    # Get month-specific size ratio
    month_name = date_obj.strftime("%B")
    text_height_ratio = MONTH_SIZE_RATIOS.get(month_name, 0.15)
    
    # Calculate maximum dimensions
    max_text_height = int(height_px * text_height_ratio)
    max_text_width = int(width_px * 0.85)  # Use 85% of label width for safety
    
    # Find the right font size
    font_size = 10
    for size in range(10, 500):
        font = ImageFont.truetype(FONT_PATH, size)
        # Use textbbox to get accurate text dimensions
        bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if text_height > max_text_height or text_width > max_text_width:
            font_size = size - 1
            break
        font_size = size
    
    # Use the determined font size
    font = ImageFont.truetype(FONT_PATH, font_size)
    
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
    # We want the bottom of the text to be BOTTOM_MARGIN pixels from the bottom
    y = height_px - BOTTOM_MARGIN - text_height
    
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
    print(f"Bottom margin: {BOTTOM_MARGIN}px")
    
    image.save("label_preview.png")  # Optional preview
    return image


def print_label(image, printer_name):
    width_px, height_px = image.size
    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        hDC.StartDoc('Label')
        hDC.StartPage()
        dib = ImageWin.Dib(image)
        dib.draw(hDC.GetHandleOutput(), (0, 0, width_px, height_px))
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        print(f"Label sent to printer: {printer_name}")
        return True
    except Exception as e:
        print(f"Printing failed: {e}")
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
    default_printer = config.get("default_printer", None)
    
    # Step 1: Get printer selection
    selected_printer = None
    
    # If we have a default and not forcing list, try to use it
    if default_printer and not args.list:
        # Get all printers to verify default still exists
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        printer_names = [p[2] for p in all_printers]
        
        if default_printer in printer_names:
            selected_printer = default_printer
            print(f"Using default printer: {selected_printer}")
        else:
            print(f"Default printer '{default_printer}' not found.")
            default_printer = None
    
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

    # Step 2: Try to connect to Bluetooth printer (best effort)
    if BLUETOOTH_DEVICE_NAME:
        reconnect_bluetooth_device(BLUETOOTH_DEVICE_NAME)
        print("Waiting for Bluetooth device to connect...")
        time.sleep(3)  # Give time to connect

    # Step 3: Generate the label image
    if args.date:
        try:
            # Parse the provided date
            date_obj = datetime.strptime(args.date, "%Y-%m-%d")
            date_str = date_obj.strftime(DATE_FORMAT)
            print(f"Using specified date: {date_str}")
        except ValueError:
            print(f"Invalid date format: {args.date}. Please use YYYY-MM-DD format.")
            exit(1)
    else:
        date_obj = datetime.now()
        date_str = date_obj.strftime(DATE_FORMAT)
    
    label_img = generate_label_image(date_str, date_obj)
    print(f"Label image generated for: {date_str}")

    # Step 4: Print the requested number of labels
    print(f"\nPrinting {args.count} label(s)...")
    
    for label_num in range(1, args.count + 1):
        if args.count > 1:
            print(f"\nLabel {label_num} of {args.count}:")
        
        # Try printing with retries
        for attempt in range(MAX_RETRIES):
            print(f"  Print attempt {attempt + 1} of {MAX_RETRIES}...")
            success = print_label(label_img, selected_printer)
            if success:
                if label_num < args.count:
                    time.sleep(1)  # Brief pause between labels
                break
            else:
                print(f"  Retrying in {WAIT_BETWEEN_TRIES} seconds...")
                time.sleep(WAIT_BETWEEN_TRIES)
        else:
            print("Failed to print after multiple attempts. Is the printer powered on, paired, and connected?")
            exit(1)
    
    print(f"\nSuccessfully printed {args.count} label(s).")
