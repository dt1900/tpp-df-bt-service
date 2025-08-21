#!/usr/bin/env python3
"""
PS4 Controller to Relay Service

This script listens for input from a PS4 controller and controls the relays on a
Sequent Microsystems 4-Relay HAT based on a JSON keymap.
"""

import json
import sys
import time
import lib4relay
from pyPS4Controller.controller import Controller
import http.server
import socketserver
import threading
import importlib.metadata

# --- Version Info ---
try:
    __version__ = importlib.metadata.version("tpp-df-bt-service")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"

# --- Global Controller Info ---
controller = None

# --- Web Server for Version Display ---
class VersionHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A simple HTTP request handler to serve the version page."""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            controller_name = "Not found"
            if controller and hasattr(controller, 'device_name'):
                controller_name = controller.device_name

            html = f"""
            <html>
            <head><title>TPP-DF-BT Service</title></head>
            <body>
            <h1>TPP-DF-BT Service</h1>
            <p>Version: {__version__}</p>
            <p>Controller: {controller_name}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404, "File Not Found")

def start_web_server(port=8000):
    """Starts the HTTP server in a new thread."""
    handler = VersionHttpRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    print(f"Serving version page at http://<your-pi-ip>:{port}")
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()

class MyController(Controller):
    """A custom controller class to handle PS4 events and map them to relays."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keymap = {}
        self.button_states = {}
        self.relay_to_buttons = {}
        self.relay_hardware_states = {1: 0, 2: 0, 3: 0, 4: 0}

    def setup(self):
        """Loads configuration and initializes hardware."""
        print("Setting up controller and relays...")
        self._load_config()
        self._initialize_button_states()
        self._initialize_relays()
        print("Setup complete. Listening for controller input...")

    def _load_config(self):
        """Loads the configuration from config.json."""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)

            keymap = config.get("keymap", {})
            if not keymap:
                print("Error: 'keymap' not found or is empty in config.json.")
                sys.exit(1)

            # Invert the map for easier lookup: relay -> [buttons]
            for relay_key, buttons in keymap.items():
                try:
                    relay_num = int(relay_key.split('_')[1])
                    if not 1 <= relay_num <= 4:
                        print(f"Warning: Invalid relay number {relay_num} in keymap. Skipping.")
                        continue
                    self.relay_to_buttons[relay_num] = [b.lower() for b in buttons]
                except (ValueError, IndexError):
                    print(f"Warning: Invalid relay key format '{relay_key}' in keymap. Skipping.")

            if not self.relay_to_buttons:
                print("Error: No valid relay mappings found in the keymap.")
                sys.exit(1)

        except FileNotFoundError:
            print("Error: config.json not found. Please create it.")
            sys.exit(1)
        except json.JSONDecodeError:
            print("Error: config.json is not a valid JSON file.")
            sys.exit(1)

    def _initialize_button_states(self):
        """Initializes the state tracker for all buttons defined in the keymap."""
        all_buttons = set()
        for buttons in self.relay_to_buttons.values():
            all_buttons.update(buttons)
        
        for button_name in all_buttons:
            self.button_states[button_name] = False

    def _initialize_relays(self):
        """Ensures all relays are turned off at the start."""
        print("Initializing all relays to OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
            self.relay_hardware_states[i] = 0

    def _update_relays(self):
        """
        Checks the state of all mapped buttons and updates the relays accordingly.
        A relay is ON if any of its mapped buttons are pressed.
        A relay is OFF only when all of its mapped buttons are released.
        """
        for relay_num, buttons in self.relay_to_buttons.items():
            # Check if any button assigned to this relay is currently pressed
            is_any_button_pressed = any(self.button_states.get(b, False) for b in buttons)
            
            current_hw_state = self.relay_hardware_states[relay_num]
            
            if is_any_button_pressed and current_hw_state == 0:
                lib4relay.set(0, relay_num, 1)
                self.relay_hardware_states[relay_num] = 1
                print(f"Relay {relay_num} ON")
            elif not is_any_button_pressed and current_hw_state == 1:
                lib4relay.set(0, relay_num, 0)
                self.relay_hardware_states[relay_num] = 0
                print(f"Relay {relay_num} OFF")

    def _handle_button_event(self, button_name, pressed):
        """A generic handler for all button events."""
        if button_name in self.button_states:
            self.button_states[button_name] = pressed
            self._update_relays()

    # --- Digital Button Handlers ---
    def on_x_press(self): self._handle_button_event("x", True)
    def on_x_release(self): self._handle_button_event("x", False)
    def on_triangle_press(self): self._handle_button_event("triangle", True)
    def on_triangle_release(self): self._handle_button_event("triangle", False)
    def on_circle_press(self): self._handle_button_event("circle", True)
    def on_circle_release(self): self._handle_button_event("circle", False)
    def on_square_press(self): self._handle_button_event("square", True)
    def on_square_release(self): self._handle_button_event("square", False)
    def on_L1_press(self): self._handle_button_event("l1", True)
    def on_L1_release(self): self._handle_button_event("l1", False)
    def on_R1_press(self): self._handle_button_event("r1", True)
    def on_R1_release(self): self._handle_button_event("r1", False)
    def on_options_press(self): self._handle_button_event("options", True)
    def on_options_release(self): self._handle_button_event("options", False)
    def on_share_press(self): self._handle_button_event("share", True)
    def on_share_release(self): self._handle_button_event("share", False)
    # Add other digital buttons as needed...

    # --- Analog/Trigger Button Handlers ---
    # Treat any non-zero value as a "press"
    def on_L2_press(self, value): self._handle_button_event("l2", value != 0)
    def on_R2_press(self, value): self._handle_button_event("r2", value != 0)
    
    # The release events for triggers are not reliable, so we use the value from on_..._press
    def on_L2_release(self): self._handle_button_event("l2", False)
    def on_R2_release(self): self._handle_button_event("r2", False)


if __name__ == "__main__":
    print("Starting PS4 controller relay service...")
    
    # Start the web server in a background thread
    start_web_server()

    try:
        # You may need to change the interface if js0 is not correct.
        controller = MyController(interface="/dev/input/js0", connecting_using_ds4drv=False)
        controller.setup()
        # Start listening for events
        controller.listen()
            
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the controller is connected and the interface is correct.")
    finally:
        # Ensure all relays are turned off on exit
        print("Turning all relays OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)