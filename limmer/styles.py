from typing import Union


class InLineStyleAttr:
    def __init__(self, value: str):
        self.value: str = value

    def __repr__(self):
        last_style = [0, 37, 40]
        for i, part in enumerate([x for x in self.value.split(";")]):
            if part.isnumeric() or part.replace(":", "").isnumeric():
                part = part.replace(":", ";")
                if not part == 0:
                    last_style[i] = part
                else:
                    last_style[i] = [0, 37, 40][i]
        style_str = ';'.join([str(y) for y in last_style])
        return f"\x1b[0m\x1b[{style_str}m"


class InlineStyle:
    @staticmethod
    def addAttr(value: str) -> InLineStyleAttr:
        return InLineStyleAttr(value)
        
    CLEAR = addAttr("0;0;0")


class Color(InlineStyle):
    BLACK = InlineStyle.addAttr(";30;")
    RED = InlineStyle.addAttr(";31;")
    GREEN = InlineStyle.addAttr(";32;")
    YELLOW = InlineStyle.addAttr(";33;")
    BLUE = InlineStyle.addAttr(";34;")
    MAGENTA = InlineStyle.addAttr(";35;")
    CYAN = InlineStyle.addAttr(";36;")
    WHITE = InlineStyle.addAttr(";37;")
    CLEAR = InlineStyle.addAttr(";0;")

    @staticmethod
    def RGB(r: Union[str, int], g: Union[str, int], b: Union[str, int]) -> InLineStyleAttr:
        return InLineStyleAttr(f";38:2:{r}:{g}:{b};")


class Formatting(InlineStyle):
    BOLD = InlineStyle.addAttr("1;;")
    ITALIC = InlineStyle.addAttr("3;;")
    STRIKETROUGH = InlineStyle.addAttr("9;;")
    UNDERLINE = InlineStyle.addAttr("4;;")
    SUBSCRIPT = InlineStyle.addAttr("8B;;")  # Source: http://www.inwap.com/pdp10/ansicode.txt
    SUPERSCRIPT = InlineStyle.addAttr("8C;;")  # Partial Line Down (subscript) ; Partial Line Up (superscript)
    CLEAR = InlineStyle.addAttr("0;;")


class Background(InlineStyle):
    BLACK = InlineStyle.addAttr(";;40")
    RED = InlineStyle.addAttr(";;41")
    GREEN = InlineStyle.addAttr(";;42")
    YELLOW = InlineStyle.addAttr(";;43")
    BLUE = InlineStyle.addAttr(";;44")
    MAGENTA = InlineStyle.addAttr(";;45")
    CYAN = InlineStyle.addAttr(";;46")
    WHITE = InlineStyle.addAttr(";;47")
    CLEAR = InlineStyle.addAttr(";;0")

    @staticmethod
    def RGB(r: Union[str, int], g: Union[str, int], b: Union[str, int]) -> InLineStyleAttr:
        return InLineStyleAttr(f";;48:2:{r}:{g}:{b}")
