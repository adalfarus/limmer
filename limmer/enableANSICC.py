import ctypes

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
