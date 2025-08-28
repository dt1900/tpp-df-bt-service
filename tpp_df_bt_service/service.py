import json
import sys
import re
import time
import traceback
import pydbus
from evdev import InputDevice, list_devices
import importlib

def find_controller_device(allowed_devices):
    """Scans for a suitable controller device using pydbus and evdev."""
    bus = pydbus.SystemBus()
    mngr = bus.get('org.bluez', '/')
    mngd_objs = mngr.GetManagedObjects()

    for device_config in allowed_devices:
        name_pattern = device_config.get("device_name_pattern")
        if not name_pattern:
            continue

        for path in mngd_objs:
            con_state = mngd_objs[path].get('org.bluez.Device1', {}).get('Connected', False)
            if con_state:
                name = mngd_objs[path].get('org.bluez.Device1', {}).get('Name')
                addr = mngd_objs[path].get('org.bluez.Device1', {}).get('Address')

                if re.search(name_pattern, name, re.IGNORECASE):
                    devices = [InputDevice(path) for path in list_devices()]
                    for device in devices:
                        if re.search(name_pattern, device.name, re.IGNORECASE):
                            return device.path, name, addr, device_config
    return None, None, None, None

def get_controller_class(controller_name):
    """Dynamically imports and returns the controller class."""
    try:
        module_name, class_name = controller_name.rsplit('.', 1)
        module = importlib.import_module(f".controllers.{module_name}", package='tpp_df_bt_service')
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        print(f"Error importing controller class: {e}")
        return None

def main():
    """Main function to run the controller service."""
    while True:
        try:
            with open("/etc/tpp-df-bt-service/config.json", "r") as f:
                config = json.load(f)
            allowed_devices = config.get("allowed_devices", [])

            device_path, device_name, device_mac, device_config = find_controller_device(allowed_devices)

            if device_path:
                controller_name = device_config.get("controller")
                if controller_name:
                    ControllerClass = get_controller_class(controller_name)
                    if ControllerClass:
                        controller = ControllerClass(
                            device_path=device_path,
                            device_name=device_name,
                            device_mac=device_mac
                        )
                        controller.setup(device_config)
                        controller.listen()
                else:
                    print("Error: Controller not defined for the device in config.json")
            else:
                print("No connected controller found. Retrying in 10 seconds...")
                time.sleep(10)

        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            traceback.print_exc()
            print("Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    main()