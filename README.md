# DatePrinter

A Python script for printing date labels on thermal label printers.

## Setup

1. Install Python dependencies:
   ```
   pip install pillow pywin32
   ```

2. Create a `printer-config.json` file (see Configuration section below)

3. Run the script:
   ```
   python date-printer.py
   ```

## Configuration

**IMPORTANT**: You must create a `printer-config.json` file before running the script. The script will not create this file automatically.

Here is a complete example configuration:

```json
{
  "default_printer": "Munbyn RW402B(Bluetooth)",
  "date_format": "%B %d, %Y",
  "font_path": "C:\\Windows\\Fonts\\arial.ttf",
  "max_retries": 3,
  "wait_between_tries": 2,
  "pause_between_labels": 1,
  "default_text_height_ratio": 0.15,
  "max_text_width_ratio": 0.85,
  "min_font_size": 10,
  "max_font_size": 500,
  "month_size_ratios": {
    "January": 0.15,
    "February": 0.15,
    "March": 0.15,
    "April": 0.15,
    "May": 0.12,
    "June": 0.15,
    "July": 0.15,
    "August": 0.15,
    "September": 0.16,
    "October": 0.15,
    "November": 0.165,
    "December": 0.165
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
    "Munbyn RW402B(Bluetooth)": {
      "label_width_in": 2.25,
      "label_height_in": 1.25,
      "dpi": 203,
      "bottom_margin": 15,
      "bluetooth_device_name": "Munbyn RW402B",
      "bluetooth_wait_time": 3
    }
  }
}
```

### Configuration Parameters:

#### Global Settings:
- `default_printer`: Name of the printer to use by default (must match a Windows printer name)
- `date_format`: Date format string using Python strftime format (e.g., "%B %d, %Y" for "November 24, 2024")
- `font_path`: Full path to the TrueType font file to use
- `max_retries`: Number of times to retry printing if it fails
- `wait_between_tries`: Seconds to wait between retry attempts
- `pause_between_labels`: Seconds to pause between printing multiple labels
- `default_text_height_ratio`: Default ratio of text height to label height (0.15 = 15%)
- `max_text_width_ratio`: Maximum ratio of text width to label width (0.85 = 85%)
- `min_font_size`: Minimum font size to try when fitting text
- `max_font_size`: Maximum font size to try when fitting text

#### Month Size Ratios:
The `month_size_ratios` object allows you to adjust text size for each month. Longer month names may need smaller ratios.

#### Windows Device Capabilities:
The `windows_device_caps` object contains Windows GetDeviceCaps API indices. These are **NOT** the actual values, but the indices used to query printer capabilities:
- `PHYSICALWIDTH` (110): Gets the physical width of the printable area
- `PHYSICALHEIGHT` (111): Gets the physical height of the printable area  
- `LOGPIXELSX` (88): Gets horizontal DPI
- `LOGPIXELSY` (90): Gets vertical DPI
- `HORZRES` (8): Gets horizontal resolution in pixels
- `VERTRES` (10): Gets vertical resolution in pixels
- `PHYSICALOFFSETX` (112): Gets left margin offset
- `PHYSICALOFFSETY` (113): Gets top margin offset

#### Printer Profiles:
The `printers` object contains settings for each printer. Add a new object for each printer you want to use:
- `label_width_in`: Label width in inches
- `label_height_in`: Label height in inches
- `dpi`: Printer DPI (dots per inch)
- `bottom_margin`: Bottom margin in pixels
- `horizontal_offset`: Horizontal offset in pixels for printer positioning (0 = no offset)
- `bluetooth_device_name`: Bluetooth device name for auto-reconnection (optional)
- `bluetooth_wait_time`: Seconds to wait after Bluetooth reconnection attempt

## Usage

Show help:
```
python date-printer.py --help
```

Print today's date:
```
python date-printer.py
```

Print a specific date:
```
python date-printer.py --date 2024-12-25
```

Print multiple labels:
```
python date-printer.py --count 5
```

Force printer selection (ignore default):
```
python date-printer.py --list
```

Combine options:
```
python date-printer.py --date 2024-07-04 --count 10
```

## Supported Printers

The default configuration includes settings for:
- Munbyn RW402B (Bluetooth)

Other printers can be added by editing the `printers` section in `printer-config.json`.