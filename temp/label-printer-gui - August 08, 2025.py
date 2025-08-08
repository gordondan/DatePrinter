#!/usr/bin/env python3

"""
Label Printer GUI - Python/tkinter wrapper for date-printer.py
Provides a tabbed interface for organizing and executing label templates
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import math

class LabelPrinterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.templates_dir = "label-images"
        self.global_copy_count = tk.IntVar(value=1)
        self.current_variables = []
        self.current_template_file = ""
        self.date_printer_options = []
        self.template_variable_widgets = {}  # Store variable widgets by template file
        self.hot_template_words = {
            'TODAY': datetime.now().strftime('%B %d, %Y'),
            'LONG-DATE-TIME': datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'),
            'CURRENT-TIME': datetime.now().strftime('%I:%M %p'),
            'MESSAGE': '',
            'BORDER MESSAGE': ''
        }
        self.setup_gui()
        
    def setup_gui(self):
        """Initialize the main GUI"""
        self.root.title("Label Printer GUI")
        self.root.geometry("1200x800")
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Global settings frame
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Global Copy Count:", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Spinbox(settings_frame, from_=1, to=99, width=5, textvariable=self.global_copy_count).pack(side=tk.LEFT, padx=(10, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize directories and templates
        self.create_initial_structure()
        self.refresh_tabs()
        
    def create_initial_structure(self):
        """Create initial directory structure and example templates"""
        # Create directories
        Path(self.templates_dir).mkdir(exist_ok=True)
        for category in ["family", "office", "personal"]:
            Path(self.templates_dir, category).mkdir(exist_ok=True)
            
        self.create_example_templates()
        
    def create_example_templates(self):
        """Create example templates for the family category"""
        family_dir = Path(self.templates_dir, "family")
        
        # Family member templates
        family_members = ["Dan", "Lexie", "Tyrell", "Natalyn", "David", "Jacob", "Isabella", "Caleb", "Julia"]
        
        for member in family_members:
            template_file = family_dir / f"{member.lower()}.template"
            if not template_file.exists():
                content = f'--message {member}'
                template_file.write_text(content, encoding='utf-8')
                
        # Birthday template with variables
        birthday_template = family_dir / "birthday.template"
        if not birthday_template.exists():
            content = '--message {{name}} --border-message {{occasion}}\n# DEFAULT: occasion=Birthday'
            birthday_template.write_text(content, encoding='utf-8')
            
        print("Created example templates")
        
    def get_categories(self):
        """Get list of category directories"""
        categories = []
        templates_path = Path(self.templates_dir)
        
        if templates_path.exists():
            for item in templates_path.iterdir():
                if item.is_dir():
                    categories.append(item.name)
                    
        return sorted(categories)
    
    def get_templates(self, category):
        """Get templates for a specific category"""
        templates = []
        category_path = Path(self.templates_dir, category)
        
        if category_path.exists():
            for template_file in category_path.glob("*.template"):
                template_name = template_file.stem
                templates.append((template_name, str(template_file)))
                
        return sorted(templates)
    
    def read_template_file(self, template_file):
        """Read content from a template file"""
        try:
            return Path(template_file).read_text(encoding='utf-8').strip()
        except Exception as e:
            print(f"Error reading template file {template_file}: {e}")
            return ""
    
    def write_template_file(self, template_file, content):
        """Write content to a template file"""
        try:
            Path(template_file).write_text(content, encoding='utf-8')
        except Exception as e:
            print(f"Error writing template file {template_file}: {e}")
            
    def extract_variables(self, template_content):
        """Extract {{variable}} patterns from template content"""
        pattern = r'\{\{([^}]+)\}\}'
        variables = []
        
        for match in re.finditer(pattern, template_content):
            var_name = match.group(1).strip()
            if var_name not in variables:
                variables.append(var_name)
                
        return variables
    
    def extract_defaults(self, template_content):
        """Extract default values from template comments"""
        defaults = {}
        
        for line in template_content.split('\n'):
            match = re.match(r'#\s*DEFAULT:\s*([^=]+)=(.*)$', line)
            if match:
                var_name = match.group(1).strip()
                var_value = match.group(2).strip()
                defaults[var_name] = var_value
                
        return defaults
    
    def substitute_variables(self, template_content, variable_values):
        """Substitute variables in template content"""
        result = template_content
        
        # First substitute hot template words
        for var_name, var_value in variable_values.items():
            # Handle hot template words
            if var_name in self.hot_template_words and var_value == "":
                var_value = self.hot_template_words[var_name]
            elif var_name == "TODAY":
                var_value = datetime.now().strftime('%B %d, %Y') if var_value == "" else var_value
            elif var_name == "LONG-DATE-TIME":
                var_value = datetime.now().strftime('%A, %B %d, %Y at %I:%M %p') if var_value == "" else var_value
            elif var_name == "CURRENT-TIME":
                var_value = datetime.now().strftime('%I:%M %p') if var_value == "" else var_value
                
            pattern = r"\{\{" + re.escape(var_name) + r"\}\}"
            result = re.sub(pattern, var_value, result)
            
        return result
    
    def get_copy_count_from_template(self, template_content):
        """Extract copy count from template or use global default"""
        match = re.search(r'(?:^|\s)(?:-c|--count)\s+(\d+)', template_content)
        if match:
            return int(match.group(1))
        return self.global_copy_count.get()
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def execute_template(self, template_file, variable_values):
        """Execute a template with given variable values"""
        self.update_status("Loading template...")
        
        template_content = self.read_template_file(template_file)
        if not template_content:
            messagebox.showerror("Error", f"Could not read template file: {template_file}")
            self.update_status("Ready")
            return
            
        # Substitute variables
        final_command = self.substitute_variables(template_content, variable_values)
        
        # Get copy count (template overrides global setting)
        copy_count = self.get_copy_count_from_template(final_command)
        
        # If no -c in template, add global setting
        if not re.search(r'(?:^|\s)(?:-c|--count)\s+\d+', final_command):
            final_command = f"{final_command} -c {copy_count}"
            
        # Execute the command
        self.update_status("Printing label...")
        
        # Build command using shell=True with proper quoting for Windows
        import shlex
        
        # Use shell=False with individual arguments for better control
        command = ["python", "date-printer.py"]
        
        # Parse the command properly by reconstructing from template and variables
        # This ensures multi-word values are handled as single arguments
        args = []
        parts = final_command.split()
        i = 0
        
        while i < len(parts):
            if parts[i].startswith('--') or parts[i].startswith('-'):
                option = parts[i]
                args.append(option)
                
                # Look for value after option
                if i + 1 < len(parts) and not parts[i + 1].startswith('-'):
                    # Collect all parts until next option or end
                    value_parts = []
                    i += 1
                    
                    # Keep collecting until we hit another option or end
                    while i < len(parts) and not parts[i].startswith('-'):
                        value_parts.append(parts[i])
                        i += 1
                    
                    if value_parts:
                        # Join the parts back into a single argument
                        full_value = ' '.join(value_parts)
                        args.append(full_value)
                    
                    # Don't increment i again, we're already positioned correctly
                    continue
                else:
                    i += 1
            else:
                i += 1
        
        command.extend(args)
        
        print(f"Executing: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.update_status("Label printed successfully")
            print(f"Command output: {result.stdout}")
            
            # Clear status after 3 seconds
            self.root.after(3000, lambda: self.update_status("Ready"))
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Print Error", f"Failed to print label:\n{e.stderr}")
            self.update_status("Print failed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to execute command:\n{str(e)}")
            self.update_status("Print failed")
    
    def get_date_printer_options(self):
        """Get available options from date-printer.py --help"""
        if not self.date_printer_options:
            try:
                result = subprocess.run(["python", "date-printer.py", "--help"], 
                                      capture_output=True, text=True, check=True)
                
                # Filter to only label-related options (actual options from --help)
                label_related = ['message', 'border-message', 'message-only', 'count', 'date', 'list']
                options = []
                
                for line in result.stdout.split('\n'):
                    match = re.match(r'^\s*(-[a-zA-Z],?\s*)?--([a-zA-Z-]+)', line)
                    if match:
                        short_opt = match.group(1) if match.group(1) else ""
                        long_opt = match.group(2)
                        
                        # Only include label-related options
                        if any(keyword in long_opt for keyword in label_related):
                            # Set default values for message options
                            default_value = ""
                            if long_opt == "message":
                                default_value = "{{MESSAGE}}"
                            elif long_opt == "border-message":
                                default_value = "{{BORDER MESSAGE}}"
                                
                            options.append((long_opt, short_opt.strip(), line.strip(), default_value))
                        
                self.date_printer_options = options
                
            except Exception as e:
                print(f"Error getting date-printer options: {e}")
                return []
                
        return self.date_printer_options
    
    def create_template_dialog(self, category):
        """Create dialog for creating new templates"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Template")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Template name
        name_frame = ttk.Frame(dialog, padding="10")
        name_frame.pack(fill=tk.X)
        
        ttk.Label(name_frame, text="Template Name:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(name_frame, width=30)
        name_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Options frame with scrollbar
        options_frame = ttk.Frame(dialog, padding="10")
        options_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(options_frame, text="Label Options:").pack(anchor=tk.W)
        
        # Scrollable frame for options
        canvas = tk.Canvas(options_frame)
        scrollbar = ttk.Scrollbar(options_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Option widgets storage
        option_vars = {}
        option_entries = {}
        
        # Populate options
        options = self.get_date_printer_options()
        for i, option in enumerate(options):
            long_opt, short_opt, description, default_value = option
            
            option_frame = ttk.Frame(scrollable_frame)
            option_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Checkbox
            var = tk.BooleanVar()
            option_vars[long_opt] = var
            checkbox = ttk.Checkbutton(option_frame, variable=var)
            checkbox.pack(side=tk.LEFT, padx=(0, 10))
            
            # Option name (non-editable)
            option_label = ttk.Label(option_frame, text=f"--{long_opt}", width=20, anchor=tk.W)
            option_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # Value entry
            entry = ttk.Entry(option_frame, width=40)
            entry.insert(0, default_value)
            entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
            option_entries[long_opt] = entry
            
        # Hot template words info
        info_frame = ttk.Frame(dialog, padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = "Hot Template Words: {{TODAY}}, {{LONG-DATE-TIME}}, {{CURRENT-TIME}}, {{MESSAGE}}, {{BORDER MESSAGE}}"
        ttk.Label(info_frame, text=info_text, foreground="blue", font=('TkDefaultFont', 8)).pack(anchor=tk.W)
        
        # Preview frame
        preview_frame = ttk.Frame(dialog, padding="10")
        preview_frame.pack(fill=tk.X)
        
        ttk.Label(preview_frame, text="Command Preview:").pack(anchor=tk.W)
        preview_text = scrolledtext.ScrolledText(preview_frame, height=3, wrap=tk.WORD)
        preview_text.pack(fill=tk.X, pady=(5, 0))
        
        # Update preview function
        def update_preview(*args):
            command_parts = []
            for long_opt, var in option_vars.items():
                if var.get():
                    entry_value = option_entries[long_opt].get()
                    if entry_value:
                        # Don't add quotes in the template - they'll be added during execution
                        command_parts.append(f'--{long_opt} {entry_value}')
                    else:
                        command_parts.append(f'--{long_opt}')
                        
            preview_text.delete(1.0, tk.END)
            preview_text.insert(1.0, ' '.join(command_parts))
            
        # Bind all checkboxes and entries to update preview
        for long_opt, var in option_vars.items():
            var.trace('w', update_preview)
            option_entries[long_opt].bind('<KeyRelease>', update_preview)
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)
        
        def create_template():
            template_name = name_entry.get().strip()
            if not template_name:
                messagebox.showerror("Error", "Please enter a template name")
                return
                
            command = preview_text.get(1.0, tk.END).strip()
            if not command:
                messagebox.showerror("Error", "Please select at least one option")
                return
                
            # Create category directory if needed
            category_path = Path(self.templates_dir, category)
            category_path.mkdir(exist_ok=True)
            
            # Write template file
            template_file = category_path / f"{template_name}.template"
            
            if template_file.exists():
                if not messagebox.askyesno("Template Exists", 
                                         f"Template '{template_name}' already exists. Overwrite?"):
                    return
                    
            self.write_template_file(str(template_file), command)
            dialog.destroy()
            # Refresh all tabs to show the new template
            self.refresh_tabs()
            self.update_status(f"Template '{template_name}' created successfully")
            
        ttk.Button(button_frame, text="Create Template", command=create_template).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
    def create_variable_form(self, parent, template_file):
        """Create input form for template variables"""
        self.current_template_file = template_file
        template_content = self.read_template_file(template_file)
        variables = self.extract_variables(template_content)
        defaults = self.extract_defaults(template_content)
        
        # Clear existing variable widgets
        for child in parent.winfo_children():
            if child.winfo_name().startswith('var_frame'):
                child.destroy()
                
        if not variables:
            self.current_variables = []
            return
            
        self.current_variables = []
        
        # Create main variables frame
        var_main_frame = ttk.Frame(parent, name='var_frame_main')
        var_main_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(var_main_frame, text="Template Variables:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        
        # Create input widgets for each variable
        for i, var_name in enumerate(variables):
            var_frame = ttk.Frame(var_main_frame, name=f'var_frame_{i}')
            var_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(var_frame, text=f"{var_name}:", width=15).pack(side=tk.LEFT, padx=(0, 5))
            
            entry = ttk.Entry(var_frame, width=25)
            entry.pack(side=tk.LEFT, padx=(0, 5))
            
            # Set default value based on hot template words or stored defaults
            default_value = ""
            if var_name in defaults:
                default_value = defaults[var_name]
            elif var_name in self.hot_template_words:
                default_value = self.hot_template_words[var_name]
                
            entry.insert(0, default_value)
                
            # Save as default button
            save_btn = ttk.Button(var_frame, text="Save as default")
            save_btn.pack(side=tk.LEFT, padx=(5, 0))
            
            # Configure button command and state
            save_btn.configure(command=lambda vn=var_name, e=entry: self.save_variable_default(vn, e))
            self.update_default_button_state(save_btn, var_name, entry, defaults)
            
            # Bind entry change to update button state
            entry.bind('<KeyRelease>', lambda event, btn=save_btn, vn=var_name, e=entry, d=defaults: 
                      self.update_default_button_state(btn, vn, e, d))
            
            self.current_variables.append((var_name, entry))
            
    def update_default_button_state(self, button, var_name, entry, defaults):
        """Update the state of the 'Save as default' button"""
        current_value = entry.get()
        default_value = defaults.get(var_name, "")
        
        if current_value == default_value:
            button.configure(state=tk.DISABLED)
        else:
            button.configure(state=tk.NORMAL)
            
    def save_variable_default(self, var_name, entry):
        """Save a variable's current value as default"""
        value = entry.get()
        template_content = self.read_template_file(self.current_template_file)
        
        # Remove existing default for this variable
        new_lines = []
        for line in template_content.split('\n'):
            pattern = r"^#\s*DEFAULT:\s*" + re.escape(var_name) + r"\s*="
            if not re.match(pattern, line):
                new_lines.append(line)
                
        # Add new default
        new_lines.append(f"# DEFAULT: {var_name}={value}")
        
        new_content = '\n'.join(new_lines)
        self.write_template_file(self.current_template_file, new_content)
        
        self.update_status(f"Default value saved for {var_name}")
        
        # Refresh the form to update button states
        parent = entry.winfo_parent()
        while parent and not parent.endswith('content'):
            parent = self.root.nametowidget(parent).winfo_parent()
        if parent:
            self.create_variable_form(self.root.nametowidget(parent), self.current_template_file)
            
    def get_variable_values(self):
        """Get current values of all template variables"""
        values = {}
        for var_name, entry in self.current_variables:
            values[var_name] = entry.get()
        return values
    
    def create_category_tab(self, category):
        """Create a tab for a specific category"""
        tab_frame = ttk.Frame(self.notebook, name=f'tab_{category}')
        self.notebook.add(tab_frame, text=category)
        
        # Main content frame
        content_frame = ttk.Frame(tab_frame, padding="10", name='content')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Templates section
        templates_frame = ttk.Frame(content_frame, name='templates')
        templates_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(templates_frame, text="Templates:", font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        
        # Template buttons frame
        buttons_frame = ttk.Frame(templates_frame, name='buttons')
        buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        # New template button
        ttk.Button(buttons_frame, text="+ New Template", 
                  command=lambda: self.create_template_dialog(category),
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Print button frame (at bottom)
        print_frame = ttk.Frame(content_frame, name='print_frame')
        print_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        print_btn = ttk.Button(print_frame, text="Print Label", command=self.print_current_template, 
                              state=tk.DISABLED, style='Accent.TButton')
        print_btn.pack(side=tk.RIGHT)
        
        # Load templates for this category
        self.refresh_category_templates(tab_frame, category)
        
        return tab_frame
    
    def refresh_category_templates(self, tab_frame, category):
        """Refresh template buttons for a category"""
        templates = self.get_templates(category)
        
        # Find content frame
        content_frame = None
        for widget in tab_frame.winfo_children():
            if widget.winfo_name() == 'content':
                content_frame = widget
                break
        
        if not content_frame:
            return
            
        # Clear existing template widgets
        for child in content_frame.winfo_children():
            if child.winfo_name().startswith('template_'):
                child.destroy()
                
        if not templates:
            return
            
        # Create template widgets with inline variable inputs
        for i, (template_name, template_file) in enumerate(templates):
            # Container frame for each template with border
            template_container = ttk.Frame(content_frame, name=f'template_{i}', relief='ridge', borderwidth=2, padding="10")
            template_container.pack(fill=tk.X, pady=5, padx=10)
            
            # Top row: template button
            button_frame = ttk.Frame(template_container)
            button_frame.pack(fill=tk.X, pady=(0, 5))
            
            # Large template button
            btn = tk.Button(button_frame, text=template_name,
                           command=lambda tf=template_file: self.print_template_immediately(tf),
                           width=20, height=2, font=('TkDefaultFont', 12, 'bold'),
                           bg='lightblue', relief='raised', bd=2)
            btn.pack(side=tk.LEFT)
            
            # Check if template has variables
            template_content = self.read_template_file(template_file)
            variables = self.extract_variables(template_content)
            defaults = self.extract_defaults(template_content)
            
            if variables:
                # Variable inputs frame
                var_frame = ttk.Frame(template_container)
                var_frame.pack(fill=tk.X, pady=(5, 0))
                
                ttk.Label(var_frame, text="Variables:", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
                
                # Store variable entries for this template
                if template_file not in self.template_variable_widgets:
                    self.template_variable_widgets[template_file] = {}
                
                # Create variable input grid
                var_grid = ttk.Frame(var_frame)
                var_grid.pack(fill=tk.X, pady=2)
                
                # Arrange variables in rows of 2
                for j, var_name in enumerate(variables):
                    row = j // 2
                    col = j % 2
                    
                    var_container = ttk.Frame(var_grid)
                    var_container.grid(row=row, column=col, padx=5, pady=2, sticky='ew')
                    
                    ttk.Label(var_container, text=f"{var_name}:", width=12).pack(side=tk.LEFT)
                    
                    entry = ttk.Entry(var_container, width=20)
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
                    
                    # Set default value
                    default_value = ""
                    if var_name in defaults:
                        default_value = defaults[var_name]
                    elif var_name in self.hot_template_words:
                        default_value = self.hot_template_words[var_name]
                        
                    entry.insert(0, default_value)
                    
                    # Store the entry widget
                    self.template_variable_widgets[template_file][var_name] = entry
                
                # Configure grid columns to expand
                var_grid.columnconfigure(0, weight=1)
                var_grid.columnconfigure(1, weight=1)
            
    def select_template(self, template_file, tab_frame):
        """Select a template and create variable form"""
        self.current_template_file = template_file
        
        # Find content frame
        content_frame = None
        for child in tab_frame.winfo_children():
            if child.winfo_name() == 'content':
                content_frame = child
                break
                
        if content_frame:
            self.create_variable_form(content_frame, template_file)
            
            # Enable print button
            for child in content_frame.winfo_children():
                if child.winfo_name() == 'print_frame':
                    for button in child.winfo_children():
                        if isinstance(button, ttk.Button) and button.cget('text') == "Print Label":
                            button.configure(state=tk.NORMAL)
                            break
                    break
                    
        template_name = Path(template_file).stem
        self.update_status(f"Selected template: {template_name}")
        
    def get_template_variable_values(self, template_file):
        """Get variable values from inline widgets for a specific template"""
        variable_values = {}
        
        if template_file in self.template_variable_widgets:
            for var_name, entry_widget in self.template_variable_widgets[template_file].items():
                try:
                    variable_values[var_name] = entry_widget.get()
                except tk.TclError:
                    # Widget might have been destroyed, skip
                    pass
                    
        return variable_values
        
    def print_template_immediately(self, template_file):
        """Print template immediately using inline variable values if any"""
        template_content = self.read_template_file(template_file)
        if not template_content:
            messagebox.showerror("Error", f"Could not read template file: {template_file}")
            return
            
        # Get variable values from the inline inputs
        variable_values = self.get_template_variable_values(template_file)
        
        # Execute the template
        self.execute_template(template_file, variable_values)
        
    def print_current_template(self):
        """Print the currently selected template"""
        if not self.current_template_file:
            messagebox.showerror("Error", "Please select a template first")
            return
            
        variable_values = self.get_variable_values()
        self.execute_template(self.current_template_file, variable_values)
        
    def refresh_current_tab(self):
        """Refresh the currently selected tab"""
        current_tab = self.notebook.select()
        if current_tab:
            tab_name = self.notebook.tab(current_tab, 'text')
            tab_frame = self.notebook.nametowidget(current_tab)
            self.refresh_category_templates(tab_frame, tab_name)
            
    def refresh_tabs(self):
        """Refresh all tabs"""
        categories = self.get_categories()
        
        # Clear existing tabs
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
            
        # Create tabs for each category
        if not categories:
            categories = ["family", "office", "personal"]
            
        for category in categories:
            self.create_category_tab(category)
            
    def run(self):
        """Start the GUI application"""
        self.update_status("Label Printer GUI loaded - Select a template to begin")
        self.root.mainloop()

def main():
    """Main function to start the application"""
    app = LabelPrinterGUI()
    app.run()

if __name__ == "__main__":
    main()