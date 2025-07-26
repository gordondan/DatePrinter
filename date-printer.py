import time
import subprocess
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

def list_printers():
    print("Available Printers:")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    for i, printer in enumerate(printers):
        print(f"{i+1}: {printer[2]}")

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

    # Dynamically find the largest font size that fits 3/4 of label height
    max_text_height = int(height_px * 0.75)
    for size in range(10, 500):
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_height > max_text_height or text_width > width_px:
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
    # Step 1: List printers if needed
    list_printers()
    print("\nSet PRINTER_NAME above if you haven't already.")

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
        success = print_label(label_img, PRINTER_NAME)
        if success:
            break
        else:
            print(f"Retrying in {WAIT_BETWEEN_TRIES} seconds...")
            time.sleep(WAIT_BETWEEN_TRIES)
    else:
        print("Failed to print after multiple attempts. Is the printer powered on, paired, and connected?")
