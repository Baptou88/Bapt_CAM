from typing import Any

import BasePostPro
from utils.formatFloat import format_float

Name = "D112"

Ext: str = ""


class PostPro(BasePostPro.BasePostPro):
    def __init__(self) -> None:
        super().__init__()
        self.useLineNumbers = True
        self.useLabel = False
        self.labels: dict[str, int] = {}  # Dictionary to store label positions

    def writeHeader(self) -> str:
        return "O0001\nG21 (mm)\nG90 (absolute programming)\nG40 (cutter radius compensation off)\nG80 (cancel canned cycle)\nG17 (XY plane selection)\nG54 (work coordinate system)\n"

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
        current_pos = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}

        def circular_move(line: str, clockwise: bool = True):

            cc_pos = {'I': None, 'J': None, 'K': None}

            for axis in ['I', 'J', 'K']:
                if axis in line:
                    parts = line.split(axis)
                    coord_part = parts[1]
                    coord_str = ''
                    for c in coord_part:
                        if c in ' XYZIJKFMGR':
                            break
                        coord_str += c
                    if coord_str != '':

                        if axis == 'I':
                            cc_pos[axis] = current_pos['X'] + float(coord_str)
                        elif axis == 'J':
                            cc_pos[axis] = current_pos['Y'] + float(coord_str)
                        elif axis == 'K':
                            cc_pos[axis] = current_pos['Z'] + float(coord_str)

            new_line = "G2 " if clockwise else "G3 "

            for axis in ['X', 'Y', 'Z']:
                if axis in line:
                    parts = line.split(axis)
                    coord_part = parts[1]
                    coord_str = ''
                    for c in coord_part:
                        if c in ' XYZIJKFMGR':
                            break
                        coord_str += c
                    if coord_str != '':
                        current_pos[axis] = float(coord_str)
                        new_line += f"{axis}{current_pos[axis]:.3f} "

            for axis in cc_pos:
                if cc_pos[axis] is not None:
                    new_line += f"{axis}{cc_pos[axis]:.3f} "
            new_line += " "

            if 'F' in line:
                parts = line.split('F')
                # remove feed from line

                feed_part = parts[1]
                feed_str = ''
                for c in feed_part:
                    if c in ' XYZIJKFMGR':
                        break
                    feed_str += c
                new_line += f' F{feed_str}'

            return new_line

        def linear_move(line: str):
            for axis in ['X', 'Y', 'Z']:
                if axis in line:
                    parts = line.split(axis)
                    coord_part = parts[1]
                    coord_str = ''
                    for c in coord_part:
                        if c in ' XYZIJKFMGR':
                            break
                        coord_str += c
                    if coord_str != '':
                        current_pos[axis] = float(coord_str)
            return line

        retour = []
        for i in range(len(lines)):
            if lines[i].startswith(';'):
                lines[i] = lines[i][1:]  # Remove the semicolon
                lines[i] = self.writeComment(lines[i])
            if lines[i].startswith(('G2', 'G02')):
                lines[i] = circular_move(lines[i], clockwise=True)
            elif lines[i].startswith(('G3', 'G03')):
                lines[i] = circular_move(lines[i], clockwise=False)
            elif lines[i].endswith(':'):
                # this is a label, memorize the name and the current position
                label_name = lines[i][:-1]
                self.labels[label_name] = i
                if not self.useLabel:
                    lines[i] = ''  # Remove the label line if not using labels
                else:
                    pass  # Keep the label line if using labels
            elif lines[i].startswith('REPEAT'):
                # example: REPEAT LabelStart LabelEnd P=1
                a = lines[i].split()
                if len(a) >= 4 and a[0] == 'REPEAT':
                    label_start = a[1]
                    label_end = a[2]
                    p_value = 1
                    for part in a[3:]:
                        if part.startswith('P='):
                            try:
                                p_value = int(part.split('=')[1])
                            except ValueError:
                                p_value = 1
                    if not self.useLabel and label_start in self.labels and label_end in self.labels:
                        start_index = self.labels[label_start]
                        end_index = self.labels[label_end]
                        # remove the REPEAT line and insert the repeated lines
                        if start_index < end_index:
                            repeat_lines = lines[start_index + 1:end_index]
                            for _ in range(p_value):
                                # retour.extend(repeat_lines) #maybe reuse transformGCode on repeat_lines to handle nested repeats
                                retour.extend(self.transformGCode('\n'.join(repeat_lines)).split('\n'))
                            continue  # Skip appending the original REPEAT line
                    else:
                        pass
                # this is a repeat command,
            retour.append(lines[i])
        return '\n'.join(retour)

    def writeComment(self, comment) -> str:
        return f"({comment})"

    def blockForm(self, stock) -> str:
        bb = stock.Shape.BoundBox
        return self.writeComment(f"xmin: {format_float(bb.XMin)}, ymin: {format_float(bb.YMin)}, zmin: {format_float(bb.ZMin)}, xmax: {format_float(bb.XMax)}, ymax: {format_float(bb.YMax)}, zmax: {format_float(bb.ZMax)}")

    def toolChange(self, tool, cam_project) -> str:
        tool_id: Any | None = getattr(tool, 'Id', None)
        spindle = getattr(tool, 'Speed', None).getValueAs("mm/min")  # FIXME Speed
        tool_name = getattr(tool, 'Label', None)
        tool_diameter = getattr(tool, 'Radius', None).getValueAs("mm") * 2
        comment = f'Changement d outil: {tool_name if tool_name else ""}, Diamètre: {format_float(tool_diameter)} mm'
        return f"\nT{tool_id} D1\nM6\nS{spindle} M3\n{self.writeComment(comment)}\n"

    def G81(self, obj) -> str:

        return obj.GCode

    def G83(self, obj) -> str:
        return obj.GCode

    def G84(self, obj) -> str:
        return obj.GCode
