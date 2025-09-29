import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from arrangLocation import generate_number_letter_report
from runRobot import send_start, on_close
import pandas as pd
from arrangeCsv import arrange_csv
from useTreadExcutor import seperateEPC, arrangeCSV
import csv
import threading
import time
import math
import random
import os

class ModernButton(tk.Canvas):

    

    def __init__(self, parent, text, command, **kwargs):
        self.bg_color = kwargs.get('bg_color', '#E8E8E8')
        self.hover_color = kwargs.get('hover_color', "#5D5C5C")
        self.text_color = kwargs.get('text_color', "#061313")
        self.font = kwargs.get('font', ('Segoe UI', 12))
        self.command = command
        self.text = text
        self.csv_file = None
        self.location = None

        
        super().__init__(parent, highlightthickness=0, 
                        height=60, bg=parent['bg'])
        
        self.bind('<Button-1>', self.on_click)
        self.bind('<Enter>', self.on_hover)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Configure>', self.on_configure)
        
        self.draw_button()
    
    def draw_button(self):
        self.delete('all')
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            self.after(10, self.draw_button)
            return
            
        # Draw rounded rectangle with gradient effect
        self.create_rounded_rectangle(4, 4, width-4, height-4, 
                                    radius=25, fill=self.bg_color, 
                                    outline='#C0C0C0', width=1)
        
        # Add subtle inner shadow
        self.create_rounded_rectangle(6, 6, width-6, height-6, 
                                    radius=23, fill='', 
                                    outline='#F5F5F5', width=1)
        
        # Draw text with icon
        self.create_text(width//2, height//2, text=self.text, 
                        fill=self.text_color, font=self.font, anchor='center')
    
    def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = []
        for x, y in [(x1, y1 + radius), (x1, y1), (x1 + radius, y1),
                     (x2 - radius, y1), (x2, y1), (x2, y1 + radius),
                     (x2, y2 - radius), (x2, y2), (x2 - radius, y2),
                     (x1 + radius, y2), (x1, y2), (x1, y2 - radius)]:
            points.extend([x, y])
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_configure(self, event):
        self.draw_button()
    
    def on_hover(self, event):
        self.bg_color = self.hover_color
        self.draw_button()
    
    def on_leave(self, event):
        self.bg_color = '#E8E8E8'
        self.draw_button()
    
    def on_click(self, event):
        if self.command:
            self.command()

class AnimationCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.robot_x = 50
        self.robot_y = 120
        self.robot_id = None
        self.path_ids = []
        self.is_running = False
        self.animation_thread = None
        self.robot_angle = 0
        self.path_points = []
        self.waypoints = []
        
    def draw_robot(self):
        if self.robot_id:
            self.delete(self.robot_id)
            for item in self.path_ids:
                self.delete(item)
            self.path_ids = []
        
        # Draw path/line for the robot to follow
        if not self.waypoints:
            width = self.winfo_width()
            if width > 100:
                # Create a straight horizontal path for the robot to follow
                self.waypoints = []
                total_points = 60  # More points for smoother movement
                y = 120  # Constant y-value for straight line
                for i in range(total_points):
                    progress = i / total_points
                    x = 50 + (width - 100) * progress
                    self.waypoints.append((x, y))
                # Draw the path
                path_id = self.create_line(
                    [point for point in self.waypoints],
                    fill='#D1D5DB', width=12, smooth=True, 
                    joinstyle=tk.ROUND, capstyle=tk.ROUND
                )
                self.path_ids.append(path_id)
                # Add a more visible center line
                center_path_id = self.create_line(
                    [point for point in self.waypoints],
                    fill='#94A3B8', width=2, smooth=True, 
                    dash=(5, 3), joinstyle=tk.ROUND, capstyle=tk.ROUND
                )
                self.path_ids.append(center_path_id)
                # Add start and end markers
                start_marker = self.create_oval(
                    self.waypoints[0][0]-8, self.waypoints[0][1]-8,
                    self.waypoints[0][0]+8, self.waypoints[0][1]+8,
                    fill='#22C55E', outline='white', width=2
                )
                self.path_ids.append(start_marker)
                end_marker = self.create_oval(
                    self.waypoints[-1][0]-8, self.waypoints[-1][1]-8,
                    self.waypoints[-1][0]+8, self.waypoints[-1][1]+8,
                    fill='#EF4444', outline='white', width=2
                )
                self.path_ids.append(end_marker)
        
        # Calculate robot angle based on current position and next position
        if self.is_running and len(self.waypoints) > 1:
            # Find the closest waypoint to current position
            min_dist = float('inf')
            closest_idx = 0
            for i, (x, y) in enumerate(self.waypoints):
                dist = (x - self.robot_x)**2 + (y - self.robot_y)**2
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            # Look ahead to calculate angle
            next_idx = min(closest_idx + 1, len(self.waypoints) - 1)
            if next_idx > closest_idx:
                dx = self.waypoints[next_idx][0] - self.robot_x
                dy = self.waypoints[next_idx][1] - self.robot_y
                self.robot_angle = math.atan2(dy, dx)
        
        # Draw the robot base (a rounded rectangle)
        robot_width = 28
        robot_height = 20
        
        # Create rounded rectangle for robot body
        x1 = self.robot_x - robot_width/2
        y1 = self.robot_y - robot_height/2
        x2 = self.robot_x + robot_width/2
        y2 = self.robot_y + robot_height/2
        
        # Rotate coordinates around robot center
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        rotated_corners = []
        for x, y in corners:
            dx = x - self.robot_x
            dy = y - self.robot_y
            rx = dx * math.cos(self.robot_angle) - dy * math.sin(self.robot_angle)
            ry = dx * math.sin(self.robot_angle) + dy * math.cos(self.robot_angle)
            rotated_corners.append((self.robot_x + rx, self.robot_y + ry))
        
        # Create the robot body
        robot_body = self.create_polygon(
            rotated_corners,
            fill='#3B82F6', outline='#1E40AF', width=2,
            smooth=True
        )
        self.path_ids.append(robot_body)
        
        # Draw wheels
        wheel_width = 6
        wheel_height = 10
        wheel_offset = robot_width/2 + 2
        
        # Left wheel
        left_wheel_x = self.robot_x - wheel_offset * math.cos(self.robot_angle + math.pi/2)
        left_wheel_y = self.robot_y - wheel_offset * math.sin(self.robot_angle + math.pi/2)
        left_wheel = self.create_rectangle(
            left_wheel_x - wheel_width/2, left_wheel_y - wheel_height/2,
            left_wheel_x + wheel_width/2, left_wheel_y + wheel_height/2,
            fill='#111827', outline='',
            width=1
        )
        self.path_ids.append(left_wheel)
        
        # Right wheel
        right_wheel_x = self.robot_x + wheel_offset * math.cos(self.robot_angle + math.pi/2)
        right_wheel_y = self.robot_y + wheel_offset * math.sin(self.robot_angle + math.pi/2)
        right_wheel = self.create_rectangle(
            right_wheel_x - wheel_width/2, right_wheel_y - wheel_height/2,
            right_wheel_x + wheel_width/2, right_wheel_y + wheel_height/2,
            fill='#111827', outline='',
            width=1
        )
        self.path_ids.append(right_wheel)
        
        # Add sensor at front
        sensor_x = self.robot_x + (robot_width/2 - 2) * math.cos(self.robot_angle)
        sensor_y = self.robot_y + (robot_width/2 - 2) * math.sin(self.robot_angle)
        sensor = self.create_oval(
            sensor_x - 3, sensor_y - 3,
            sensor_x + 3, sensor_y + 3,
            fill='#EF4444', outline='white', width=1
        )
        self.path_ids.append(sensor)
        
        # Add LED indicators
        led_radius = 2
        led_distance = 5
        
        for i in range(3):
            angle_offset = -math.pi/6 + (i * math.pi/6)
            led_x = self.robot_x + (robot_width/2 - 5) * math.cos(self.robot_angle + angle_offset)
            led_y = self.robot_y + (robot_width/2 - 5) * math.sin(self.robot_angle + angle_offset)
            
            # Different colors for LEDs
            colors = ['#EF4444', '#22C55E', '#3B82F6']
            
            led = self.create_oval(
                led_x - led_radius, led_y - led_radius,
                led_x + led_radius, led_y + led_radius,
                fill=colors[i], outline='white', width=0.5
            )
            self.path_ids.append(led)
        
        # The composite robot drawing is stored in path_ids
        self.robot_id = robot_body
    
    def start_animation(self, callback=None):
        if self.is_running:
            return
            
        self.is_running = True
        self.robot_x = 50
        self.robot_y = 120
        self.robot_angle = 0
        self.waypoints = []  # Will be generated when drawing robot
        self.draw_robot()  # Create path and initial robot
        
        def animate():
            # Initialize position
            start_time = time.time()
            self.robot_x = 50
            self.robot_y = 120
            self.robot_angle = 0
            self.draw_robot()  # Redraw at starting position
            
            # Ensure we have waypoints
            if not self.waypoints:
                self.is_running = False
                if callback:
                    self.after_idle(callback)
                return
            
            # Calculate timing to complete in exactly 45 seconds
            total_points = len(self.waypoints)
            total_distance = 0
            
            # Calculate total path distance
            for i in range(1, total_points):
                x1, y1 = self.waypoints[i-1]
                x2, y2 = self.waypoints[i]
                segment_distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                total_distance += segment_distance
            
            # Time per unit of distance to complete in 45 seconds
            time_per_distance = 45.0 / total_distance if total_distance > 0 else 0.01
            
            # Progress through all waypoints
            current_time = 0
            for idx in range(1, total_points):
                if not self.is_running:
                    break
                
                # Check if total animation time has exceeded 45 seconds
                elapsed_total = time.time() - start_time
                if elapsed_total >= 45.0:
                    break
                
                # Get current and target positions
                prev_x, prev_y = self.waypoints[idx-1]
                target_x, target_y = self.waypoints[idx]
                
                # Calculate segment distance
                dx = target_x - prev_x
                dy = target_y - prev_y
                segment_distance = math.sqrt(dx**2 + dy**2)
                
                # Calculate time needed for this segment
                segment_time = segment_distance * time_per_distance
                
                # Number of steps for this segment based on distance
                steps = max(int(segment_distance / 5), 1)
                
                # Move along this segment
                segment_start_time = time.time()
                segment_progress = 0
                
                while segment_progress < 1.0 and self.is_running:
                    # Check if total animation time has exceeded 45 seconds
                    elapsed_total = time.time() - start_time
                    if elapsed_total >= 45.0:
                        break
                    
                    # Calculate progress based on elapsed time
                    elapsed = time.time() - segment_start_time
                    segment_progress = min(elapsed / segment_time, 1.0)
                    
                    # Update position
                    self.robot_x = prev_x + dx * segment_progress
                    self.robot_y = prev_y + dy * segment_progress
                    
                    # Update angle to face movement direction
                    if abs(dx) > 0.1 or abs(dy) > 0.1:
                        target_angle = math.atan2(dy, dx)
                        angle_diff = target_angle - self.robot_angle
                        
                        # Normalize angle difference to [-pi, pi]
                        while angle_diff > math.pi:
                            angle_diff -= 2 * math.pi
                        while angle_diff < -math.pi:
                            angle_diff += 2 * math.pi
                        
                        # Smooth angle transition
                        self.robot_angle += angle_diff * 0.2
                    
                    # Redraw robot
                    self.after_idle(self.draw_robot)
                    
                    # Sleep to control frame rate
                    time.sleep(0.02)
                
                # Update current time
                current_time += segment_time
                
                # Check again if we've reached the 45 second mark
                if time.time() - start_time >= 45.0:
                    break
            
            # Stop the animation after 45 seconds
            final_time = time.time() - start_time
            print(f"Animation completed in {final_time:.2f} seconds")
            
            # Set is_running to False to indicate animation has stopped
            self.is_running = False
            
            # Call the callback
            if callback:
                self.after_idle(callback)
        
        self.animation_thread = threading.Thread(target=animate)
        self.animation_thread.daemon = True
        self.animation_thread.start()
    
    def stop_animation(self):
        self.is_running = False
        if self.animation_thread:
            self.animation_thread.join(timeout=0.5)

class EasyTrackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyTrack - Advanced Robot Tracking System")
        
        # Set window to maximize to screen size
        self.root.state('zoomed')  # Works on Windows to maximize the window
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set minimum size
        self.root.minsize(width=800, height=600)
        
        # Make window resizable
        self.root.resizable(True, True)
        
        # Bind resize event
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Bind escape key to exit fullscreen
        self.root.bind('<Escape>', self.toggle_fullscreen)
        self.root.bind('<F11>', self.toggle_fullscreen)
        
        # Initialize variables
        self.config_data = {
            'robot_speed': '25.0',
            'tracking_interval': '100',
            'communication_port': 'COM3',
            'ip_address': '192.168.1.100',
            'output_format': 'CSV',
            'storage_path': '/data/tracking/',
            'backup_interval': '5'
        }
        
        self.csv_file_path = ""
        self.selected_location = ""
        self.location_boxes = []
        
        # EPC -> Letter mapping for Location map
        self.epc_map = {
            "E2806995000040058378221E": "A",
            "E2806995000040058378661E": "B",
            "E28069950000400583786A1E": "C",
            "E28069950000400583787E1E": "D",
            "E2806995000040058378821E": "E",
            "E2806995000040058378961E": "F",
        }
        
        # Modern styling
        self.setup_styles()
        self.setup_ui()
        
    def toggle_fullscreen(self, event=None):
        current_state = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current_state)
    
    def on_window_resize(self, event=None):
        # This method is called when the window is resized
        # We only want to process resize events from the root window
        if event and event.widget == self.root:
            # Update UI components that need to adjust with window size
            self.root.update_idletasks()
            
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Modern color scheme
        self.colors = {
            'primary': "#0E108E",      # Indigo
            'secondary': "#622CE0",    # Purple  
            'accent': "#059EBA",       # Cyan
            'success': "#086F4D",      # Green
            'warning': '#F59E0B',      # Amber
            'danger': '#EF4444',       # Red
            'surface': '#FFFFFF',      # White
            'background': '#F8FAFC',   # Light gray
            'card': '#FFFFFF',         # White
            'text_primary': '#1F2937', # Dark gray
            'text_secondary': '#6B7280' # Medium gray
        }
        
    def setup_ui(self):
        # Main container with gradient background
        self.create_gradient_background()
        
        # Create a main container frame that will resize with the window
        main_container = tk.Frame(self.root, bg='#F8FAFC')
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configure the container for resizing
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)  # Content area should expand
        
        # Left sidebar with glassmorphism effect
        self.create_sidebar(main_container)
        
        # Right content area with modern card design
        self.create_content_area(main_container)
    def create_gradient_background(self):
        # Simple background color fill (replace with gradient if needed)
        self.root.configure(bg="#e0eafc")
        
    def create_sidebar(self, parent):
        # Glassmorphism sidebar
        sidebar_container = tk.Frame(parent, bg='#F8FAFC')
        sidebar_container.pack(side="left", fill="y", padx=(0, 20))
        
        # Make the sidebar a fixed width but expandable in height
        sidebar_card = tk.Frame(sidebar_container, bg='#FFFFFF', 
                               relief='flat', bd=0, width=280)
        sidebar_card.pack(fill="y", expand=True)
        sidebar_card.pack_propagate(False)  # Keep fixed width
        
        # Modern title with gradient text effect
        title_frame = tk.Frame(sidebar_card, bg='#FFFFFF', height=100)
        title_frame.pack(fill='x', padx=30, pady=(30, 20))
        title_frame.pack_propagate(False)
        
        # Title with modern typography
        title_label = tk.Label(title_frame, text="EASYTRACK", 
                              font=("Segoe UI", 24, "bold"), 
                              bg='#FFFFFF', fg=self.colors['primary'])
        title_label.pack(expand=True)
        
        # Subtitle
        subtitle_label = tk.Label(title_frame, text="Advanced Robot Tracking", 
                                 font=("Segoe UI", 10), 
                                 bg='#FFFFFF', fg=self.colors['text_secondary'])
        subtitle_label.pack()
        
        # Navigation buttons with modern design
        nav_frame = tk.Frame(sidebar_card, bg='#FFFFFF')
        nav_frame.pack(fill='both', expand=True, padx=30)
        
        # Modern menu items
        menu_items = [
            ("⚙️  Configuration", self.configuration),
            ("🤖  Run Robot", self.run_robot), 
            ("📊  Upload CSV", self.upload_csv),
            ("📍  Location", self.location),
            ("�📈  Calculate", self.calculate),
            ("🗑️  Clear", self.clear)
        ]
        
        for text, command in menu_items:
            btn_frame = tk.Frame(nav_frame, bg='#FFFFFF')
            btn_frame.pack(fill='x', pady=(0, 12))
            
            btn = ModernButton(btn_frame, text, command,
                             bg_color='#F1F5F9',
                             hover_color=self.colors['primary'],
                             text_color=self.colors['text_primary'],
                             font=("Segoe UI", 11))
            btn.pack(fill='x')
            
    def create_content_area(self, parent):
        # Content area with modern card design - should expand to fill available space
        content_container = tk.Frame(parent, bg='#F8FAFC')
        content_container.pack(side="right", fill="both", expand=True)
        
        # Configure the content container for resizing
        content_container.grid_rowconfigure(0, weight=1)
        content_container.grid_columnconfigure(0, weight=1)
        
        # Modern content card
        self.content_card = tk.Frame(content_container, bg='#FFFFFF', relief='flat', bd=0)
        self.content_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure content card for resizing
        self.content_card.grid_rowconfigure(2, weight=1)  # Main content area should expand
        self.content_card.grid_columnconfigure(0, weight=1)
        
        # Header bar
        header_frame = tk.Frame(self.content_card, bg='#FFFFFF', height=60)
        header_frame.pack(fill='x', padx=40, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        self.page_title = tk.Label(header_frame, text="Welcome to EasyTrack", 
                                  font=("Segoe UI", 20, "bold"), 
                                  bg='#FFFFFF', fg=self.colors['text_primary'])
        self.page_title.pack(side='left', expand=True, anchor='w')
        
        # Exit fullscreen button
        
        
        # Separator line
        separator = tk.Frame(self.content_card, bg='#E5E7EB', height=1)
        separator.pack(fill='x', padx=40, pady=15)
        
        # Main content area - this should expand to fill available space
        self.main_content = tk.Frame(self.content_card, bg='#FFFFFF')
        self.main_content.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        self.show_welcome()
    
    def clear_content(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()
    
    def show_welcome(self):
        self.clear_content()
        self.page_title.config(text="Welcome to EasyTrack")
        
        # Modern welcome dashboard
        welcome_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        welcome_frame.pack(fill="both", expand=True)
        
        # Hero section
        hero_frame = tk.Frame(welcome_frame, bg='#FFFFFF')
        hero_frame.pack(fill='x', pady=(40, 40))
        
        tk.Label(hero_frame, 
                text="Advanced Robot Tracking & Analytics Platform",
                font=("Segoe UI", 22, "bold"), bg='#FFFFFF', 
                fg=self.colors['text_primary']).pack()
        
        tk.Label(hero_frame, 
                text="Monitor, analyze, and optimize your robot's performance in real-time",
                font=("Segoe UI", 14), bg='#FFFFFF', 
                fg=self.colors['text_secondary']).pack(pady=(15, 0))
        
        # Feature cards section - Complete rewrite to ensure all 4 cards are displayed
        cards_container = tk.Frame(welcome_frame, bg='#FFFFFF')
        cards_container.pack(fill='both', expand=True)
        
        # First row - Precision Tracking and Data Analytics
        row1 = tk.Frame(cards_container, bg='#FFFFFF')
        row1.pack(fill='x', expand=True, pady=(20, 10))
        
        # Precision Tracking card
        card1 = tk.Frame(row1, bg='#F8FAFC', relief='flat', bd=0)
        card1.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(card1, text="🎯", font=("Segoe UI", 28), 
                bg='#F8FAFC', fg=self.colors['primary']).pack(pady=(25, 8))
        tk.Label(card1, text="Precision Tracking", font=("Segoe UI", 13, "bold"), 
                bg='#F8FAFC', fg=self.colors['text_primary']).pack(pady=(0, 4))
        tk.Label(card1, text="Real-time location monitoring", font=("Segoe UI", 10), 
                bg='#F8FAFC', fg=self.colors['text_secondary']).pack(pady=(0, 25))
        
        # Data Analytics card
        card2 = tk.Frame(row1, bg='#F8FAFC', relief='flat', bd=0)
        card2.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(card2, text="📊", font=("Segoe UI", 28), 
                bg='#F8FAFC', fg=self.colors['primary']).pack(pady=(25, 8))
        tk.Label(card2, text="Data Analytics", font=("Segoe UI", 13, "bold"), 
                bg='#F8FAFC', fg=self.colors['text_primary']).pack(pady=(0, 4))
        tk.Label(card2, text="Comprehensive performance metrics", font=("Segoe UI", 10), 
                bg='#F8FAFC', fg=self.colors['text_secondary']).pack(pady=(0, 25))
        
        # Second row - Fast Processing and Secure Connection
        row2 = tk.Frame(cards_container, bg='#FFFFFF')
        row2.pack(fill='x', expand=True, pady=(10, 20))
        
        # Fast Processing card
        card3 = tk.Frame(row2, bg='#F8FAFC', relief='flat', bd=0)
        card3.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(card3, text="⚡", font=("Segoe UI", 28), 
                bg='#F8FAFC', fg=self.colors['primary']).pack(pady=(25, 8))
        tk.Label(card3, text="Fast Processing", font=("Segoe UI", 13, "bold"), 
                bg='#F8FAFC', fg=self.colors['text_primary']).pack(pady=(0, 4))
        tk.Label(card3, text="Optimized for speed and efficiency", font=("Segoe UI", 10), 
                bg='#F8FAFC', fg=self.colors['text_secondary']).pack(pady=(0, 25))
        
        # Secure Connection card
        card4 = tk.Frame(row2, bg='#F8FAFC', relief='flat', bd=0)
        card4.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(card4, text="🔒", font=("Segoe UI", 28), 
                bg='#F8FAFC', fg=self.colors['primary']).pack(pady=(25, 8))
        tk.Label(card4, text="Secure Connection", font=("Segoe UI", 13, "bold"), 
                bg='#F8FAFC', fg=self.colors['text_primary']).pack(pady=(0, 4))
        tk.Label(card4, text="Encrypted IP communication", font=("Segoe UI", 10), 
                bg='#F8FAFC', fg=self.colors['text_secondary']).pack(pady=(0, 25))
    
    def configuration(self):
        self.clear_content()
        self.page_title.config(text="System Configuration")
        
        config_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        config_frame.pack(fill="both", expand=True, pady=20)
        
        # Configuration form
        form_container = tk.Frame(config_frame, bg='#FFFFFF')
        form_container.pack(fill='both', expand=True)
        
        # Configuration sections
        sections = [
            ("Robot Parameters", [
                
                ("Communication Port", "communication_port"),
                ("IP Address", "ip_address")
            ]),
            
        ]
        
        self.config_entries = {}
        
        for section_title, fields in sections:
            # Section header
            section_frame = tk.Frame(form_container, bg='#FFFFFF')
            section_frame.pack(fill='x', pady=(20, 15))
            
            tk.Label(section_frame, text=section_title, 
                    font=("Segoe UI", 16, "bold"), 
                    bg='#FFFFFF', fg=self.colors['text_primary']).pack(anchor='w')
            
            tk.Frame(section_frame, bg=self.colors['primary'], height=2).pack(fill='x', pady=(5, 0))
            
            # Fields
            for field_name, field_key in fields:
                field_frame = tk.Frame(form_container, bg='#FFFFFF')
                field_frame.pack(fill='x', pady=8)
                
                tk.Label(field_frame, text=field_name, 
                        font=("Segoe UI", 11), bg='#FFFFFF', 
                        fg=self.colors['text_primary'], width=25, anchor='w').pack(side='left')
                
                if field_key == "output_format":
                    entry = ttk.Combobox(field_frame, values=["CSV", "JSON", "XML"], 
                                       font=("Segoe UI", 10), width=35)
                    entry.set(self.config_data[field_key])
                else:
                    entry = tk.Entry(field_frame, font=("Segoe UI", 10), width=40, 
                                   bg='#F8FAFC', relief='flat', bd=1)
                    entry.insert(0, self.config_data[field_key])
                
                entry.pack(side='left', padx=(20, 0), ipady=6)
                self.config_entries[field_key] = entry
        
        # Button frame
        button_frame = tk.Frame(form_container, bg='#FFFFFF')
        button_frame.pack(fill='x', pady=40)
        
        # Save and Cancel buttons
        save_btn = tk.Button(button_frame, text="💾 Save Configuration",
                           command=self.save_config,
                           font=("Segoe UI", 11, "bold"),
                           bg=self.colors['success'],
                           fg='white', relief='flat',
                           padx=25, pady=10)
        save_btn.pack(side='left', padx=(0, 15))
        
        cancel_btn = tk.Button(button_frame, text="❌ Cancel",
                             command=self.cancel_config,
                             font=("Segoe UI", 11, "bold"),
                             bg=self.colors['text_secondary'],
                             fg='white', relief='flat',
                             padx=25, pady=10)
        cancel_btn.pack(side='left')
    
    def run_robot(self):
        self.clear_content()
        self.page_title.config(text="Robot Control Center")
        
        control_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        control_frame.pack(fill="both", expand=True, pady=20)
        
        # Animation area with better styling
        animation_frame = tk.Frame(control_frame, bg='#F1F5F9', relief='ridge', bd=1)
        animation_frame.pack(fill='both', expand=True, pady=(0, 20), padx=20)
        
        # Heading with icon
        header_frame = tk.Frame(animation_frame, bg='#F1F5F9')
        header_frame.pack(fill='x', pady=(15, 5))
        
        tk.Label(header_frame, text="🤖", 
                font=("Segoe UI", 18), bg='#F1F5F9',
                fg=self.colors['text_primary']).pack(side='left', padx=(20, 5))
        
        tk.Label(header_frame, text="Line Following Robot Simulation", 
                font=("Segoe UI", 14, "bold"), bg='#F1F5F9',
                fg=self.colors['text_primary']).pack(side='left')
        
        # Description
        description = "This simulation shows a line following robot navigating along a complex path using its sensors."
        tk.Label(animation_frame, text=description, 
                font=("Segoe UI", 10), bg='#F1F5F9',
                fg=self.colors['text_secondary']).pack(pady=(0, 10))
        
        # Animation canvas with border
        canvas_frame = tk.Frame(animation_frame, bg='#E2E8F0', bd=1, relief='flat')
        canvas_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.animation_canvas = AnimationCanvas(canvas_frame, bg='#FFFFFF', 
                                              height=250, relief='flat', bd=0)
        self.animation_canvas.pack(fill='x', padx=2, pady=2)
        
        # Draw initial robot
        self.animation_canvas.after(100, self.animation_canvas.draw_robot)
        
        # Simple button frame
        button_frame = tk.Frame(animation_frame, bg='#F1F5F9')
        button_frame.pack(pady=(0, 15))
        
        # Start button
        self.start_btn = tk.Button(button_frame, text="▶️ Start Simulation",
                                command=self.start_robot_animation,
                                font=("Segoe UI", 11, "bold"),
                                bg='#16A34A',
                                fg='white', relief='flat',
                                padx=15, pady=8)
        self.start_btn.pack(side='left', padx=5)
        
        # Reset button
        self.reset_btn = tk.Button(button_frame, text="🔄 Reset",
                                command=self.reset_robot_animation,
                                font=("Segoe UI", 11, "bold"),
                                bg='#6B7280',
                                fg='white', relief='flat',
                                padx=15, pady=8)
        self.reset_btn.pack(side='left', padx=5)
        
        # Back button
        back_btn = tk.Button(control_frame, text="← Back to Menu",
                           command=self.show_main_menu,
                           font=("Segoe UI", 10),
                           bg='#F1F5F9',
                           fg=self.colors['text_secondary'], relief='flat',
                           padx=15, pady=5)
        back_btn.pack(anchor='w', padx=20, pady=(10, 0))
    
    def start_robot_animation(self):
        # Disable start button, ensure reset button remains enabled
        self.start_btn.config(state='disabled')
        self.reset_btn.config(state='normal')
        # Call send_start from runRobot.py
        send_start()
        # Start animation
        self.animation_canvas.start_animation(callback=self.animation_complete)
    
    def reset_robot_animation(self):
        # Enable the start button
        self.start_btn.config(state='normal')
        # Call on_close from runRobot.py
        on_close()
        # Reset animation
        if hasattr(self.animation_canvas, 'is_running') and self.animation_canvas.is_running:
            # Stop the running animation first
            self.animation_canvas.stop_animation()
            # Wait briefly to ensure animation thread has stopped
            self.root.after(100, self._complete_reset)
        else:
            # If not running, reset immediately
            self._complete_reset()
    
    def _complete_reset(self):
        # Reset robot position and properties
        self.animation_canvas.robot_x = 50
        self.animation_canvas.robot_y = 120
        self.animation_canvas.robot_angle = 0
        self.animation_canvas.waypoints = []
        
        # Clear the canvas and redraw the robot
        self.animation_canvas.delete("all")  # Clear everything
        self.animation_canvas.draw_robot()   # Redraw robot in initial position
    
    def animation_complete(self):
        # Only reset the button if the animation has actually stopped
        if not self.animation_canvas.is_running:
            self.start_btn.config(state='normal')
    
    def show_main_menu(self):
        # Clear content and show the welcome screen again
        self.clear_content()
        self.show_welcome()
    
    def upload_csv(self):
        self.clear_content() 
        self.page_title.config(text="Data Import & Location Setup")
        
        upload_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        upload_frame.pack(fill="both", expand=True, pady=20)
        
        # CSV Upload Section
        csv_section = tk.Frame(upload_frame, bg='#FFFFFF')
        csv_section.pack(fill='x', pady=(0, 30))
        
        tk.Label(csv_section, text="📊 CSV File Upload", 
                font=("Segoe UI", 14, "bold"), bg='#FFFFFF',
                fg=self.colors['text_primary']).pack(anchor='w', pady=(0, 15))
        
        # File selection area
        file_frame = tk.Frame(csv_section, bg='#F8FAFC', relief='flat', bd=1)
        file_frame.pack(fill='x', pady=(0, 15), ipady=20)
        
        self.file_var = tk.StringVar(value="No file selected")
        file_label = tk.Label(file_frame, textvariable=self.file_var,
                             font=("Segoe UI", 11), bg='#F8FAFC', 
                             fg=self.colors['text_secondary'])
        file_label.pack(pady=10)
        
        browse_btn = tk.Button(file_frame, text="📁 Browse Files",
                             command=self.browse_file,
                             font=("Segoe UI", 10, "bold"),
                             bg=self.colors['primary'], fg='white',
                             relief='flat', padx=20, pady=8)
        browse_btn.pack()
        
        # Location Setting Section
        location_section = tk.Frame(upload_frame, bg='#FFFFFF')
        location_section.pack(fill='x', pady=(0, 30))
        
        tk.Label(location_section, text="📍 Set Location", 
                font=("Segoe UI", 14, "bold"), bg='#FFFFFF',
                fg=self.colors['text_primary']).pack(anchor='w', pady=(0, 15))
        
        # Location selection area with similar style as file selection
        location_frame = tk.Frame(location_section, bg='#F8FAFC', relief='flat', bd=1)
        location_frame.pack(fill='x', pady=(0, 15), ipady=20)
        
        # Create a StringVar to hold the location name for display
        self.location_var = tk.StringVar(value="No location selected")
        location_label = tk.Label(location_frame, textvariable=self.location_var,
                               font=("Segoe UI", 11), bg='#F8FAFC', 
                               fg=self.colors['text_secondary'])
        location_label.pack(pady=10)
        
        # Hidden entry field (we'll still use it to store the location)
        self.location_entry = tk.Entry(self.root)
        
        # Browse location button
        select_location_btn = tk.Button(location_frame, text="📍 Select Location",
                                      command=self.browse_location,
                                      font=("Segoe UI", 10, "bold"),
                                      bg=self.colors['primary'], fg='white',
                                      relief='flat', padx=20, pady=8)
        select_location_btn.pack()
        
        # Single Save button for both CSV and location
        save_button_frame = tk.Frame(upload_frame, bg='#FFFFFF')
        save_button_frame.pack(fill='x', pady=20)
        
        save_all_btn = tk.Button(save_button_frame, text="💾 Save CSV & Location",
                              command=self.save_csv_and_location,
                              font=("Segoe UI", 12, "bold"),
                              bg=self.colors['success'], fg='white',
                              relief='flat', padx=25, pady=12)
        save_all_btn.pack()
        
        # Button frame
        button_frame = tk.Frame(upload_frame, bg='#FFFFFF')
        button_frame.pack(fill='x', pady=30)
        
        cancel_btn = tk.Button(button_frame, text="❌ Cancel",
                             command=self.cancel_csv_upload,
                             font=("Segoe UI", 11, "bold"),
                             bg='#EF4444', fg='white',
                             relief='flat', padx=25, pady=10)
        cancel_btn.pack(side='left', padx=(0, 15))
        
        # Home button
        home_btn = tk.Button(button_frame, text="🏠 Back to Home",
                            command=self.go_home,
                            font=("Segoe UI", 11),
                            bg='#F3F4F6', fg=self.colors['text_secondary'],
                            relief='flat', padx=15, pady=8)
        home_btn.pack(side='left', padx=(0, 15))
        
        # Cancel button (redundant, but keeping for safety)
        cancel_btn = tk.Button(button_frame, text="❌ Cancel",
                             command=self.cancel_csv_upload,
                             font=("Segoe UI", 11, "bold"),
                             bg='#EF4444', fg='white',
                             relief='flat', padx=25, pady=10)
        cancel_btn.pack(side='left', padx=(0, 15))
        
        # Home button (redundant, but keeping for safety)
        home_btn = tk.Button(button_frame, text="🏠 Back to Home",
                            command=self.go_home,
                            font=("Segoe UI", 11),
                            bg='#F3F4F6', fg=self.colors['text_secondary'],
                            relief='flat', padx=15, pady=8)
        home_btn.pack(side='left')
    
    def location(self):
        self.clear_content()
        self.page_title.config(text="Location Tracking")
        
        location_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        location_frame.pack(fill="both", expand=True, pady=20)
        
        # Interactive map only (removed current robot position section)
        map_frame = tk.Frame(location_frame, bg='#F1F5F9', relief='flat', bd=1)
        map_frame.pack(fill='both', expand=True)
        
        tk.Label(map_frame, text="🗺️ Interactive Tracking Map", 
                font=("Segoe UI", 12, "bold"), bg='#F1F5F9',
                fg=self.colors['text_primary']).pack(pady=20)
        
        canvas = tk.Canvas(map_frame, bg='#FFFFFF', height=400, relief='flat', bd=0)
        canvas.pack(fill='both', expand=True, padx=30, pady=(0, 30))
        
        # Draw grid and positions from estimated_positions.csv (XZ only)
        canvas.bind('<Configure>', lambda e: self.draw_location_map(canvas))
    
    def calculate(self):
        self.clear_content()
        self.page_title.config(text="Location Grid Calculator")
        
        calc_frame = tk.Frame(self.main_content, bg='#FFFFFF')
        calc_frame.pack(fill="both", expand=True, pady=10)
        
        # Instructions
        tk.Label(calc_frame, text="🔢 Select location boxes to calculate distances and paths", 
                font=("Segoe UI", 12), bg='#FFFFFF',
                fg=self.colors['text_secondary']).pack(pady=(0, 15))
        
        # Dictionary mapping location numbers to values
        input_file = os.path.join(self.selected_location, 'estimated_positions.csv')
        report = generate_number_letter_report(input_file)
        new_report = {k: v for k, v in zip(reversed(report.keys()), report.values())}
        print(new_report)
        location_dict=new_report
        # 6 boxes in 2 rows and 3 columns with consistent sizing
        grid_frame = tk.Frame(calc_frame, bg='#FFFFFF')
        grid_frame.pack(expand=True, fill='both', padx=20, pady=10)
        
        self.location_boxes = []
        box_colors = ['#F8FAFC', self.colors['primary']]
        
        # Fixed box dimensions for consistency
        box_width = 200
        box_height = 180
        
        for row in range(2):
            row_frame = tk.Frame(grid_frame, bg='#FFFFFF')
            row_frame.pack(pady=15, fill='x')
            
            # Create a weight configuration for even distribution
            row_frame.columnconfigure(0, weight=1)
            row_frame.columnconfigure(1, weight=1)
            row_frame.columnconfigure(2, weight=1)
            
            for col in range(3):
                box_index = row * 3 + col + 1
                
                # Container frame to maintain consistent sizing
                container = tk.Frame(row_frame, width=box_width, height=box_height, bg='#FFFFFF')
                container.grid(row=0, column=col, padx=15, pady=10)
                container.pack_propagate(False)  # Prevent inner widgets from changing size
                
                box_frame = tk.Frame(container, bg=box_colors[0], relief='flat', bd=2,
                                   highlightbackground='#E5E7EB', highlightthickness=2)
                box_frame.pack(fill='both', expand=True)
                
                # Box label with consistent styling
                box_label = tk.Label(box_frame, text=f"Location {box_index}", 
                                   font=("Segoe UI", 14, "bold"), bg=box_colors[0],
                                   fg=self.colors['text_primary'])
                box_label.pack(pady=(15, 5))
                
                # Dictionary value displayed prominently in the center
                value_label = tk.Label(box_frame, text=location_dict[box_index], 
                                     font=("Segoe UI", 36, "bold"), bg=box_colors[0],
                                     fg=self.colors['primary'])
                value_label.pack(pady=10)

                # Apply per-letter background colors
                letter_colors = {
                    'A': '#EF4444',  # Red
                    'B': '#22C55E',  # Green
                    'C': '#3B82F6',  # Blue
                    'D': '#EC4899',  # Pink
                    'E': "#4D4935",  # Gray
                    'F': '#F59E0B',  # Yellow
                }
                letter = str(location_dict.get(box_index, '')).upper()
                bg_color = letter_colors.get(letter, '#F8FAFC')
                # Choose text color for contrast (dark text on yellow, white otherwise)
                text_color = '#111827' if letter == 'G' else '#FFFFFF'
                
                # Set colors on the box and labels
                box_frame.config(bg=bg_color)
                box_label.config(bg=bg_color, fg=text_color)
                value_label.config(bg=bg_color, fg=text_color)
                
                # Make box clickable
                def on_box_click(box_idx=box_index, frame=box_frame, label=box_label, value=value_label):
                    self.toggle_location_box(box_idx, frame, label, value)
                
                box_frame.bind('<Button-1>', lambda e, idx=box_index: on_box_click(idx))
                box_label.bind('<Button-1>', lambda e, idx=box_index: on_box_click(idx))
                value_label.bind('<Button-1>', lambda e, idx=box_index: on_box_click(idx))
                
                self.location_boxes.append({
                    'index': box_index,
                    'frame': box_frame,
                    'label': box_label,
                    'value': value_label,
                    'selected': False
                })
        
        # Create a more prominent button frame with background color
        button_frame = tk.Frame(calc_frame, bg='#F0F4F8', padx=20, pady=20)
        button_frame.pack(fill='x', pady=30, side='bottom')
        
        # Create separate buttons with clear styling
        back_btn = tk.Button(button_frame, text="← Back to Menu",
                           command=self.show_main_menu,
                           font=("Segoe UI", 14, "bold"),
                           bg=self.colors['primary'], fg='white',
                           relief='raised', padx=20, pady=10,
                           cursor="hand2")
        back_btn.pack(side='left', padx=20, expand=True)
        
        not_back_btn = tk.Button(button_frame, text="Not in the back to menu",
                               command=self.show_main_menu,  # Same command for now
                               font=("Segoe UI", 14, "bold"),
                               bg='#4B5563', fg='white',
                               relief='raised', padx=20, pady=10,
                               cursor="hand2")
        not_back_btn.pack(side='right', padx=20, expand=True)
    
    def clear(self):
        result = messagebox.askyesno("Clear All Data", 
                                   "This will permanently delete all tracking data, configurations, and session history.\n\nAre you sure you want to continue?",
                                   icon='warning')
        if result:
            # Reset all data
            self.config_data = {
                'robot_speed': '25.0',
                'tracking_interval': '100',
                'communication_port': 'COM3',
                'ip_address': '192.168.1.100',
                'output_format': 'CSV',
                'storage_path': '/data/tracking/',
                'backup_interval': '5'
            }
            self.csv_file_path = ""
            self.selected_location = ""
            self.location_boxes = []
            
            self.show_welcome()
            messagebox.showinfo("Data Cleared", "✅ All data has been successfully cleared.")
    
    # Configuration methods
    def save_config(self):
        try:
            # Update config data from entries
            for key, entry in self.config_entries.items():
                self.config_data[key] = entry.get()
            
            messagebox.showinfo("Configuration Saved", 
                               f"✅ Configuration saved successfully!\n\nIP Address: {self.config_data['ip_address']}\nRobot Speed: {self.config_data['robot_speed']} cm/s")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def cancel_config(self):
        # Reset entries to original values
        for key, entry in self.config_entries.items():
            if hasattr(entry, 'set'):  # Combobox
                entry.set(self.config_data[key])
            else:  # Entry
                entry.delete(0, tk.END)
                entry.insert(0, self.config_data[key])
        messagebox.showinfo("Changes Cancelled", "Configuration changes have been cancelled.")
    
    # The robot animation methods are defined earlier in the file
    # We're commenting these out to avoid duplicates
    """
    def start_robot_animation(self):
        self.status_var.set("Running")
        self.status_label.config(bg='#DCFCE7', fg='#16A34A')
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Start timer
        self.start_time = time.time()
        self.update_timer()
        
        # Start battery drain simulation
        self.battery_level = 100
        self.update_battery()
        
        # Start animation
        self.animation_canvas.start_animation(callback=self.animation_complete)
    """
    
    # Animation methods are now defined earlier in the file
    # def cancel_robot_animation(self):
    #     self.animation_canvas.stop_animation()
    #     self.start_btn.config(state='normal')
    #     self.cancel_btn.config(state='disabled')
    #     self.status_var.set("Robot Status: Mission Cancelled")
    #     self.timer_var.set("Timer: 00:00")
    
    # def animation_complete(self):
    #     self.start_btn.config(state='normal')
    #     self.cancel_btn.config(state='disabled')
    #     self.status_var.set("Robot Status: Mission Completed")
    #     messagebox.showinfo("Mission Complete", "🎉 Robot mission completed successfully in 45 seconds!")
    
    # These methods have been removed since we simplified the UI
    """
    def update_timer(self):
        if hasattr(self, 'start_time') and self.animation_canvas.is_running:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.timer_var.set(f"Timer: {minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.update_timer)
    """
    
    # CSV upload methods
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.csv_file_path = filename
            
            # Get the file basename (without path)
            file_basename = os.path.basename(filename)
            
            # Set the displayed file name
            self.file_var.set(f"Selected: {file_basename}")
            
            # Automatically set location name from the file name
            # Remove file extension to use as location name
            location_name = os.path.splitext(file_basename)[0]
            
            # Clean up the location name (remove special characters, etc.)
            location_name = ''.join(c if c.isalnum() or c.isspace() else '_' for c in location_name)
            
            # Set the location entry to match the file name
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, location_name)
            
            # Update the displayed location in the UI
            if hasattr(self, 'location_var'):
                self.location_var.set(f"Selected: {location_name}")
            
            # Auto-save the data
            self.root.after(100, self.auto_save_csv_data)
    
    def browse_location(self):
        """Open a folder selection dialog to choose a location"""
        folder_path = filedialog.askdirectory(
            title="Select Location Folder"
        )
        
        if folder_path:
            # Get just the folder name (not the full path)
            folder_name = os.path.basename(folder_path)
            
            # If it's empty (like if they selected root), use the full path's last part
            if not folder_name and folder_path:
                folder_name = os.path.normpath(folder_path).split(os.sep)[-1]
            
            # If still empty, use a default
            if not folder_name:
                folder_name = "Custom_Location"
                
            # Update the location entry and display
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, folder_name)
            
            # Update the displayed location in the UI
            self.location_var.set(f"Selected: {folder_name}")
            
            # If we have a CSV file, auto-save with the new location
            if self.csv_file_path:
                self.auto_save_csv_data()
    
                              
    def auto_save_csv_data(self):
        # Auto-save CSV after selection
        if not self.csv_file_path:
            return
            
        # Get location from filename (already set in browse_file)
        location_name = self.location_entry.get().strip()
        
        # Save the location
        self.selected_location = location_name
        
        # Visual feedback - briefly highlight the location entry
        original_bg = self.location_entry.cget("bg")
        self.location_entry.config(bg="#D1FAE5")  # Light green background
        
        # Return to original background after a delay
        self.root.after(800, lambda: self.location_entry.config(bg=original_bg))
        
        # Show confirmation after a brief delay
        import os
        self.root.after(500, lambda: messagebox.showinfo(
            "Data Auto-Saved", 
            f"✅ CSV file and location saved automatically!\n\nFile: {os.path.basename(self.csv_file_path)}\nLocation: {location_name}"
        ))
    
    def save_location_only(self):
        """Method to save just the location data when the Save button is clicked"""
        location_name = self.location_entry.get().strip()
        
        if not location_name:
            messagebox.showwarning("No Location", "Please enter a location name.")
            return
        
        # Save the location
        self.selected_location = location_name
        
        # Visual feedback
        messagebox.showinfo(
            "Location Saved", 
            f"✅ Location saved successfully!\n\nLocation: {location_name}"
        )
    
    def save_csv_and_location(self):
        """Method to save both CSV file and location data with one button"""
        if not self.csv_file_path:
            messagebox.showwarning("No File", "Please select a CSV file first.")
            return

        if not self.selected_location:
            messagebox.showwarning("No Location", "Please select a location folder.")
            return

        self.csvfile = self.csv_file_path
        self.location = self.selected_location

        file_basename = os.path.basename(self.csv_file_path)
        messagebox.showinfo(
            "Data Saved",
            f"✅ CSV file and location saved successfully!\n\nFile: {file_basename}\nLocation: {self.location}"
        )
        #df = pd.read_csv(self.csv_file_path)
        output_csv_path = os.path.join(self.location, "arranged.csv")
        df=arrange_csv(self.csvfile, output_csv_path)
        results = arrangeCSV(df)
        results.to_csv(os.path.join(self.selected_location, f'timed_data.csv'), index=False)
        output_path = os.path.join(self.selected_location, 'estimated_positions.csv')
        if os.path.exists(output_path):
            os.remove(output_path)
        seperateEPC(results, output_path)
        messagebox.showinfo(
            "Calculation",
            f"✅ Location Calculation Sucessfully!"
        )
       
    
    def save_csv_data(self):
        if not self.csv_file_path:
            messagebox.showwarning("No File", "Please select a CSV file first.")
            return
        
        location_name = self.location_entry.get().strip()
        if not location_name:
            messagebox.showwarning("No Location", "Please enter a location name.")
            return
        
        self.selected_location = location_name
        
        import os
        # Get file basename (without path)
        file_basename = os.path.basename(self.csv_file_path)
        
        messagebox.showinfo("Data Saved", 
                           f"✅ CSV file and location saved successfully!\n\nFile: {file_basename}\nLocation: {location_name}")
    
    def save_location_data(self):
        """Save only the location data without requiring CSV file"""
        location_name = self.location_entry.get().strip()
        
        if not location_name:
            messagebox.showwarning("No Location", "Please enter a location name.")
            return
        
        self.selected_location = location_name
        
        # Update the location preview
        self.draw_location_preview()
        
        messagebox.showinfo("Location Saved", 
                           f"✅ Location saved successfully!\n\nLocation: {location_name}")
    
    def cancel_csv_upload(self):
        # Reset variables
        self.csv_file_path = ""
        self.selected_location = ""
        self.file_var.set("No file selected")
        if hasattr(self, 'location_entry'):
            self.location_entry.delete(0, tk.END)
        
        # Show confirmation message
        messagebox.showinfo("Upload Cancelled", "CSV upload has been cancelled.")
        
        # Return to welcome screen
        self.show_welcome()
        
    def go_home(self):
        # Simply return to welcome screen
        self.show_welcome()
    
    # Location tracking methods
    def draw_location_map(self, canvas):
        """Draw an interactive map of tag positions from estimated_positions.csv (XZ only)."""
        canvas.delete('all')
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        # Draw background grid
        grid_size = 30
        for i in range(0, width, grid_size):
            canvas.create_line(i, 0, i, height, fill='#E5E7EB', width=1)
        for i in range(0, height, grid_size):
            canvas.create_line(0, i, width, i, fill='#E5E7EB', width=1)

        # No dynamic robot/current position; render tag XZ positions from CSV
        if not getattr(self, 'selected_location', ''):
            canvas.create_text(width/2, height/2, text="Select a location folder to view estimated_positions.csv",
                               fill=self.colors['text_secondary'], font=("Segoe UI", 12))
            return

        file_path = os.path.join(self.selected_location, 'estimated_positions.csv')
        if not os.path.exists(file_path):
            canvas.create_text(width/2, height/2, text="estimated_positions.csv not found in the selected folder",
                               fill=self.colors['danger'], font=("Segoe UI", 12, 'bold'))
            return

        try:
            points = self._load_estimated_positions(file_path)  # list of dicts: {'tag','x','z'}
        except Exception as e:
            canvas.create_text(width/2, height/2, text=f"Error loading CSV: {e}",
                               fill=self.colors['danger'], font=("Segoe UI", 12))
            return

        if not points:
            canvas.create_text(width/2, height/2, text="No positions to display",
                               fill=self.colors['text_secondary'], font=("Segoe UI", 12))
            return

        # Compute normalization for X and Z to fit canvas with padding
        pad = 30
        min_x = min(p['x'] for p in points)
        max_x = max(p['x'] for p in points)
        min_z = min(p['z'] for p in points)
        max_z = max(p['z'] for p in points)
        range_x = max(1e-6, max_x - min_x)
        range_z = max(1e-6, max_z - min_z)

        # Maintain aspect ratio inside canvas
        scale_x = (width - 2*pad) / range_x
        scale_z = (height - 2*pad) / range_z
        scale = min(scale_x, scale_z)

        # Centering offsets
        total_w = range_x * scale
        total_h = range_z * scale
        offset_x = (width - total_w) / 2
        offset_y = (height - total_h) / 2

        # Draw axes labels (optional, light)
        canvas.create_text(pad/2, pad/2, text="Z↑", fill=self.colors['text_secondary'], font=("Segoe UI", 10))
        canvas.create_text(width - pad/2, height - pad/2, text="X→", fill=self.colors['text_secondary'], font=("Segoe UI", 10))

        # Simple tooltip support
        tooltip_id = {'text': None, 'bg': None}

        def world_to_canvas(x, z):
            # Map: X to right, Z up (invert Y for canvas)
            cx = offset_x + (x - min_x) * scale
            cy = offset_y + (max_z - z) * scale
            return cx, cy

        def show_tooltip(x, y, text):
            # Remove existing
            if tooltip_id['bg']:
                try:
                    canvas.delete(tooltip_id['bg'])
                except Exception:
                    pass
            if tooltip_id['text']:
                try:
                    canvas.delete(tooltip_id['text'])
                except Exception:
                    pass
            # Draw new tooltip
            padding = 4
            tw = canvas.create_text(x, y, text=text, anchor='nw',
                                    font=("Segoe UI", 10), fill='#111827')
            bbox = canvas.bbox(tw)
            if bbox:
                bg = canvas.create_rectangle(bbox[0]-padding, bbox[1]-padding,
                                             bbox[2]+padding, bbox[3]+padding,
                                             fill='#F9FAFB', outline='#CBD5E1')
                canvas.tag_raise(tw, bg)
                tooltip_id['bg'] = bg
                tooltip_id['text'] = tw

        def hide_tooltip():
            if tooltip_id['bg']:
                canvas.delete(tooltip_id['bg'])
                tooltip_id['bg'] = None
            if tooltip_id['text']:
                canvas.delete(tooltip_id['text'])
                tooltip_id['text'] = None

        # Draw points
        r = 6
        for p in points:
            cx, cy = world_to_canvas(p['x'], p['z'])
            dot = canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self.colors['primary'], outline='white', width=1)
            # Map EPC to letter if available
            epc_value = p.get('tag', '') or ''
            mapped_label = self.epc_map.get(epc_value, epc_value)
            label = canvas.create_text(cx + 10, cy - 10, text=str(mapped_label), anchor='w',
                                       fill=self.colors['text_primary'], font=("Segoe UI", 10, 'bold'))

            # Hover interactions
            def make_handlers(epc=epc_value, disp=mapped_label, x=p['x'], z=p['z'], d=dot):
                def on_enter(_):
                    canvas.itemconfig(d, fill=self.colors['danger'])
                    # Show detailed tooltip with EPC and coords
                    show_tooltip(cx + 12, cy + 12, f"{disp} | EPC: {epc}\nx={x}, z={z}")
                def on_leave(_):
                    canvas.itemconfig(d, fill=self.colors['primary'])
                    hide_tooltip()
                return on_enter, on_leave
            enter, leave = make_handlers()
            canvas.tag_bind(dot, '<Enter>', enter)
            canvas.tag_bind(dot, '<Leave>', leave)

    def _load_estimated_positions(self, file_path):
        """Load estimated_positions.csv and return list of {'tag','x','z'} dicts.
        Attempts to be flexible with column names.
        """
        df = pd.read_csv(file_path)
        # Normalize columns
        lower_map = {c.lower().strip(): c for c in df.columns}
        # Candidates for tag/x/z
        tag_cols = [c for k, c in lower_map.items() if k in ('tag', 'tag_id', 'id', 'epc', 'label', 'name')]
        x_cols = [c for k, c in lower_map.items() if k in ('x', 'x_pos', 'xposition', 'x_position')]
        z_cols = [c for k, c in lower_map.items() if k in ('z', 'z_pos', 'zposition', 'z_position')]

        if not x_cols or not z_cols:
            # Try common alternatives like capitalized
            for c in df.columns:
                lc = c.lower()
                if lc.startswith('x') and not x_cols:
                    x_cols.append(c)
                if lc.startswith('z') and not z_cols:
                    z_cols.append(c)

        x_col = x_cols[0] if x_cols else None
        z_col = z_cols[0] if z_cols else None
        tag_col = tag_cols[0] if tag_cols else None

        if x_col is None or z_col is None:
            raise ValueError("CSV must contain X and Z columns")

        # Build list
        records = []
        for _, row in df.iterrows():
            try:
                x = float(row[x_col])
                z = float(row[z_col])
            except Exception:
                continue
            tag = str(row[tag_col]) if tag_col is not None and not pd.isna(row[tag_col]) else ''
            records.append({'tag': tag, 'x': x, 'z': z})
        return records
        

if __name__ == "__main__":
    root = tk.Tk()
    
    # Configure the root window to resize properly
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    # Initialize app
    app = EasyTrackApp(root)
    
    # Start the application
    root.mainloop()