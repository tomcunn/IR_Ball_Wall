import socket
import threading
import sys
from keyboard import send
import pygame
import numpy as np
from datetime import datetime

def get_local_ip():
    """Get the local IP address of this computer"""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Unable to determine"

# ============================================================
# CONFIGURATION: Set to True for simulator, False for ESP32
# ============================================================
USE_SIMULATOR = True  # Change this to switch modes
# ============================================================

if USE_SIMULATOR:
    # ***** SIMULATOR_CONFIGURATION ***********
    GRID_APP_IP = "127.0.0.1"
    SEND_PORT = 5006  # Port to send color commands to grid app
    RECEIVE_PORT = 5005  # Port to receive click events from grid app
    print("MODE: SIMULATOR")
else:
    # ***** ESP32_CONFIGURATION ***********
    GRID_APP_IP = "192.168.0.156"
    SEND_PORT = 5008  # Port to send color commands to grid app
    RECEIVE_PORT = 5007  # Port to receive click events from grid app
    print("MODE: ESP32 HARDWARE")


# Create UDP sockets
send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_socket.bind(("", RECEIVE_PORT))

print("UDP Controller Started")
print(f"This computer's IP address: {get_local_ip()}")
print(f"Listening for click events on port {RECEIVE_PORT}")
print(f"Sending color commands to {GRID_APP_IP}:{SEND_PORT}")
print("\nIMPORTANT: Make sure ESP32 is sending to this computer's IP address!")
print("\nAvailable colors: WHITE, BLACK, BLUE, GREY, RED, GREEN")
print("\nCommands:")
print("  - Change by box number: <box_number>,<color>  (e.g., 5,RED)")
print("  - Type 'quit' to exit\n")

# Flag to control threads
running = True

