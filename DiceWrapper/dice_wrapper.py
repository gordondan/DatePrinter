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
        # Handle different OpenCV versions
        try:
            self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        except AttributeError:
            self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        
        # Standard dice is typically 16mm (5/8 inch)
        self.default_dice_size_mm = 16
        
        # Label sizes
        self.label_sizes = {
            "small": {"width": 2.25, "height": 1.25},  # inches
            "large": {"width": 4, "height": 6}          # inches (portrait orientation)
        }
        
    def mm_to_pixels(self, mm, dpi):
        """Convert millimeters to pixels at given DPI"""
        inches = mm / 25.4
        return int(inches * dpi)
    
    def generate_t_shape_layout(self, dice_size_mm=16, dpi=203, label_size="large"):
        """Generate T-shape layout for wrapping dice with ArUco markers
        
        Capital T Layout:
        [4] [2] [3] [5]
            [1]
            [6]
        
        Returns: (image, layout_info)
        """
        # Get label dimensions
        label_info = self.label_sizes.get(label_size, self.label_sizes["large"])
        label_width_px = int(label_info["width"] * dpi)
        label_height_px = int(label_info["height"] * dpi)
        
        face_size_px = self.mm_to_pixels(dice_size_mm, dpi)
        margin = self.mm_to_pixels(2, dpi)  # 2mm margin for cutting
        
        # Generate single T-shape
        return self._generate_single_t_shape(dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin)
    
    def _generate_single_t_shape(self, dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin):
        """Generate a single T-shape label with ArUco markers
        
        Capital T Layout:
        [4] [2] [3] [5]
            [1]
            [6]
        
        Die placement: Face 2 (or any face) goes on top
        """
        # Create image for full label
        img = Image.new('RGB', (label_width_px, label_height_px), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw 3% margin border box
        border_margin = int(min(label_width_px, label_height_px) * 0.03)
        draw.rectangle((border_margin, border_margin, 
                       label_width_px - border_margin - 1, 
                       label_height_px - border_margin - 1), 
                      outline='lightgray', width=1)
        
        # Load font
        try:
            font_size = face_size_px // 6
            if sys.platform == 'win32':
                font_path = self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf')
            else:
                font_path = self.config.get('font_path', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf')
            font = ImageFont.truetype(font_path, font_size)
            small_font = ImageFont.truetype(font_path, font_size // 2)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Calculate T-shape center position (capital T)
        t_width = 4 * face_size_px  # Top bar is 4 faces wide
        t_height = 3 * face_size_px  # Total height is 3 faces
        x_offset = (label_width_px - t_width) // 2
        y_offset = (label_height_px - t_height) // 2
        
        # Face positions in capital T-shape
        face_positions = {
            4: (x_offset, y_offset),                           # Top left
            2: (x_offset + face_size_px, y_offset),           # Top center-left (die top)
            3: (x_offset + 2 * face_size_px, y_offset),       # Top center-right  
            5: (x_offset + 3 * face_size_px, y_offset),       # Top right
            1: (x_offset + face_size_px + face_size_px // 2, y_offset + face_size_px),  # Middle (die front)
            6: (x_offset + face_size_px + face_size_px // 2, y_offset + 2 * face_size_px) # Bottom
        }
        
        # Draw cutting outline for capital T-shape
        # Top horizontal bar
        draw.rectangle((x_offset - 2, y_offset - 2, 
                       x_offset + 4 * face_size_px + 2, y_offset + face_size_px + 2), 
                      outline='black', width=2)
        # Vertical stem  
        stem_x = x_offset + face_size_px + face_size_px // 2
        draw.rectangle((stem_x - 2, y_offset + face_size_px - 2,
                       stem_x + face_size_px + 2, y_offset + 3 * face_size_px + 2),
                      outline='black', width=2)
        
        # Generate and place ArUco markers for each face
        for face_num, (x, y) in face_positions.items():
            # Generate ArUco marker
            marker_size = int(face_size_px * 0.7)  # 70% of face size
            # Handle different OpenCV versions
            try:
                # Use face_num - 1 since ArUco IDs start at 0
                marker_img = aruco.generateImageMarker(self.aruco_dict, face_num - 1, marker_size)
            except AttributeError:
                marker_img = aruco.drawMarker(self.aruco_dict, face_num - 1, marker_size)
            marker_pil = Image.fromarray(marker_img)
            
            # Center marker in face
            marker_x = x + (face_size_px - marker_size) // 2
            marker_y = y + (face_size_px - marker_size) // 2
            img.paste(marker_pil, (marker_x, marker_y))
            
            # Draw face boundary
            draw.rectangle((x, y, x + face_size_px, y + face_size_px), 
                         outline='lightgray', width=1)
            
            # Add face number in corner
            draw.text((x + 3, y + 3), str(face_num), fill='red', font=small_font)
            
            # Draw fold lines
            if face_num in [2, 3]:  # Vertical folds between top faces
                draw.line((x + face_size_px, y, x + face_size_px, y + face_size_px), 
                        fill='lightgray', width=1)
            elif face_num == 4:  # Fold from left edge to center
                draw.line((x + face_size_px, y, x + face_size_px, y + face_size_px), 
                        fill='lightgray', width=1)
            elif face_num in [1, 6]:  # Horizontal fold lines on stem
                if face_num == 1:
                    draw.line((x, y, x + face_size_px, y), 
                            fill='lightgray', width=1)
        
        # Add instructions at the top, above the T shape
        instructions = "Capital T Die Wrapper: Place die with face 2 on top"
        instructions_y = max(margin, y_offset - font_size - margin)
        draw.text((margin, instructions_y), instructions, fill='black', font=font)
        
        # Add assembly guide at the bottom, below the T shape
        guide_y = min(label_height_px - margin - font_size * 4, 
                      y_offset + 3 * face_size_px + margin * 2)
        guide_text = "1. Place die with face 2 on top in position 2\n2. Fold faces 4 & 5 down as sides\n3. Fold face 3 over as opposite side\n4. Fold stem (1 & 6) down as front/bottom"
        draw.text((margin, guide_y), guide_text, fill='black', font=small_font)
        
        return img.convert('L'), {"type": "single_t", "face_size_px": face_size_px}
    
    def generate_combined_label(self, dice_size_mm=16, printer_config=None, label_size="small"):
        """Generate T-shape label for wrapping dice"""
        if printer_config is None:
            label_info = self.label_sizes.get(label_size, self.label_sizes["small"])
            dpi = 203
            label_width_in = label_info["width"]
            label_height_in = label_info["height"]
        else:
            dpi = printer_config.get('dpi', 203)
            label_width_in = printer_config.get('label_width_in', 2.25)
            label_height_in = printer_config.get('label_height_in', 1.25)
            # Determine label size from dimensions
            if label_width_in >= 4 and label_height_in >= 3:
                label_size = "large"
            else:
                label_size = "small"
        
        # Generate T-shape layout
        img, layout_info = self.generate_t_shape_layout(dice_size_mm, dpi, label_size)
        
        return img


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
    parser.add_argument('--label-size', type=str, choices=['small', 'large'], default='large',
                       help='Label size: small (2.25x1.25") or large (4x6" portrait)')
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
        
        # Generate T-shape layout
        img, layout_info = generator.generate_t_shape_layout(args.size, args.dpi, args.label_size)
        default_name = "dice_wrapper_t_shape.png"
        
        # Save preview
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join(output_folder, default_name)
        
        img.save(output_path)
        print(f"✅ Saved dice wrapper preview to {output_path}")
        print(f"   Image size: {img.size}")
        print(f"   Dice size: {args.size}mm")
        print(f"   Label size: {args.label_size}")
        print(f"   Layout type: {layout_info['type']}")
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
    label_img = generator.generate_combined_label(args.size, printer_config, args.label_size)
    
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
            print("1. Cut out the T-shape along the black outline")
            print("2. Place die with face 2 on top in position 2")
            print("3. Fold faces 4 & 5 down as sides")
            print("4. Fold face 3 over as opposite side")
            print("5. Fold stem (1 & 6) down as front/bottom")
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