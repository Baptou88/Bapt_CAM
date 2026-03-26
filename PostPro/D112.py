from typing import Any


import BasePostPro
from utils.formatFloat import format_float

Name = "D112"

Ext: str = ""


class PostPro(BasePostPro.BasePostPro):
    def __init__(self) -> None:
        super().__init__()

    def writeHeader(self) -> str:
        return "O0001\nG21 (mm)\nG90 (absolute programming)\nG40 (cutter radius compensation off)\nG80 (cancel canned cycle)\nG17 (XY plane selection)\n"

    def coolantModeToCode(self, mode) -> str:
        if mode == "Off":
            return "9"
        elif mode == "Flood":
            return "8"
        elif mode == "Mist":
            return "7"
        else:
            return "9"  # Default to Off if unknown mode

    def transformGCode(self, gcode) -> str:
        lines: list[str] = gcode.split('\n')
        retour = []
        for i in range(len(lines)):
            if lines[i].startswith('(') and lines[i].endswith(')'):
                lines[i] = lines[i][1:-1]  # Remove parentheses
                lines[i] = self.writeComment(lines[i])
            retour.append(lines[i])
        return '\n'.join(retour)

    def writeComment(self, comment) -> str:
        return f"; {comment}"

    def blockForm(self, stock) -> str:
        bb = stock.Shape.BoundBox

        return f"WORKPIECE(,\"\",,\"BOX\",112,{format_float(bb.ZMax)},{format_float(bb.ZMin)},-80,{format_float(bb.XMin)},{format_float(bb.YMin)},{format_float(bb.XMax)},{format_float(bb.YMax)})"

    def toolChange(self, tool, cam_project) -> str:
        tool_id: Any | None = getattr(tool, 'Name', None)
        spindle = getattr(tool, 'Speed', None).getValueAs("mm/min")  # FIXME Speed
        return f"\nT={tool_id} D1\nM6\nS{spindle} M3\n"

    def G81(self, obj) -> str:

        return obj.GCode

    def G83(self, obj) -> str:
        return obj.GCode

    def G84(self, obj) -> str:
        return obj.GCode
