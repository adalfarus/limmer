from .basics import Cursor
import threading
import time


class Event:
    length = 0

    def __init__(self, position=(1, 1)):
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
            time.sleep(0.1)  # Do stuff

            # Update
            if self.current_cursor:
                self.doUpdate(self.current_cursor)
                self.current_cursor = None

    def stopEventLoop(self):
        self.loop_running = False
        self.loop_thread.join()  # Wait for the event loop thread to finish


class SpinningEvent(Event):
    length = 1

    def __init__(self, position=(0, 0)):
        super().__init__(position)
        self.spinner = spinning_cursor()
        
    def doUpdate(self, cursor: Cursor):
        cursor.go_to(*self.position)
        cursor.go_left()
        cursor.appendCMD(next(self.spinner))
        cursor.finishCMD()


def spinning_cursor():
    while True:
        for cursor in '\\|/-':
            yield cursor


class PointingsEvent(Event):
    length = 3

    def __init__(self, position=(0, 0)):
        super().__init__(position)
        self.spinner = pointings_cursor()
        
    def doUpdate(self, cursor: Cursor):
        cursor.go_to(*self.position)
        cursor.go_left(3)
        cursor.appendCMD(next(self.spinner))
        cursor.finishCMD()


def pointings_cursor():
    while True:
        for cursor in ["   ", ".  ", ".. ", "..."]:
            yield cursor


class BetterPointingsEvent(PointingsEvent):
    def doUpdate(self, cursor: Cursor):
        cursor.go_to(*self.position)
        cursor.go_left(3)
        
        pointing = next(self.spinner).strip()
        
        difference = self.length - len(pointing)
        
        cursor.appendCMD(pointing + (" " * difference))
        cursor.go_left(difference)
        cursor.finishCMD()
