import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
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
        
        # Create queue for handling output
        self.queue = queue.Queue()
        
        self.watch_process = None
        self.watching = False
        
        self.setup_gui()
        self.setup_output_handling()

    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.LabelFrame(main_frame, text="Available Scripts", padding="5")
        buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=5, pady=5)
        
        # Script buttons
        ttk.Button(buttons_frame, text="Pull Data", command=lambda: self.run_script("pullData.py")).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(buttons_frame, text="Push Data", command=lambda: self.run_script("pushData.py")).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(buttons_frame, text="Calculate Distributions", command=lambda: self.run_script("calculate_distributions.py")).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(buttons_frame, text="Assign Timestamps", command=lambda: self.run_script("assign_timestamps.py")).grid(row=0, column=3, padx=5, pady=2)
        
        # Clear and Save buttons
        ttk.Button(buttons_frame, text="Clear Output", command=self.clear_output).grid(row=0, column=4, padx=5, pady=2)
        ttk.Button(buttons_frame, text="Save Output", command=self.save_output).grid(row=0, column=5, padx=5, pady=2)
        
        # Add Watch Changes toggle button
        self.watch_button = ttk.Button(
            buttons_frame, 
            text="Start Watching", 
            command=self.toggle_watch
        )
        self.watch_button.grid(row=0, column=6, padx=5, pady=2)
        
        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=100, height=30)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
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

    def run_script(self, script_name):
        """Run a Python script in a separate thread"""
        self.status_var.set(f"Running {script_name}...")
        self.output_text.insert(tk.END, f"\n{'='*50}\nRunning {script_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n")
        
        def run():
            try:
                script_path = os.path.join("scripts", script_name)
                process = subprocess.Popen(
                    ["python", script_path],
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
            self.watch_button.configure(text="Stop Watching")
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
            self.watch_button.configure(text="Start Watching")
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
        self.watch_button.configure(text="Start Watching")
        self.status_var.set("Watch process ended")

def main():
    root = tk.Tk()
    app = ScriptGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
