import socket

ESP32_IP = "192.168.8.120"
ESP32_PORT = 4210

sock = None

def send_start():
    global sock
    if sock is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = "start "
    sock.sendto(message.encode(), (ESP32_IP, ESP32_PORT))
    print(f"Sent: {message}")

def on_close():
    global sock
    if sock is not None:
        sock.close()
        sock = None
    print("Socket closed")



