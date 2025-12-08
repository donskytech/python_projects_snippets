import socket
import struct
import numpy as np
import cv2 
import time
from collections import defaultdict

# --- Configuration (Must match ESP32 C++ Code) ---
UDP_IP = "192.168.1.3"  
UDP_PORT = 5000     
MAX_INCOMPLETE_FRAMES = 2 # Aggressively discard old frames

# === Image Parameters (QQVGA RGB565) ===
FRAME_WIDTH = 160
FRAME_HEIGHT = 120
EXPECTED_SIZE = FRAME_WIDTH * FRAME_HEIGHT * 2 # 38400 bytes

frame_buffer = {}
HEADER_SIZE = 10 # Must match C++ header size
MAX_PACKET_SIZE = 2048

# --- RGB565 Conversion Function (Confirmed Working Logic) ---

def convert_rgb565_to_bgr(rgb565_data):
    """
    Big Endian byte swap (>u2) + B5G6R5 color channel swap.
    """
    # 1. Convert byte data to a NumPy array of unsigned 16-bit integers
    rgb565_1d = np.frombuffer(rgb565_data, dtype='>u2') 
    
    if rgb565_1d.size * 2 != EXPECTED_SIZE:
        print(f"❌ Error: Reassembled size ({rgb565_1d.size * 2}) does not match expected size ({EXPECTED_SIZE})")
        return None

    # 2. Extract B, G, R components (B5 G6 R5 assumed after byte swap)
    R = (rgb565_1d & 0x1F)
    G = ((rgb565_1d >> 5) & 0x3F)
    B = ((rgb565_1d >> 11) & 0x1F)
    
    # 3. Scale components to 8-bit (0-255) range
    R = (R * 255) // 31
    G = (G * 255) // 63
    B = (B * 255) // 31

    # 4. Create the final BGR image array for OpenCV
    bgr_data = np.stack((B.astype(np.uint8), G.astype(np.uint8), R.astype(np.uint8)), axis=-1)
    bgr_frame = bgr_data.reshape((FRAME_HEIGHT, FRAME_WIDTH, 3))
    
    return bgr_frame

# --- Helper Functions ---

def display_frame_opencv(bgr_frame, packet_id):
    """Displays the BGR frame."""
    if bgr_frame is not None:
        # Scale the QQVGA image up for better viewing (4x scale)
        display_frame = cv2.resize(bgr_frame, (FRAME_WIDTH * 4, FRAME_HEIGHT * 4), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("ESP32-CAM RGB565 Stream (QQVGA 160x120)", display_frame)
        
        # Stability fix
        if cv2.waitKey(5) == 27:  
            return False 
        return True
    else:
        return True


def reconstruct_frame(packet_id, total_len, fragments_dict):
    """Reconstructs the raw RGB565 frame from its fragments."""
    if len(fragments_dict) == 0:
        return None 
        
    rgb_data = bytearray(total_len)
    filled_bytes = 0
    
    # Copy fragments into the correct position
    for offset, data in fragments_dict.items():
        write_len = min(len(data), total_len - offset)
        if write_len > 0:
            rgb_data[offset:offset + write_len] = data[:write_len]
            filled_bytes += write_len
    
    if filled_bytes == total_len:
        # Removed FPS print here for performance
        return bytes(rgb_data)
    else:
        return None

# --- Main Listener ---

def main_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Maximize socket buffer size
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8388608) 
    
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError as e:
        print(f"🛑 ERROR: Failed to bind to {UDP_IP}:{UDP_PORT}.")
        return
    
    print(f"👂 Listening for QQVGA RGB565 stream on {UDP_IP}:{UDP_PORT}. EXPECTED SIZE: {EXPECTED_SIZE} bytes.")

    running = True
    frame_count = 0
    last_time = time.time()
    
    while running:
        try:
            data, addr = sock.recvfrom(MAX_PACKET_SIZE) 
            
            header = data[:HEADER_SIZE]
            fragment_data = data[HEADER_SIZE:]
            
            # Unpack the 10-byte header
            try:
                packet_id, total_len, start_offset = struct.unpack('<HII', header) 
            except struct.error:
                continue

            # --- Assembly Logic ---
            if packet_id not in frame_buffer:
                frame_buffer[packet_id] = (total_len, {})
                
                # Cleanup: Discard oldest frame if buffer is too full
                if len(frame_buffer) > MAX_INCOMPLETE_FRAMES:
                    oldest_id = min(frame_buffer.keys()) 
                    if oldest_id != packet_id:
                        del frame_buffer[oldest_id]
                        
            fragments_dict = frame_buffer[packet_id][1]
            fragments_dict[start_offset] = fragment_data

            # --- Check for Completion and Convert ---
            assembled_rgb565 = reconstruct_frame(packet_id, total_len, fragments_dict)

            if assembled_rgb565 is not None:
                # Frame assembled: Convert and display
                bgr_frame = convert_rgb565_to_bgr(assembled_rgb565)
                
                running = display_frame_opencv(bgr_frame, packet_id) 
                
                # FPS Calculation (Print less frequently for better speed)
                frame_count += 1
                if frame_count % 10 == 0:
                    now = time.time()
                    fps = 10.0 / (now - last_time)
                    last_time = now
                    print(f"FPS: {fps:.1f}")
                
                del frame_buffer[packet_id]
                
        except KeyboardInterrupt:
            running = False
        except Exception:
            pass 

    cv2.destroyAllWindows()
    print("Stream receiver closed.")

if __name__ == '__main__':
    main_listener()