import time
import lib4relay
import sys

# The stack level is assumed to be 0.
STACK_LEVEL = 0

def main():
    """
    Cycles through the 4 relays on the Sequent Microsystems board,
    turning each one on and then off in sequence.
    """
    print("Starting relay test cycle...")
    print("Press Ctrl-C to exit.")

    while True:
        for i in range(1, 5):
            try:
                print(f"Turning relay {i} ON")
                lib4relay.set(STACK_LEVEL, i, 1)
                time.sleep(1)
                print(f"Turning relay {i} OFF")
                lib4relay.set(STACK_LEVEL, i, 0)
                time.sleep(1)
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Please check the I2C connection and the board address.")
                sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        # Ensure all relays are turned off on exit
        print("Turning all relays OFF.")
        try:
            lib4relay.set_all(STACK_LEVEL, 0)
        except Exception as e:
            print(f"An error occurred while turning off relays: {e}")
