#!/usr/bin/env python3
"""
Controller to Relay Service

This script listens for input from a generic controller and controls the relays on a
Sequent Microsystems 4-Relay HAT based on a JSON keymap.
"""

import signal
import sys
import threading
import time
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

    print("Starting generic controller relay service...")
    
    # Initialize the controller
    controller = MyController()
    
    # Start the controller listener in a separate thread
    controller_thread = threading.Thread(target=controller.listen)
    controller_thread.daemon = True
    controller_thread.start()

    # Start the web server in a background thread
    start_web_server(controller, 8000)

    # Keep the main thread alive
    while True:
        time.sleep(1)