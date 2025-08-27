from .base_controller import BaseController
from evdev import ecodes
import lib4relay

class JX05Controller(BaseController):
    """Controller class for the JX-05 device."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.virtual_buttons = {}
        self.active_virtual_buttons = set()
        self.touch_x = None
        self.touch_y = None

    def _load_config(self, device_config):
        """Loads the virtual button configuration for the JX-05."""
        virtual_buttons = device_config.get("virtual_buttons")
        if not virtual_buttons:
            print("Error: 'virtual_buttons' not found for JX-05 Controller.")
            return
        self.virtual_buttons = virtual_buttons

    def listen(self):
        """Listens for input events and handles device disconnection."""
        try:
            for event in self.device.read_loop():
                if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                    if event.value == 1: # Touch pressed
                        self._handle_touch_press()
                    else: # Touch released
                        self._handle_touch_release()
                elif event.type == ecodes.EV_ABS and event.code == ecodes.ABS_X:
                    self.touch_x = event.value
                elif event.type == ecodes.EV_ABS and event.code == ecodes.ABS_Y:
                    self.touch_y = event.value
                elif event.type == ecodes.EV_ABS and event.code == ecodes.ABS_MT_POSITION_X:
                    self.touch_x = event.value
                elif event.type == ecodes.EV_ABS and event.code == ecodes.ABS_MT_POSITION_Y:
                    self.touch_y = event.value
        except (OSError, FileNotFoundError) as e:
            self.is_connected = False
            print(f"Error: Device disconnected or not found: {e}. Retrying in 5 seconds...")
            if self.device:
                self.device.close()
            self.device_path = None

    def _handle_touch_press(self):
        """Handles a touch press event by checking virtual buttons."""
        if self.touch_x is not None and self.touch_y is not None:
            for relay_key, button_areas in self.virtual_buttons.items():
                try:
                    relay_num = int(relay_key.split('_')[1])
                    for coords in button_areas:
                        if coords["x_min"] <= self.touch_x <= coords["x_max"] and \
                           coords["y_min"] <= self.touch_y <= coords["y_max"]:
                            self.active_virtual_buttons.add(relay_num)
                except (ValueError, IndexError):
                    print(f"Warning: Invalid relay key format '{relay_key}' in virtual_buttons. Skipping.")
            self._update_relays(self.active_virtual_buttons)

    def _handle_touch_release(self):
        """Handles a touch release event."""
        self.active_virtual_buttons.clear()
        self._update_relays(self.active_virtual_buttons)
        # Reset touch coordinates
        self.touch_x = None
        self.touch_y = None

    def _update_virtual_relays(self):
        """Updates the relays based on the active virtual buttons."""
        for relay_num in range(1, 5):
            current_hw_state = self.relay_hardware_states[relay_num]
            if relay_num in self.active_virtual_buttons and current_hw_state == 0:
                lib4relay.set(0, relay_num, 1)
                self.relay_hardware_states[relay_num] = 1
            elif relay_num not in self.active_virtual_buttons and current_hw_state == 1:
                lib4relay.set(0, relay_num, 0)
                self.relay_hardware_states[relay_num] = 0
