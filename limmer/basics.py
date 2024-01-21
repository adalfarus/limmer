import time
import sys
import threading
from .styles import InlineStyle
#from .events import Event

class Cursor:
    def __init__(self, position=(0, 0)):
        self.position = position
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
        
class Event:
    length = 0
    def __init__(self, position=(0, 0)):
        self.position = position
        self.current_cursor = None
        self.loop_running = False
        self.loop_thread = None
        
    def update(self, cursor: Cursor):
        self.current_cursor = cursor
        
    def doUpdate(self, cursor: Cursor):
        cursor.go_to(*self.position)
        # ...
        cursor.finishCMD()
        
    def startEventLoop(self):
        self.loop_running = True
        self.loop_thread = threading.Thread(target=self.eventLoop)
        self.loop_thread.start()
        
    def eventLoop(self):
        for i in range(100):
            time.sleep(0.1) # Do stuff
            
            # Update
            if self.current_cursor:
                self.doUpdate(self.current_cursor)
                self.current_cursor = None
    
    def stopEventLoop(self):
        self.loop_running = False
        self.loop_thread.join()  # Wait for the event loop thread to finish

class Window:
    def __init__(self):
        self.cursor = Cursor()
        self.events = []
        self.loop_running = False
        self.loop_thread = None
        
        self.max_position = (0, 0)
        
    def windowTick(self):
        for event in self.events:
            event.update(self.cursor)
            
    def startEventLoop(self, interval=0.1):
        self.loop_running = True
        self.loop_thread = threading.Thread(target=self.eventLoop, args=(interval,))
        self.loop_thread.start()
        
    def eventLoop(self, interval):
        while self.loop_running:
            time.sleep(interval)
            self.windowTick()
            
    def sendText(self, *content):
        for item in content:
            if issubclass(item, Event):
                self.events.append(item)
            elif issubclass(item, InlineStyle):
                self.style
            
    def stopEventLoop(self):
        self.loop_running = False
        self.loop_thread.join()  # Wait for the event loop thread to finish
            
    def _appendEvent(self, event):
        self.events.append(event)
        
    def _removeEvent(self, event):
        self.events.remove(event)
        
    def _clearEvents(self):
        self.events = []
        
    def _replaceEvents(self, events: list):
        self.events = events
