import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("192.168.1.3", 5000))

print("Sniffing raw UDP packets on port 5000...")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"Packet from {addr}, length={len(data)} bytes")
