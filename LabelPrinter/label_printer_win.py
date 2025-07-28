import win32print
import win32ui
import win32con
from PIL import ImageWin


class WindowsLabelPrinter:
    def __init__(self, config):
        self.config = config
    
    def list_printers(self):
        """List all available printers"""
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        return [(i, printer[2]) for i, printer in enumerate(printers)]
    
    def print_label(self, image, printer_name, printer_config):
        """Print a label image to the specified printer
        
        Args:
            image: PIL.Image object to print
            printer_name: Name of the printer
            printer_config: Printer-specific configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        width_px, height_px = image.size
        try:
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)
            
            # Get device capability indices from config
            caps = self.config.get('windows_device_caps', {})
            
            # Query printer capabilities
            printer_width = hDC.GetDeviceCaps(caps.get('PHYSICALWIDTH', 110))
            printer_height = hDC.GetDeviceCaps(caps.get('PHYSICALHEIGHT', 111))
            printer_dpi_x = hDC.GetDeviceCaps(caps.get('LOGPIXELSX', 88))
            printer_dpi_y = hDC.GetDeviceCaps(caps.get('LOGPIXELSY', 90))
            printable_width = hDC.GetDeviceCaps(caps.get('HORZRES', 8))
            printable_height = hDC.GetDeviceCaps(caps.get('VERTRES', 10))
            offset_x = hDC.GetDeviceCaps(caps.get('PHYSICALOFFSETX', 112))
            offset_y = hDC.GetDeviceCaps(caps.get('PHYSICALOFFSETY', 113))
            
            print(f"\n=== Printer Info ===")
            print(f"Printer DPI: {printer_dpi_x}x{printer_dpi_y}")
            print(f"Physical size: {printer_width}x{printer_height} device units")
            print(f"Printable area: {printable_width}x{printable_height} pixels")
            print(f"Margins: left={offset_x}, top={offset_y} device units")
            
            hDC.StartDoc('Label')
            hDC.StartPage()
            
            # Set mapping mode to match pixels 1:1
            hDC.SetMapMode(win32con.MM_TEXT)
            
            # Create the DIB from our image
            dib = ImageWin.Dib(image)
            
            # Calculate positioning
            if printable_width > width_px:
                auto_center_offset = (printable_width - width_px) // 2
                print(f"Auto-centering offset: {auto_center_offset}px")
            else:
                auto_center_offset = 0
            
            # Positioning based on mode
            positioning_mode = printer_config.get('positioning_mode', 'auto')
            
            if positioning_mode == 'auto':
                if printable_width > width_px:
                    h_offset = auto_center_offset
                else:
                    h_offset = offset_x
            elif positioning_mode == 'physical_offset':
                h_offset = offset_x
            elif positioning_mode == 'center':
                h_offset = auto_center_offset
            elif positioning_mode == 'manual':
                h_offset = printer_config.get('horizontal_offset', 0)
            else:
                h_offset = offset_x
            
            # Add additional offset if not in manual mode
            additional_offset = printer_config.get('horizontal_offset', 0)
            if additional_offset != 0 and positioning_mode != 'manual':
                h_offset += additional_offset
            
            # Draw the image
            dib.draw(hDC.GetHandleOutput(), 
                    (h_offset, 0, h_offset + width_px, height_px))
            
            print(f"Drawing at position ({h_offset}, 0, {h_offset + width_px}, {height_px})")
            
            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()
            
            print(f"Label sent to printer: {printer_name}")
            return True
            
        except Exception as e:
            print(f"Printing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def reconnect_bluetooth_device(self, device_name):
        """Attempt to reconnect a Bluetooth device (Windows-specific)"""
        import subprocess
        print(f"Trying to reconnect Bluetooth device: {device_name}")
        connect_cmd = f'''
        $device = Get-PnpDevice | Where-Object {{ $_.FriendlyName -like "*{device_name}*" }}
        if ($device) {{
            $deviceId = $device.InstanceId
            & "C:\\Windows\\System32\\DevicePairingWizard.exe" /connect $deviceId
        }}'''
        try:
            subprocess.run(["powershell", "-Command", connect_cmd], check=True)
            print("Bluetooth reconnect command sent.")
        except Exception as e:
            print("Bluetooth reconnect attempt failed or not supported. Error:", e)