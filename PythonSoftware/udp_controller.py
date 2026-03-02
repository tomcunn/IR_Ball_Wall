import socket
import threading
import sys
import pygame
import numpy as np

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
USE_SIMULATOR = False  # Change this to switch modes
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
print("  - Change by position: <row>,<col>,<color>  (e.g., 1,1,BLUE)")
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
        pygame.display.set_caption("0x16 Command Counter")
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (0, 120, 215)
        self.GREEN = (0, 200, 0)
        
        # Fonts
        self.title_font = pygame.font.Font(None, 48)
        self.counter_font = pygame.font.Font(None, 72)
        self.info_font = pygame.font.Font(None, 24)
        
        # Counter
        self.counter = 0
        
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
        """Process received command"""
        if command == 0x16:
            self.counter += 1
            self.flash_timer = pygame.time.get_ticks()
            self.play_chime()
    
    def draw(self):
        """Draw the GUI"""
        current_time = pygame.time.get_ticks()
        
        # Determine if we should flash
        is_flashing = (current_time - self.flash_timer) < self.flash_duration
        
        # Background color
        bg_color = self.GREEN if is_flashing else self.WHITE
        self.screen.fill(bg_color)
        
        # Draw title
        title_text = self.title_font.render("0x16 Command Counter", True, self.BLACK)
        title_rect = title_text.get_rect(center=(self.width // 2, 60))
        self.screen.blit(title_text, title_rect)
        
        # Draw counter
        counter_text = self.counter_font.render(str(self.counter), True, self.BLUE)
        counter_rect = counter_text.get_rect(center=(self.width // 2, 150))
        self.screen.blit(counter_text, counter_rect)
        
        # Draw info
        info_text = self.info_font.render("Waiting for 0x16 commands...", True, self.BLACK)
        info_rect = info_text.get_rect(center=(self.width // 2, 240))
        self.screen.blit(info_text, info_rect)
        
        pygame.display.flip()
    
    def update(self):
        """Update the GUI (non-blocking)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                global running
                running = False
        
        self.draw()
        self.clock.tick(60)  # 60 FPS

# Initialize ChimeCounter GUI
chime_gui = ChimeCounter()

# ============================================================
# UDP THREADS
# ============================================================

def receive_clicks():
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
                # Try to parse as hex value
                if message.startswith("0x"):
                    value = int(message, 16)
                    chime_gui.receive_command(value)
                # Also check for decimal 22 (0x16 in decimal)
                elif message.isdigit() and int(message) == 22:
                    chime_gui.receive_command(0x16)
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
        print(f"[SENT] {command}")
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
receive_thread = threading.Thread(target=receive_clicks, daemon=True)
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
