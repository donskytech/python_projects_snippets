import socket
import binascii

LISTEN_IP = "192.168.1.3"
LISTEN_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))

print("Sniffing headers on", LISTEN_IP, LISTEN_PORT)

while True:
    data, addr = sock.recvfrom(4096)

    print("\nPacket from", addr, "length:", len(data))
    print("Hex dump (first 32 bytes):", binascii.hexlify(data[:32]))
