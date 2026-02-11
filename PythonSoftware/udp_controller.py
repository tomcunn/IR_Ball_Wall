import socket
import threading
import sys

# UDP Configuration
GRID_APP_IP = "127.0.0.1"
SEND_PORT = 5006  # Port to send color commands to grid app
RECEIVE_PORT = 5005  # Port to receive click events from grid app

# Create UDP sockets
send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_socket.bind(("", RECEIVE_PORT))

print("UDP Controller Started")
print(f"Listening for click events on port {RECEIVE_PORT}")
print(f"Sending color commands to {GRID_APP_IP}:{SEND_PORT}")
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
            print(f"\n[RECEIVED] {message}")
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
