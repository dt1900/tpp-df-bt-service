
import lib4relay
from pyPS4Controller.controller import Controller
import json
import sys
import re
import subprocess

class MyController(Controller):
    """A custom controller class to handle PS4 events and map them to relays."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.keymap = {}
        self.button_states = {}
        self.relay_to_buttons = {}
        self.relay_hardware_states = {1: 0, 2: 0, 3: 0, 4: 0}
        self.is_connected = False
        self.device_name = None
        self.device_mac = None

    def get_status(self):
        """Returns the current status of the controller."""
        controller_name = "Not found"
        if self.is_connected:
            controller_name = f"{self.device_name} ({self.device_mac})" if self.device_name else 'Connecting...'
        return {
            'controller_name': controller_name
        }

    def on_connect(self):
        print("Controller connected (pyPS4Controller callback)")
        self.is_connected = True

    def update_controller_info(self):
        js0_device_name = None
        try:
            with open("/proc/bus/input/devices", "r") as f:
                content = f.read()
            
            # Split content into device blocks
            device_blocks = content.strip().split("\n\n")

            for block in device_blocks:
                if "Handlers=js0" in block:
                    name_match = re.search(r'N: Name="([^"]+)"', block)
                    if name_match:
                        js0_device_name = name_match.group(1)
                        break
            
            if not js0_device_name:
                print("Could not find device name for /dev/input/js0 in /proc/bus/input/devices.")
                self.device_name = None
                self.device_mac = None
                return

            # Now use bluetoothctl to find the MAC address for this specific device name
            output = subprocess.check_output(["bluetoothctl", "devices", "Connected"], text=True)
            lines = output.strip().split('\n')
            
            found_mac = None
            for line in lines:
                match = re.search(r"Device ([0-9A-Fa-f:]{17}) (.+)", line)
                if match:
                    mac_address = match.group(1)
                    device_name_from_bt = match.group(2)
                    if device_name_from_bt == js0_device_name:
                        found_mac = mac_address
                        break
            
            if found_mac:
                self.device_name = js0_device_name
                self.device_mac = found_mac
                print(f"Updated controller info: Name={self.device_name}, MAC={self.device_mac}")
            else:
                print(f"Could not find connected Bluetooth device with name '{js0_device_name}'.")
                self.device_name = None
                self.device_mac = None

        except FileNotFoundError:
            print("Error: /proc/bus/input/devices not found.")
            self.device_name = None
            self.device_mac = None
        except subprocess.CalledProcessError as e:
            print(f"Error calling bluetoothctl: {e}")
            print(f"bluetoothctl stderr: {e.stderr}")
            self.device_name = None
            self.device_mac = None
        except Exception as e:
            print(f"An unexpected error occurred while updating controller info: {e}")
            self.device_name = None
            self.device_mac = None

    def on_disconnect(self):
        print("Controller disconnected")
        self.is_connected = False
        self.device_name = None
        self.device_mac = None

    def setup(self, config):
        """Loads configuration and initializes hardware."""
        print("Setting up controller and relays...")
        self._load_config(config)
        self._initialize_button_states()
        self._initialize_relays()
        print("Setup complete. Listening for controller input...")

    def _load_config(self, config):
        """Loads the configuration from config.json."""
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

    def cleanup(self):
        """Turns off all relays."""
        print("Turning all relays OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
