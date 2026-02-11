import pygame
import sys
import socket

# Initialize pygame
pygame.init()

# Window settings
WINDOW_SIZE = 500
WINDOW = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
pygame.display.set_caption("4x4 Grid")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 150, 255)
GREY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Grid settings
BOX_SIZE = 100
GRID_SIZE = 4
GRID_OFFSET = (WINDOW_SIZE - (BOX_SIZE * GRID_SIZE)) // 2
INNER_BOX_SIZE = 70
INNER_OFFSET = (BOX_SIZE - INNER_BOX_SIZE) // 2

# Box color interface - stores color for each box
box_colors = [[WHITE for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

# UDP Configuration
UDP_SEND_IP = "127.0.0.1"  # localhost for sending click events
UDP_SEND_PORT = 5005
UDP_RECEIVE_PORT = 5006  # port to listen for color change commands

# Create UDP sockets
udp_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_receive_socket.setblocking(False)  # Non-blocking so game loop doesn't wait
udp_receive_socket.bind(("", UDP_RECEIVE_PORT))

# Color name to RGB mapping for external control
color_map = {
    "WHITE": WHITE,
    "BLACK": BLACK,
    "BLUE": BLUE,
    "GREY": GREY,
    "RED": RED,
    "GREEN": GREEN
}


# Clock for controlling frame rate
clock = pygame.time.Clock()

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # Check each box to see if click is in the black inner area
            for row in range(GRID_SIZE):
                for col in range(GRID_SIZE):
                    box_x = GRID_OFFSET + col * BOX_SIZE
                    box_y = GRID_OFFSET + row * BOX_SIZE
                    inner_x = box_x + INNER_OFFSET
                    inner_y = box_y + INNER_OFFSET
                    # Check if click is within the inner black box
                    if (inner_x <= mouse_x <= inner_x + INNER_BOX_SIZE and
                        inner_y <= mouse_y <= inner_y + INNER_BOX_SIZE):
                        box_number = row * GRID_SIZE + col
                        print(f"Black portion clicked - Box: Row {row}, Column {col}, Box Number: {box_number}")
                        box_colors[row][col] = GREEN
                        # Send UDP message with click info
                        message = f"CLICK:{box_number},{row},{col}"
                        udp_send_socket.sendto(message.encode(), (UDP_SEND_IP, UDP_SEND_PORT))
    
    # Check for incoming UDP messages to change box colors
    try:
        data, addr = udp_receive_socket.recvfrom(1024)
        message = data.decode().strip()
        # Expected format: "box_number,color" or "row,col,color"
        parts = message.split(',')
        if len(parts) == 2:
            # Format: box_number,color
            box_number = int(parts[0])
            color_name = parts[1].upper()
            if color_name in color_map and 0 <= box_number < GRID_SIZE * GRID_SIZE:
                row = box_number // GRID_SIZE
                col = box_number % GRID_SIZE
                box_colors[row][col] = color_map[color_name]
                print(f"UDP: Changed box {box_number} (row {row}, col {col}) to {color_name}")
        elif len(parts) == 3:
            # Format: row,col,color
            row = int(parts[0])
            col = int(parts[1])
            color_name = parts[2].upper()
            if color_name in color_map and 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                box_colors[row][col] = color_map[color_name]
                print(f"UDP: Changed box at row {row}, col {col} to {color_name}")
    except BlockingIOError:
        # No data available, continue
        pass
    except Exception as e:
        print(f"Error processing UDP message: {e}")
    
    # Fill background
    WINDOW.fill(GREY)
    
    # Draw 4x4 grid of boxes
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            x = GRID_OFFSET + col * BOX_SIZE
            y = GRID_OFFSET + row * BOX_SIZE
            # Draw outer box with color from box_colors interface
            pygame.draw.rect(WINDOW, box_colors[row][col], (x, y, BOX_SIZE, BOX_SIZE))
            pygame.draw.rect(WINDOW, BLACK, (x, y, BOX_SIZE, BOX_SIZE), 2)
            # Draw inner black box (70x70, centered)
            pygame.draw.rect(WINDOW, BLACK, (x + INNER_OFFSET, y + INNER_OFFSET, INNER_BOX_SIZE, INNER_BOX_SIZE))
    
    # Update display
    pygame.display.flip()
    clock.tick(60)

# Close UDP sockets
udp_send_socket.close()
udp_receive_socket.close()

# Quit pygame
pygame.quit()
sys.exit()
