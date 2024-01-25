import time
import sys
import signal
import threading
from .styles import InLineStyleAttr
from . import events
from .ANSIUtils import query_cursor_position
import os


class Cursor:
    def __init__(self, position=None):
        self.position = position or query_cursor_position()
        self.current_command = ""
        
    def go_up(self, n=1):
        self.current_command += f"\033[{n}A"
    
    def go_down(self, n=1):
        self.current_command += f"\033[{n}B"
    
    def go_left(self, n=1):
        self.current_command += f"\033[{n}D"
    
    def go_right(self, n=1):
        self.current_command += f"\033[{n}C"
    
    def go_to(self, x, y):
        #self.position = query_cursor_position()
        current_x = self.position[0]
        current_y = self.position[1]
        
        if x > current_x:
            self.go_right(x - current_x)
        elif x < current_x:
            self.go_left(current_x - x)
            
        if y > current_y:
            self.go_down(y - current_y)
        elif y < current_y:
            self.go_up(current_y - y)
            
    def appendCMD(self, string: str):
        self.current_command += string
    
    def finishCMD(self):
        # Finish and clear command
        sys.stdout.write(self.current_command)
        sys.stdout.flush()
        self.clearCMD()
    
    def clearCMD(self):
        self.current_command = ""
    
    def setCMD(self, new_cmd: str):
        self.current_command = new_cmd


class Window:
    def __init__(self):
        self.cursor = Cursor()
        self.events = []
        self.loop_thread = None
        self.stop_event = threading.Event()

        self.max_position = list(self.get_terminal_size())
        self.last_style = [1, 37, 40]

    @staticmethod
    def get_terminal_size():
        terminal_size_object = os.get_terminal_size()
        x, y = terminal_size_object.columns, terminal_size_object.lines
        return x, y

    def handle_resize(self):
        new_size = list(self.get_terminal_size())
        if new_size[0] != self.max_position[0]:
            self.recalculate_positions(new_size)
            self.max_position = new_size  # Needs to be adjusted here or recalculate position can't scale old positions
            self.redraw_interface()

    def recalculate_positions(self, new_size):
        print("\nRE", new_size, self.max_position)
        for event in self.events:  # Dynamic events length is kinda easy with this now
            # Logic to adjust the position of each event
            last_event_position = event.position
            old_size = self.max_position

            event_pos_chars = last_event_position[0] + (last_event_position[1] * old_size[0])
            new_event_pos = [*reversed([*divmod(event_pos_chars, new_size[0])])]  # [event_pos_chars // new_size[0], event_pos_chars % new_size[0]]
            event.position = new_event_pos

    def redraw_interface(self):
        # Clear the screen and redraw all elements
        # Maybe call finishCMD or similar methods on each event or element
        # But not needed for now as the terminal re-wraps everything for us
        pass

    def windowTick(self):
        self.handle_resize()
        for event in self.events:
            #print(event)
            #print(self.max_position)
            event.update(self.cursor)
        self.cursor.go_to(*self.max_position)
            
    def startEventLoop(self, interval=0.1):
        self.loop_thread = threading.Thread(target=self.eventLoop, args=(interval,))
        self.loop_thread.start()
        
    def eventLoop(self, interval):
        while not self.stop_event.is_set():
            try:
                time.sleep(interval)
                self.windowTick()
            except Exception as e: # Check for ctr + c
                print(f"An error has occurred: {e}")
                break
            
    def sendText(self, *content, no_send=False):
        for item in content:
            if issubclass(type(item), events.Event):
                self.max_position[1] += item.length
                item.position = self.cursor.position
                self._appendEvent(item)
            elif issubclass(type(item), InLineStyleAttr):
                self._appendStyle(item)
            else:
                #input(type(item))
                if item != "\n":
                    self.max_position[1] += 1
                else:
                    self.max_position[0] += 1
                self._appendText(item)
        if not no_send:
            self.cursor.finishCMD()
            
    def _appendText(self, text):
        self.cursor.appendCMD(text)
        #self.cursor.finishCMD()


    def _appendStyle(self, new_style):
        self.cursor.appendCMD("\033[0m")
        for i, part in enumerate([x for x in new_style.value.split(";")]):
            if part.isnumeric():
                if not part == 0:
                    self.last_style[i] = part
                else:
                    self.last_style[i] = [1, 37, 40][i]
        style_str = ';'.join([str(y) for y in self.last_style])
        print(style_str)
        self.cursor.appendCMD(f"\033[{style_str}m")
        #self.cursor.finishCMD()
            
    def stopEventLoop(self):
        self.stop_event.set()
        self.loop_thread.join()  # Wait for the event loop thread to finish
            
    def _appendEvent(self, event):
        self.events.append(event)
        
    def _removeEvent(self, event):
        self.events.remove(event)
        
    def _clearEvents(self):
        self.events = []
        
    def _replaceEvents(self, events: list):
        self.events = events
