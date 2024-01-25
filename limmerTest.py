import limmer
from limmer.basics import Window
import signal
import time

# Main program execution
def main():
    def signal_handler(sig, frame):
        window.stopEventLoop()

    window = Window()
    signal.signal(signal.SIGINT, signal_handler)
    window.startEventLoop()

    # Other main thread tasks can go here
    while not window.stop_event.is_set():
        time.sleep(0.1)  # Just to prevent the main thread from spinning
    print("EXITED from window loop")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    window = limmer.Window()
    event1 = limmer.SpinningEvent()
    #window._appendEvent(event1)
    
    window.sendText(event1, "\n", limmer.styles.Color.RED, "HELLO WORLD")
    
    window.startEventLoop(0.1)
    event1.startEventLoop()
    
# Example: print "Hello, World!" in bold red text on a yellow background
#print("\033[1;31;43mHello, World!\033[0m")
print("\033[2;37;41mHello, World, 2!\033[0m")
print("\033[2;37;40mHello, World, 2!\033[0m")

# Reset to default after printing
print("\033[0m")
    