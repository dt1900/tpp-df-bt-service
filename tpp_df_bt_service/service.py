import lib4relay
import json
import sys
import re
import subprocess
import time
import traceback
import pydbus
from evdev import InputDevice, list_devices, ecodes

def find_controller_device(allowed_devices):
    """Scans for a suitable controller device using pydbus and evdev."""
    bus = pydbus.SystemBus()
    mngr = bus.get('org.bluez', '/')
    mngd_objs = mngr.GetManagedObjects()

    for device_config in allowed_devices:
        name_pattern = device_config.get("device_name_pattern")
        keymap = device_config.get("keymap")
        if not name_pattern or not keymap:
            continue

        # Get all button names from the keymap
        all_button_names = set()
        for relay_key, button_names in keymap.items():
            for name in button_names:
                if not name.startswith("DPAD_"):
                    all_button_names.add(name.upper())

        # Convert button names to evdev codes
        expected_codes = set()
        for name in all_button_names:
            try:
                code = getattr(ecodes, name)
                expected_codes.add(code)
            except AttributeError:
                # This name is in the config but not a valid evdev code.
                # We can ignore it here; the main class logs a warning for this.
                pass

        if not expected_codes:
            continue # No valid keys to check for this device

        for path in mngd_objs:
            con_state = mngd_objs[path].get('org.bluez.Device1', {}).get('Connected', False)
            if con_state:
                name = mngd_objs[path].get('org.bluez.Device1', {}).get('Name')
                addr = mngd_objs[path].get('org.bluez.Device1', {}).get('Address')

                if re.search(name_pattern, name, re.IGNORECASE):
                    devices = [InputDevice(path) for path in list_devices()]
                    for device in devices:
                        if name.lower() in device.name.lower():
                            capabilities = device.capabilities(verbose=False)
                            if ecodes.EV_KEY in capabilities:
                                supported_codes = set(capabilities[ecodes.EV_KEY])
                                # Check if any of the expected keys are supported by this device
                                if not expected_codes.isdisjoint(supported_codes):
                                    return device.path, name, addr, keymap
    return None, None, None, None

