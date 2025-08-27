from .base_controller import BaseController
from evdev import ecodes
import lib4relay

class WirelessController(BaseController):
    """Controller class for standard wireless gamepads."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.button_states = {}
        self.relay_to_buttons = {}
        self.dpad_to_relay = {}

    def _load_config(self, device_config):
        """Loads the keymap for the wireless controller."""
        keymap = device_config.get("keymap")
        if not keymap:
            print("Error: 'keymap' not found for Wireless Controller.")
            return

        for relay_key, button_names in keymap.items():
            try:
                relay_num = int(relay_key.split('_')[1])
                if not 1 <= relay_num <= 4:
                    print(f"Warning: Invalid relay number {relay_num} in keymap. Skipping.")
                    continue
                
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
                            code = getattr(ecodes, name.upper())
                            evdev_codes.append(code)
                        except AttributeError:
                            print(f"Warning: Unknown evdev code '{name}' in config.json. Skipping.")
                
                self.relay_to_buttons[relay_num] = evdev_codes
            except (ValueError, IndexError):
                print(f"Warning: Invalid relay key format '{relay_key}' in keymap. Skipping.")

        all_codes = set()
        for codes in self.relay_to_buttons.values():
            all_codes.update(codes)
        for code in all_codes:
            self.button_states[code] = False

    def listen(self):
        """Listens for input events and handles device disconnection."""
        try:
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
            self.device_path = None

    def _handle_button_event(self, event_code, pressed):
        """A generic handler for all button events."""
        if event_code in self.button_states:
            self.button_states[event_code] = pressed
            active_relays = set()
            for relay_num, codes in self.relay_to_buttons.items():
                if any(self.button_states.get(c, False) for c in codes):
                    active_relays.add(relay_num)
            self._update_relays(active_relays)
