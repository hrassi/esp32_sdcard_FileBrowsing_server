How it Works:
The ESP32 acts as a simple HTTP server that clients (like your phone or computer) can connect to via Wi-Fi.
The server serves both directory listings and image files stored on the SD card.
Clients can click on folders to navigate through the SD card, and clicking on image files opens them directly in the browser.
In essence, this script provides a very basic web interface to browse files and view images stored on an SD card connected to an ESP32.


1. Access Point Setup
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="sam", password="12345678")
network.WLAN(network.AP_IF): Initializes the ESP32 as an Access Point (AP), allowing devices to connect to it like a Wi-Fi router.
ap.active(True): Activates the access point.
ap.config(essid="sam", password="12345678"): Configures the access point with an SSID (sam) and password (12345678).
The script waits for the Access Point to become active, then prints the IP address (ap.ifconfig()[0]) that clients (like your phone or computer) can use to connect to the ESP32.

2. SD Card Initialization
spi = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT)
sd = sdcard.SDCard(spi, cs)
vfs = os.VfsFat(sd)
os.mount(vfs, "/sd")
SPI Initialization: Sets up the SPI bus to communicate with the SD card. The SPI pins (SCK, MOSI, and MISO) are configured along with the baud rate. These pins (18, 23, and 19) are the hardware SPI pins on the ESP32.
sdcard.SDCard(spi, cs): Initializes the SD card using the SPI interface and the Chip Select (CS) pin.
os.VfsFat(sd): Creates a virtual file system (VFS) over the SD card, allowing access to files on the SD card using regular file system functions.
os.mount(vfs, "/sd"): Mounts the virtual file system at /sd, making it accessible like any other directory in the file system.
This setup ensures that the ESP32 can access and read from the SD card.

3. list_files Function
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
The list_files function generates an HTML page that lists all files and directories in the given path.
If the requested path is the root ("/"), it defaults to the /sd directory.
    if path != "/sd":
        parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/sd"
        html += f"<li><a href='?path={parent_path}'>[Back]</a></li>"
If the path is not the root (/sd), a "Back" link is generated to navigate to the parent directory.
    for item in os.listdir(path):
        if item.startswith("."):
            continue
        item_path = f"{path}/{item}"
        
        if os.stat(item_path)[0] & 0x4000:  # Directory
            html += f"<li><a href='?path={item_path}'>{item}/</a></li>"
        else:
            html += f"<li><a href='?path={item_path}'>{item}</a></li>"
    
    html += "</ul></body></html>"
    return html
os.listdir(path): Lists all files and directories in the given path.
os.stat(item_path): Retrieves file stats. The 0x4000 check identifies whether an item is a directory (directories return this flag in the first byte of their status).
For directories, a link is generated to browse the folder. For files, a link is generated to open or download the file.
The HTML structure is returned, forming the list of files and folders.
4. serve_file Function
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
serve_file handles serving image files.
The function checks the file extension (.jpg, .png, .gif) to determine the correct content type for the file (used in the HTTP response headers).
        with open(path, "rb") as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                cl.send(data)
open(path, "rb"): Opens the file in binary read mode ("rb").
The file is read in chunks of 1024 bytes and sent over the socket to the client.
    except Exception as e:
        print(f"Failed to serve file {path}: {e}")
        cl.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
If an error occurs while reading or sending the file, a 404 Not Found response is sent to the client.
5. serve_page Function (Main Request Handling)
def serve_page():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Server listening on:", addr)
The server listens on all available network interfaces (0.0.0.0) and port 80 for HTTP connections.
socket.getaddrinfo() retrieves address information (IP address and port).
s.bind() binds the server to the IP address and port.
s.listen(1) prepares the server to listen for incoming connections (with a backlog of 1 client).
    while True:
        cl, addr = s.accept()
        print("Client connected from:", addr)
        cl_file = cl.makefile("rwb", 0)
        request_line = cl_file.readline().decode()
s.accept(): Accepts a new incoming connection from a client.
cl.makefile("rwb", 0): Creates a file-like object for the client socket to read and write data.
request_line = cl_file.readline().decode(): Reads the first line of the HTTP request (which contains the requested URL).
        path = "/sd"
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
If the URL contains a query (e.g., ?path=/sd/images), the path is extracted from the query string.
        try:
            if not os.stat(path)[0] & 0x4000:
                serve_file(cl, path)
            else:
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{list_files(path)}"
                cl.send(response.encode())
os.stat(path)[0] & 0x4000: Checks whether the requested path is a file or a directory.
If it's a file, the serve_file() function is called to serve the file.
If it's a directory, the list_files() function is called to display the list of files and directories.
        except OSError:
            cl.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
        
        cl.close()
If the requested path does not exist, a 404 Not Found response is sent to the client.
cl.close() closes the client connection after handling the request.
6. Running the Server
serve_page()
serve_page() is called to start the server, and it runs in an infinite loop to handle incoming client requests.
