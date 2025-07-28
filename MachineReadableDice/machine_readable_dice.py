import cv2
import cv2.aruco as aruco
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import sys
import argparse
import json

# Add parent directory to path to import LabelPrinter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LabelPrinter import LabelGenerator, LabelPrinter


class ArucoDiceGenerator:
    def __init__(self, config):
        self.config = config
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        
    def generate_dice_matrix(self, marker_size=300, columns=3, rows=2, 
                            font_size_ratio=0.3, font_color=(255, 0, 0)):
        """Generate a matrix of ArUco markers with overlay numbers for dice faces"""
        
        font_size = int(marker_size * font_size_ratio)
        
        # Try to load a font
        try:
            if sys.platform == 'win32':
                font_path = self.config.get('font_path', 'C:\\Windows\\Fonts\\arial.ttf')
            else:
                font_path = self.config.get('font_path', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf')
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Warning: Could not load font from {font_path}, using default")
            font = ImageFont.load_default()
        
        # Generate ArUco markers with overlay numbers
        images = []
        for marker_id in range(1, 7):  # Dice faces 1-6
            # Create marker image
            marker_img = aruco.drawMarker(self.aruco_dict, marker_id, marker_size)
            marker_pil = Image.fromarray(marker_img).convert("RGB")
            draw = ImageDraw.Draw(marker_pil)
            
            # Draw the number in the center
            text = str(marker_id)
            # Use textbbox for better text positioning
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            position = ((marker_size - text_width) // 2 - bbox[0], 
                       (marker_size - text_height) // 2 - bbox[1])
            draw.text(position, text, font=font, fill=font_color)
            
            images.append(marker_pil)
        
        # Create matrix
        matrix_width = columns * marker_size
        matrix_height = rows * marker_size
        matrix_img = Image.new("RGB", (matrix_width, matrix_height), "white")
        
        # Paste each marker in correct position
        for idx, img in enumerate(images):
            row = idx // columns
            col = idx % columns
            x = col * marker_size
            y = row * marker_size
            matrix_img.paste(img, (x, y))
        
        return matrix_img
    
    def generate_for_label(self, printer_config):
        """Generate ArUco dice sized for label printing"""
        # Calculate marker size based on label dimensions
        label_width_px = int(printer_config['label_width_in'] * printer_config['dpi'])
        label_height_px = int(printer_config['label_height_in'] * printer_config['dpi'])
        
        # For 2.25" x 1.25" label, we can fit 3x2 grid with some margin
        margin = 20  # pixels
        usable_width = label_width_px - (2 * margin)
        usable_height = label_height_px - (2 * margin)
        
        # Calculate marker size to fit grid
        marker_width = usable_width // 3
        marker_height = usable_height // 2
        marker_size = min(marker_width, marker_height)
        
        # Generate the matrix
        matrix_img = self.generate_dice_matrix(
            marker_size=marker_size,
            columns=3,
            rows=2,
            font_size_ratio=0.3,
            font_color=(255, 0, 0)
        )
        
        # Create label-sized image with white background
        label_img = Image.new('RGB', (label_width_px, label_height_px), 'white')
        
        # Center the matrix on the label
        matrix_width, matrix_height = matrix_img.size
        x_offset = (label_width_px - matrix_width) // 2
        y_offset = (label_height_px - matrix_height) // 2
        
        label_img.paste(matrix_img, (x_offset, y_offset))
        
        # Convert to grayscale for thermal printing
        return label_img.convert('L')


def load_config():
    """Load configuration from JSON file"""
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dice-config.json")
    
    # Default configuration
    default_config = {
        "default_printer": None,
        "font_path": "C:\\Windows\\Fonts\\arial.ttf" if sys.platform == 'win32' else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "output_folder": "generated_aruco_dice",
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
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dice-config.json")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def get_printer_config(config, printer_name):
    """Get printer-specific configuration, creating default if needed"""
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
        description='Generate and print machine-readable dice with ArUco markers'
    )
    parser.add_argument('-p', '--preview', action='store_true',
                       help='Only generate preview, do not print')
    parser.add_argument('-l', '--list', action='store_true',
                       help='List available printers')
    parser.add_argument('-s', '--size', type=int, default=300,
                       help='Marker size in pixels for preview (default: 300)')
    parser.add_argument('-o', '--output', type=str,
                       help='Output file path for preview')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Create generator
    generator = ArucoDiceGenerator(config)
    
    # Preview mode
    if args.preview:
        output_folder = config.get('output_folder', 'generated_aruco_dice')
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate full-size preview
        matrix_img = generator.generate_dice_matrix(marker_size=args.size)
        
        # Save preview
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join(output_folder, "aruco_dice_preview.png")
        
        matrix_img.save(output_path)
        print(f"✅ Saved ArUco dice preview to {output_path}")
        print(f"   Matrix size: {matrix_img.size}")
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
    
    # Generate dice for label
    print("\nGenerating ArUco dice for label printing...")
    label_img = generator.generate_for_label(printer_config)
    
    # Save preview
    output_folder = config.get('output_folder', 'generated_aruco_dice')
    os.makedirs(output_folder, exist_ok=True)
    preview_path = os.path.join(output_folder, "aruco_dice_label.png")
    label_img.save(preview_path)
    print(f"Preview saved to: {preview_path}")
    
    # Print the label
    print(f"\nPrinting ArUco dice label...")
    
    for attempt in range(config.get('max_retries', 3)):
        print(f"Print attempt {attempt + 1}...")
        success = label_printer.print_label(label_img, selected_printer, printer_config)
        if success:
            print("✅ Successfully printed ArUco dice label!")
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