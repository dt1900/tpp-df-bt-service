#!/usr/bin/env python3
"""
Controller to Relay Service

This script listens for input from a generic controller and controls the relays on a
Sequent Microsystems 4-Relay HAT based on a JSON keymap.
"""

from .service import main

if __name__ == "__main__":
    main()