class MyController:
    """A custom controller class to handle generic input events and map them to relays."""

    def __init__(self, device_path=None, device_name=None, device_mac=None, **kwargs):
        self.keymap = {}
        self.button_states = {}
        self.relay_to_buttons = {} # This will now store evdev integer codes
        self.dpad_to_relay = {}
        self.relay_hardware_states = {1: 0, 2: 0, 3: 0, 4: 0}
        self.is_connected = False
        self.device_name = device_name
        self.device_mac = device_mac
        self.device_path = device_path
        self.device = None

        if self.device_path:
            try:
                self.device = InputDevice(self.device_path)
                self.is_connected = True
                print(f"Successfully opened input device: {self.device.name} ({self.device.path})")
                if not self.device_name:
                    self.device_name = self.device.name
            except (FileNotFoundError, PermissionError) as e:
                print(f"Warning: Could not open device {self.device_path}: {e}")
                self.is_connected = False

    def get_status(self):
        """Returns the current status of the controller."""
        controller_info = "Not found"
        if self.is_connected and self.device:
            controller_info = f"{self.device_name} ({self.device.path})"
            if self.device_mac:
                controller_info += f" [{self.device_mac}]"
        
        capabilities = self.get_evdev_capabilities()

        return {
            'controller_name': controller_info,
            'evdev_capabilities': capabilities
        }

    def get_evdev_capabilities(self, verbose=True):
        """Returns the evdev capabilities of the controller."""
        if self.device:
            return self.device.capabilities(verbose=verbose)
        return None

    def setup(self, keymap):
        """Loads configuration and initializes hardware."""
        print("Setting up controller and relays...")
        print(f"Keymap received in setup: {keymap}")
        self._load_config(keymap)
        self._initialize_button_states()
        self._initialize_relays()
        print("Setup complete. Listening for controller input...")

    def _load_config(self, keymap):
        """Loads the configuration from the provided keymap."""
        print(f"Keymap in _load_config: {keymap}")
        print(f"Type of keymap in _load_config: {type(keymap)}")
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
                    if name.startswith("DPAD_"):
                        direction = name.split("_")[1]
                        if direction == "UP":
                            self.dpad_to_relay[("ABS_HAT0Y", -1)] = relay_num
                        elif direction == "DOWN":
                            self.dpad_to_relay[("ABS_HAT0Y", 1)] = relay_num
                        elif direction == "LEFT":
                            self.dpad_to_relay[("ABS_HAT0X", -1)] = relay_num
                        elif direction == "RIGHT":
                            self.dpad_to_relay[("ABS_HAT0X", 1)] = relay_num
                    else:
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
        print("Updating relays...")
        for relay_num, codes in self.relay_to_buttons.items():
            # Check if any button assigned to this relay is currently pressed
            is_any_button_pressed = any(self.button_states.get(c, False) for c in codes)
            
            current_hw_state = self.relay_hardware_states[relay_num]
            
            if is_any_button_pressed and current_hw_state == 0:
                print(f"Turning relay {relay_num} ON")
                lib4relay.set(0, relay_num, 1)
                self.relay_hardware_states[relay_num] = 1
            elif not is_any_button_pressed and current_hw_state == 1:
                print(f"Turning relay {relay_num} OFF")
                lib4relay.set(0, relay_num, 0)
                self.relay_hardware_states[relay_num] = 0

    def listen(self):
        """Listens for input events and handles device disconnection."""
        while True:
            if not self.device_path:
                allowed_devices = self.get_allowed_devices()
                self.device_path, self.device_name, self.device_mac, keymap = find_controller_device(allowed_devices)
                if not self.device_path:
                    time.sleep(10)
                    continue
                self.setup(keymap)


            print(f"Connecting to device: {self.device_path}...")
            try:
                self.device = InputDevice(self.device_path)
                self.is_connected = True
                print(f"Successfully connected to {self.device_name}. Listening for events...")

                for event in self.device.read_loop():
                    if event.type == ecodes.EV_KEY and event.code in self.button_states:
                        pressed = (event.value == 1)
                        self._handle_button_event(event.code, pressed)
                    elif event.type == ecodes.EV_ABS and event.code in [ecodes.ABS_HAT0X, ecodes.ABS_HAT0Y]:
                        if (ecodes.bytype[event.type][event.code], event.value) in self.dpad_to_relay:
                            relay_num = self.dpad_to_relay[(ecodes.bytype[event.type][event.code], event.value)]
                            self._toggle_relay(relay_num)
                        elif event.value == 0: # D-pad released
                            for key, relay_num in self.dpad_to_relay.items():
                                if key[0] == ecodes.bytype[event.type][event.code]:
                                    lib4relay.set(0, relay_num, 0)
                                    self.relay_hardware_states[relay_num] = 0


            except (OSError, FileNotFoundError) as e:
                self.is_connected = False
                print(f"Error: Device disconnected or not found: {e}. Retrying in 5 seconds...")
                if self.device:
                    self.device.close()
                self.device_path = None # Reset device path to trigger rediscovery
                time.sleep(5)
            except Exception as e:
                self.is_connected = False
                print(f"An unexpected error occurred: {e}.")
                traceback.print_exc() # This will print the full traceback
                print("Retrying in 5 seconds...")
                if self.device:
                    self.device.close()
                self.device_path = None # Reset device path to trigger rediscovery
                time.sleep(5)


    def _handle_button_event(self, event_code, pressed):
        """A generic handler for all button events."""
        print(f"Button event: code={event_code}, pressed={pressed}")
        # event_code is now the evdev integer code
        if event_code in self.button_states:
            self.button_states[event_code] = pressed
            self._update_relays()
        else:
            pass

    def _toggle_relay(self, relay_num):
        """Toggles the state of a relay."""
        current_state = self.relay_hardware_states[relay_num]
        new_state = 1 - current_state
        lib4relay.set(0, relay_num, new_state)
        self.relay_hardware_states[relay_num] = new_state

    def cleanup(self):
        """Turns off all relays and closes the device."""
        print("Turning all relays OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
        if self.device:
            self.device.close()
            print("Input device closed.")

    def get_allowed_devices(self):
        with open("/etc/tpp-df-bt-service/config.json", "r") as f:
            config = json.load(f)
        return config.get("allowed_devices", [])

def main():
    """Main function to run the controller service."""
    # Initialize and run the controller
    controller = MyController()
    try:
        controller.listen()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main()