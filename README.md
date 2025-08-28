# TPP-DF-BT Service

This service allows a Raspberry Pi to control a 4-relay board using a Bluetooth controller. It is designed to run as a background service.

## Hardware

This service is specifcally written to run on a Raspberry Pi 3b+ with a Sequent Microsystems 4-Relay board. A similar hardware setup can be found here: https://www.microcenter.com/FindIt/?t=6H7NJE

## Pairing a Controller

**IMPORTANT:** A controller must be paired with the Raspberry Pi. The service will automatically detect and use the first available controller that matches one of the device configurations in the [`config.json`](config.json) file.

## Configuration

The service is configured via the `/etc/tpp-df-bt-service/config.json` file. This file contains a version number and a list of allowed devices.

The service now supports multiple controller types. The `allowed_devices` property is a list of configurations, and the service will use the first one that matches a connected device.

Example [`config.json`](config.json):
```json
{
  "version": "1.1.0",
  "allowed_devices": [
    {
      "device_name_pattern": "^Wireless Controller$",
      "controller": "wireless_controller.WirelessController",
      "keymap": {
        "relay_1": [],
        "relay_2": ["BTN_TL", "BTN_TL2"],
        "relay_3": ["BTN_START", "BTN_SOUTH", "DPAD_DOWN"],
        "relay_4": ["BTN_TR", "BTN_TR2", "DPAD_RIGHT"]
      }
    },
    {
      "device_name_pattern": "^JX-05(?!.*Consumer Control)",
      "controller": "jx05_controller.JX05Controller",
      "swipe_map": {
        "relay_2": ["DOWN", "LEFT"],
        "relay_4": ["UP", "RIGHT"],
        "relay_3": ["TAP"]
      }
    }
  ]
}
```

*   `version`: The version of the configuration file format.
*   `allowed_devices`: A list of controller configurations.
*   `device_name_pattern`: A regular expression used to identify the controller device.
*   `controller`: The name of the controller module and class to use.
*   `keymap` / `swipe_map`: Maps controller inputs to relays. The keys are the relay numbers (e.g., "relay_1"), and the values are a list of button names from the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library or swipe directions.

### Configuration Updates

The [`config.json`](config.json) file is versioned. When the service is updated, the installation script ([`postinst`](debian/postinst)) will check the version of the existing config file. If the new version is greater, the old config file will be replaced with the new one. Otherwise, the existing config file will be preserved.

## The Service

The service consists of three main components: the [controller/relay service](#controllerrelay), a [web server](#web-server), and a [bluetooth display script](tpp_df_bt_service/bt-display.py).

### Controller/Relay ([`service.py`](tpp_df_bt_service/service.py))

This is the core of the service. It listens for input from a paired controller and controls the relays based on the mappings in the [`config.json`](config.json) file. It uses the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library to handle controller input and the [`lib4relay`](4relay/lib4relay/__init__.py) library to control the relays.

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
*   [`debian/postinst`](debian/postinst): A script that is run after the package is installed. It handles the `config.json` update logic, reloads the `systemd` daemon, and starts the service.
*   [`debian/prerm`](debian/prerm): A script that is run before the package is removed. It stops and disables the service.

## Build Process

### Using `local-build.sh`

The [`local-build.sh`](local-build.sh) script automates the build and installation process. It automatically increments the patch version number in [`debian/control`](debian/control), [`README.md`](README.md), and [`config.json`](config.json), then builds and installs the new package.

To use it, simply run the script:
```bash
./local-build.sh
```

### Using `build.sh`

The [`build.sh`](build.sh) script creates a `.deb` package for the service.

To build the package, run the script with a version number:

```bash
./build.sh 1.1.0
```

This will create a file named `tpp-df-bt-service_1.1.0-1_all.deb`.

## Installation

To install the service from a `.deb` package, you can either download it manually or install it directly from the GitHub URL.

### Manual Installation

1.  Download the latest `.deb` package from the [GitHub Releases page](https://github.com/dt1900/tpp-df-bt-service/releases).
2.  Install the package using `apt`:

    ```bash
    sudo apt install ./tpp-df-bt-service_1.1.0-1_all.deb
    ```

### Direct Installation from GitHub

You can also install the package directly from the GitHub URL.

```bash
curl -L https://github.com/dt1900/tpp-df-bt-service/releases/download/1.1.0/tpp-df-bt-service_1.1.0-1_all.deb -o /tmp/tpp-df-bt-service_1.1.0-1_all.deb && sudo apt install /tmp/tpp-df-bt-service_1.1.0-1_all.deb
```

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