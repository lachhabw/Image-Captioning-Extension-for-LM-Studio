import tkinter as tk
from tkinter import ttk  # Import ttk module for Progressbar
from tkinter import filedialog
from openai import OpenAI
import base64
import os
import threading
from configparser import ConfigParser

class CaptioningApp:
    def __init__(self, master):
        self.master = master
        master.title("Image Captioning Extension")
        self.source_folder_path = ""
        self.destination_folder_path = ""
        self.create_widgets()

        # Read configuration from the file
        config = ConfigParser()
        config.read('config.ini')
        self.client = OpenAI(base_url=config.get('OpenAI', 'base_url'), api_key=config.get('OpenAI', 'api_key'))

    def create_widgets(self):
        self.master.geometry("800x600")  # Set initial size
        self.master.grid_rowconfigure(3, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        # Source Folder
        self.source_label = tk.Label(self.master, text="Source Folder:")
        self.source_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        self.source_folder_entry = tk.Entry(self.master, width=40)
        self.source_folder_entry.grid(row=0, column=1, pady=10, sticky="we")

        self.source_folder_button = tk.Button(self.master, text="Browse", command=self.select_source_folder)
        self.source_folder_button.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        # Destination Folder
        self.destination_label = tk.Label(self.master, text="Destination Folder:")
        self.destination_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")

        self.destination_folder_entry = tk.Entry(self.master, width=40)
        self.destination_folder_entry.grid(row=1, column=1, pady=10, sticky="we")

        self.destination_folder_button = tk.Button(self.master, text="Browse", command=self.select_destination_folder)
        self.destination_folder_button.grid(row=1, column=2, padx=10, pady=10, sticky="w")

        # Configure grid column weights for centering
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(2, weight=1)

        # Captioning Button
        self.caption_button = tk.Button(self.master, text="Run Captioning", command=self.run_captioning_thread)
        self.caption_button.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

        # Debug Text
        self.debug_text = tk.Text(self.master, height=10, width=50, wrap=tk.WORD, bg="black", fg="white", font=("Consolas", 10))
        self.debug_text.grid(row=3, column=0, columnspan=3, pady=10, sticky="nsew")

        # Configure tags for styling
        self.debug_text.tag_configure("success_message", foreground="green")
        self.debug_text.tag_configure("error_message", foreground="red")
        self.debug_text.tag_configure("finish_message", foreground="#00FFFF")

        # Make the debug text read-only and scrollable
        self.debug_text.config(state=tk.DISABLED)
        scrollbar = tk.Scrollbar(self.master, command=self.debug_text.yview)
        scrollbar.grid(row=3, column=3, sticky="nsew")
        self.debug_text.config(yscrollcommand=scrollbar.set)

    def select_source_folder(self):
        folder_path = filedialog.askdirectory()
        self.source_folder_entry.delete(0, tk.END)
        self.source_folder_entry.insert(0, folder_path)
        self.source_folder_path = folder_path

    def select_destination_folder(self):
        folder_path = filedialog.askdirectory()
        self.destination_folder_entry.delete(0, tk.END)
        self.destination_folder_entry.insert(0, folder_path)
        self.destination_folder_path = folder_path


    def run_captioning_thread(self):
        # Disable the captioning button
        self.caption_button.config(state=tk.DISABLED)
        # Start a new thread for captioning
        new_thread = threading.Thread(target=self.run_captioning)
        new_thread.start()

    def run_captioning(self):
        # Get folders paths
        self.source_folder_path = self.source_folder_entry.get()
        self.destination_folder_path = self.destination_folder_entry.get()
        progress_bar = None

        if not self.source_folder_path or not self.destination_folder_path:
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, "Please select both source and destination folders.\n", "error_message")
            self.debug_text.config(state=tk.DISABLED)
            self.caption_button.config(state=tk.NORMAL)
            return
        
        try: 
            # Check the existance of folders
            os.listdir(self.destination_folder_path)
            files = os.listdir(self.source_folder_path)
            n_files = len(files)
            # Set up progress bar
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(self.master, variable=progress_var, mode="determinate", maximum=100)
            progress_bar.grid(row=4, column=0, columnspan=3, padx=2, pady=5, sticky="nsew")
            # Start captioning
            for i, file in enumerate(files):
                file_path = os.path.join(self.source_folder_path, file)
                destination_path = os.path.join(self.destination_folder_path, f"{file.split('.')[0]}.txt")
                img = self.load_img64(file_path)
                if not img:
                    continue

                captions = self.caption_server(img)
                if not captions:
                    self.debug_text.config(state=tk.NORMAL)
                    self.debug_text.insert(tk.END, "- Failure: ", "error_message")
                    self.debug_text.insert(tk.END, f"Unable to caption the image '{file}'. Check if the image is valid, with a supported format (jpeg, jpg, png, are recommended).\n")
                    self.debug_text.config(state=tk.DISABLED)
                else:
                    with open(destination_path, "w") as f:
                        f.write(captions)
                    self.debug_text.config(state=tk.NORMAL)
                    self.debug_text.insert(tk.END, f"- Success: ", "success_message")
                    self.debug_text.insert(tk.END, f"Image '{file}' has been captioned and the result saved to '{destination_path}'.\n")
                    self.debug_text.config(state=tk.DISABLED)

                # Update progress bar
                progress_value = (i + 1) / n_files * 100
                progress_var.set(progress_value)
                self.master.update_idletasks()

            # Add a green message indicating the process has finished
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, "Captioning process has finished.\n", "finish_message")
            self.debug_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"Error: {e}\n", "error_message")
            self.debug_text.config(state=tk.DISABLED)
        
        finally:
            # Enable the captioning button after the process finishes
            self.caption_button.config(state=tk.NORMAL)
            # Destroy progress bar if it exists
            if progress_bar:
                progress_bar.destroy()

    def load_img64(self, file_path):
        base64_image = ""
        try:
            image = open(file_path, "rb").read()
            base64_image = base64.b64encode(image).decode("utf-8")
        except Exception as e:
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"Couldn't read the file: {file_path}\n", "error_message")
            self.debug_text.config(state=tk.DISABLED)
        return base64_image

    def caption_server(self, base64_image):
        completion = self.client.chat.completions.create(
            model="local-model",  # not used
            messages=[
                {
                    "role": "system",
                    "content": "This is a chat between a user and an assistant. The assistant is helping the user to describe an image.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe in detail what this image depicts in as much detail as possible without mistakes."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
            stream=True
        )

        captions = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                caption = chunk.choices[0].delta.content
                captions += caption
        return captions.strip()


if __name__ == "__main__":
    root = tk.Tk()
    app = CaptioningApp(root)
    root.mainloop()
