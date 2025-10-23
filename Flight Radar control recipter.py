import tkinter as tk
import math
import random
import time

# --- Configuration Constants ---
# We use this as a consistent virtual base for coordinates (0-600)
VIRTUAL_SCOPE_MAX = 600 
SCOPE_RADIUS_FACTOR = 0.5 - (20 / VIRTUAL_SCOPE_MAX) # Percentage of canvas size for the radar circle

# Colors for the vintage phosphor look
COLOR_BG = '#000000'    # Black background
COLOR_GLOW = '#00FF00'  # Bright Green (Phosphor)
COLOR_DIM = '#006600'   # Dim Green (Trails/Grid)

PLANE_SIZE = 6
SWEEP_SPEED = 0.05 # Radians per frame
PLANE_BASE_SPEED = 0.35 

# --- Plane Data Structure ---
class Aircraft:
    def __init__(self, code, x, y, speed, color):
        # x, y, dest_x, dest_y should be relative to the VIRTUAL_SCOPE_MAX (0-600)
        self.code = code
        self.x = x
        self.y = y
        self.dest_x = x
        self.dest_y = y
        self.speed = speed
        self.color = color
        self.trail = [] 

# --- Radar Application Class ---
class RadarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WWII Ground Control Intercept (GCI) Radar")
        self.configure(bg=COLOR_BG)
        self.geometry(f"{VIRTUAL_SCOPE_MAX + 400}x{VIRTUAL_SCOPE_MAX}")
        self.resizable(True, True) 
        
        self.is_fullscreen = False
        self.sweep_angle = 0
        self.planes = []
        self.previous_radar_size = VIRTUAL_SCOPE_MAX 

        self.setup_ui()
        
        self.update_radar_dimensions()
        self.initialize_planes() 
        
        # --- DYNAMIC RESIZE BINDING ---
        self.bind('<Configure>', self.on_resize)
        
        # --- FULLSCREEN BINDING ---
        self.bind('<F11>', self.toggle_fullscreen)
        self.bind('<Escape>', self.exit_fullscreen)
        
        # Initial draw and start animation
        self.draw_radar()
        self.animate()
        
        self.log_to_console("SYSTEM: Radar powered up. Scanning initiated.", "SYSTEM")
        self.log_to_console(f"INSTRUCTIONS: Command format: [CODE] [X] [Y] where X, Y are 0-{VIRTUAL_SCOPE_MAX} (e.g., FW190 400 150). F11 for Fullscreen.", "SYSTEM")
        self.log_to_console("Aircraft Codes: " + ", ".join([p.code for p in self.planes]), "SYSTEM")


    # ---------------------------

    def update_radar_dimensions(self):
        """Updates internal dimensions based on current canvas size."""
        self.RADAR_SIZE = self.radar_canvas.winfo_width() 
        self.CENTER = self.RADAR_SIZE / 2
        self.SCOPE_RADIUS = self.RADAR_SIZE * SCOPE_RADIUS_FACTOR


    def on_resize(self, event=None):
        """Redraws and scales coordinates when the window is resized."""
        if event and event.widget != self.radar_canvas and event.widget != self:
             return
        
        old_size = self.previous_radar_size
        self.update_radar_dimensions()
        new_size = self.RADAR_SIZE

        scale_factor = new_size / old_size
        
        # --- CRITICAL FIX: SCALE PLANE COORDINATES ---
        if scale_factor != 1:
            for plane in self.planes:
                plane.x *= scale_factor
                plane.y *= scale_factor
                plane.dest_x *= scale_factor
                plane.dest_y *= scale_factor
                plane.trail = [] 

        self.previous_radar_size = new_size 

        self.radar_canvas.delete("static_grid") 
        self.draw_radar() 
        
    # --- FULLSCREEN METHODS ---
    def toggle_fullscreen(self, event=None):
        """Toggles the window between normal and fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)
        self.update_idletasks()
        self.on_resize()
        return "break" 

    def exit_fullscreen(self, event=None):
        """Exits fullscreen mode (bound to Escape key)."""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes('-fullscreen', False)
        self.on_resize()
        return "break"
    # ---------------------------


    def setup_ui(self):
        """Sets up the Tkinter widgets with responsive grid weights."""
        
        self.grid_columnconfigure(0, weight=2) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1) 

        # --- 1. Radar Canvas (Left Side) ---
        self.radar_canvas = tk.Canvas(self, width=VIRTUAL_SCOPE_MAX, height=VIRTUAL_SCOPE_MAX, 
                                      bg=COLOR_BG, highlightthickness=0)
        self.radar_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- 2. Console Frame (Right Side) ---
        console_frame = tk.Frame(self, bg=COLOR_BG)
        console_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1) 

        # Console Log Text Area
        log_label = tk.Label(console_frame, text="LOG & PILOT COMMS", bg=COLOR_BG, fg=COLOR_GLOW, font=("Courier", 12, "bold"))
        log_label.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        self.console_log = tk.Text(console_frame, height=20, width=50, bg=COLOR_BG, fg=COLOR_GLOW, 
                                   font=("Courier", 10), insertbackground=COLOR_GLOW, bd=2, relief=tk.FLAT, 
                                   padx=5, pady=5, borderwidth=1, highlightbackground=COLOR_DIM)
        self.console_log.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
        self.console_log.config(state=tk.DISABLED) 
        
        # Command Input
        input_frame = tk.Frame(console_frame, bg=COLOR_BG)
        input_frame.grid(row=2, column=0, sticky='ew')
        
        input_frame.grid_columnconfigure(1, weight=1) 
        
        input_label = tk.Label(input_frame, text="COMMAND:", bg=COLOR_BG, fg=COLOR_GLOW, font=("Courier", 10))
        input_label.grid(row=0, column=0, padx=(0, 5))

        self.command_entry = tk.Entry(input_frame, bg=COLOR_BG, fg=COLOR_GLOW, font=("Courier", 10), insertbackground=COLOR_GLOW)
        self.command_entry.grid(row=0, column=1, sticky='ew')
        self.command_entry.bind('<Return>', lambda event: self.handle_input())

        self.command_button = tk.Button(input_frame, text="EXECUTE", command=self.handle_input, 
                                        bg=COLOR_DIM, fg=COLOR_BG, activebackground=COLOR_GLOW, 
                                        activeforeground=COLOR_BG, font=("Courier", 10, "bold"), bd=1)
        self.command_button.grid(row=0, column=2, padx=(5, 0))


    def initialize_planes(self):
        """Creates starting aircraft using the VIRTUAL_SCOPE_MAX for positioning."""
        codes = ['FW190', 'SPITF', 'BF109', 'P51MUS', 'MOSSI']
        colors = ['#FFD700', '#A8E6CF', '#FF8C94', '#99C1DE', '#E0BBE4']
        
        VIRTUAL_CENTER = VIRTUAL_SCOPE_MAX / 2
        VIRTUAL_RADIUS = VIRTUAL_SCOPE_MAX * SCOPE_RADIUS_FACTOR

        for i, code in enumerate(codes):
            # Place planes randomly within 70% of the virtual radius
            r = random.uniform(0, VIRTUAL_RADIUS * 0.7)
            angle = random.uniform(0, 2 * math.pi)
            
            # Start position in the virtual (0-600) coordinate system
            x = VIRTUAL_CENTER + r * math.cos(angle)
            y = VIRTUAL_CENTER + r * math.sin(angle)
            
            speed = PLANE_BASE_SPEED + random.random() * 0.15 
            
            plane = Aircraft(code, x, y, speed, colors[i % len(colors)])
            self.planes.append(plane)
            self.set_new_random_destination(plane)


    def set_new_random_destination(self, plane):
        """Assigns a new, random destination within the virtual scope (0-600)."""
        VIRTUAL_CENTER = VIRTUAL_SCOPE_MAX / 2
        VIRTUAL_RADIUS = VIRTUAL_SCOPE_MAX * SCOPE_RADIUS_FACTOR
        
        r = random.uniform(VIRTUAL_RADIUS * 0.2, VIRTUAL_RADIUS)
        angle = random.uniform(0, 2 * math.pi)
        
        plane.dest_x = VIRTUAL_CENTER + r * math.cos(angle)
        plane.dest_y = VIRTUAL_CENTER + r * math.sin(angle)


    def log_to_console(self, message, source="SYSTEM"):
        """Appends a timestamped message to the console log."""
        timestamp = time.strftime("[%H:%M:%S]")
        
        self.console_log.config(state=tk.NORMAL)
        
        tag = source.lower()
        
        if tag not in self.console_log.tag_names():
            if source == "COMMAND":
                color = '#FFFF00' 
            elif source == "PILOT":
                color = '#00AAFF' 
            else:
                color = COLOR_GLOW 
            self.console_log.tag_config(tag, foreground=color)
            self.console_log.tag_config('dim_time', foreground=COLOR_DIM)

        self.console_log.insert(tk.END, f"{timestamp} ", 'dim_time')
        self.console_log.insert(tk.END, f"{source}: ", tag)
        self.console_log.insert(tk.END, f"{message}\n")
        
        self.console_log.config(state=tk.DISABLED)
        self.console_log.see(tk.END) 


    def parse_command(self, command_string):
        """
        Parses the command string, enforcing the simple 'CODE X Y' format.
        Returns coordinates in the VIRTUAL (0-600) system.
        """
        parts = command_string.split()
        
        if len(parts) != 3:
             return None, None, None, "ERROR: Invalid format. Use: [CODE] [X] [Y] (e.g., SPITF 400 150)."

        code = parts[0]
        
        try:
            new_x = float(parts[1])
            new_y = float(parts[2])
        except ValueError:
            return None, None, None, "ERROR: Coordinates must be numbers."

        return code, new_x, new_y, None


    def handle_input(self):
        """Processes the command from the entry field."""
        command_string = self.command_entry.get().strip().upper()
        self.command_entry.delete(0, tk.END) 

        if not command_string:
            return

        self.log_to_console(command_string, "COMMAND")
        
        # Note: new_x and new_y are now 0-600 virtual coordinates
        code, new_x, new_y, error_msg = self.parse_command(command_string)

        if error_msg:
            self.log_to_console(error_msg, "SYSTEM")
            return

        plane = next((p for p in self.planes if p.code == code), None)

        if not plane:
            self.log_to_console(f"ERROR: Aircraft code {code} not found.", "SYSTEM")
            return
        
        # Check against virtual scope limit (0-600)
        if not (0 <= new_x <= VIRTUAL_SCOPE_MAX and 0 <= new_y <= VIRTUAL_SCOPE_MAX):
            self.log_to_console(f"ERROR: Destination ({int(new_x)}, {int(new_y)}) outside of tactical scope (0-{VIRTUAL_SCOPE_MAX}).", "SYSTEM")
            self.log_to_console(f"ACFT {plane.code}: Negative, control. That position is outside sector limits.", "PILOT")
            return

        # Command successful: store the virtual coordinates
        plane.dest_x = new_x
        plane.dest_y = new_y

        self.log_to_console(f"ACFT {plane.code}: Roger, turning to intercept coordinates X={int(new_x)}, Y={int(new_y)}. Tally ho!", "PILOT")


    def distance(self, x1, y1, x2, y2):
        """Calculates Euclidean distance."""
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


    def get_scaled_position(self, plane):
        """Returns the plane's position scaled to the CURRENT canvas size."""
        scale_factor = self.RADAR_SIZE / VIRTUAL_SCOPE_MAX
        
        scaled_x = plane.x * scale_factor
        scaled_y = plane.y * scale_factor
        scaled_dest_x = plane.dest_x * scale_factor
        scaled_dest_y = plane.dest_y * scale_factor
        
        return scaled_x, scaled_y, scaled_dest_x, scaled_dest_y


    def move_plane(self, plane):
        """Updates the position of a single plane using VIRTUAL coordinates."""
        
        # Calculate distance and direction based on VIRTUAL coordinates (0-600)
        dist = self.distance(plane.x, plane.y, plane.dest_x, plane.dest_y)

        if dist > plane.speed:
            dx = plane.dest_x - plane.x
            dy = plane.dest_y - plane.y

            factor = plane.speed / dist
            
            # Update virtual position
            plane.x += dx * factor
            plane.y += dy * factor
            
            # Update trail with scaled coordinates for drawing
            scaled_x, scaled_y, _, _ = self.get_scaled_position(plane)
            plane.trail.append((scaled_x, scaled_y))
            if len(plane.trail) > 5: 
                plane.trail.pop(0)

        elif dist > 1: # Close enough to destination
            plane.x = plane.dest_x
            plane.y = plane.dest_y
            self.log_to_console(f"ACFT {plane.code}: I'm at the target area. Awaiting new orders.", "PILOT")
            self.set_new_random_destination(plane)
            plane.trail = [] 


    def draw_radar(self):
        """
        Draws the static radar elements using dynamic canvas sizes.
        UPDATED to add 'X' and 'Y' labels to the coordinate grid.
        """
        
        # 1. Main circle (Scope edge)
        self.radar_canvas.create_oval(
            self.CENTER - self.SCOPE_RADIUS, self.CENTER - self.SCOPE_RADIUS, 
            self.CENTER + self.SCOPE_RADIUS, self.CENTER + self.SCOPE_RADIUS, 
            outline=COLOR_GLOW, width=2, tags="static_grid"
        )

        # 2. Concentric Range Rings (Faded)
        ring_count = 3
        for i in range(1, ring_count + 1):
            r = (self.SCOPE_RADIUS / ring_count) * i
            self.radar_canvas.create_oval(
                self.CENTER - r, self.CENTER - r, 
                self.CENTER + r, self.CENTER + r, 
                outline=COLOR_DIM, width=1, dash=(3, 3), tags="static_grid"
            )

        # 3. Crosshairs (Faded)
        self.radar_canvas.create_line(0, self.CENTER, self.RADAR_SIZE, self.CENTER, fill=COLOR_DIM, width=1, tags="static_grid")
        self.radar_canvas.create_line(self.CENTER, 0, self.CENTER, self.RADAR_SIZE, fill=COLOR_DIM, width=1, tags="static_grid")

        # 4. Add Coordinate Markers and Labels
        tick_count = 6 
        virtual_interval = VIRTUAL_SCOPE_MAX / tick_count # 100 units
        visual_interval = self.RADAR_SIZE / tick_count 
        
        for i in range(tick_count + 1):
            coord_value = int(i * virtual_interval)
            pos = i * visual_interval
            
            # --- X-Axis Ticks and Labels (Bottom) ---
            self.radar_canvas.create_line(pos, self.CENTER - 4, pos, self.CENTER + 4, fill=COLOR_GLOW, width=1, tags="static_grid")
            
            if i < tick_count: 
                 # Added ' X' label
                 self.radar_canvas.create_text(
                    pos, self.RADAR_SIZE - 15, text=f"{coord_value} X", fill=COLOR_GLOW, 
                    font=("Courier", 8), anchor=tk.N, tags="static_grid"
                )
            
            # --- Y-Axis Ticks and Labels (Left) ---
            self.radar_canvas.create_line(self.CENTER - 4, pos, self.CENTER + 4, pos, fill=COLOR_GLOW, width=1, tags="static_grid")

            if i != 0 and i <= tick_count: 
                # Added ' Y' label and adjusted position slightly right
                self.radar_canvas.create_text(
                    8, pos, text=f"{coord_value} Y", fill=COLOR_GLOW, 
                    font=("Courier", 8), anchor=tk.W, tags="static_grid"
                )
                
        # Special case for the 600 X-coordinate label at the far right
        # Added ' X' label and adjusted position slightly left
        self.radar_canvas.create_text(
            self.RADAR_SIZE - 25, self.RADAR_SIZE - 15, text="600 X", fill=COLOR_GLOW, 
            font=("Courier", 8), anchor=tk.N, tags="static_grid"
        )


    def draw_sweep(self):
        """Draws the rotating sweep line."""
        
        x2 = self.CENTER + math.cos(self.sweep_angle) * self.SCOPE_RADIUS
        y2 = self.CENTER + math.sin(self.sweep_angle) * self.SCOPE_RADIUS
        
        self.radar_canvas.create_line(self.CENTER, self.CENTER, x2, y2, fill=COLOR_GLOW, width=3, tags="sweep_line")
        
        self.sweep_angle += SWEEP_SPEED
        if self.sweep_angle > 2 * math.pi:
            self.sweep_angle -= 2 * math.pi


    def draw_planes(self):
        """Draws the aircraft, trails, and labels, using scaled coordinates."""
        
        for plane in self.planes:
            # Get the current scaled coordinates for drawing
            scaled_x, scaled_y, scaled_dest_x, scaled_dest_y = self.get_scaled_position(plane)
            
            # Draw trail (uses already scaled coordinates saved in move_plane)
            for i, (tx, ty) in enumerate(plane.trail):
                alpha = i / (len(plane.trail) + 1)
                trail_color = self.fade_color(plane.color, alpha)
                self.radar_canvas.create_oval(
                    tx - 1, ty - 1, tx + 1, ty + 1, fill=trail_color, outline='', tags="plane_data"
                )

            # Draw the plane dot (the primary return)
            self.radar_canvas.create_oval(
                scaled_x - PLANE_SIZE/2, scaled_y - PLANE_SIZE/2, 
                scaled_x + PLANE_SIZE/2, scaled_y + PLANE_SIZE/2, 
                fill=plane.color, outline=COLOR_GLOW, width=1, 
                tags="plane_data"
            )

            # Draw the destination marker (dim cross)
            self.radar_canvas.create_line(
                scaled_dest_x - 5, scaled_dest_y, scaled_dest_x + 5, scaled_dest_y, fill=COLOR_DIM, tags="plane_data"
            )
            self.radar_canvas.create_line(
                scaled_dest_x, scaled_dest_y - 5, scaled_dest_x, scaled_dest_y + 5, fill=COLOR_DIM, tags="plane_data"
            )

            # Draw the plane code label (just below the dot)
            self.radar_canvas.create_text(
                scaled_x, scaled_y + 10, text=plane.code, fill=plane.color, 
                font=("Courier", 8), tags="plane_data"
            )
            
            # Draw X, Y coordinates for the aircraft
            coords_text = f"X={int(plane.x)}, Y={int(plane.y)}"
            self.radar_canvas.create_text(
                scaled_x, scaled_y + 20, text=coords_text, fill=COLOR_DIM, 
                font=("Courier", 7), tags="plane_data"
            )

    def fade_color(self, hex_color, alpha):
        """A simplified way to make a color appear faded by blending towards black."""
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        alpha = max(0.0, min(1.0, alpha))
        
        r_faded = int(r * (1 - alpha))
        g_faded = int(g * (1 - alpha))
        b_faded = int(b * (1 - alpha))

        return f"#{r_faded:02x}{g_faded:02x}{b_faded:02x}"


    def animate(self):
        """The main animation loop."""
        
        self.radar_canvas.delete("plane_data") 
        self.radar_canvas.delete("sweep_line") 
        
        self.update_radar_dimensions() 
        
        for plane in self.planes:
            self.move_plane(plane)
            
        self.draw_planes()
        self.draw_sweep()
        
        self.after(33, self.animate)


# --- Initial Setup ---
if __name__ == "__main__":
    app = RadarApp()
    app.mainloop()