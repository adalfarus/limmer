from .ANSIUtils import enable_ansi, query_cursor_position
from .styles import *
from .events import *
from .basics import *


enable_ansi()
print(f"{Color.CLEAR}Cmd Win [{Color.RED}SECURE{Color.CLEAR}] for {Color.RGB(0, 0, 0)}Windows{Color.CLEAR} [Version 1.0.0]")
print("(c) Limmer LLC. All rights reserved.")
print("Welcome to limmer, the version you're currently working with has 'some' problems, the biggest is positioning.")
print("\nC:\\Users\\user_> ")

#print(f"\033[100B",
#      f"\033[100C")
# print("1" * 200)
# print("\033[1C")
#input(query_cursor_position())
# print("\033[1A\b\b\b\b")
#input()
#input(query_cursor_position())
