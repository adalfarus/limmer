import time
import sys
import signal
import threading
from .styles import InLineStyleAttr
from . import events
from .ANSIUtils import query_cursor_position
import os
from typing import List, Optional, Union


class Cursor:
    def __init__(self, position: Optional[List[int]]=None):
        self.position = list(position or query_cursor_position())
        self.current_command = ""
        
    def go_up(self, n: int=1):
        self.position[1] -= n
        self.current_command += f"\x1b[{n}A"
    
    def go_down(self, n: int=1):
        self.position[1] += n
        self.current_command += f"\x1b[{n}B"
    
    def go_left(self, n: int=1):
        self.position[0] -= n
        self.current_command += f"\x1b[{n}D"
    
    def go_right(self, n: int=1):
        self.position[0] += n
        self.current_command += f"\x1b[{n}C"

    def refresh_pos(self):
        self.position = list(query_cursor_position())

    def go_to(self, x: int, y: int):
        #self.refresh_pos()
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
        #sys.stdout.write(" \b")
        #sys.stdout.flush()
        self.cursor = Cursor()
        print("CCCCCCCCCC", self.cursor.position)
        self.events = []
        self.loop_thread = None
        self.stop_event = threading.Event()

        self.max_position = self.get_terminal_size()
        self.last_style = [0, 37, 40]

    @staticmethod
    def get_terminal_size():
        terminal_size_object = os.get_terminal_size()
        width, height = terminal_size_object.columns, terminal_size_object.lines
        return [width, height]

    @staticmethod
    def clamp_list(lst: list, smallest: list, biggest: list):
        for i, element in enumerate(lst):
            lst[i] = min(max(element, smallest[i]), biggest[i])
        return lst

    def handle_resize(self):
        new_size = self.get_terminal_size()
        if new_size[0] != self.max_position[0]:
            self.recalculate_positions(new_size)
            self.max_position = new_size  # Needs to be adjusted here or recalculate position can't scale old positions
            self.redraw_interface()
        if new_size != self.max_position:
            cursor_position = self.cursor.position
            self.cursor.position = self.clamp_list(cursor_position, [1, 1], self.max_position)

    def recalculate_positions(self, new_size: List[int]):
        #print("\nRE", new_size, self.max_position)
        for event in self.events:  # Dynamic event length is kinda easy with this now
            # Logic to adjust the position of each event
            last_event_position = event.position
            old_width = self.max_position[0]

            # x + (y * width)
            event_pos_chars = last_event_position[0] + (last_event_position[1] * old_width)
            new_event_pos = [*divmod(event_pos_chars, new_size[0])][::-1]
            # [event_pos_chars // new_size[0], event_pos_chars % new_size[0]] = divmod
            # Slicing is more readable,but can be a lot slower than the old with large lists as it creates entire copies
            event.position = new_event_pos

    def redraw_interface(self):
        # Clear the screen and redraw all elements
        # Maybe call finishCMD or similar methods on each event or element
        # But not needed for now as the terminal re-wraps everything for us
        pass

    def windowTick(self):
        #self.cursor.refresh_pos()
        self.handle_resize()
        for event in self.events:
            #print(event)
            #print(self.max_position)
            event.update(self.cursor)
        #sys.stdout.write(" \b")
        #sys.stdout.flush()
        #self.cursor.refresh_pos()#self.cursor.go_to(*self.max_position)
            
    def startEventLoop(self, interval: Union[int, float]=0.1):
        self.loop_thread = threading.Thread(target=self.eventLoop, args=(interval,))
        self.loop_thread.start()
        
    def eventLoop(self, interval: Union[int, float]):
        while not self.stop_event.is_set():
            try:
                time.sleep(interval)
                self.windowTick()
            except Exception as e: # Check for ctr + c
                print(f"An error has occurred: {e}")
                break

    # : Union[events.Event, str, InLineStyleAttr]
    def sendText(self, *content, no_send: bool=False):
        for item in content:
            if issubclass(type(item), events.Event):
                #self.max_position[1] += item.length
                #self.cursor.position = self.max_position
                item.position = self.cursor.position
                self._appendEvent(item)
                print("HEEEELLLLPPPP", item.position)
            elif issubclass(type(item), InLineStyleAttr):
                self._appendStyle(item)
            else:
                #input(type(item))
                #if item != "\n":
                #    self.max_position[1] += 1
                #else:
                #    self.max_position[0] += 1
                self._appendText(item)
            self.cursor.refresh_pos()
        if not no_send:
            self.cursor.finishCMD()
            
    def _appendText(self, text: str):
        self.cursor.appendCMD(text)
        #self.cursor.finishCMD()


    def _appendStyle(self, new_style: InLineStyleAttr):
        self.cursor.appendCMD("\x1b[0m")
        for i, part in enumerate([x for x in new_style.value.split(";")]):
            if part.isnumeric() or part.replace(":", "").isnumeric():
                part = part.replace(":", ";")
                if not part == 0:
                    self.last_style[i] = part
                else:
                    self.last_style[i] = [0, 37, 40][i]
        style_str = ';'.join([str(y) for y in self.last_style])
        print(style_str)
        self.cursor.appendCMD(f"\x1b[{style_str}m")
        #self.cursor.finishCMD()
            
    def stopEventLoop(self):
        self.stop_event.set()
        self.loop_thread.join()  # Wait for the event loop thread to finish

    # : events.Event
    def _appendEvent(self, event):
        self.events.append(event)

    # : events.Event
    def _removeEvent(self, event):
        self.events.remove(event)
        
    def _clearEvents(self):
        self.events = []

    # : List[events.Event]
    def _replaceEvents(self, events_lst):
        self.events = events_lst
