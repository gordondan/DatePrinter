import subprocess
import os


class LinuxLabelPrinter:
    def __init__(self, config):
        self.config = config
    
    def list_printers(self):
        """List all available printers using lpstat"""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                printers = []
                for i, line in enumerate(result.stdout.strip().split('\n')):
                    if line.startswith('printer'):
                        printer_name = line.split()[1]
                        printers.append((i, printer_name))
                return printers
            else:
                print("Failed to list printers")
                return []
        except FileNotFoundError:
            print("lpstat command not found. Is CUPS installed?")
            return []
    
    def print_label(self, image, printer_name, printer_config):
        """Print a label image to the specified printer using CUPS
        
        Args:
            image: PIL.Image object to print
            printer_name: Name of the printer
            printer_config: Printer-specific configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Save image to temporary file
            temp_file = '/tmp/label_print.png'
            image.save(temp_file)
            
            # Build lp command with options
            cmd = ['lp', '-d', printer_name]
            
            # Add media size if specified
            if 'label_width_in' in printer_config and 'label_height_in' in printer_config:
                width_mm = printer_config['label_width_in'] * 25.4
                height_mm = printer_config['label_height_in'] * 25.4
                media_size = f"Custom.{width_mm}x{height_mm}mm"
                cmd.extend(['-o', f'media={media_size}'])
            
            # Add DPI if specified
            if 'dpi' in printer_config:
                cmd.extend(['-o', f'Resolution={printer_config["dpi"]}dpi'])
            
            # Add the file to print
            cmd.append(temp_file)
            
            print(f"Printing with command: {' '.join(cmd)}")
            
            # Execute print command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Label sent to printer: {printer_name}")
                # Clean up temp file
                os.remove(temp_file)
                return True
            else:
                print(f"Printing failed: {result.stderr}")
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False
                
        except Exception as e:
            print(f"Printing failed: {e}")
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    def reconnect_bluetooth_device(self, device_name):
        """Attempt to reconnect a Bluetooth device (Linux-specific)"""
        print(f"Trying to reconnect Bluetooth device: {device_name}")
        try:
            # Try using bluetoothctl
            cmd = f'echo -e "connect $(bluetoothctl devices | grep "{device_name}" | cut -d\' \' -f2)\\nquit" | bluetoothctl'
            subprocess.run(cmd, shell=True, check=True)
            print("Bluetooth reconnect command sent.")
        except Exception as e:
            print("Bluetooth reconnect attempt failed. Error:", e)