#!/usr/bin/env python3
"""Simple test to understand Munbyn positioning"""

from PIL import Image, ImageDraw
import win32print
import win32ui
import win32con
from PIL import ImageWin
import json

# Load config
with open('printer-config.json', 'r') as f:
    config = json.load(f)

printer_name = config.get('default_printer', 'Munbyn RW402B(Bluetooth)')
printer_config = config['printers'][printer_name]
dpi = printer_config['dpi']

# Create printer DC to get info
hDC = win32ui.CreateDC()
hDC.CreatePrinterDC(printer_name)

# Get ALL device capabilities
print(f"Analyzing {printer_name}")
print("=" * 60)

# Extended list of capabilities
capabilities = {
    0: "TECHNOLOGY",
    2: "DRIVERVERSION", 
    8: "HORZRES (Printable Width)",
    10: "VERTRES (Printable Height)",
    88: "LOGPIXELSX (DPI X)",
    90: "LOGPIXELSY (DPI Y)",
    110: "PHYSICALWIDTH (Total Width)",
    111: "PHYSICALHEIGHT (Total Height)",
    112: "PHYSICALOFFSETX (Left Margin)",
    113: "PHYSICALOFFSETY (Top Margin)",
    118: "VREFRESH",
    119: "RASTERCAPS"
}

print("Device Capabilities:")
for cap_id, name in sorted(capabilities.items()):
    try:
        value = hDC.GetDeviceCaps(cap_id)
        print(f"  {cap_id:3d}: {name:30} = {value}")
    except:
        pass

# Get key values
printable_width = hDC.GetDeviceCaps(8)
printable_height = hDC.GetDeviceCaps(10)
phys_width = hDC.GetDeviceCaps(110)
phys_height = hDC.GetDeviceCaps(111)
offset_x = hDC.GetDeviceCaps(112)
offset_y = hDC.GetDeviceCaps(113)
dpi_x = hDC.GetDeviceCaps(88)

hDC.DeleteDC()

print(f"\nKey measurements:")
print(f"  Physical size: {phys_width}x{phys_height} device units")
print(f"  Printable area: {printable_width}x{printable_height} pixels")
print(f"  Margins: left={offset_x}, top={offset_y}")
print(f"  DPI: {dpi_x}")

# Calculate expected label size
label_width_px = int(printer_config['label_width_in'] * dpi)
label_height_px = int(printer_config['label_height_in'] * dpi)

print(f"\nLabel expectations:")
print(f"  Config size: {printer_config['label_width_in']}\" x {printer_config['label_height_in']}\"")
print(f"  Expected pixels: {label_width_px}x{label_height_px}")

# Analyze the discrepancy
print(f"\nAnalysis:")
if printable_width > label_width_px:
    extra_width = printable_width - label_width_px
    print(f"  Printable width ({printable_width}) > Label width ({label_width_px})")
    print(f"  Extra width: {extra_width}px")
    print(f"  This suggests the printer might be centering within a larger area")
    
    # Theory: The printer might center labels in its printable area
    center_offset = extra_width // 2
    print(f"\nPossible centering scenarios:")
    print(f"  1. If printer auto-centers: No offset needed")
    print(f"  2. If (0,0) is true corner: Offset = {center_offset}px")
    print(f"  3. If (0,0) is at margin: Offset = {offset_x}px")
    print(f"  4. Combined: Offset = {offset_x + center_offset}px")

# Create a simple test image
image = Image.new('L', (label_width_px, label_height_px), 255)
draw = ImageDraw.Draw(image)

# Draw a thick border
draw.rectangle([0, 0, label_width_px-1, label_height_px-1], outline=0, width=5)

# Draw diagonal lines to show if image is shifted
draw.line([(0, 0), (label_width_px-1, label_height_px-1)], fill=0, width=2)
draw.line([(0, label_height_px-1), (label_width_px-1, 0)], fill=0, width=2)

# Add text in center
center_x = label_width_px // 2
center_y = label_height_px // 2
draw.text((center_x-30, center_y-10), "CENTER", fill=0)

image.save("position-test.png")
print(f"\nCreated position-test.png ({label_width_px}x{label_height_px})")

print("\n" + "=" * 60)
print("Theory: The Munbyn printer might be doing one of:")
print("1. Auto-centering labels in the printable area")
print("2. Using a non-standard origin point")
print("3. Applying its own offset based on label size")
print("\nThe test pattern will help determine which is true.")