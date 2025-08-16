import platform
import sys

# Import the appropriate printer class based on the platform
if platform.system() == 'Windows':
    from .label_printer_win import WindowsLabelPrinter as LabelPrinter
elif platform.system() == 'Linux':
    from .label_printer_lin import LinuxLabelPrinter as LabelPrinter
else:
    raise NotImplementedError(f"Platform {platform.system()} is not supported")

# Export the main classes
from .label_generator import LabelGenerator

__all__ = ['LabelGenerator', 'LabelPrinter']