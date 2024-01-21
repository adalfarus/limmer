from .basics import Event, Cursor

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
