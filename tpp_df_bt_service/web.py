import http.server
import socketserver
import threading
import importlib.metadata

import subprocess
import socket # Import socket

httpd = None
__version__ = "unknown"

try:
    version_output = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "tpp-df-bt-service"]).decode().strip()
    if version_output:
        __version__ = version_output
except Exception:
    pass

class VersionHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A simple HTTP request handler to serve the version page."""
    def __init__(self, *args, controller, **kwargs):
        self.controller = controller
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            status = self.controller.get_status()

            html = f"""
            <html>
            <head><title>TPP-DF-BT Service</title></head>
            <body>
            <h1>TPP-DF-BT Service</h1>
            <p>Version: {__version__}</p>
            <p>Controller: {status['controller_name']}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404, "File Not Found")

class ReusableTCPServer(socketserver.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

def start_web_server(controller, port=8000):
    """Starts the HTTP server in a new thread."""
    global httpd
    handler = lambda *args, **kwargs: VersionHttpRequestHandler(*args, controller=controller, **kwargs)
    # Use ReusableTCPServer instead of socketserver.TCPServer
    httpd = ReusableTCPServer(('', port), handler)
    print(f"Serving version page at http://<your-pi-ip>:{port}")
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    return httpd

def cleanup_web_server():
    print("\nCleaning up and exiting web server.")
    if httpd:
        httpd.shutdown()
        httpd.server_close()