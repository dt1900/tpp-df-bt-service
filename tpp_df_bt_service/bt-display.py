import pydbus
from evdev import InputDevice, list_devices, ecodes
import re
import json

def get_allowed_devices():
    with open("config.json", "r") as f:
        config = json.load(f)
    return config.get("allowed_devices", [])

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
                        if name.lower() in device.name.lower():
                            capabilities = device.capabilities(verbose=False)
                            if ecodes.EV_KEY in capabilities:
                                return device.path, name, addr
    return None, None, None

def get_connected_devices():
    """
    Returns a list of dictionaries, where each dictionary represents a connected Bluetooth device.
    """
    bus = pydbus.SystemBus()
    mngr = bus.get('org.bluez', '/')
    mngd_objs = mngr.GetManagedObjects()
    connected_devices = []
    for path in mngd_objs:
        con_state = mngd_objs[path].get('org.bluez.Device1', {}).get('Connected', False)
        if con_state:
            addr = mngd_objs[path].get('org.bluez.Device1', {}).get('Address')
            name = mngd_objs[path].get('org.bluez.Device1', {}).get('Name')
            connected_devices.append({"name": name, "address": addr})
    return connected_devices

def get_evdev_devices():
    """
    Returns a list of evdev InputDevice objects.
    """
    devices = [InputDevice(path) for path in list_devices()]
    return devices

def main():
    """
    Main function to display connected Bluetooth devices and their evdev ecodes.
    """
    allowed_devices = get_allowed_devices()
    controller_path, _, _ = find_controller_device(allowed_devices)

    print("Searching for connected Bluetooth devices...")
    connected_bluetooth_devices = get_connected_devices()
    evdev_devices = get_evdev_devices()

    if not connected_bluetooth_devices:
        print("No connected Bluetooth devices found.")
        return

    print("\n--- Connected Bluetooth Devices and evdev ecodes ---")
    for bt_device in connected_bluetooth_devices:
        print(f"\nDevice Name: {bt_device['name']}")
        print(f"Device Address: {bt_device['address']}")
        
        matching_evdev_devices = []
        for device in evdev_devices:
            if bt_device['name'].lower() in device.name.lower():
                matching_evdev_devices.append(device)

        if matching_evdev_devices:
            for device in matching_evdev_devices:
                is_controller = "✅" if device.path == controller_path else ""
                print(f"  {is_controller} evdev device found:")
                print(f"    Device Path: {device.path}")
                print(f"    Device Info: {device.info}")
                
                capabilities = device.capabilities(verbose=True)
                if capabilities:
                    print("    Supported evdev ecodes:")
                    for event_type, codes in capabilities.items():
                        print(f"      {event_type}:")
                        for code in codes:
                            if isinstance(code[0], int) and event_type == ('EV_KEY', 1):
                                try:
                                    print(f"        - {ecodes.KEY[code[0]]}")
                                except KeyError:
                                    print(f"        - {code}")
                            else:
                                print(f"        - {code}")
                else:
                    print("    No evdev ecodes found for this device.")
        else:
            print("  No matching evdev device found.")

        print("-" * 20)

if __name__ == "__main__":
    main()