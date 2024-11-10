import network
import socket
import os
from machine import Pin, SPI
import sdcard

# Configure Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="sam", password="12345678")

# Wait for the Access Point to be active
while not ap.active():
    pass
print("Access Point is active with IP:", ap.ifconfig()[0])

# Initialize SPI and SD Card
spi = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT)
sd = sdcard.SDCard(spi, cs)
vfs = os.VfsFat(sd)
os.mount(vfs, "/sd")
print("SD card mounted successfully.")

# Function to list files in a directory
def list_files(path):
    if path == "/":
        path = "/sd"
    
    html = """
    <html>
    <head><title>SD Card Browser</title></head>
    <body>
        <h1>SD Card Files</h1>
        <ul>
    """
    if path != "/sd":
        parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/sd"
        html += f"<li><a href='?path={parent_path}'>[Back]</a></li>"

    for item in os.listdir(path):
        if item.startswith("."):
            continue
        item_path = f"{path}/{item}"
        
        # Check if the item is a directory or a file
        if os.stat(item_path)[0] & 0x4000:  # Directory
            html += f"<li><a href='?path={item_path}'>{item}/</a></li>"
        else:
            # Add ?path= prefix for files to ensure they open directly
            html += f"<li><a href='?path={item_path}'>{item}</a></li>"
    
    html += "</ul></body></html>"
    return html


# Function to serve a file in binary mode (for images)
def serve_file(cl, path):
    try:
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif path.endswith(".png"):
            content_type = "image/png"
        elif path.endswith(".gif"):
            content_type = "image/gif"
        else:
            content_type = "text/plain"

        cl.send(f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n".encode())

        with open(path, "rb") as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                cl.send(data)
                
    except Exception as e:
        print(f"Failed to serve file {path}: {e}")
        cl.send(b"HTTP/1.1 404 Not Found\r\n\r\n")

# Main function to handle requests
def serve_page():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Server listening on:", addr)

    while True:
        cl, addr = s.accept()
        print("Client connected from:", addr)
        cl_file = cl.makefile("rwb", 0)
        request_line = cl_file.readline().decode()
        
        # Default path to root
        path = "/sd"
        
        # Check for the path query parameter
        if "?" in request_line:
            try:
                query = request_line.split()[1].split("?")[1]
                for param in query.split("&"):
                    if param.startswith("path="):
                        path = param.split("=")[1]
                        if path == "":
                            path = "/sd"
            except Exception as e:
                print(f"Error parsing path: {e}")
        
        # Determine if the path is a file or directory
        try:
            if not os.stat(path)[0] & 0x4000:
                # If it's a file, serve it directly
                serve_file(cl, path)
            else:
                # If it's a directory, list the directory contents
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{list_files(path)}"
                cl.send(response.encode())
        
        except OSError:
            cl.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
        
        cl.close()

# Run the server
serve_page()
