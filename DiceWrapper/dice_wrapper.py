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
            "large": {"width": 6, "height": 4}          # inches
        }
        
    def mm_to_pixels(self, mm, dpi):
        """Convert millimeters to pixels at given DPI"""
        inches = mm / 25.4
        return int(inches * dpi)
    
    def generate_t_shape_layout(self, dice_size_mm=16, dpi=203, label_size="small"):
        """Generate T-shape layout for wrapping dice with ArUco markers
        
        T-shape layout:
        - Horizontal strip: 4 faces wrapping around middle (2-3-5-4)
        - Vertical strip: 3 faces wrapping perpendicular (6-front-1)
        
        Returns: (image, layout_info) where layout_info indicates if T was split
        """
        # Get label dimensions
        label_info = self.label_sizes.get(label_size, self.label_sizes["small"])
        label_width_px = int(label_info["width"] * dpi)
        label_height_px = int(label_info["height"] * dpi)
        
        face_size_px = self.mm_to_pixels(dice_size_mm, dpi)
        margin = self.mm_to_pixels(2, dpi)  # 2mm margin for cutting
        
        # Check if T-shape fits as single piece
        # T-shape dimensions: 3 faces wide x 4 faces tall (with center intersection)
        t_width = 3 * face_size_px + 2 * margin
        t_height = 4 * face_size_px + 2 * margin
        
        # Decision logic: use separate strips if T doesn't fit
        use_separate_strips = (t_width > label_width_px or t_height > label_height_px)
        
        # Alternative check: if 3x die size > label width * 0.8, use separate strips
        if 3 * dice_size_mm > label_info["width"] * 25.4 * 0.8:
            use_separate_strips = True
        
        if use_separate_strips:
            # Generate separate strips that fit on label
            return self._generate_separate_strips(dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin)
        else:
            # Generate single T-shape
            return self._generate_single_t_shape(dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin)
    
    def _generate_single_t_shape(self, dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin):
        """Generate a single T-shape label with ArUco markers
        
        Layout:
                [1]
                [2]
        [4] [3] [center] [5]
                [6]
        """
        # Create image for full label
        img = Image.new('RGB', (label_width_px, label_height_px), 'white')
        draw = ImageDraw.Draw(img)
        
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
        
        # Calculate T-shape center position
        t_width = 3 * face_size_px
        t_height = 4 * face_size_px
        x_offset = (label_width_px - t_width) // 2
        y_offset = (label_height_px - t_height) // 2
        
        # Face positions in T-shape
        face_positions = {
            1: (x_offset + face_size_px, y_offset),                    # Top
            2: (x_offset + face_size_px, y_offset + face_size_px),     # Center top
            3: (x_offset + face_size_px, y_offset + 2 * face_size_px), # Center (intersection)
            4: (x_offset, y_offset + 2 * face_size_px),                # Left
            5: (x_offset + 2 * face_size_px, y_offset + 2 * face_size_px), # Right
            6: (x_offset + face_size_px, y_offset + 3 * face_size_px)  # Bottom
        }
        
        # Draw cutting outline for T-shape
        # Vertical part
        draw.rectangle((x_offset + face_size_px - 2, y_offset - 2, 
                       x_offset + 2 * face_size_px + 2, y_offset + 4 * face_size_px + 2), 
                      outline='black', width=2)
        # Horizontal part
        draw.rectangle((x_offset - 2, y_offset + 2 * face_size_px - 2,
                       x_offset + 3 * face_size_px + 2, y_offset + 3 * face_size_px + 2),
                      outline='black', width=2)
        
        # Generate and place ArUco markers for each face
        for face_num, (x, y) in face_positions.items():
            # Generate ArUco marker
            marker_size = int(face_size_px * 0.7)  # 70% of face size
            # Handle different OpenCV versions
            try:
                marker_img = aruco.generateImageMarker(self.aruco_dict, face_num, marker_size)
            except AttributeError:
                marker_img = aruco.drawMarker(self.aruco_dict, face_num, marker_size)
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
            if face_num in [1, 2, 4, 5]:  # Not for center (3) or bottom (6)
                if face_num in [1, 2]:  # Vertical fold lines
                    draw.line((x, y + face_size_px, x + face_size_px, y + face_size_px), 
                            fill='lightgray', width=1)
                elif face_num == 4:  # Left fold line
                    draw.line((x + face_size_px, y, x + face_size_px, y + face_size_px), 
                            fill='lightgray', width=1)
                elif face_num == 5:  # Right fold line
                    draw.line((x, y, x, y + face_size_px), 
                            fill='lightgray', width=1)
        
        # Add instructions
        instructions = "T-Shape Die Wrapper: Place die with any face up in center (3), fold sides"
        draw.text((margin, margin), instructions, fill='black', font=font)
        
        # Add assembly guide
        guide_y = label_height_px - margin - font_size * 3
        guide_text = "1. Place die in center square\n2. Fold up all sides\n3. Sides overlap at edges"
        draw.text((margin, guide_y), guide_text, fill='black', font=small_font)
        
        return img.convert('L'), {"type": "single_t", "face_size_px": face_size_px}
    
    def _generate_separate_strips(self, dice_size_mm, dpi, label_width_px, label_height_px, face_size_px, margin):
        """Generate two separate strips: horizontal (4 faces) and vertical (3 faces)"""
        img = Image.new('RGB', (label_width_px, label_height_px), 'white')
        draw = ImageDraw.Draw(img)
        
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
        
        # Calculate strip sizes
        h_strip_width = 4 * face_size_px + 2 * margin
        h_strip_height = face_size_px + 2 * margin
        v_strip_width = face_size_px + 2 * margin
        v_strip_height = 3 * face_size_px + 2 * margin
        
        # Position strips on label
        h_strip_x = (label_width_px - h_strip_width) // 2
        h_strip_y = margin
        
        v_strip_x = (label_width_px - v_strip_width) // 2
        v_strip_y = h_strip_y + h_strip_height + margin
        
        # Check if both strips fit
        if v_strip_y + v_strip_height > label_height_px:
            # Try side-by-side layout
            if h_strip_width + v_strip_width + 3 * margin <= label_width_px:
                h_strip_x = margin
                v_strip_x = h_strip_x + h_strip_width + margin
                v_strip_y = margin
            else:
                # Scale down
                scale = min((label_height_px - 3 * margin) / (h_strip_height + v_strip_height),
                           (label_width_px - 2 * margin) / max(h_strip_width, v_strip_width))
                face_size_px = int(face_size_px * scale)
                margin = int(margin * scale)
                # Recalculate with scaled dimensions
                h_strip_width = 4 * face_size_px + 2 * margin
                h_strip_height = face_size_px + 2 * margin
                v_strip_width = face_size_px + 2 * margin
                v_strip_height = 3 * face_size_px + 2 * margin
                h_strip_x = (label_width_px - h_strip_width) // 2
                h_strip_y = margin
                v_strip_x = (label_width_px - v_strip_width) // 2
                v_strip_y = h_strip_y + h_strip_height + margin
        
        # Draw horizontal strip (faces 2, 3, 5, 4)
        draw.rectangle((h_strip_x, h_strip_y, h_strip_x + h_strip_width, h_strip_y + h_strip_height),
                      outline='black', width=2)
        
        h_faces = [2, 3, 5, 4]  # Wrap around middle
        for i, face_num in enumerate(h_faces):
            x = h_strip_x + margin + i * face_size_px
            y = h_strip_y + margin
            
            # Generate ArUco marker
            marker_size = int(face_size_px * 0.7)
            # Handle different OpenCV versions
            try:
                marker_img = aruco.generateImageMarker(self.aruco_dict, face_num, marker_size)
            except AttributeError:
                marker_img = aruco.drawMarker(self.aruco_dict, face_num, marker_size)
            marker_pil = Image.fromarray(marker_img)
            
            # Center marker
            marker_x = x + (face_size_px - marker_size) // 2
            marker_y = y + (face_size_px - marker_size) // 2
            img.paste(marker_pil, (marker_x, marker_y))
            
            # Face boundary
            draw.rectangle((x, y, x + face_size_px, y + face_size_px), 
                         outline='lightgray', width=1)
            
            # Face number
            draw.text((x + 3, y + 3), str(face_num), fill='red', font=small_font)
            
            # Fold lines
            if i < len(h_faces) - 1:
                draw.line((x + face_size_px, y - margin//2, x + face_size_px, y + face_size_px + margin//2),
                         fill='lightgray', width=1)
        
        # Draw vertical strip (faces 6, front, 1)
        draw.rectangle((v_strip_x, v_strip_y, v_strip_x + v_strip_width, v_strip_y + v_strip_height),
                      outline='black', width=2)
        
        v_faces = [6, 0, 1]  # 0 will be the overlapping center
        for i, face_num in enumerate(v_faces):
            x = v_strip_x + margin
            y = v_strip_y + margin + i * face_size_px
            
            if face_num == 0:  # Center overlap area
                draw.rectangle((x, y, x + face_size_px, y + face_size_px), 
                             outline='red', width=2)
                text = "Overlap\nCenter"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (face_size_px - text_width) // 2
                text_y = y + (face_size_px - text_height) // 2
                draw.text((text_x, text_y), text, fill='red', font=font, align='center')
            else:
                # Generate ArUco marker
                marker_size = int(face_size_px * 0.7)
                # Handle different OpenCV versions
            try:
                marker_img = aruco.generateImageMarker(self.aruco_dict, face_num, marker_size)
            except AttributeError:
                marker_img = aruco.drawMarker(self.aruco_dict, face_num, marker_size)
                marker_pil = Image.fromarray(marker_img)
                
                # Center marker
                marker_x = x + (face_size_px - marker_size) // 2
                marker_y = y + (face_size_px - marker_size) // 2
                img.paste(marker_pil, (marker_x, marker_y))
                
                # Face boundary
                draw.rectangle((x, y, x + face_size_px, y + face_size_px), 
                             outline='lightgray', width=1)
                
                # Face number
                draw.text((x + 3, y + 3), str(face_num), fill='red', font=small_font)
            
            # Fold lines
            if i < len(v_faces) - 1:
                draw.line((x - margin//2, y + face_size_px, x + face_size_px + margin//2, y + face_size_px),
                         fill='lightgray', width=1)
        
        # Add instructions
        instructions = "1. Apply horizontal strip around middle\n2. Apply vertical strip perpendicular"
        draw.text((margin, margin), instructions, fill='black', font=font)
        
        return img.convert('L'), {"type": "separate_strips", "face_size_px": face_size_px}
    
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
            # Handle different OpenCV versions
            try:
                marker_img = aruco.generateImageMarker(self.aruco_dict, face_num, marker_size)
            except AttributeError:
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
    parser.add_argument('--label-size', type=str, choices=['small', 'large'], default='small',
                       help='Label size: small (2.25x1.25") or large (4x6")')
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
        
        if layout_info["type"] == "single_t":
            default_name = "dice_wrapper_t_shape.png"
        else:
            default_name = "dice_wrapper_strips.png"
        
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
            print("For T-shape layout:")
            print("1. Cut out the T-shape along the black outline")
            print("2. Place die in center square with any face up")
            print("3. Fold all sides up around the die")
            print("4. Sides will overlap at edges for secure fit")
            print("\nFor separate strips:")
            print("1. Cut out both strips along the outer edges")
            print("2. Apply horizontal strip around middle of die")
            print("3. Apply vertical strip perpendicular, overlapping center")
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