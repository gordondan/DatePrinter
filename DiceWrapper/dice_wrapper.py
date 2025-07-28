import cv2
import cv2.aruco as aruco
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import argparse
import json
import math

# Add parent directory to path to import LabelPrinter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LabelPrinter import LabelGenerator, LabelPrinter


class DiceWrapperGenerator:
    def __init__(self, config):
        self.config = config
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        
        # Standard dice is typically 16mm (5/8 inch)
        self.default_dice_size_mm = 16
        
    def mm_to_pixels(self, mm, dpi):
        """Convert millimeters to pixels at given DPI"""
        inches = mm / 25.4
        return int(inches * dpi)
    
    def generate_first_layer(self, dice_size_mm=16, dpi=203, label_height_in=1.25):
        """Generate first layer strip with alignment guides and registration marks
        
        The first layer wraps around faces 1-2-3-4 with overlap on face 1.
        Face layout when die is oriented with 1 on top:
        - Strip goes: 4 (left) -> 2 (front) -> 3 (right) -> 5 (back) -> overlap area
        """
        face_size_px = self.mm_to_pixels(dice_size_mm, dpi)
        margin = self.mm_to_pixels(2, dpi)  # 2mm margin for cutting
        overlap_size = face_size_px // 3  # 1/3 face overlap for secure adhesion
        
        # Calculate strip dimensions
        strip_width = (4 * face_size_px) + overlap_size + (2 * margin)
        strip_height = face_size_px + (2 * margin)
        
        # Ensure it fits on label
        label_height_px = int(label_height_in * dpi)
        if strip_height > label_height_px:
            # Scale down if needed
            scale = label_height_px / strip_height
            face_size_px = int(face_size_px * scale)
            margin = int(margin * scale)
            overlap_size = int(overlap_size * scale)
            strip_width = (4 * face_size_px) + overlap_size + (2 * margin)
            strip_height = face_size_px + (2 * margin)
        
        # Create image
        img = Image.new('RGB', (strip_width, strip_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font_size = face_size_px // 4
            if sys.platform == 'win32':
                font_path = self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf')
            else:
                font_path = self.config.get('font_path', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf')
            font = ImageFont.truetype(font_path, font_size)
            small_font = ImageFont.truetype(font_path, font_size // 2)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Draw cutting guides
        draw.rectangle((0, 0, strip_width-1, strip_height-1), outline='black', width=2)
        
        # Draw face boundaries and content
        faces = [
            ("4", "Face 4", False),
            ("2", "Face 2", False), 
            ("3", "Face 3", False),
            ("5", "Face 5", False),
            ("1", "Overlap\n(Face 1)", True)
        ]
        
        x = margin
        for i, (face_num, label, is_overlap) in enumerate(faces):
            if i < 4:
                face_width = face_size_px
            else:
                face_width = overlap_size
            
            # Draw face boundary
            draw.rectangle((x, margin, x + face_width, margin + face_size_px), 
                         outline='gray', width=1)
            
            # Draw registration marks (corners)
            mark_size = face_size_px // 10
            # Top-left
            draw.line((x + mark_size, margin, x, margin), fill='black', width=2)
            draw.line((x, margin, x, margin + mark_size), fill='black', width=2)
            # Top-right
            draw.line((x + face_width - mark_size, margin, x + face_width, margin), fill='black', width=2)
            draw.line((x + face_width, margin, x + face_width, margin + mark_size), fill='black', width=2)
            # Bottom-left
            draw.line((x + mark_size, margin + face_size_px, x, margin + face_size_px), fill='black', width=2)
            draw.line((x, margin + face_size_px - mark_size, x, margin + face_size_px), fill='black', width=2)
            # Bottom-right
            draw.line((x + face_width - mark_size, margin + face_size_px, x + face_width, margin + face_size_px), fill='black', width=2)
            draw.line((x + face_width, margin + face_size_px - mark_size, x + face_width, margin + face_size_px), fill='black', width=2)
            
            # Add center registration dot
            center_x = x + face_width // 2
            center_y = margin + face_size_px // 2
            dot_radius = face_size_px // 20
            draw.ellipse((center_x - dot_radius, center_y - dot_radius,
                         center_x + dot_radius, center_y + dot_radius),
                        fill='black')
            
            # Add face number and instructions
            if is_overlap:
                # Overlap area - just instructions
                text = "Overlap\nhere"
                bbox = draw.textbbox((0, 0), text, font=small_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (face_width - text_width) // 2
                text_y = margin + (face_size_px - text_height) // 2
                draw.text((text_x, text_y), text, fill='red', font=small_font, align='center')
            else:
                # Regular face - add number
                bbox = draw.textbbox((0, 0), face_num, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (face_width - text_width) // 2
                text_y = margin + (face_size_px - text_height) // 2
                draw.text((text_x, text_y), face_num, fill='gray', font=font)
                
                # Add small label
                bbox = draw.textbbox((0, 0), label, font=small_font)
                text_width = bbox[2] - bbox[0]
                label_y = margin + face_size_px - font_size // 2 - 5
                draw.text((x + (face_width - text_width) // 2, label_y), 
                         label, fill='gray', font=small_font)
            
            # Draw fold line (except for last overlap section)
            if i < len(faces) - 1:
                draw.line((x + face_width, margin - 5, x + face_width, margin + face_size_px + 5),
                         fill='lightgray', width=1)
            
            x += face_width
        
        # Add instructions
        instructions = "Layer 1: Wrap around die with 1 on top. Start with face 4 on left side."
        draw.text((margin, 2), instructions, fill='black', font=small_font)
        
        return img, face_size_px, margin
    
    def generate_second_layer(self, dice_size_mm=16, dpi=203, label_height_in=1.25, 
                             face_size_px=None, margin=None):
        """Generate second layer strip with ArUco markers
        
        The second layer wraps around faces 6-2-1-5 with overlap on face 6.
        This goes perpendicular to the first layer.
        Face layout: 6 (bottom) -> 3 (front) -> 1 (top) -> 4 (back) -> overlap area
        """
        if face_size_px is None:
            face_size_px = self.mm_to_pixels(dice_size_mm, dpi)
        if margin is None:
            margin = self.mm_to_pixels(2, dpi)
        
        overlap_size = face_size_px // 3
        
        # Calculate strip dimensions (same as first layer)
        strip_width = (4 * face_size_px) + overlap_size + (2 * margin)
        strip_height = face_size_px + (2 * margin)
        
        # Create image
        img = Image.new('RGB', (strip_width, strip_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw cutting guides
        draw.rectangle((0, 0, strip_width-1, strip_height-1), outline='black', width=2)
        
        # Generate ArUco markers for second layer faces
        # Order: 6, 3, 1, 4 (with overlap on 6)
        face_order = [6, 3, 1, 4]
        
        x = margin
        for i, face_num in enumerate(face_order):
            # Generate ArUco marker
            marker_size = int(face_size_px * 0.8)  # 80% of face size for margin
            marker_img = aruco.drawMarker(self.aruco_dict, face_num, marker_size)
            marker_pil = Image.fromarray(marker_img)
            
            # Calculate position to center marker
            marker_x = x + (face_size_px - marker_size) // 2
            marker_y = margin + (face_size_px - marker_size) // 2
            
            # Paste marker
            img.paste(marker_pil, (marker_x, marker_y))
            
            # Draw face boundary
            draw.rectangle((x, margin, x + face_size_px, margin + face_size_px), 
                         outline='gray', width=1)
            
            # Add face number in corner
            try:
                small_font = ImageFont.truetype(
                    self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf'), 
                    face_size_px // 8
                )
            except:
                small_font = ImageFont.load_default()
            
            face_label = str(face_num)
            draw.text((x + 5, margin + 5), face_label, fill='red', font=small_font)
            
            # Draw fold line
            if i < 3:  # Don't draw after last face before overlap
                draw.line((x + face_size_px, margin - 5, x + face_size_px, margin + face_size_px + 5),
                         fill='lightgray', width=1)
            
            x += face_size_px
        
        # Draw overlap area
        overlap_x = x
        draw.rectangle((overlap_x, margin, overlap_x + overlap_size, margin + face_size_px),
                      outline='gray', width=1)
        
        # Add overlap instructions
        try:
            font = ImageFont.truetype(
                self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf'),
                face_size_px // 6
            )
        except:
            font = ImageFont.load_default()
        
        text = "Overlap\n(Face 6)"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = overlap_x + (overlap_size - text_width) // 2
        text_y = margin + (face_size_px - text_height) // 2
        draw.text((text_x, text_y), text, fill='red', font=font, align='center')
        
        # Add instructions
        instructions = "Layer 2: Wrap perpendicular to Layer 1. Start with face 6 on bottom."
        draw.text((margin, 2), instructions, fill='black', font=small_font)
        
        return img
    
    def generate_combined_label(self, dice_size_mm=16, printer_config=None):
        """Generate both layers on a single label for printing"""
        if printer_config is None:
            dpi = 203
            label_width_in = 2.25
            label_height_in = 1.25
        else:
            dpi = printer_config.get('dpi', 203)
            label_width_in = printer_config.get('label_width_in', 2.25)
            label_height_in = printer_config.get('label_height_in', 1.25)
        
        label_width_px = int(label_width_in * dpi)
        label_height_px = int(label_height_in * dpi)
        
        # Generate both layers
        layer1_img, face_size_px, margin = self.generate_first_layer(dice_size_mm, dpi, label_height_in)
        layer2_img = self.generate_second_layer(dice_size_mm, dpi, label_height_in, face_size_px, margin)
        
        # Check if both strips fit on one label
        strip_height = layer1_img.size[1]
        total_height = 2 * strip_height + self.mm_to_pixels(2, dpi)  # 2mm gap
        
        if total_height <= label_height_px and layer1_img.size[0] <= label_width_px:
            # Both fit on one label
            combined_img = Image.new('RGB', (label_width_px, label_height_px), 'white')
            
            # Center strips horizontally
            x_offset = (label_width_px - layer1_img.size[0]) // 2
            
            # Place first layer at top
            y1 = self.mm_to_pixels(1, dpi)  # 1mm from top
            combined_img.paste(layer1_img, (x_offset, y1))
            
            # Place second layer below
            y2 = y1 + strip_height + self.mm_to_pixels(2, dpi)
            combined_img.paste(layer2_img, (x_offset, y2))
            
            # Add title
            draw = ImageDraw.Draw(combined_img)
            try:
                title_font = ImageFont.truetype(
                    self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf'),
                    self.mm_to_pixels(3, dpi)
                )
            except:
                title_font = ImageFont.load_default()
            
            return combined_img.convert('L')  # Convert to grayscale for thermal printing
        else:
            # Too big for one label, return just the second layer (with ArUco markers)
            # User will need to print twice or use regular printer
            return layer2_img.convert('L')


def load_config():
    """Load configuration from JSON file"""
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wrapper-config.json")
    
    # Default configuration
    default_config = {
        "default_printer": None,
        "font_path": "C:\\Windows\\Fonts\\arial.ttf" if sys.platform == 'win32' else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "output_folder": "generated_dice_wrappers",
        "default_dice_size_mm": 16,
        "max_retries": 3,
        "wait_between_tries": 2,
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
        "printers": {}
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            # Merge with defaults
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    # Save default config
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    return default_config


def save_config(config):
    """Save configuration to JSON file"""
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wrapper-config.json")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def get_printer_config(config, printer_name):
    """Get printer-specific configuration"""
    if printer_name not in config.get("printers", {}):
        if "printers" not in config:
            config["printers"] = {}
        config["printers"][printer_name] = {
            "label_width_in": 2.25,
            "label_height_in": 1.25,
            "dpi": 203,
            "positioning_mode": "auto",
            "horizontal_offset": 0
        }
    return config["printers"][printer_name]


def main():
    parser = argparse.ArgumentParser(
        description='Generate wrapper strips for applying ArUco markers to existing dice'
    )
    parser.add_argument('-p', '--preview', action='store_true',
                       help='Only generate preview, do not print')
    parser.add_argument('-l', '--list', action='store_true',
                       help='List available printers')
    parser.add_argument('-s', '--size', type=float, default=16,
                       help='Dice size in millimeters (default: 16mm)')
    parser.add_argument('-o', '--output', type=str,
                       help='Output file path for preview')
    parser.add_argument('--layer', type=int, choices=[1, 2],
                       help='Generate only specific layer (1 or 2)')
    parser.add_argument('--dpi', type=int, default=203,
                       help='DPI for preview mode (default: 203)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Create generator
    generator = DiceWrapperGenerator(config)
    
    # Preview mode
    if args.preview:
        output_folder = config.get('output_folder', 'generated_dice_wrappers')
        os.makedirs(output_folder, exist_ok=True)
        
        if args.layer == 1:
            # Generate only first layer
            img, _, _ = generator.generate_first_layer(args.size, args.dpi)
            default_name = "dice_wrapper_layer1.png"
        elif args.layer == 2:
            # Generate only second layer
            img = generator.generate_second_layer(args.size, args.dpi)
            default_name = "dice_wrapper_layer2.png"
        else:
            # Generate combined preview
            img = generator.generate_combined_label(args.size)
            default_name = "dice_wrapper_combined.png"
        
        # Save preview
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join(output_folder, default_name)
        
        img.save(output_path)
        print(f"✅ Saved dice wrapper preview to {output_path}")
        print(f"   Image size: {img.size}")
        print(f"   Dice size: {args.size}mm")
        return
    
    # Printing mode
    label_printer = LabelPrinter(config)
    
    # List printers if requested
    if args.list:
        printers = label_printer.list_printers()
        if not printers:
            print("No printers found!")
            return
        print("Available Printers:")
        for i, printer_name in printers:
            print(f"{i+1}: {printer_name}")
        return
    
    # Get printer selection
    selected_printer = None
    
    if config.get('default_printer'):
        all_printers = label_printer.list_printers()
        printer_names = [p[1] for p in all_printers]
        
        if config['default_printer'] in printer_names:
            selected_printer = config['default_printer']
            print(f"Using default printer: {selected_printer}")
        else:
            print(f"Default printer '{config['default_printer']}' not found.")
    
    # If no valid default, show selection menu
    if not selected_printer:
        printers = label_printer.list_printers()
        
        if not printers:
            print("No printers found!")
            return
            
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
    
    # Get printer configuration
    printer_config = get_printer_config(config, selected_printer)
    
    # Generate wrapper for label
    print(f"\nGenerating dice wrapper for {args.size}mm dice...")
    label_img = generator.generate_combined_label(args.size, printer_config)
    
    # Save preview
    output_folder = config.get('output_folder', 'generated_dice_wrappers')
    os.makedirs(output_folder, exist_ok=True)
    preview_path = os.path.join(output_folder, "dice_wrapper_label.png")
    label_img.save(preview_path)
    print(f"Preview saved to: {preview_path}")
    
    # Print the label
    print(f"\nPrinting dice wrapper label...")
    
    for attempt in range(config.get('max_retries', 3)):
        print(f"Print attempt {attempt + 1}...")
        success = label_printer.print_label(label_img, selected_printer, printer_config)
        if success:
            print("✅ Successfully printed dice wrapper label!")
            print("\nInstructions:")
            print("1. Cut out both strips along the outer edges")
            print("2. Apply Layer 1 first (with numbers) around the die horizontally")
            print("3. Apply Layer 2 (with ArUco markers) perpendicular to Layer 1")
            print("4. Use the registration marks to ensure proper alignment")
            break
        else:
            if attempt < config.get('max_retries', 3) - 1:
                import time
                print(f"Retrying in {config.get('wait_between_tries', 2)} seconds...")
                time.sleep(config.get('wait_between_tries', 2))
    else:
        print("❌ Failed to print after multiple attempts.")


if __name__ == "__main__":
    main()