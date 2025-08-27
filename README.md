# TPP-DF-BT Service

This service allows a Raspberry Pi to control a 4-relay board using a Bluetooth controller. It is designed to run as a background service.

## Pairing a Controller

**IMPORTANT:** A controller must be paired with the Raspberry Pi. The service will automatically detect and use the first available controller that matches the `device_name_pattern` in the [`config.json`](config.json) file.

## Configuration

The service is configured via the [`/etc/tpp-df-bt-service/config.json`](config.json) file.

```json
{
  "device_name_pattern": "^Wireless Controller$",
  "keymap": {
    "relay_1": [],
    "relay_2": ["BTN_TL", "BTN_TL2"],
    "relay_3": ["BTN_START", "BTN_SOUTH", "DPAD_DOWN"],
    "relay_4": ["BTN_TR", "BTN_TR2", "DPAD_RIGHT"]
  }
}
```

*   `device_name_pattern`: A regular expression used to identify the controller device.
*   `keymap`: Maps controller buttons to relays. The keys are the relay numbers (e.g., "relay_1"), and the values are a list of button names from the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library. The d-pad can be mapped using `DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, and `DPAD_RIGHT`.

## The Service

The service consists of three main components: the controller/relay service, a web server, and a [bluetooth display script](tpp_df_bt_service/bt-display.py).

### Controller/Relay ([`service.py`](tpp_df_bt_service/service.py))

This is the core of the service. It listens for input from the paired controller and controls the relays based on the mappings in the [`config.json`](config.json) file. It uses the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library to handle controller input and the [`lib4relay`](4relay/lib4relay/__init__.py) library to control the relays.

### Web Server ([`web.py`](tpp_df_bt_service/web.py))

A simple web server runs on port 8000 and displays the service's version, the name of the connected controller and the evdev capabilities.

### Bluetooth Display ([`bt-display.py`](tpp_df_bt_service/bt-display.py))

This script displays all connected Bluetooth devices and their `evdev` information. It also indicates which device is being used by the service with a green check emoji (✅).

To run the script:
```bash
sudo python3 /usr/lib/python3/dist-packages/tpp_df_bt_service/bt-display.py
```

## Update Script

The [`update-tpp-df-bt-service.sh`](update-tpp-df-bt-service.sh) script, located in `/usr/local/bin`, checks for new releases of the service on GitHub and automatically downloads and installs them. This script is run daily via a cron job located at [`/etc/cron.d/tpp-df-bt-service-update`](debian/tpp-df-bt-service-update).

To run the update script manually:

```bash
/usr/local/bin/update-tpp-df-bt-service.sh
```

## Debian Files

The project includes Debian files to create a `.deb` package for easy installation.

*   [`debian/control`](debian/control): Contains the package metadata.
*   [`debian/postinst`](debian/postinst): A script that is run after the package is installed. It reloads the `systemd` daemon and starts the service.
*   [`debian/prerm`](debian/prerm): A script that is run before the package is removed. It stops and disables the service.

## Build Process

The [`build.sh`](build.sh) script creates a `.deb` package for the service.

To build the package, run the script with a version number:

```bash
./build.sh <version>
```

For example:

```bash
./build.sh 1.0.19
```

This will create a file named `tpp-df-bt-service_<version>-1_all.deb`.

## Installation

To install the service from a `.deb` package:

1.  Download the latest `.deb` package from the [GitHub Releases page](https://github.com/dt1900/tpp-df-bt-service/releases).
2.  Install the package using `apt`:

    ```bash
    sudo apt install ./tpp-df-bt-service_<version>-1_all.deb
    ```

    Replace `<version>` with the actual version number of the downloaded package.

## Service Management

The service is managed by `systemd`.

### Check Service Status

To check the status of the service:

```bash
sudo systemctl status tpp-df-bt.service
```

### View Service Logs

To view the logs for the service:

```bash
sudo journalctl -u tpp-df-bt.service
```
