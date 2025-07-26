import time
import subprocess
import json
import os
import sys
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
DATE_FORMAT = "%Y-%m-%d"
MAX_RETRIES = 6
WAIT_BETWEEN_TRIES = 5  # Seconds
CONFIG_FILE = "printer-config.json"
TEXT_HEIGHT_RATIO = 0.3  # Text fills 30% of label height for smaller text

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

def generate_label_image(date_str):
    width_px = int(LABEL_WIDTH_IN * DPI)
    height_px = int(LABEL_HEIGHT_IN * DPI)
    image = Image.new('L', (width_px, height_px), 255)
    draw = ImageDraw.Draw(image)

    # Dynamically find the largest font size that fits TEXT_HEIGHT_RATIO of label height
    max_text_height = int(height_px * TEXT_HEIGHT_RATIO)
    max_text_width = int(width_px * 0.8)  # Also limit to 80% of label width
    for size in range(10, 500):
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_height > max_text_height or text_width > max_text_width:
            font_size = size - 1
            break
    font = ImageFont.truetype(FONT_PATH, font_size)
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width_px - text_width) // 2
    y = (height_px - text_height) // 2
    draw.text((x, y), date_str, font=font, fill=0)
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
    # Check for command line arguments
    force_list = "--list" in sys.argv or "-l" in sys.argv
    
    # Load configuration
    config = load_config()
    default_printer = config.get("default_printer", None)
    
    # Step 1: List printers and allow selection
    printers = list_printers()
    
    if not printers:
        print("No printers found!")
        exit(1)
    
    # Use default printer if available and not forcing list
    selected_printer = None
    if default_printer and not force_list:
        # Check if default printer still exists
        printer_names = [p[2] for p in printers]
        if default_printer in printer_names:
            selected_printer = default_printer
            print(f"\nUsing default printer: {selected_printer}")
        else:
            print(f"\nDefault printer '{default_printer}' not found.")
            default_printer = None
    
    # Ask user to select a printer if no valid default or forcing list
    if not selected_printer or force_list:
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
    date_str = datetime.now().strftime(DATE_FORMAT)
    label_img = generate_label_image(date_str)
    print("Label image generated (preview saved as label_preview.png)")

    # Step 4: Try printing, with retries
    for attempt in range(MAX_RETRIES):
        print(f"Print attempt {attempt + 1} of {MAX_RETRIES}...")
        success = print_label(label_img, selected_printer)
        if success:
            break
        else:
            print(f"Retrying in {WAIT_BETWEEN_TRIES} seconds...")
            time.sleep(WAIT_BETWEEN_TRIES)
    else:
        print("Failed to print after multiple attempts. Is the printer powered on, paired, and connected?")
