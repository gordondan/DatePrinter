# DatePrinter

A Python script for printing date labels on thermal label printers.

## Setup

1. Install Python dependencies:
   ```
   pip install pillow pywin32
   ```

2. Configure your printer:
   - Copy `printer-config.json.default` to `printer-config.json`
   - Edit `printer-config.json` to match your printer settings

## Configuration

The configuration file supports multiple printer profiles and customizable settings:

```json
{
  "default_printer": "Your Printer Name",
  "date_format": "%B %d, %Y",
  "printers": {
    "Your Printer Name": {
      "label_width_in": 2.25,
      "label_height_in": 1.25,
      "dpi": 203,
      "bottom_margin": 15
    }
  }
}
```

### Key Settings:
- `default_printer`: The printer to use automatically
- `date_format`: How dates are formatted (uses Python strftime)
- `month_size_ratios`: Adjust text size for each month
- `printers`: Define settings for each printer

## Usage

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

Force printer selection:
```
python date-printer.py --list
```

## Supported Printers

The default configuration includes settings for:
- Munbyn RW402B (Bluetooth)

Other printers can be added by editing the `printers` section in `printer-config.json`.