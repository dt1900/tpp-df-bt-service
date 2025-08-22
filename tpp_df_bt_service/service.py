import lib4relay
import json
import sys
import re
import subprocess
from evdev import InputDevice, categorize, ecodes

class MyController:
    """A custom controller class to handle generic input events and map them to relays."""

    def __init__(self, interface, **kwargs):
        self.keymap = {}
        self.button_states = {}
        self.relay_to_buttons = {} # This will now store evdev integer codes
        self.relay_hardware_states = {1: 0, 2: 0, 3: 0, 4: 0}
        self.is_connected = False
        self.device_name = None
        self.device_mac = None

        try:
            self.device = InputDevice(interface)
            self.is_connected = True
            print(f"Successfully opened input device: {self.device.name} ({self.device.path})")
            self.device_name = self.device.name
            self.device_mac = None
        except FileNotFoundError:
            print(f"Error: Input device not found at {interface}. Please check the interface path.\n")
            sys.exit(1)
        except PermissionError:
            print(f"Error: Permission denied to open {interface}. Run with sudo or check permissions.\n")
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while opening device {interface}: {e}\n")
            sys.exit(1)


    def get_status(self):
        """Returns the current status of the controller."""
        controller_info = "Not found"
        if self.is_connected:
            controller_info = f"{self.device_name} ({self.device.path})"
            if self.device_mac:
                controller_info += f" [{self.device_mac}]"
        return {
            'controller_name': controller_info
        }

    def update_controller_info(self):
        """Updates controller name from /proc/bus/input/devices."""
        try:
            with open("/proc/bus/input/devices", "r") as f:
                content = f.read()
            
            device_blocks = content.strip().split("\n\n")

            for block in device_blocks:
                if self.device.path in block:
                    name_match = re.search(r'N: Name="([^"]+)"', block)
                    if name_match:
                        self.device_name = name_match.group(1)
                        print(f"Updated controller info: Name={self.device_name}, Path={self.device.path}")
                        return
            print(f"Could not find device name for {self.device.path} in /proc/bus/input/devices.")
            self.device_name = self.device.name
        except FileNotFoundError:
            print("Error: /proc/bus/input/devices not found.")
        except Exception as e:
            print(f"An unexpected error occurred while updating controller info: {e}")
        
        self.device_name = self.device.name


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
        for relay_key, button_names in keymap.items():
            try:
                relay_num = int(relay_key.split('_')[1])
                if not 1 <= relay_num <= 4:
                    print(f"Warning: Invalid relay number {relay_num} in keymap. Skipping.")
                    continue
                
                # Resolve button names to evdev integer codes
                evdev_codes = []
                for name in button_names:
                    try:
                        # Use getattr to get the integer value of the ecodes constant
                        code = getattr(ecodes, name.upper())
                        evdev_codes.append(code)
                    except AttributeError:
                        print(f"Warning: Unknown evdev code '{name}' in config.json. Skipping.")
                
                self.relay_to_buttons[relay_num] = evdev_codes
            except (ValueError, IndexError):
                print(f"Warning: Invalid relay key format '{relay_key}' in keymap. Skipping.")

        if not self.relay_to_buttons:
            print("Error: No valid relay mappings found in the keymap.")
            sys.exit(1)

    def _initialize_button_states(self):
        """Initializes the state tracker for all buttons defined in the keymap."""
        all_codes = set()
        for codes in self.relay_to_buttons.values():
            all_codes.update(codes)
        
        # We now track states by evdev integer code
        for code in all_codes:
            self.button_states[code] = False # Initialize all to False (not pressed)

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
        for relay_num, codes in self.relay_to_buttons.items():
            # Check if any button assigned to this relay is currently pressed
            is_any_button_pressed = any(self.button_states.get(c, False) for c in codes)
            
            current_hw_state = self.relay_hardware_states[relay_num]
            
            if is_any_button_pressed and current_hw_state == 0:
                lib4relay.set(0, relay_num, 1)
                self.relay_hardware_states[relay_num] = 1
                print(f"Relay {relay_num} ON")
            elif not is_any_button_pressed and current_hw_state == 1:
                lib4relay.set(0, relay_num, 0)
                self.relay_hardware_states[relay_num] = 0
                print(f"Relay {relay_num} OFF")

    def listen(self):
        """Listens for input events from the device."""
        print(f"Listening for events from {self.device.name} ({self.device.path})...")
        try:
            for event in self.device.read_loop():
                # Directly use event.code and check if it's in our tracked button states
                if event.code in self.button_states:
                    if event.type == ecodes.EV_KEY:
                        # Button event (press or release)
                        pressed = (event.value == 1) # 1 for press, 0 for release
                        self._handle_button_event(event.code, pressed)
                    elif event.type == ecodes.EV_ABS:
                        # Analog axis event (joystick, trigger)
                        is_active = (event.value != 0) # Treat non-zero as active
                        self._handle_button_event(event.code, is_active)
        except Exception as e:
            print(f"Error during event listening: {e}")
            self.is_connected = False


    def _handle_button_event(self, event_code, pressed):
        """A generic handler for all button events."""
        # event_code is now the evdev integer code
        if event_code in self.button_states:
            self.button_states[event_code] = pressed
            self._update_relays()
        else:
            pass


    def cleanup(self):
        """Turns off all relays and closes the device."""
        print("Turning all relays OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
        if self.device:
            self.device.close()
            print("Input device closed.")