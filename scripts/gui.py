import tkinter as tk
from tkinter import ttk, scrolledtext, font, Canvas
import subprocess
import threading
import time

def configure_styles():
    style = ttk.Style()
    
    # Configure dark theme base
    style.theme_use('clam')  # Use clam theme as base
    
    # Configure colors
    style.configure(".",
        background="#1e1e1e",
        foreground="#ffffff",
        fieldbackground="#1e1e1e",
        troughcolor="#2d2d2d"
    )
    
    # Button style
    style.configure("Metallic.TButton",
        background="#2d2d2d",
        foreground="#ffffff",
        padding=(10, 5),
        font=("Segoe UI", 9, "bold")
    )
    style.map("Metallic.TButton",
        background=[("active", "#3d3d3d"), ("pressed", "#1d1d1d")],
        foreground=[("active", "#ffffff"), ("pressed", "#ffffff")]
    )
    
    # Toggle button style
    style.configure("MetallicToggle.TButton",
        background="#2d2d2d",
        foreground="#ffffff",
        padding=(15, 5),
        font=("Segoe UI", 9, "bold")
    )
    style.map("MetallicToggle.TButton",
        background=[
            ("pressed", "#1d1d1d"),
            ("active", "#3d3d3d"),
            ("!disabled", "#2d2d2d"),
            ("selected", "#404da1")
        ],
        foreground=[("pressed", "#ffffff"), ("active", "#ffffff")]
    )
    
    # Frame style
    style.configure("Metallic.TFrame",
        background="#1e1e1e"
    )
    
    # LabelFrame style
    style.configure("Metallic.TLabelframe",
        background="#1e1e1e",
        foreground="#ffffff"
    )
    style.configure("Metallic.TLabelframe.Label",
        background="#1e1e1e",
        foreground="#ffffff",
        font=("Segoe UI", 9, "bold")
    )
import sys
import queue
import os
from datetime import datetime
from threading import Thread
import signal

class RedirectText:
    def __init__(self, text_widget, queue):
        self.queue = queue
        self.text_widget = text_widget

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

class ScriptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UBC Scripts Manager")
        self.root.geometry("1000x600")
        self.root.configure(bg="#1a1a1a")  # Dark background
        
        # Configure styles
        configure_styles()
        
        # Create queue for handling output
        self.queue = queue.Queue()
        
        self.watch_process = None
        self.watching = False
        
        self.setup_gui()
        self.setup_output_handling()
        
    def cleanup(self):
        """Clean up resources before exit"""
        if self.watching and self.watch_process:
            self.toggle_watch()  # Stop watching process
        
        # Restore original stdout
        sys.stdout = sys.__stdout__
        
        # Destroy the root window
        if self.root:
            self.root.destroy()

    def setup_gui(self):
        # Configure root
        self.root.configure(bg="#1e1e1e")
        
        # Main container with metallic frame
        main_frame = ttk.Frame(self.root, padding="10", style="Metallic.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame with metallic effect
        buttons_frame = ttk.LabelFrame(
            main_frame,
            text="Available Scripts",
            padding="8",
            style="Metallic.TLabelframe"
        )
        buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=5, pady=5)
        
        # Create two rows of buttons for better layout
        def create_metallic_button(frame, text, command, row, column):
            btn = ttk.Button(
                frame,
                text=text,
                command=command,
                style="Metallic.TButton",
                width=20
            )
            btn.grid(row=row, column=column, padx=4, pady=4)
            return btn

        # First row of buttons
        create_metallic_button(buttons_frame, "Pull Data", lambda: self.run_script("pullData.py"), 0, 0)
        create_metallic_button(buttons_frame, "Push Data", lambda: self.run_script("pushData.py"), 0, 1)
        create_metallic_button(buttons_frame, "Calculate Distributions", lambda: self.run_script("calculate_distributions.py"), 0, 2)
        create_metallic_button(buttons_frame, "List Relations", lambda: self.run_script("list_swarm_relations.py"), 0, 3)

        # Second row of buttons
        create_metallic_button(buttons_frame, "Send Recap", lambda: self.run_script("send_recap.py"), 1, 0)
        create_metallic_button(buttons_frame, "Clear Output", self.clear_output, 1, 1)
        create_metallic_button(buttons_frame, "Save Output", self.save_output, 1, 2)
        
        # Watch toggle button with metallic effect
        self.watch_button = ttk.Button(
            buttons_frame,
            text="⚪ Watch Changes",
            command=self.toggle_watch,
            style="MetallicToggle.TButton"
        )
        self.watch_button.grid(row=1, column=3, padx=6, pady=3)
        
        # Conversation Generator Frame
        conv_frame = ttk.LabelFrame(
            main_frame,
            text="Conversation Generator",
            padding="8",
            style="Metallic.TLabelframe"
        )
        conv_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Collaboration Selector
        collab_label = ttk.Label(
            conv_frame,
            text="Select Collaboration:",
            style="Metallic.TLabel"
        )
        collab_label.grid(row=0, column=0, padx=4, pady=4, sticky=tk.W)

        self.collab_var = tk.StringVar()
        self.collab_selector = ttk.Combobox(
            conv_frame,
            textvariable=self.collab_var,
            style="Metallic.TCombobox",
            width=40,
            state="readonly"
        )
        self.collab_selector.grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)
        self.load_collaborations()

        # Prompt Text Box
        prompt_label = ttk.Label(
            conv_frame,
            text="Enter Prompt:",
            style="Metallic.TLabel"
        )
        prompt_label.grid(row=1, column=0, padx=4, pady=4, sticky=tk.W)

        self.prompt_text = tk.Text(
            conv_frame,
            height=3,
            width=60,
            bg="#202020",
            fg="#e0e0e0",
            insertbackground="#ffffff",
            relief="flat",
            borderwidth=1,
            font=("Consolas", 10)
        )
        self.prompt_text.grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)

        # Generate Button
        generate_button = ttk.Button(
            conv_frame,
            text="Generate Conversation",
            command=self.generate_conversation,
            style="Metallic.TButton"
        )
        generate_button.grid(row=2, column=1, padx=4, pady=4, sticky=tk.E)

        # Output area with better contrast
        output_frame = ttk.LabelFrame(
            main_frame,
            text="Output",
            padding="8",
            style="Metallic.TLabelframe"
        )
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=6, pady=6)
        
        # Enhanced output text area
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            width=100,
            height=30,
            bg="#202020",
            fg="#e0e0e0",
            insertbackground="#ffffff",
            selectbackground="#404040",
            selectforeground="#ffffff",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=1,
            padx=10,
            pady=10
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Enhanced status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            style="Metallic.TLabel",
            relief="sunken",
            padding=(8, 4)
        )
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=6, pady=4)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def setup_output_handling(self):
        # Redirect stdout to the Text widget
        sys.stdout = RedirectText(self.output_text, self.queue)
        self.root.after(100, self.check_queue)

    def check_queue(self):
        """Check if there's something in the queue"""
        while True:
            try:
                text = self.queue.get_nowait()
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
                self.queue.task_done()
            except queue.Empty:
                break
        self.root.after(100, self.check_queue)

    def run_script(self, script_command):
        """Run a Python script in a separate thread"""
        self.status_var.set(f"Running {script_command}...")
        self.output_text.insert(tk.END, f"\n{'='*50}\nRunning {script_command} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n")
        
        def run():
            try:
                # Split the command into parts while preserving quoted strings
                import shlex
                command_parts = shlex.split(script_command)
                script_path = os.path.join("scripts", command_parts[0])
                
                # Construct the command list
                command = ["python", script_path] + command_parts[1:]
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.queue.put(output)
                
                self.queue.put(f"\nScript completed with return code: {process.poll()}\n")
                self.status_var.set("Ready")
            except Exception as e:
                self.queue.put(f"\nError running script: {str(e)}\n")
                self.status_var.set("Error")
        
        threading.Thread(target=run, daemon=True).start()

    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, tk.END)

    def save_output(self):
        """Save the output to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}.log"
        with open(filename, "w") as f:
            f.write(self.output_text.get(1.0, tk.END))
        self.status_var.set(f"Output saved to {filename}")

    def toggle_watch(self):
        """Toggle the watch_changes script on/off"""
        if not self.watching:
            # Start watching
            self.watching = True
            self.watch_button.configure(
                text="⚫ Watching...", 
                style="MetallicToggle.TButton"
            )
            self.status_var.set("Started watching for changes...")
            self.output_text.insert(tk.END, "\n=== Started watching for changes ===\n")
            
            def watch_runner():
                try:
                    process = subprocess.Popen(
                        ["python", "scripts/watch_changes.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                    self.watch_process = process
                    
                    while self.watching:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            self.queue.put(output)
                            
                    if self.watching:  # If we didn't manually stop
                        self.queue.put("\nWatch process ended unexpectedly\n")
                        self.watching = False
                        self.root.after(0, self._update_watch_button)
                except Exception as e:
                    self.queue.put(f"\nError in watch process: {str(e)}\n")
                    self.watching = False
                    self.root.after(0, self._update_watch_button)

            Thread(target=watch_runner, daemon=True).start()
            
        else:
            # Stop watching
            self.watching = False
            self.watch_button.configure(
                text="⚪ Watch Changes", 
                style="MetallicToggle.TButton"
            )
            self.status_var.set("Stopped watching for changes")
            self.output_text.insert(tk.END, "\n=== Stopped watching for changes ===\n")
            
            if self.watch_process:
                try:
                    # Send SIGTERM to the process group
                    if os.name == 'nt':  # Windows
                        self.watch_process.terminate()
                    else:  # Unix/Linux/Mac
                        os.killpg(os.getpgid(self.watch_process.pid), signal.SIGTERM)
                except Exception as e:
                    print(f"Error stopping watch process: {e}")
                self.watch_process = None

    def _update_watch_button(self):
        """Update watch button state - called from non-main thread"""
        self.watch_button.configure(
            text="⚪ Watch Changes", 
            style="MetallicToggle.TButton"
        )
        self.status_var.set("Watch process ended")

    def load_collaborations(self):
        """Load available collaborations into the selector"""
        try:
            import glob
            import json
            collab_files = glob.glob('data/collaborations/*.json')
            collabs = []
            for file in collab_files:
                with open(file, 'r') as f:
                    data = json.load(f)
                    desc = f"{data.get('collaborationId')} - {data.get('clientSwarmId')} with {data.get('providerSwarmId')}"
                    collabs.append(desc)
            self.collab_selector['values'] = sorted(collabs)
            if collabs:
                self.collab_selector.set(collabs[0])
        except Exception as e:
            print(f"Error loading collaborations: {e}")

    def generate_conversation(self):
        """Generate conversation based on selected collaboration and prompt"""
        collab_id = self.collab_var.get().split(' - ')[0]
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        
        if not prompt:
            self.status_var.set("Please enter a prompt")
            return
            
        self.status_var.set("Generating conversation...")
        self.run_script(f"generate_conversation.py {collab_id} \"{prompt}\"")

def main():
    root = tk.Tk()
    app = ScriptGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down gracefully...")
        app.cleanup()
    finally:
        # Ensure cleanup happens even if other exceptions occur
        app.cleanup()

if __name__ == "__main__":
    main()
