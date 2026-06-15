import BasePostPro
from utils.formatFloat import format_float

Name = "Siemens828D"

Ext = "MPF"


class PostPro(BasePostPro.BasePostPro):
    def __init__(self):
        super().__init__()
        self.useLineNumbers = True

    def writeHeader(self):
        return ""

    def coolantModeToCode(self, mode):
        if mode == "Off":
            return "9"
        elif mode == "Flood":
            return "8"
        elif mode == "Mist":
            return "7"
        else:
            return "9"  # Default to Off if unknown mode

    def transformGCode(self, gcode):
        lines = gcode.split('\n')
        retour = []
        for i in range(len(lines)):
            if lines[i].startswith('(') and lines[i].endswith(')'):
                lines[i] = lines[i][1:-1]  # Remove parentheses
                lines[i] = self.writeComment(lines[i])
            lines[i] = lines[i].replace('G80', 'MCALL')  # Siemens 828D uses MCALL instead of G80 for canned cycle cancel
            lines[i] = lines[i].replace('(', ';')

            retour.append(lines[i])
        return '\n'.join(retour)

    def writeComment(self, comment):
        return f"; {comment}"

    def blockForm(self, stock):
        bb = stock.Shape.BoundBox

        return f"WORKPIECE(,\"\",,\"BOX\",112,{format_float(bb.ZMax)},{format_float(bb.ZMin)},-80,{format_float(bb.XMin)},{format_float(bb.YMin)},{format_float(bb.XMax)},{format_float(bb.YMax)})"

    def toolChange(self, tool, cam_project):
        tool_name = getattr(tool, 'Label', None)
        spindle = getattr(tool, 'Speed', None).getValueAs("mm/min")  # FIXME Speed
        return f"\nT=\"{tool_name}\" D1\nM6\nS{format_float(spindle, 0)} M3\n"

    def G81(self, obj):
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight', 5.0).Value
        final_z = getattr(obj, 'FinalDepth', -5.0).Value
        dwell = getattr(obj, 'DwellTime', 0.0)
        coolant = getattr(obj, 'CoolantMode', False)
        planDeRetrait = safe_z
        DistSecurite = safe_z
        z0 = None
        Speed = getattr(obj, 'SpindleSpeed', None).getValueAs("mm/min")  # FIXME Speed
        Feed = getattr(obj, 'FeedRate', None).getValueAs("mm/min")
        gcode_lines = f"S{format_float(Speed, 0)}\n"
        gcode_lines += f"F{Feed}\n"
        gcode_lines += f"M{self.coolantModeToCode(coolant)}\n"
        for pt in points:
            if z0 is None or z0 != pt.z:
                z0 = pt.z
                gcode_lines += (f"MCALL CYCLE81({z0 + planDeRetrait},{z0},{DistSecurite},{final_z},,{dwell},0,1,12)\n")
            gcode_lines += (f"G0 X{pt.x:.3f} Y{pt.y:.3f} \n")
        gcode_lines += "MCALL\n"
        return gcode_lines

    def G83(self, obj):
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight', 5.0).Value
        final_z = getattr(obj, 'FinalDepth', -5.0).Value
        dwell = getattr(obj, 'DwellTime', 0.0)
        coolant = getattr(obj, 'CoolantMode', False)
        peckDepth = getattr(obj, 'PeckDepth', 1.0).Value
        planDeRetrait = safe_z
        DistSecurite = safe_z
        z0 = None
        Speed = getattr(obj, 'SpindleSpeed', None).getValueAs("mm/min")  # FIXME Speed
        Feed = getattr(obj, 'FeedRate', None).getValueAs("mm/min")
        gcode_lines = f"S{format_float(Speed, 0)}\n"
        gcode_lines += f"F{Feed}\n"
        gcode_lines += f"M{self.coolantModeToCode(coolant)}\n"
        for pt in points:
            if z0 is None or z0 != pt.z:
                z0 = pt.z
                gcode_lines += (f"MCALL CYCLE83({z0 + planDeRetrait},{z0},{DistSecurite},{final_z},,,{peckDepth},{peckDepth},0,0,100,1,0,0,,,{dwell},0,0,1,11111112)\n")
            gcode_lines += (f"G0 X{pt.x:.3f} Y{pt.y:.3f} \n")
        gcode_lines += "MCALL\n"
        return gcode_lines

    def G84(self, obj):
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions

        safe_z = getattr(obj, 'SafeHeight', 5.0).Value
        final_z = getattr(obj, 'FinalDepth', -5.0).Value
        coolant = getattr(obj, 'CoolantMode', False)
        planDeRetrait = safe_z
        DistSecurite = safe_z
        z0 = None
        Speed = getattr(obj, 'SpindleSpeed', None).getValueAs("mm/min")  # FIXME Speed
        Feed = getattr(obj, 'FeedRate', None).getValueAs("mm/min")
        gcode_lines = f"S{Speed}\n"
        gcode_lines += f"F{Feed}\n"
        gcode_lines += f"M{self.coolantModeToCode(coolant)}\n"
        for pt in points:
            if z0 is None or z0 != pt.z:
                z0 = pt.z
                gcode_lines += (f"MCALL CYCLE84({z0 + planDeRetrait},{z0},{DistSecurite},{final_z},,1,12)\n")
            gcode_lines += (f"G0 X{pt.x:.3f} Y{pt.y:.3f} \n")
        gcode_lines += "MCALL\n"
        return gcode_lines
