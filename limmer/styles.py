

class InLineStyleAttr:
    def __init__(self, value):
        self.value = value

class InlineStyle:
    @staticmethod
    def addAttr(value):
        return InLineStyleAttr(value)
        
    CLEAR = addAttr("0;0;0")

class Color(InlineStyle):
    BLACK = InlineStyle.addAttr(";30;")
    RED = InlineStyle.addAttr(";31;")
