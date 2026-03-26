

class BasePostPro:
    Ext = ""

    def __init__(self):
        self.line = 10
        self.lineIncrement = 10
        self.useLineNumbers = False

    def writeComment(self, comment: str) -> str:
        return f"({comment})"

    def writeHeader(self) -> str:
        h = []
        h.append("%")
        h.append("O0001")
        h.append(f"G21 {self.writeComment('mm')}")
        h.append(f"G90 {self.writeComment('absolute programming')}")
        h.append(f"G40 {self.writeComment('cutter radius compensation off')}")
        h.append(f"G80 {self.writeComment('cancel canned cycle')}")
        h.append(f"G17 {self.writeComment('XY plane selection')}")
        return '\n'.join(h)

    def addLineNumbers(self, gcode: str) -> str:
        if not self.useLineNumbers:
            return gcode
        numbered = []
        n = self.line
        for line in gcode.split('\n'):
            if line.strip():
                numbered.append(f"N{n} {line}")
                n += self.lineIncrement
            else:
                numbered.append(line)
        return '\n'.join(numbered)

    def transformGCode(self, gcode: str) -> str:
        return gcode

    def writeFooter(self) -> str:
        f = []
        f.append(f"M9 {self.writeComment('coolant off')}")
        f.append(f"M5 {self.writeComment('stop spindle')}")
        f.append(f"M30 {self.writeComment('end of program')}")
        return '\n'.join(f)

    def blockForm(self, stock) -> str:
        bb = stock.Shape.BoundBox
        s = f"{bb.XMin},{bb.YMin},{bb.ZMin} to {bb.XMax},{bb.YMax},{bb.ZMax}"
        return f"{self.writeComment(s)}"

    def toolChange(self, tool, cam_project) -> str:
        tool_id = getattr(tool, 'Id', None)
        tool_name = getattr(tool, 'Label', None)
        spindle = getattr(tool, 'SpindleSpeed', None)

        gcode_lines = []
        gcode_lines.append(self.writeComment(f'Changement d\'outil: {tool_name if tool_name else ""}'))
        gcode_lines.append(f"M6 T{tool_id}")
        if spindle:
            gcode_lines.append(f"S{spindle} M3")
        return '\n'.join(gcode_lines)

    def coolantChange(self, coolantMode) -> str:
        if coolantMode == "Off":
            return f"M9 {self.writeComment('Coolant Off')}"
        elif coolantMode == "Flood":
            return f"M8 {self.writeComment('Coolant Flood On')}"
        elif coolantMode == "Mist":
            return f"M7 {self.writeComment('Coolant Mist On')}"
        else:
            return f"M9 {self.writeComment(f'Coolant Off - Unknown mode: {coolantMode}')}"  # Default to Off if unknown mode

    def G81(self, obj):
        """G81 - Canned Drilling Cycle"""
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight').Value
        gcode_lines = []
        gcode_lines.append(f"G81 R{safe_z} Z{obj.FinalDepth.Value} F{obj.FeedRate.Value}")
        for pt in points:
            gcode_lines.append(f"G0 X{pt.x} Y{pt.y} Z{safe_z}")
        gcode_lines.append("G80")
        return '\n'.join(gcode_lines)

    def G83(self, obj):
        """Cycle de perçage par reprise (G83)"""
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight').Value
        gcode_lines = []
        gcode_lines.append(f"G83 R{safe_z} Z{obj.FinalDepth.Value} Q{obj.PeckDepth.Value} F{obj.FeedRate.Value}")
        for pt in points:
            gcode_lines.append(f"G0 X{pt.x} Y{pt.y} Z{safe_z}")
        gcode_lines.append("G80")
        return '\n'.join(gcode_lines)

    def G84(self, obj):
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight').Value
        spindle = getattr(obj, 'SpindleSpeed', None)
        gcode_lines = []
        gcode_lines.append(f"S{spindle} M3")
        gcode_lines.append(f"G84 R{safe_z} Z{obj.FinalDepth.Value} F{obj.FeedRate.Value}")
        for pt in points:
            gcode_lines.append(f"G0 X{pt.x} Y{pt.y} Z{safe_z}")
        gcode_lines.append("G80")
        return '\n'.join(gcode_lines)
