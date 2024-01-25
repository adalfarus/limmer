from .ANSIUtils import enable_ansi, query_cursor_position
from .styles import *
from .events import *
from .basics import *


enable_ansi()
#print(f"\033[100B",
#      f"\033[100C")
print("1" * 200)
print("\033[1C")
#input(query_cursor_position())
print("\033[1A\b\b\b\b")
#input()
#input(query_cursor_position())
