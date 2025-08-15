# LabelPrinter Project Structure

This repository has been restructured to support multiple label printing applications with cross-platform compatibility.

## New Directory Structure

```
LabelPrinter/
├── LabelPrinter/           # Core label printing library
│   ├── __init__.py        # Module exports
│   ├── label_generator.py  # Label image generation logic
│   ├── label_printer_win.py # Windows-specific printing code
│   └── label_printer_lin.py # Linux-specific printing code
│
├── DatePrinter/           # Date label printing application
│   ├── __init__.py
│   ├── date_printer.py    # Main date printer application
│   └── printer-config.json # Configuration file
│
├── Server/                # Web server for remote printing
│   ├── __init__.py
│   ├── server.py          # Flask server
│   └── [other server variants]
│
└── [Other printing apps]  # Future printing applications
```

## Key Changes

1. **Modular Design**: Label generation and printing logic separated into reusable modules
2. **Cross-Platform**: Platform-specific code isolated with automatic platform detection
3. **Extensible**: Easy to add new label printing applications
4. **Organized**: Clear separation between library code, applications, and server

## Usage

### Running DatePrinter
```bash
# Windows
python DatePrinter/date_printer.py

# Linux
python3 DatePrinter/date_printer.py
```

### Running the Server
```bash
cd Server
python server.py
```

## Adding New Printing Applications

1. Create a new folder for your application
2. Import the LabelPrinter modules:
   ```python
   from LabelPrinter import LabelGenerator, LabelPrinter
   ```
3. Use the label generator and printer classes for your specific needs

## Platform Support

- **Windows**: Full support using win32print
- **Linux**: Support via CUPS (Common Unix Printing System)
- Platform detection is automatic

## Migration Notes

- The main date printer script is now at `DatePrinter/date_printer.py`
- Server files have been moved to the `Server/` directory
- Configuration files remain with their respective applications