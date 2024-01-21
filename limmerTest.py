import limmer


if __name__ == "__main__":
    window = limmer.Window()
    event1 = limmer.SpinningEvent()
    window.appendEvent(event1)
    
    window.startEventLoop(0.1)
    event1.startEventLoop()
    
# Example: print "Hello, World!" in bold red text on a yellow background
print("\033[1;31;43mHello, World!\033[0m")

# Reset to default after printing
print("\033[0m")
    