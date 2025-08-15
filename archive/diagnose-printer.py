#!/usr/bin/env python3
"""Diagnostic script to understand printer capabilities and offsets"""

import win32print
import win32ui
import json

# Load config
with open('printer-config.json', 'r') as f:
    config = json.load(f)

printer_name = config.get('default_printer', 'Munbyn RW402B(Bluetooth)')
printer_config = config['printers'][printer_name]

print(f"Diagnosing printer: {printer_name}")
print("=" * 60)

# Create printer DC
hDC = win32ui.CreateDC()
hDC.CreatePrinterDC(printer_name)

# Get all capabilities
caps_to_check = [
    (8, "HORZRES", "Horizontal resolution (printable width in pixels)"),
    (10, "VERTRES", "Vertical resolution (printable height in pixels)"),
    (88, "LOGPIXELSX", "Horizontal DPI"),
    (90, "LOGPIXELSY", "Vertical DPI"),
    (110, "PHYSICALWIDTH", "Physical page width in device units"),
    (111, "PHYSICALHEIGHT", "Physical page height in device units"),
    (112, "PHYSICALOFFSETX", "Left unprintable margin in device units"),
    (113, "PHYSICALOFFSETY", "Top unprintable margin in device units"),
]

print("\nPrinter Capabilities:")
for cap_id, name, desc in caps_to_check:
    value = hDC.GetDeviceCaps(cap_id)
    print(f"{name:20} = {value:6} | {desc}")

# Calculate expected values
dpi_x = hDC.GetDeviceCaps(88)
dpi_y = hDC.GetDeviceCaps(90)
phys_width = hDC.GetDeviceCaps(110)
phys_height = hDC.GetDeviceCaps(111)
offset_x = hDC.GetDeviceCaps(112)
offset_y = hDC.GetDeviceCaps(113)
printable_width = hDC.GetDeviceCaps(8)
printable_height = hDC.GetDeviceCaps(10)

print("\nCalculated values:")
print(f"Physical page size: {phys_width/dpi_x:.3f}\" x {phys_height/dpi_y:.3f}\"")
print(f"Printable area: {printable_width/dpi_x:.3f}\" x {printable_height/dpi_y:.3f}\"")
print(f"Left margin: {offset_x} device units = {offset_x/dpi_x:.3f}\" = {offset_x:.0f} pixels")
print(f"Top margin: {offset_y} device units = {offset_y/dpi_y:.3f}\" = {offset_y:.0f} pixels")

print("\nLabel configuration:")
print(f"Expected size: {printer_config['label_width_in']}\" x {printer_config['label_height_in']}\"")
print(f"Expected pixels: {printer_config['label_width_in'] * dpi_x:.0f} x {printer_config['label_height_in'] * dpi_y:.0f}")

print("\nOffset analysis:")
print(f"Printer reports left offset: {offset_x} device units")
print(f"This means the printable area starts {offset_x} pixels from the left edge")

# Check if we need to center within printable area
label_width_px = int(printer_config['label_width_in'] * dpi_x)
if printable_width > label_width_px:
    center_offset = (printable_width - label_width_px) // 2
    print(f"\nPrintable area ({printable_width}px) is wider than label ({label_width_px}px)")
    print(f"To center the label, we might need additional offset: {center_offset}px")
    print(f"Total offset would be: {offset_x} + {center_offset} = {offset_x + center_offset}px")
else:
    print(f"\nPrintable area ({printable_width}px) matches label width ({label_width_px}px)")
    print(f"Using printer offset only: {offset_x}px")

hDC.DeleteDC()

print("\n" + "=" * 60)
print("Run date-printer.py and check if the offset calculations match!")