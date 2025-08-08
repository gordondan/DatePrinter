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

def load_config():
    """Load configuration from JSON file, fail if missing"""
    if not os.path.exists(CONFIG_FILE):
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

def list_printers():
    print("Available Printers:")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    for i, printer in enumerate(printers):
        print(f"{i+1}: {printer[2]}")
    return printers

def wrap_text_to_fit(text, font, draw, max_width):
    """
    Wrap text at word boundaries to fit within max_width.
    Returns a list of lines.
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word would exceed max width
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]
        
        if test_width <= max_width:
            current_line.append(word)
        else:
            # If current line has words, finish it and start new line
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway to avoid infinite loop
                lines.append(word)
    
    # Add remaining words as final line
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def find_optimal_font_size(text, font_path, draw, max_width, max_height, min_size=10, max_size=500):
    """Find the largest font size that fits within the given constraints."""
    optimal_size = min_size
    for size in range(min_size, max_size):
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if text_height > max_height or text_width > max_width:
            optimal_size = max(size - 1, min_size)
            break
        optimal_size = size
    return optimal_size

def find_optimal_font_size_for_wrapped_text(text, font_path, draw, max_width, max_height, min_size=10, max_size=500):
    """Find optimal font size for text that will be wrapped to fit within constraints."""
    optimal_size = min_size
    final_lines = []
    final_total_height = 0
    
    for size in range(min_size, max_size):
        font = ImageFont.truetype(font_path, size)
        wrapped_lines = wrap_text_to_fit(text, font, draw, max_width)
        
        # Calculate total height needed for all lines
        line_heights = []
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        
        line_spacing = 2
        total_height = sum(line_heights) + (len(wrapped_lines) - 1) * line_spacing
        
        if total_height <= max_height:
            optimal_size = size
            final_lines = wrapped_lines
            final_total_height = total_height
        else:
            break
    
    return optimal_size, final_lines, final_total_height

def draw_text_with_bold_effect(draw, position, text, font, fill=0):
    """Draw text with a bold effect by drawing multiple times with slight offsets."""
    x, y = position
    # Draw shadow/bold effect
    for offset_x in [-1, 0, 1]:
        for offset_y in [-1, 0, 1]:
            if offset_x == 0 and offset_y == 0:
                continue
            draw.text((x + offset_x, y + offset_y), text, font=font, fill=fill)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill)

def center_text_horizontally(text_width, container_width, bbox_left=0):
    """Calculate x position to center text horizontally."""
    logical_x = (container_width - text_width) // 2
    return logical_x - bbox_left

def draw_border(draw, width, height, margin=4, thickness=6):
    """Draw a border around the image."""
    left = margin
    top = margin
    right = width - margin
    bottom = height - margin
    
    for i in range(thickness):
        # Top border
        draw.rectangle([left + i, top + i, right - i, top + i], fill=0)
        # Bottom border
        draw.rectangle([left + i, bottom - i, right - i, bottom - i], fill=0)
        # Left border
        draw.rectangle([left + i, top + i, left + i, bottom - i], fill=0)
        # Right border
        draw.rectangle([right - i, top + i, right - i, bottom - i], fill=0)

def draw_date_at_bottom(draw, date_str, font, width_px, height_px, bottom_margin):
    """Draw date text at the bottom of the label."""
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position and draw the date
    date_y = height_px - bottom_margin - text_height
    draw_x = center_text_horizontally(text_width, width_px, bbox[0])
    draw_y = date_y - bbox[1]
    
    # Safety bounds checking
    draw_x = max(0, min(draw_x, width_px - text_width))
    
    draw.text((draw_x, draw_y), date_str, font=font, fill=0)
    return date_y, text_height

def draw_rotated_date_at_top(image, draw, date_str, font, width_px, top_margin=15):
    """Draw rotated (upside down) date at the top of the label."""
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create temporary image for rotation
    temp_img = Image.new('L', (text_width + 40, text_height + 40), 255)
    temp_draw = ImageDraw.Draw(temp_img)
    temp_draw.text((20 - bbox[0], 20 - bbox[1]), date_str, font=font, fill=0)
    
    # Rotate and position
    rotated_temp = temp_img.rotate(180, expand=True)
    rotated_x = (width_px - rotated_temp.width) // 2
    rotated_y = top_margin
    
    # Create mask and paste onto main image
    mask = rotated_temp.point(lambda x: 255 if x < 128 else 0, mode='1')
    black_overlay = Image.new('L', rotated_temp.size, 0)
    image.paste(black_overlay, (rotated_x, rotated_y), mask)
    
    return rotated_y + rotated_temp.height

def draw_centered_message(draw, message, font_path, width_px, space_start, space_end, min_font=10, max_font=500):
    """Draw a centered message with text wrapping and bold effect."""
    available_height = space_end - space_start
    max_message_width = int(width_px * 0.9)
    
    # Find optimal font size and get wrapped lines
    message_font_size, final_lines, final_total_height = find_optimal_font_size_for_wrapped_text(
        message, font_path, draw, max_message_width, available_height, min_font, max_font
    )
    
    if not final_lines:  # Fallback if no size works
        font = ImageFont.truetype(font_path, min_font)
        final_lines = wrap_text_to_fit(message, font, draw, max_message_width)
        final_total_height = len(final_lines) * min_font  # Rough estimate
        message_font_size = min_font
    
    message_font = ImageFont.truetype(font_path, message_font_size)
    
    # Calculate vertical centering
    block_start_y = space_start + (available_height - final_total_height) // 2
    
    # Draw each line centered
    current_y = block_start_y
    line_spacing = 2
    
    for line in final_lines:
        bbox = draw.textbbox((0, 0), line, font=message_font)
        text_width = bbox[2] - bbox[0]
        
        draw_x = center_text_horizontally(text_width, width_px, bbox[0])
        draw_y = current_y - bbox[1]
        
        # Draw with bold effect
        draw_text_with_bold_effect(draw, (draw_x, draw_y), line, message_font)
        
        current_y += (bbox[3] - bbox[1]) + line_spacing
    
    return message_font_size, final_lines, block_start_y

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

def generate_label_image(date_str, date_obj, config, printer_config, message=None, border_message=None, message_only=False):
    """Generate a label image with dates and/or message."""
    # Create image based on printer-specific settings
    width_px = int(printer_config['label_width_in'] * printer_config['dpi'])
    height_px = int(printer_config['label_height_in'] * printer_config['dpi'])
    image = Image.new('L', (width_px, height_px), 255)
    draw = ImageDraw.Draw(image)

    # Get font configuration
    min_font = config.get('min_font_size', 10)
    max_font = config.get('max_font_size', 500)
    
    # Initialize variables for layout calculations
    date_y = height_px - printer_config['bottom_margin']
    date_text_height = 0
    rotated_date_end_y = 15  # Default top margin
    
    # Draw dates if not in message-only mode
    if not message_only:
        # Calculate date font size based on label proportions and message presence
        month_name = date_obj.strftime("%B")
        base_text_height_ratio = config.get('month_size_ratios', {}).get(month_name, config.get('default_text_height_ratio', 0.15))
        
        # Adjust date size if message or border_message is present
        date_text_height_ratio = base_text_height_ratio * (0.85 if message or border_message else 1.0)
        max_date_height = int(height_px * date_text_height_ratio)
        max_text_width = int(width_px * config.get('max_text_width_ratio', 0.85))
        
        # Find optimal font size for date
        date_font_size = find_optimal_font_size(date_str, config['font_path'], draw, max_text_width, max_date_height, min_font, max_font)
        date_font = ImageFont.truetype(config['font_path'], date_font_size)
        
        # Draw bottom date
        date_y, date_text_height = draw_date_at_bottom(draw, date_str, date_font, width_px, height_px, printer_config['bottom_margin'])
        
        # Draw rotated top date
        rotated_date_end_y = draw_rotated_date_at_top(image, draw, date_str, date_font, width_px)
    
    # Draw message if provided
    message_font_size = min_font
    final_lines = []
    msg_block_y = 0
    
    if message:
        # Calculate available space for message - always reserve space for dates for consistency
        # This ensures message uses same space whether dates are shown or not
        
        # Calculate where dates would be positioned
        if message_only:
            # Still calculate date positions for consistent spacing, but don't draw them
            month_name = date_obj.strftime("%B")
            base_text_height_ratio = config.get('month_size_ratios', {}).get(month_name, config.get('default_text_height_ratio', 0.15))
            date_text_height_ratio = base_text_height_ratio * 0.85  # Assume message present
            max_date_height = int(height_px * date_text_height_ratio)
            max_text_width = int(width_px * config.get('max_text_width_ratio', 0.85))
            
            theoretical_date_font_size = find_optimal_font_size(date_str, config['font_path'], draw, max_text_width, max_date_height, min_font, max_font)
            theoretical_date_font = ImageFont.truetype(config['font_path'], theoretical_date_font_size)
            
            # Calculate theoretical positions
            date_bbox = draw.textbbox((0, 0), date_str, font=theoretical_date_font)
            theoretical_date_text_height = date_bbox[3] - date_bbox[1]
            theoretical_date_y = height_px - printer_config['bottom_margin'] - theoretical_date_text_height
            
            # Calculate theoretical rotated date end
            temp_img_height = theoretical_date_text_height + 40
            theoretical_rotated_date_end_y = 15 + temp_img_height
            
            space_start = theoretical_rotated_date_end_y + 5
            space_end = theoretical_date_y - 5
        else:
            space_start = rotated_date_end_y + 5  # Buffer after rotated date
            space_end = date_y - 5  # Buffer before bottom date
        
        print(f"DEBUG: message_only={message_only}, space_start={space_start}, space_end={space_end}")
        
        # Calculate optimal font size first (without drawing)
        available_height = space_end - space_start
        max_message_width = int(width_px * 0.9)
        
        optimal_font_size, _, _ = find_optimal_font_size_for_wrapped_text(
            message, config['font_path'], draw, max_message_width, available_height, min_font, max_font
        )
        
        # Reduce font size by two for better appearance
        if optimal_font_size > min_font + 1:
            final_font_size = optimal_font_size - 2
        else:
            final_font_size = optimal_font_size
        
        # Now draw with the final font size
        message_font_size, final_lines, msg_block_y = draw_centered_message(
            draw, message, config['font_path'], width_px, space_start, space_end, final_font_size, final_font_size
        )
    
    # Handle border message
    border_message_font_size = min_font
    border_final_lines = []
    border_msg_block_y = 0
    
    if border_message:
        # Calculate border message space using same logic as regular message
        # This ensures consistent spacing regardless of which messages are present
        
        if message_only:
            # Still calculate date positions for consistent spacing
            month_name = date_obj.strftime("%B")
            base_text_height_ratio = config.get('month_size_ratios', {}).get(month_name, config.get('default_text_height_ratio', 0.15))
            date_text_height_ratio = base_text_height_ratio * 0.85  # Assume message present
            max_date_height = int(height_px * date_text_height_ratio)
            max_text_width = int(width_px * config.get('max_text_width_ratio', 0.85))
            
            theoretical_date_font_size = find_optimal_font_size(date_str, config['font_path'], draw, max_text_width, max_date_height, min_font, max_font)
            theoretical_date_font = ImageFont.truetype(config['font_path'], theoretical_date_font_size)
            
            # Calculate theoretical positions
            date_bbox = draw.textbbox((0, 0), date_str, font=theoretical_date_font)
            theoretical_date_text_height = date_bbox[3] - date_bbox[1]
            theoretical_date_y = height_px - printer_config['bottom_margin'] - theoretical_date_text_height
            
            # Calculate theoretical rotated date end
            temp_img_height = theoretical_date_text_height + 40
            theoretical_rotated_date_end_y = 15 + temp_img_height
            
            border_space_start = theoretical_rotated_date_end_y + 5
            border_space_end = theoretical_date_y - 5
        else:
            border_space_start = rotated_date_end_y + 5  # Buffer after rotated date
            border_space_end = date_y - 5  # Buffer before bottom date
        
        # If both message and border_message exist, split the space
        if message:
            # Split available space between message and border message
            total_space = border_space_end - border_space_start
            # Give slightly more space to the main message
            border_space_start = border_space_start + int(total_space * 0.6)
        
        # Calculate optimal font size for border message (with reduced font for appearance)
        available_height = border_space_end - border_space_start
        max_border_width = int(width_px * 0.9)
        
        optimal_border_font_size, _, _ = find_optimal_font_size_for_wrapped_text(
            border_message, config['font_path'], draw, max_border_width, available_height, min_font, max_font
        )
        
        # Reduce font size by two for better appearance (same as message logic)
        if optimal_border_font_size > min_font + 1:
            final_border_font_size = optimal_border_font_size - 2
        else:
            final_border_font_size = optimal_border_font_size
        
        # Draw the border message
        border_message_font_size, border_final_lines, border_msg_block_y = draw_centered_message(
            draw, border_message, config['font_path'], width_px, border_space_start, border_space_end, 
            final_border_font_size, final_border_font_size
        )
    
    # Draw border
    draw_border(draw, width_px, height_px)
    
    # Debug output
    print(f"\n=== Debug Info ===")
    print(f"Message-only mode: {message_only}")
    if not message_only:
        print(f"Date string: '{date_str}', font size: {date_font_size}")
    if message:
        print(f"Message: '{message}' (length: {len(message)})")
        print(f"Message font size: {message_font_size}, lines: {len(final_lines)}")
        print(f"Message lines: {final_lines}")
    if border_message:
        print(f"Border message: '{border_message}' (length: {len(border_message)})")
        print(f"Border message font size: {border_message_font_size}, lines: {len(border_final_lines)}")
        print(f"Border message lines: {border_final_lines}")
    print(f"Label dimensions: {width_px}x{height_px}")
    
    image.save("label_preview.png")  # Optional preview
    return image


def print_label(image, printer_name, config, printer_config):
    width_px, height_px = image.size
    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        
        # Get device capability indices from config
        caps = config.get('windows_device_caps', {})
        
        # Query printer capabilities using Windows GetDeviceCaps
        # These return the ACTUAL values (not the index constants)
        printer_width = hDC.GetDeviceCaps(caps.get('PHYSICALWIDTH', 110))     # Full paper width
        printer_height = hDC.GetDeviceCaps(caps.get('PHYSICALHEIGHT', 111))   # Full paper height
        printer_dpi_x = hDC.GetDeviceCaps(caps.get('LOGPIXELSX', 88))         # Horizontal DPI
        printer_dpi_y = hDC.GetDeviceCaps(caps.get('LOGPIXELSY', 90))         # Vertical DPI
        printable_width = hDC.GetDeviceCaps(caps.get('HORZRES', 8))           # Printable width
        printable_height = hDC.GetDeviceCaps(caps.get('VERTRES', 10))         # Printable height
        offset_x = hDC.GetDeviceCaps(caps.get('PHYSICALOFFSETX', 112))        # Left margin
        offset_y = hDC.GetDeviceCaps(caps.get('PHYSICALOFFSETY', 113))        # Top margin
        
        print(f"\n=== Printer Info ===")
        print(f"Printer DPI: {printer_dpi_x}x{printer_dpi_y}")
        print(f"Physical size: {printer_width}x{printer_height} device units")
        print(f"Printable area: {printable_width}x{printable_height} pixels")
        print(f"Margins: left={offset_x}, top={offset_y} device units")
        print(f"Label should print from x={offset_x} to x={offset_x + width_px}")
        
        # Example: For a 2.25"×1.25" label at 203 DPI:
        # - printer_dpi_x/y = 203
        # - printable_width/height = 457×254 pixels (2.25"×1.25" × 203 DPI)
        # - The indices (8,10,88,etc) are just lookups - NOT the actual dimensions
        
        hDC.StartDoc('Label')
        hDC.StartPage()
        
        # Set mapping mode to match pixels 1:1
        hDC.SetMapMode(win32con.MM_TEXT)
        
        # Create the DIB from our image
        dib = ImageWin.Dib(image)
        
        # Calculate positioning for the Munbyn printer
        # The printer might be centering labels within its printable area
        
        # Check if printable area is wider than our label
        if printable_width > width_px:
            # The printer has a wider printable area than our label
            # It might be expecting us to center the content
            auto_center_offset = (printable_width - width_px) // 2
            print(f"Printable width ({printable_width}) > Image width ({width_px})")
            print(f"Auto-centering offset would be: {auto_center_offset}px")
        else:
            auto_center_offset = 0
        
        # Try different positioning strategies based on config
        positioning_mode = printer_config.get('positioning_mode', 'auto')
        
        if positioning_mode == 'auto':
            # Try to auto-detect best positioning
            if printable_width > width_px:
                # Center in printable area
                h_offset = auto_center_offset
                print(f"Using auto-center mode: offset={h_offset}px")
            else:
                # Use physical offset
                h_offset = offset_x
                print(f"Using physical offset mode: offset={h_offset}px")
        elif positioning_mode == 'physical_offset':
            # Use only the physical offset
            h_offset = offset_x
            print(f"Using physical offset only: {h_offset}px")
        elif positioning_mode == 'center':
            # Force centering in printable area
            h_offset = auto_center_offset
            print(f"Using center mode: {h_offset}px")
        elif positioning_mode == 'manual':
            # Use only manual offset
            h_offset = printer_config.get('horizontal_offset', 0)
            print(f"Using manual offset: {h_offset}px")
        else:
            # Default to physical offset
            h_offset = offset_x
            print(f"Unknown positioning mode, using physical offset: {h_offset}px")
        
        # Add any additional configured offset
        additional_offset = printer_config.get('horizontal_offset', 0)
        if additional_offset != 0 and positioning_mode != 'manual':
            h_offset += additional_offset
            print(f"Added additional offset: {additional_offset}px")
        
        total_offset = h_offset
        
        # Draw the image with calculated offset
        dib.draw(hDC.GetHandleOutput(), 
                (total_offset, 0, total_offset + width_px, height_px))
        
        print(f"Drawing at position ({total_offset}, 0, {total_offset + width_px}, {height_px})")
        print(f"  Printer physical offset: {offset_x} device units")
        print(f"  Additional configured offset: {additional_offset}px")
        print(f"  Total horizontal offset: {total_offset} device units")
        
        hDC.EndPage()
        hDC.EndDoc()
        
        # Force the printer to process the job immediately
        try:
            import win32print
            printer_handle = win32print.OpenPrinter(printer_name)
            win32print.FlushPrinter(printer_handle)
            win32print.ClosePrinter(printer_handle)
            print("Printer job flushed to device")
        except Exception as flush_error:
            print(f"Warning: Could not flush printer job: {flush_error}")
        
        hDC.DeleteDC()
        print(f"Label sent to printer: {printer_name}")
        print(f"Image size: {width_px}x{height_px} pixels (created at {printer_config['dpi']} DPI)")
        print(f"Drew at coordinates: (0, 0, {width_px}, {height_px})")
        print(f"Expected physical size: {printer_config['label_width_in']}x{printer_config['label_height_in']} inches")
        return True
    except Exception as e:
        print(f"Printing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
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
    parser.add_argument('-m', '--message', type=str, 
                        help='Custom message to print in center of label')
    parser.add_argument('-b', '--border-message', type=str,
                        help='Custom border message - follows date scaling rules when --message is present')
    parser.add_argument('-o', '--message-only', action='store_true',
                        help='When using -m/--message, omit the dates and show only the message')
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
    
    label_img = generate_label_image(date_str, date_obj, config, printer_config, args.message, args.border_message, args.message_only)
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
