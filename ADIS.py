import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk, messagebox
import random
import datetime
import urllib.request
import numpy as np
from PIL import Image, ImageTk
import json
import os
from typing import Dict, List, Tuple, Optional
import time

class Color:
    def __init__(self, rgb: Tuple[int, int, int], check_direction: str, activation_colors: List[Tuple[int, int, int]]):
        self.rgb = rgb
        self.check_direction = check_direction  # 'left', 'right', 'up', 'down'
        self.activation_colors = activation_colors

class ADISFile:
    def __init__(self, resolution: int, color_depth: int, iteration_speed: int,
                 last_time: int = 0, now_time: int = 0, iteration_count: int = 0):
        self.resolution = resolution
        self.color_depth = color_depth
        self.iteration_speed = iteration_speed
        self.last_time = last_time
        self.now_time = now_time
        self.iteration_count = iteration_count
        self.color_set: List[Color] = []
        self.image_array = np.zeros((resolution, resolution, 3), dtype=np.uint8)
        self.encrypted_string: Optional[str] = None
        self.key_image: Optional[np.ndarray] = None
        
    def generate_random_colors(self) -> None:
        """Generate random unique colors for the color set"""
        used_colors = set()
        directions = ['left', 'right', 'up', 'down']
        
        for _ in range(self.color_depth):
            # Generate unique RGB color
            while True:
                rgb = (random.randint(0, 255), 
                      random.randint(0, 255),
                      random.randint(0, 255))
                if rgb not in used_colors:
                    used_colors.add(rgb)
                    break
            # Generate activation colors
            available_colors = list(used_colors - {rgb})
            if len(available_colors) >= 1:
                num_activation_colors = random.randint(1, min(2, len(available_colors)))
                activation_colors = random.sample(available_colors, num_activation_colors)
            else:
                activation_colors = []

            # Assign random check direction
            check_direction = random.choice(directions)
            
            self.color_set.append(Color(rgb, check_direction, activation_colors))

    def initialize_image(self) -> None:
        """Fill image with random colors from color set"""
        for i in range(self.resolution):
            for j in range(self.resolution):
                color = random.choice(self.color_set).rgb
                self.image_array[i, j] = color

    def get_check_position(self, x: int, y: int, direction: str) -> Tuple[int, int]:
        """Get the position to check based on direction and handling wraparound"""
        if direction == 'right':
            return (x, (y + 1) % self.resolution)
        elif direction == 'left':
            return (x, (y - 1) % self.resolution)
        elif direction == 'up':
            return ((x - 1) % self.resolution, y)
        else:  # down
            return ((x + 1) % self.resolution, y)

    def iterate_once(self) -> None:
        """Perform one iteration of the color rules"""
        new_array = np.copy(self.image_array)
        
        for x in range(self.resolution):
            for y in range(self.resolution):
                current_color = tuple(self.image_array[x, y])
                
                # Find the color object for the current pixel
                color_obj = next((c for c in self.color_set if c.rgb == current_color), None)
                if color_obj:
                    check_x, check_y = self.get_check_position(x, y, color_obj.check_direction)
                    neighbor_color = tuple(self.image_array[check_x, check_y])
                    
                    if neighbor_color in color_obj.activation_colors:
                        # Swap colors
                        new_array[x, y] = self.image_array[check_x, check_y]
                        new_array[check_x, check_y] = self.image_array[x, y]
        
        self.image_array = new_array

    def get_internet_time(self) -> int:
        """Get current internet time in minutes since epoch"""
        try:
            response = urllib.request.urlopen('http://worldtimeapi.org/api/timezone/Etc/UTC')
            data = json.loads(response.read())
            return int(data['unixtime'] / 60)  # Convert to minutes
        except:
            return int(time.time() / 60)  # Fallback to local time

    def update_times(self) -> None:
        """Update last and now times"""
        current_time = self.get_internet_time()
        if self.last_time == 0:
            self.last_time = current_time
            self.now_time = self.last_time + self.iteration_speed
        else:
            self.last_time = self.now_time
            self.now_time = current_time

    def iterate_required(self) -> None:
        """Perform required iterations based on time difference"""
        time_diff = self.now_time - self.last_time
        iterations_needed = time_diff // self.iteration_speed
        
        for _ in range(iterations_needed):
            self.iterate_once()
            self.iteration_count += 1

    def generate_key(self) -> str:
        """Generate encryption key from image array"""
        binary = ''
        for x in range(self.resolution):
            for y in range(self.resolution):
                # Convert RGB values to binary representation
                for value in self.image_array[x, y]:
                    binary += format(value, '08b')
        
        # Compress consecutive bits
        compressed = ''
        current_bit = binary[0]
        count = 1
        
        for bit in binary[1:]:
            if bit == current_bit:
                count += 1
            else:
                compressed += f"{current_bit}{count}"
                current_bit = bit
                count = 1
        
        compressed += f"{current_bit}{count}"
        return compressed
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt string using the generated key"""
        key = self.generate_key()
        key_bytes = [int(key[i:i+2], 10) for i in range(0, len(key), 2)]
        text_bytes = text.encode('utf-8')
        encrypted_bytes = bytes(a ^ b for a, b in zip(text_bytes, key_bytes * (len(text_bytes) // len(key_bytes) + 1)))
        return encrypted_bytes.hex()


    def decrypt_string(self, encrypted_hex: str) -> str:
        """Decrypt string using the generated key"""
        key = self.generate_key()
        key_bytes = [int(key[i:i+2], 10) for i in range(0, len(key), 2)]
        encrypted_bytes = bytes.fromhex(encrypted_hex)
        decrypted_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, key_bytes * (len(encrypted_bytes) // len(key_bytes) + 1)))
        return decrypted_bytes.decode('utf-8')

class ADISEncryptionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ADIS Encryption Program")
        self.setup_ui()
        self.canvas = None  # Canvas for displaying ADIS image
        self.adis_image_label = None  # Label for holding the ADIS image
    
    def setup_ui(self):
        # Main menu buttons
        tk.Button(self.root, text="Create New ADIS", command=self.show_new_adis_menu).pack(pady=5)
        tk.Button(self.root, text="Use Existing ADIS", command=self.show_existing_adis_menu).pack(pady=5)
        

    def show_new_adis_menu(self):
        new_window = tk.Toplevel(self.root)
        new_window.title("Create New ADIS")
        
        # Resolution selection
        tk.Label(new_window, text="Resolution:").pack()
        resolution_var = tk.StringVar()
        resolutions = ['4', '8', '16', '32', '64', '128', '256', '512', '1024']
        ttk.Combobox(new_window, textvariable=resolution_var, values=resolutions).pack()
        
        # Color depth selection
        tk.Label(new_window, text="Color Depth:").pack()
        color_depth_var = tk.StringVar()
        color_depths = ['4', '8', '16', '32']
        ttk.Combobox(new_window, textvariable=color_depth_var, values=color_depths).pack()
        
        # Iteration speed
        tk.Label(new_window, text="Iteration Speed (minutes):").pack()
        iteration_speed_entry = tk.Entry(new_window)
        iteration_speed_entry.pack()
        
        # File name
        tk.Label(new_window, text="File Name:").pack()
        file_name_entry = tk.Entry(new_window)
        file_name_entry.pack()
        
        # String to encrypt
        tk.Label(new_window, text="String to Encrypt:").pack()
        string_entry = tk.Entry(new_window)
        string_entry.pack()
        
        def create_adis():
            try:
                adis = ADISFile(
                    resolution=int(resolution_var.get()),
                    color_depth=int(color_depth_var.get()),
                    iteration_speed=int(iteration_speed_entry.get())
                )
                
                adis.generate_random_colors()
                adis.initialize_image()
                adis.update_times()
                adis.iterate_required()
                
                encrypted = adis.encrypt_string(string_entry.get())
                adis.encrypted_string = encrypted
                adis.key_image = np.copy(adis.image_array)
                
                # Save ADIS file
                filename = f"{file_name_entry.get()}.adis"
                self.save_adis(adis, filename)
                
                messagebox.showinfo("Success", f"Encrypted string: {encrypted}")
                new_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        tk.Button(new_window, text="Create", command=create_adis).pack(pady=10)
        
    def show_existing_adis_menu(self):
        existing_window = tk.Toplevel(self.root)
        existing_window.title("Use Existing ADIS")
        
        # File selection
        tk.Label(existing_window, text="Select ADIS File:").pack()
        file_var = tk.StringVar()
        files = [f for f in os.listdir() if f.endswith('.adis')]
        file_dropdown = ttk.Combobox(existing_window, textvariable=file_var, values=files)
        file_dropdown.pack()
        
        # Create a canvas to display the image
        self.canvas = tk.Canvas(existing_window, width=256, height=256)  # Adjust dimensions as needed
        self.canvas.pack(pady=10)
        
        # Add button to select the ADIS file and display image
        def show_encrypt_decrypt_menu():
            adis_file = self.load_adis(file_var.get())
            if not adis_file:
                messagebox.showerror("Error", "Could not load ADIS file")
                return

            # Display the ADIS image
            self.display_adis_image(adis_file.image_array)

            ed_window = tk.Toplevel(existing_window)
            ed_window.title("Encrypt/Decrypt")
            
            def encrypt_string():
                try:
                    string = tk.simpledialog.askstring("Input", "Enter string to encrypt:")
                    if string:
                        encrypted = adis_file.encrypt_string(string)
                        adis_file.encrypted_string = encrypted
                        adis_file.key_image = np.copy(adis_file.image_array)
                        self.save_adis(adis_file, file_var.get())
                        messagebox.showinfo("Success", f"Encrypted string: {encrypted}")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            def decrypt_string():
                try:
                    if not adis_file.encrypted_string:
                        messagebox.showerror("Error", "No encrypted string found")
                        return
                    
                    decrypted = adis_file.decrypt_string(adis_file.encrypted_string)
                    messagebox.showinfo("Success", f"Decrypted string: {decrypted}")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            tk.Button(ed_window, text="Encrypt", command=encrypt_string).pack(pady=5)
            tk.Button(ed_window, text="Decrypt", command=decrypt_string).pack(pady=5)
        
        tk.Button(existing_window, text="Select", command=show_encrypt_decrypt_menu).pack(pady=10)
    
    def display_adis_image(self, image_array: np.ndarray):
        """Convert and display ADIS image array in the Tkinter Canvas."""
        # Convert the image array to a PIL Image, then to ImageTk.PhotoImage for display
        img = Image.fromarray(image_array)
        img = img.resize((256, 256), Image.NEAREST)  # Resize for the canvas display if necessary
        photo_img = ImageTk.PhotoImage(img)
        
        # Clear the canvas and display the new image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=photo_img)
        self.canvas.image = photo_img  # Keep a reference to avoid garbage collection
    
    def save_adis(self, adis: ADISFile, filename: str) -> None:
        """Save ADIS file to disk"""
        data = {
            'resolution': adis.resolution,
            'color_depth': adis.color_depth,
            'iteration_speed': adis.iteration_speed,
            'last_time': adis.last_time,
            'now_time': adis.now_time,
            'iteration_count': adis.iteration_count,
            'image_array': adis.image_array.tolist(),
            'encrypted_string': adis.encrypted_string,
            'key_image': adis.key_image.tolist() if adis.key_image is not None else None,
            'color_set': [(c.rgb, c.check_direction, c.activation_colors) for c in adis.color_set]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
    
    def load_adis(self, filename: str) -> Optional[ADISFile]:
        """Load ADIS file from disk"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            adis = ADISFile(
                resolution=data['resolution'],
                color_depth=data['color_depth'],
                iteration_speed=data['iteration_speed'],
                last_time=data['last_time'],
                now_time=data['now_time'],
                iteration_count=data['iteration_count']
            )
            
            adis.image_array = np.array(data['image_array'], dtype=np.uint8)
            adis.encrypted_string = data['encrypted_string']
            adis.key_image = np.array(data['key_image'], dtype=np.uint8) if data['key_image'] else None
            
            for rgb, direction, activation_colors in data['color_set']:
                adis.color_set.append(Color(tuple(rgb), direction, [tuple(c) for c in activation_colors]))
            
            return adis
        except Exception as e:
            print(f"Error loading ADIS file: {e}")
            return None

    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ADISEncryptionApp()
    app.run()