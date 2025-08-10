#!/usr/bin/env python3
"""Test script to understand PIL textbbox behavior"""

from PIL import Image, ImageDraw, ImageFont
import json

# Load config to get font path
with open('printer-config.json', 'r') as f:
    config = json.load(f)

# Create test image
img = Image.new('L', (800, 200), 255)
draw = ImageDraw.Draw(img)

# Test different text strings
test_strings = [
    "January 1, 2024",
    "September 30, 2024",
    "December 25, 2024",
    "May 9, 2024"
]

font = ImageFont.truetype(config['font_path'], 40)
y_pos = 20

print("Understanding textbbox() behavior:")
print("=" * 60)

for text in test_strings:
    # Get bbox at origin (0,0)
    bbox = draw.textbbox((0, 0), text, font=font)
    
    print(f"\nText: '{text}'")
    print(f"bbox at (0,0): {bbox}")
    print(f"  bbox[0] (left):   {bbox[0]} {'(extends left!)' if bbox[0] < 0 else ''}")
    print(f"  bbox[1] (top):    {bbox[1]} {'(extends up!)' if bbox[1] < 0 else ''}")
    print(f"  bbox[2] (right):  {bbox[2]}")
    print(f"  bbox[3] (bottom): {bbox[3]}")
    print(f"  Width:  {bbox[2] - bbox[0]}px")
    print(f"  Height: {bbox[3] - bbox[1]}px")
    
    # Draw with red box showing bbox
    draw.rectangle([(100 + bbox[0], y_pos + bbox[1]), 
                    (100 + bbox[2], y_pos + bbox[3])], 
                   outline=128, width=1)
    
    # Draw text at position
    draw.text((100, y_pos), text, font=font, fill=0)
    
    # Also show what happens with our offset calculation
    text_width = bbox[2] - bbox[0]
    center_x = (800 - text_width) // 2
    draw_x = center_x - bbox[0]
    
    print(f"  For 800px wide image:")
    print(f"    center_x = (800 - {text_width}) // 2 = {center_x}")
    print(f"    draw_x = {center_x} - {bbox[0]} = {draw_x}")
    
    y_pos += 50

img.save("bbox-test.png")
print("\nSaved visualization to bbox-test.png")

# Now test the actual label dimensions
print("\n" + "=" * 60)
print("Testing with actual label dimensions:")

# Get printer config
printer_name = config.get('default_printer', 'Munbyn RW402B(Bluetooth)')
printer_config = config['printers'][printer_name]

width_px = int(printer_config['label_width_in'] * printer_config['dpi'])
height_px = int(printer_config['label_height_in'] * printer_config['dpi'])

print(f"Label size: {width_px}x{height_px}px ({printer_config['label_width_in']}x{printer_config['label_height_in']}\" at {printer_config['dpi']} DPI)")

# Test problematic dates
problem_dates = [
    "September 30, 2024",
    "November 24, 2024",
    "December 25, 2024"
]

for date_str in problem_dates:
    # Find font size that fits
    font_size = 10
    for size in range(10, 500):
        font = ImageFont.truetype(config['font_path'], size)
        bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        max_text_height = int(height_px * 0.165)  # November ratio
        max_text_width = int(width_px * 0.85)
        
        if text_height > max_text_height or text_width > max_text_width:
            font_size = size - 1
            break
    
    font = ImageFont.truetype(config['font_path'], font_size)
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    
    # Calculate positions
    x = (width_px - text_width) // 2
    draw_x = x - bbox[0]
    
    # With printer offset
    half_label_width = int(printer_config['label_width_in'] * printer_config['dpi'] / 2)
    
    print(f"\n'{date_str}':")
    print(f"  Font size: {font_size}")
    print(f"  Text width: {text_width}px")
    print(f"  bbox[0]: {bbox[0]}")
    print(f"  Center x: {x}")
    print(f"  Draw x: {draw_x}")
    print(f"  Right edge: {draw_x + text_width} (limit: {width_px})")
    print(f"  With printer offset: {half_label_width + draw_x} to {half_label_width + draw_x + text_width}")
    print(f"  Overflows by: {max(0, draw_x + text_width - width_px)}px")