# ============================================================
# CHIME COUNTER GUI CLASS
# ============================================================
class ChimeCounter:
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        
        # Window settings
        self.width = 400
        self.height = 300
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("LED Ball Wall Control Panel")
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (0, 120, 215)
        self.GREEN = (0, 200, 0)
        self.RED = (255, 0, 0)
        self.GREY = (128, 128, 128)
        self.LIGHT_GREY = (211, 211, 211)
        
        # Color mapping for box colors
        self.color_map = {
            "WHITE": self.WHITE,
            "BLACK": self.BLACK,
            "BLUE": self.BLUE,
            "GREEN": self.GREEN,
            "RED": self.RED,
            "GREY": self.GREY
        }
        
        # Fonts
        self.title_font = pygame.font.Font(None, 48)
        self.counter_font = pygame.font.Font(None, 72)
        self.info_font = pygame.font.Font(None, 24)
        self.box_font = pygame.font.Font(None, 14)  # Small font for box text
        
        # Counter
        self.counter = 0
        self.frame_counter = 0 
        self.timer = 0  # Timer in 0.1 second increments
        
        # Box colors array (16 boxes)
        self.box_colors = ["WHITE"] * 16
        self.box_colors_previous = ["WHITE"] * 16
        self.box_hits = [0] * 16
        self.box_points = [0] * 16

        self.total_points = 0
        
        # Animation
        self.flash_timer = 0
        self.flash_duration = 500  # milliseconds
        
        # Clock
        self.clock = pygame.time.Clock()
        
        # Generate chime sound
        self.chime_sound = self.generate_chime()
    
    def generate_chime(self) -> pygame.mixer.Sound:
        """Generate a pleasant chime sound"""
        sample_rate = 22050
        duration = 0.5
        
        # Create harmonious frequencies (C major chord: C, E, G)
        frequencies = [523.25, 659.25, 783.99]  # C5, E5, G5
        
        samples = np.zeros(int(sample_rate * duration))
        
        for freq in frequencies:
            t = np.linspace(0, duration, int(sample_rate * duration))
            # Create note with exponential decay envelope
            envelope = np.exp(-3 * t)
            note = np.sin(2 * np.pi * freq * t) * envelope
            samples += note / len(frequencies)
        
        # Normalize
        samples = samples * 32767 / np.max(np.abs(samples))
        samples = samples.astype(np.int16)
        
        # Convert to stereo
        stereo_samples = np.column_stack((samples, samples))
        
        sound = pygame.sndarray.make_sound(stereo_samples)
        return sound
    
    def play_chime(self):
        """Play the chime sound"""
        self.chime_sound.play()
    
    def receive_command(self, command: int):
        self.counter += 1
        #Add in the number of hits here
        self.box_hits[command] += 1

        #Set the scoring for the game
        if(self.box_colors[command] == "GREEN"):
            self.box_points[command] += 1
        elif(self.box_colors[command] == "RED"):
            self.box_points[command] += 2
        elif(self.box_colors[command] == "BLUE"):
            self.box_points[command] += 3

        self.total_points = sum(self.box_points)

        self.flash_timer = pygame.time.get_ticks()
        self.play_chime()
    
    def draw_grid(self):
        """Draw a 4x4 grid of boxes (20px each, 3px spacing)"""
        box_size = 60
        spacing = 3
        start_x = 10
        start_y = 10
        
        for row in range(4):
            for col in range(4):
                box_index = row * 4 + col
                # Calculate box position
                x = start_x + col * (box_size + spacing)
                y = start_y + row * (box_size + spacing)
                # Get color for this box
                color_name = self.box_colors[box_index]
                color = self.color_map.get(color_name, self.WHITE)
                # Draw box
                pygame.draw.rect(self.screen, color, (x, y, box_size, box_size))
                # Draw border
                pygame.draw.rect(self.screen, self.BLACK, (x, y, box_size, box_size), 1)
                
                # Draw hits and points inside the box
                hits_text = self.box_font.render(f"H:{self.box_hits[box_index]}", True, self.BLACK)
                points_text = self.box_font.render(f"P:{self.box_points[box_index]}", True, self.BLACK)
                
                # Position text in upper and lower half of box
                hits_rect = hits_text.get_rect(center=(x + box_size // 2, y + box_size // 3))
                points_rect = points_text.get_rect(center=(x + box_size // 2, y + 2 * box_size // 3))
                
                self.screen.blit(hits_text, hits_rect)
                self.screen.blit(points_text, points_rect)
    
    def draw(self):
        """Draw the GUI"""
        # Background color (light grey)
        self.screen.fill(self.LIGHT_GREY)
        
        # Draw grid
        self.draw_grid()
        
        # Draw timer at position (300, 5)
        # Increment timer every 6 frames (0.1 seconds at 60 FPS)
        if self.frame_counter % 6 == 0:
            self.timer += 1
        timer_text = self.info_font.render(f"Timer: {self.timer * 0.1:.1f}s", True, self.BLACK)
        self.screen.blit(timer_text, (300, 5))
        
        # Draw total points below timer
        points_text = self.info_font.render(f"Points: {self.total_points}", True, self.BLACK)
        self.screen.blit(points_text, (300, 30))
        
        pygame.display.flip()
    
    def RunGameEngine(self):
        self.frame_counter += 1
        self.seconds = self.frame_counter // 60

        #The starting box colors
        self.box_colors[0] = "GREEN"
        self.box_colors[1] = "GREEN"
        self.box_colors[2] = "GREEN"
        self.box_colors[3] = "GREEN"
        self.box_colors[4] = "GREEN"
        self.box_colors[5] = "RED"
        self.box_colors[6] = "RED"
        self.box_colors[7] = "GREEN"
        self.box_colors[8] = "GREEN"
        self.box_colors[9] = "RED"
        self.box_colors[10] = "RED"
        self.box_colors[11] = "GREEN"
        self.box_colors[12] = "GREEN"
        self.box_colors[13] = "GREEN"
        self.box_colors[14] = "GREEN"
        self.box_colors[15] = "GREEN"

        if(self.seconds >= 20):
            self.box_colors[0] = "RED"
            self.box_colors[1] = "RED"
            self.box_colors[2] = "RED"
            self.box_colors[3] = "RED"
            self.box_colors[4] = "RED"
            self.box_colors[5] = "GREEN"
            self.box_colors[6] = "GREEN"
            self.box_colors[7] = "RED"
            self.box_colors[8] = "RED"
            self.box_colors[9] = "GREEN"
            self.box_colors[10] = "GREEN"
            self.box_colors[11] = "BLUE"
            self.box_colors[12] = "BLUE"
            self.box_colors[13] = "BLUE"
            self.box_colors[14] = "BLUE"
            self.box_colors[15] = "BLUE"

        if(self.seconds >= 40):
            self.box_colors[0] = "GREEN"
            self.box_colors[1] = "GREEN"
            self.box_colors[2] = "GREEN"
            self.box_colors[3] = "GREEN"
            self.box_colors[4] = "GREEN"
            self.box_colors[5] = "GREEN"
            self.box_colors[6] = "GREEN"
            self.box_colors[7] = "GREEN"
            self.box_colors[8] = "GREEN"
            self.box_colors[9] = "GREEN"
            self.box_colors[10] = "GREEN"
            self.box_colors[11] = "GREEN"
            self.box_colors[12] = "GREEN"
            self.box_colors[13] = "GREEN"
            self.box_colors[14] = "GREEN"
            self.box_colors[15] = "GREEN"

    def update(self):
        """Update the GUI (non-blocking)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                global running
                running = False

        self.RunGameEngine()
        #check for box color updates and send commands if needed
        self.CheckforBoxColorUpdates()

        self.draw()
        self.clock.tick(60)  # 60 FPS

    #Create a method that checks to see if any of the boxes have changed color
    #this allows us to only send updates when necessary, instead of every frame
    def CheckforBoxColorUpdates(self):
        """Check if any box colors have changed and send updates if needed"""
        for i in range(16):
            if self.box_colors[i] != self.box_colors_previous[i]:
                # Send update for this box
                color = self.box_colors[i]
                command = f"{i},{color}"
                send_color_command(command)
                # Update previous colors
                self.box_colors_previous[i] = self.box_colors[i]

# Initialize ChimeCounter GUI
chime_gui = ChimeCounter()

# Timer for periodic color commands
last_color_command_time = 0

# ============================================================
# UDP THREADS
# ============================================================

def receive_hits():
    """Thread function to receive click events from the grid app"""
    global running
    while running:
        try:
            receive_socket.settimeout(1.0)  # Timeout to check running flag periodically
            data, addr = receive_socket.recvfrom(1024)
            message = data.decode()
            print(f"\n[RECEIVED from {addr[0]}:{addr[1]}] {message}")
            
            # Check if the message contains 0x16 command
            try:
                # Try to parse
                if message.startswith("H:"):
                    value = int(message[2:])  # Get the number after "H:"
                    chime_gui.receive_command(value)
            except:
                pass  # Not a hex/int value, ignore for chime
            
            print("Enter command: ", end="", flush=True)
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"\nError receiving data: {e}")
            break

def send_color_command(command):
    """Send a color change command to the grid app"""
    try:
        send_socket.sendto(command.encode(), (GRID_APP_IP, SEND_PORT))
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[SENT {timestamp}] {command}")
    except Exception as e:
        print(f"Error sending command: {e}")

def input_thread():
    """Thread for handling user input"""
    global running
    while running:
        try:
            user_input = input("Enter command: ").strip()
            
            if user_input.lower() == 'quit':
                running = False
                break
            
            if user_input:
                # Validate format
                parts = user_input.split(',')
                if len(parts) in [2, 3]:
                    send_color_command(user_input)
                else:
                    print("Invalid format. Use: <box_number>,<color> or <row>,<col>,<color>")
        except:
            break

# Start threads
receive_thread = threading.Thread(target=receive_hits, daemon=True)
receive_thread.start()

input_thread_obj = threading.Thread(target=input_thread, daemon=True)
input_thread_obj.start()

# Main GUI loop
try:
    while running:
        chime_gui.update()

except KeyboardInterrupt:
    print("\nShutting down...")
    running = False

# Cleanup
pygame.quit()
receive_socket.close()
send_socket.close()
print("UDP Controller stopped")
sys.exit()
