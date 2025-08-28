from .base_controller import BaseController
from evdev import ecodes

class JX05Controller(BaseController):
    """Controller class for the JX-05 device, using swipe detection."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.swipe_map = {}
        self.touch_start_x = None
        self.touch_start_y = None
        self.touch_end_x = None
        self.touch_end_y = None

    def _load_config(self, device_config):
        """Loads the swipe map for the JX-05."""
        swipe_map = device_config.get("swipe_map")
        if not swipe_map:
            print("Error: 'swipe_map' not found for JX-05 Controller.")
            return
        self.swipe_map = swipe_map

    def listen(self):
        """Listens for input events and handles device disconnection."""
        try:
            for event in self.device.read_loop():
                if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                    if event.value == 1:  # Touch pressed
                        self._handle_touch_press()
                    else:  # Touch released
                        self._handle_touch_release()
                elif event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_X or event.code == ecodes.ABS_MT_POSITION_X:
                        if self.touch_start_x is None:
                            self.touch_start_x = event.value
                        self.touch_end_x = event.value
                    elif event.code == ecodes.ABS_Y or event.code == ecodes.ABS_MT_POSITION_Y:
                        if self.touch_start_y is None:
                            self.touch_start_y = event.value
                        self.touch_end_y = event.value
        except (OSError, FileNotFoundError) as e:
            self.is_connected = False
            print(f"Error: Device disconnected or not found: {e}. Retrying in 5 seconds...")
            if self.device:
                self.device.close()
            self.device_path = None

    def _handle_touch_press(self):
        """Records the starting coordinates of a touch."""
        self.touch_start_x = self.touch_end_x
        self.touch_start_y = self.touch_end_y

    def _handle_touch_release(self):
        """Calculates swipe direction and triggers relays."""
        if self.touch_start_x is not None and self.touch_start_y is not None and \
           self.touch_end_x is not None and self.touch_end_y is not None:

            delta_x = self.touch_end_x - self.touch_start_x
            delta_y = self.touch_end_y - self.touch_start_y

            swipe_direction = self._get_swipe_direction(delta_x, delta_y)

            if swipe_direction:
                for relay_key, directions in self.swipe_map.items():
                    if swipe_direction in directions:
                        try:
                            relay_num = int(relay_key.split('_')[1])
                            self._toggle_relay(relay_num)
                        except (ValueError, IndexError):
                            print(f"Warning: Invalid relay key format '{relay_key}' in swipe_map. Skipping.")

        # Reset coordinates
        self.touch_start_x = None
        self.touch_start_y = None
        self.touch_end_x = None
        self.touch_end_y = None

    def _get_swipe_direction(self, delta_x, delta_y):
        """Determines the swipe direction based on coordinate changes."""
        abs_delta_x = abs(delta_x)
        abs_delta_y = abs(delta_y)

        # Simple tap detection (adjust threshold as needed)
        if abs_delta_x < 50 and abs_delta_y < 50:
            return "TAP"

        if abs_delta_x > abs_delta_y:
            return "RIGHT" if delta_x > 0 else "LEFT"
        else:
            return "DOWN" if delta_y > 0 else "UP"