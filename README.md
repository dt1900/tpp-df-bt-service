# TPP-DF-BT Service

This service allows a Raspberry Pi to control a 4-relay board using a Bluetooth controller. It is designed to run as a background service.

## Pairing a Controller

**IMPORTANT:** A controller must be paired with the Raspberry Pi. The service will automatically detect and use the first available controller that matches the `device_name_pattern` in the `config.json` file.

## Configuration

The service is configured via the `/etc/tpp-df-bt-service/config.json` file.

```json
{
  "device_name_pattern": "^Wireless Controller$",
  "keymap": {
    "relay_1": [],
    "relay_2": ["BTN_TL", "BTN_TL2"],
    "relay_3": ["BTN_START", "BTN_SOUTH"],
    "relay_4": ["BTN_TR", "BTN_TR2"]
  }
}
```

*   `device_name_pattern`: A regular expression used to identify the controller device.
*   `keymap`: Maps controller buttons to relays. The keys are the relay numbers (e.g., "relay_1"), and the values are a list of button names from the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library.

## The Service

The service consists of two main components: the controller/relay service and a web server.

### Controller/Relay (service.py)

This is the core of the service. It listens for input from the paired controller and controls the relays based on the mappings in the `config.json` file. It uses the [`evdev`](https://python-evdev.readthedocs.io/en/latest/) library to handle controller input and the `lib4relay` library to control the relays.

### Web Server (web.py)

A simple web server runs on port 8000 and displays the service's version and the name of the connected controller.

## Update Script

The `update-tpp-df-bt-service.sh` script, located in `/usr/local/bin`, checks for new releases of the service on GitHub and automatically downloads and installs them. This script is run daily via a cron job located at `/etc/cron.d/tpp-df-bt-service-update`.

To run the update script manually:

```bash
/usr/local/bin/update-tpp-df-bt-service.sh
```

## Debian Files

The project includes Debian files to create a `.deb` package for easy installation.

*   `debian/control`: Contains the package metadata.
*   `debian/postinst`: A script that is run after the package is installed. It reloads the `systemd` daemon and starts the service.
*   `debian/prerm`: A script that is run before the package is removed. It stops and disables the service.

## Build Process

The `build.sh` script creates a `.deb` package for the service.

To build the package, run the script with a version number:

```bash
./build.sh <version>
```

For example:

```bash
./build.sh 1.0.1
```

This will create a file named `tpp-df-bt-service_<version>-1_all.deb`.

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