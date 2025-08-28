import lib4relay
from evdev import InputDevice, ecodes

class BaseController:
    """Base class for controllers."""

    def __init__(self, device_path, device_name, device_mac, **kwargs):
        self.device_path = device_path
        self.device_name = device_name
        self.device_mac = device_mac
        self.device = None
        self.is_connected = False
        self.relay_hardware_states = {1: 0, 2: 0, 3: 0, 4: 0}

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

    def setup(self, device_config):
        """Loads configuration and initializes hardware."""
        print("Setting up controller and relays...")
        self._load_config(device_config)
        self._initialize_relays()
        print("Setup complete. Listening for controller input...")

    def _load_config(self, device_config):
        """This method should be implemented by subclasses."""
        raise NotImplementedError

    def _initialize_relays(self):
        """Ensures all relays are turned off at the start."""
        print("Initializing all relays to OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
            self.relay_hardware_states[i] = 0

    def listen(self):
        """This method should be implemented by subclasses."""
        raise NotImplementedError

    def _toggle_relay(self, relay_num):
        """Toggles the state of a relay."""
        current_state = self.relay_hardware_states[relay_num]
        new_state = 1 - current_state
        lib4relay.set(0, relay_num, new_state)
        self.relay_hardware_states[relay_num] = new_state

    def _update_relays(self, active_relays):
        """Updates the relays based on the set of active relays."""
        for relay_num in range(1, 5):
            current_hw_state = self.relay_hardware_states[relay_num]
            should_be_on = relay_num in active_relays

            if should_be_on and current_hw_state == 0:
                lib4relay.set(0, relay_num, 1)
                self.relay_hardware_states[relay_num] = 1
            elif not should_be_on and current_hw_state == 1:
                lib4relay.set(0, relay_num, 0)
                self.relay_hardware_states[relay_num] = 0

    def cleanup(self):
        """Turns off all relays and closes the device."""
        print("Turning all relays OFF.")
        for i in range(1, 5):
            lib4relay.set(0, i, 0)
        if self.device:
            self.device.close()
            print("Input device closed.")
