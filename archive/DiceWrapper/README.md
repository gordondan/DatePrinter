# Dice Wrapper - ArUco Marker Wraps for Existing Dice

This application generates two-layer wrapper strips that can be applied to existing dice to add machine-readable ArUco markers.

## How It Works

The system uses a two-layer approach to ensure proper alignment and complete coverage:

### Layer 1 - Alignment Guide
- Wraps horizontally around faces 4→2→3→5 (when die oriented with 1 on top)
- Contains registration marks (corner marks and center dots) for alignment
- Shows face numbers in gray for reference
- Includes an overlap section for secure adhesion

### Layer 2 - ArUco Markers  
- Wraps perpendicular to Layer 1, around faces 6→3→1→4
- Contains the actual ArUco markers for computer vision detection
- Aligns with Layer 1's registration marks
- Each face gets a unique ArUco marker (IDs 1-6)

## Face Mapping

When the die is oriented with 1 on top and 2 facing you:
- Top: 1
- Bottom: 6  
- Front: 2
- Back: 5
- Left: 4
- Right: 3

## Usage

### Preview Mode
```bash
# Generate combined preview (both layers)
python DiceWrapper/dice_wrapper.py --preview

# Generate only Layer 1 (alignment guides)
python DiceWrapper/dice_wrapper.py --preview --layer 1

# Generate only Layer 2 (ArUco markers)
python DiceWrapper/dice_wrapper.py --preview --layer 2

# Specify dice size (default is 16mm)
python DiceWrapper/dice_wrapper.py --preview --size 20

# Custom DPI for preview
python DiceWrapper/dice_wrapper.py --preview --dpi 300
```

### Printing Mode
```bash
# Print wrapper strips
python DiceWrapper/dice_wrapper.py

# List available printers
python DiceWrapper/dice_wrapper.py --list

# Print for specific dice size
python DiceWrapper/dice_wrapper.py --size 18
```

## Application Instructions

1. **Print the wrapper strips** on thermal label printer
2. **Cut out both strips** along the outer black borders
3. **Apply Layer 1 first:**
   - Orient die with 1 on top, 2 facing you
   - Start with face 4 (marked) on the left side of the die
   - Wrap horizontally around the die
   - The overlap section covers part of face 1
4. **Apply Layer 2:**
   - Keep die in same orientation
   - Start with face 6 (marked) on the bottom
   - Wrap perpendicular to Layer 1 (vertically)
   - Use registration marks from Layer 1 to align properly
   - The overlap section covers part of face 6

## Configuration

Configuration is stored in `wrapper-config.json`:
- `default_dice_size_mm`: Standard dice size (default: 16mm)
- `default_printer`: Saved printer preference
- `output_folder`: Where preview images are saved

## Supported Dice Sizes

The application automatically scales the wrapper to fit on standard 2.25" × 1.25" thermal labels. Common dice sizes:
- 12mm (small)
- 16mm (standard) - default
- 19mm (casino size)
- 25mm (jumbo)

## Tips

- Clean dice surface before applying
- Use the registration marks (corner marks and center dots) for precise alignment
- Apply firm, even pressure to ensure good adhesion
- The gray numbers on Layer 1 are just for reference during application
- If strips are too long for your label, print each layer separately

## Requirements

- OpenCV with contrib modules (`opencv-contrib-python`)
- PIL/Pillow
- NumPy
- LabelPrinter library (included in parent directory)