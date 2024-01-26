import limmer
import signal
import time


# Main program execution

def main():
    def signal_handler(sig, frame):
        window.stopEventLoop()

    window = limmer.Window()
    signal.signal(signal.SIGINT, signal_handler)

    spinning_event = limmer.SpinningEvent()
    pointings_event = limmer.PointingsEvent()

    window.startEventLoop(0.1)
    spinning_event.startEventLoop()
    pointings_event.startEventLoop()

    window.sendText("Formatting: ", spinning_event, "\n", limmer.Color.RGB(255, 0, 0), limmer.Background.RGB(0, 0, 255),
                    limmer.Formatting.STRIKETROUGH, limmer.Formatting.ITALIC, "HELLO WORLD" * 20)

    window.sendText("\n" * 3, " " * 100)

    window.sendText(limmer.InlineStyle.CLEAR, "HELLO WORLDSSS" * 10, pointings_event, "END")

    # Other main thread tasks can go here
    while not window.stop_event.is_set():
        time.sleep(0.1)  # Just to prevent the main thread from spinning
    print("EXITED from window loop")


if __name__ == "__main__":
    print("\033[6n")
    main()

# Example: print "Hello, World!" in bold red text on a yellow background
# print("\033[38;2;255;0;0m Hello, World!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\033[0m")
# print("\033[2;37;41mHello, World!\033[0m")
# print("\033[1;37;40mHello, World, 2!\033[0m")

# Reset to default after printing
# print("\033[0m")
