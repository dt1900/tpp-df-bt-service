#!/usr/bin/env python3
"""
PS4 Controller to Relay Service

This script listens for input from a PS4 controller and controls the relays on a
Sequent Microsystems 4-Relay HAT based on a JSON keymap.
"""

import signal
import sys
import json
import threading
import time # Import time
from .service import MyController
from .web import start_web_server, cleanup_web_server

def cleanup(signum, frame):
    print("\nCleaning up and exiting.")
    cleanup_web_server()
    if controller:
        controller.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("Starting PS4 controller relay service...")
    
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        interface = config.get("interface")
        if not interface:
            print("Error: 'interface' not found in config.json.")
            sys.exit(1)

        # You may need to change the interface if js0 is not correct.
        controller = MyController(interface=interface, connecting_using_ds4drv=False)
        controller.setup(config)
        
        # Start the controller listener in a separate thread
        controller_thread = threading.Thread(target=controller.listen)
        controller_thread.daemon = True
        controller_thread.start()

        # Give some time for the controller to connect and for the listener to start
        time.sleep(10) # Increased sleep duration

        # Update controller info using bluetoothctl directly
        controller.update_controller_info()

        # Start the web server in a background thread
        start_web_server(controller, 8000)

        # Keep the main thread alive
        while True:
            time.sleep(1) # Keep the main thread alive

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the controller is connected and the interface is correct.")
    finally:
        cleanup(None, None)



