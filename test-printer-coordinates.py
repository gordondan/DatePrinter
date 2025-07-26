#!/usr/bin/env python3
"""Test script to understand printer coordinate system"""

from PIL import Image, ImageDraw, ImageFont
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

print(f"Testing coordinate system for: {printer_name}")
print("=" * 60)

# Create a test pattern image
width_px = int(printer_config['label_width_in'] * dpi)
height_px = int(printer_config['label_height_in'] * dpi)

print(f"Creating test image: {width_px}x{height_px}px")

# Create image with markers
image = Image.new('L', (width_px, height_px), 255)
draw = ImageDraw.Draw(image)

# Try to load a small font
try:
    font = ImageFont.truetype(config['font_path'], 20)
    small_font = ImageFont.truetype(config['font_path'], 12)
except:
    font = ImageFont.load_default()
    small_font = font

# Draw border (1px inside edge)
draw.rectangle([0, 0, width_px-1, height_px-1], outline=0, width=2)

# Mark corners with text
draw.text((5, 5), "TL", font=font, fill=0)  # Top-left
draw.text((width_px-30, 5), "TR", font=font, fill=0)  # Top-right
draw.text((5, height_px-30), "BL", font=font, fill=0)  # Bottom-left
draw.text((width_px-30, height_px-30), "BR", font=font, fill=0)  # Bottom-right

# Draw center crosshair
center_x = width_px // 2
center_y = height_px // 2
draw.line([(center_x-20, center_y), (center_x+20, center_y)], fill=0, width=2)
draw.line([(center_x, center_y-20), (center_x, center_y+20)], fill=0, width=2)
draw.text((center_x-20, center_y+25), "CENTER", font=small_font, fill=0)

# Draw measurement markers every 50 pixels
for x in range(0, width_px, 50):
    draw.line([(x, 0), (x, 10)], fill=0, width=1)
    draw.line([(x, height_px-10), (x, height_px)], fill=0, width=1)
    if x > 0:
        draw.text((x-10, 15), str(x), font=small_font, fill=0)

for y in range(0, height_px, 50):
    draw.line([(0, y), (10, y)], fill=0, width=1)
    draw.line([(width_px-10, y), (width_px, y)], fill=0, width=1)
    if y > 0:
        draw.text((15, y-8), str(y), font=small_font, fill=0)

# Add text showing what we expect
info_text = f"{width_px}x{height_px}px"
draw.text((center_x-40, center_y-40), info_text, font=font, fill=0)

# Save test image
image.save("coordinate-test.png")
print(f"Saved test pattern to coordinate-test.png")

# Now try different printing approaches
print("\nTesting different coordinate systems...")

def print_with_offset(offset_x, offset_y, description):
    """Print the test image with specified offset"""
    print(f"\n{description}")
    print(f"Offset: ({offset_x}, {offset_y})")
    
    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        
        # Get printer info
        phys_offset_x = hDC.GetDeviceCaps(112)  # PHYSICALOFFSETX
        phys_offset_y = hDC.GetDeviceCaps(113)  # PHYSICALOFFSETY
        printable_width = hDC.GetDeviceCaps(8)  # HORZRES
        printable_height = hDC.GetDeviceCaps(10)  # VERTRES
        
        print(f"Printer reports: offset=({phys_offset_x},{phys_offset_y}), printable={printable_width}x{printable_height}")
        
        hDC.StartDoc(f'Coordinate Test - {description}')
        hDC.StartPage()
        hDC.SetMapMode(win32con.MM_TEXT)
        
        dib = ImageWin.Dib(image)
        
        # Try the specified offset
        dib.draw(hDC.GetHandleOutput(), 
                (offset_x, offset_y, offset_x + width_px, offset_y + height_px))
        
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        
        print(f"Printed at: ({offset_x}, {offset_y}, {offset_x + width_px}, {offset_y + height_px})")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

# Get printer capabilities first
hDC = win32ui.CreateDC()
hDC.CreatePrinterDC(printer_name)
phys_offset_x = hDC.GetDeviceCaps(112)
printable_width = hDC.GetDeviceCaps(8)
hDC.DeleteDC()

# Test different scenarios
tests = [
    (0, 0, "Test 1: Origin (0,0)"),
    (phys_offset_x, 0, f"Test 2: Printer offset ({phys_offset_x},0)"),
    (-phys_offset_x, 0, f"Test 3: Negative offset ({-phys_offset_x},0)"),
    ((printable_width - width_px) // 2, 0, f"Test 4: Centered in printable area"),
]

print("\nWhich test would you like to run?")
for i, (x, y, desc) in enumerate(tests):
    print(f"{i+1}. {desc}")

choice = input("\nEnter test number (or 'all' for all tests): ").strip()

if choice.lower() == 'all':
    for x, y, desc in tests:
        print_with_offset(x, y, desc)
        input("Press Enter to continue to next test...")
else:
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tests):
            x, y, desc = tests[idx]
            print_with_offset(x, y, desc)
        else:
            print("Invalid choice")
    except:
        print("Invalid input")

print("\n" + "=" * 60)
print("Check which test printed correctly!")
print("If TL appears in top-left of label, that offset is correct.")