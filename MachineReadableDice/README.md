# Machine Readable Dice

This application generates dice faces with ArUco markers that can be read by computer vision systems.

## Features

- Generates 6 dice faces (1-6) using ArUco markers
- Overlays readable numbers on the markers
- Supports both preview mode and direct printing
- Integrates with the LabelPrinter library for thermal printing
- Configurable marker sizes and layout

## Usage

### Preview Mode (No Printing)
```bash
# Generate preview with default size (300px markers)
python MachineReadableDice/machine_readable_dice.py --preview

# Generate preview with custom size
python MachineReadableDice/machine_readable_dice.py --preview --size 500

# Save preview to specific location
python MachineReadableDice/machine_readable_dice.py --preview --output my_dice.png
```

### Printing Mode
```bash
# Print to default printer
python MachineReadableDice/machine_readable_dice.py

# List available printers
python MachineReadableDice/machine_readable_dice.py --list

# Force printer selection (ignore default)
python MachineReadableDice/machine_readable_dice.py --list
```

## Configuration

The application uses `dice-config.json` for configuration. It will be created automatically on first run.

### Configuration Options:
- `default_printer`: Name of the default printer
- `font_path`: Path to the font file for number overlays
- `output_folder`: Folder for saving preview images
- `printers`: Printer-specific settings (DPI, label size, etc.)

## ArUco Markers

The dice use ArUco markers from the 4x4_50 dictionary:
- Marker ID 1 = Dice face 1
- Marker ID 2 = Dice face 2
- ... and so on up to 6

These markers can be detected and read by computer vision systems using OpenCV's ArUco module.

## Requirements

- OpenCV with contrib modules (`opencv-contrib-python`)
- PIL/Pillow
- NumPy
- The LabelPrinter library (included in parent directory)