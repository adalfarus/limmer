import ctypes
import sys
import msvcrt


def enable_ansi():
    # Constants from the Windows API
    STD_OUTPUT_HANDLE = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

    # Get the handle to the standard output
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    hstdout = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    # Get the current console mode
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(hstdout, ctypes.byref(mode))

    # Set the ENABLE_VIRTUAL_TERMINAL_PROCESSING flag
    mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING

    # Update the console mode
    kernel32.SetConsoleMode(hstdout, mode)


# Function to query the cursor position
def query_cursor_position():
    # Send the DSR request
    sys.stdout.write("\033[6n")
    sys.stdout.flush()

    # Read the response (expecting format ESC[n;mR)
    response = ""
    while True:
        ch = msvcrt.getwch()  # Get a character from the console without echo
        response += ch
        if ch == 'R':
            break

    # Parse the response to get the cursor position
    response = response.replace("\033[", "").rstrip('R')
    rows, cols = map(int, response.split(';'))
    return rows, cols
