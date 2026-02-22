import socket
import threading
import sys

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
    GRID_APP_IP = "192.168.0.200"
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

def receive_clicks():
    """Thread function to receive click events from the grid app"""
    global running
    while running:
        try:
            receive_socket.settimeout(1.0)  # Timeout to check running flag periodically
            data, addr = receive_socket.recvfrom(1024)
            message = data.decode()
            print(f"\n[RECEIVED from {addr[0]}:{addr[1]}] {message}")
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

# Start receive thread
receive_thread = threading.Thread(target=receive_clicks, daemon=True)
receive_thread.start()

# Main loop for user input
try:
    while running:
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

except KeyboardInterrupt:
    print("\nShutting down...")
    running = False

# Cleanup
receive_socket.close()
send_socket.close()
print("UDP Controller stopped")
sys.exit()
