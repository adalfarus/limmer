class AddOnAccessDescriptor:
    def __init__(self, value, formatter):
        self.value = value
        self.formatter = formatter

    def __str__(self):
        return self.formatter(self.value)

def inline_style_formatter(value):
    return f"\033[{value}m"

class InlineStyle:
    @staticmethod
    def addAttr(value):
        return AddOnAccessDescriptor(value, inline_style_formatter)
        
    CLEAR = addAttr("0")

class Color(InlineStyle):
    BLACK = InlineStyle.addAttr("0;30")
    RED = InlineStyle.addAttr("0;31")
