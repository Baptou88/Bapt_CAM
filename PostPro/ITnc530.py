import math
from BasePostPro import BasePostPro

from utils.formatFloat import format_float

Ext = "h"
Name = "ITnc530"


class PostPro(BasePostPro):

    def __init__(self):
        super().__init__()

    def writeHeader(self):
        header = ""
        header += "BEGIN PGM ITNC530 MM\n"
        header += "CYCLE DEF 7\n"

        return header

    def writeFooter(self):
        footer = "M30"
        footer += "END PGM ITNC530 MM\n"

        return footer

    def writeComment(self, comment):
        return f"; {comment}"

    def blockForm(self, stock):
        bb = stock.Shape.BoundBox
        blk = f"BLK FORM 01 X{bb.XMin:.3f} Y{bb.YMin:.3f} Z{bb.ZMin:.3f}\n"
        blk += f"BLK FORM 02 X{bb.XMax:.3f} Y{bb.YMax:.3f} Z{bb.ZMax:.3f}\n"
        return blk

    def transformGCode(self, gcode):
        current_pos = {'X': 0.0, 'Y': 0.0, 'Z': 0.0}
        lines = gcode.split('\n')
        retour = []

        def linear_move(line: str, rapid: bool = None):
            current_move = 'G1'
            if rapid is not None:
                current_move = 'G0' if rapid else 'G1'

            if line.startswith('G'):
                space = line.index(' ')
                new_line = line[space + 1:]
            else:
                new_line = line

            for axis in ['X', 'Y', 'Z']:
                if axis in new_line:
                    parts = new_line.split(axis)
                    coord_part = parts[1]
                    coord_str = ''
                    for c in coord_part:
                        if c in ' XYZFMG':
                            break
                        coord_str += c
                    if coord_str != '':
                        current_pos[axis] = float(coord_str)

            if 'G40' in line:
                new_line = new_line.replace('G40', '')
                new_line += ' R0'

            if 'G41' in line:
                new_line = new_line.replace('G41', '')
                new_line += ' RL'

            if 'G42' in line:
                new_line = new_line.replace('G42', '')
                new_line += ' RR'

            if 'F' in new_line:
                parts = new_line.split('F')
                # remove feed from line
                new_line = parts[0]
                feed = parts[1]
                new_line += f' F{feed}'

            if current_move == 'G0':
                # place Fmax before ';'
                if ';' in new_line:
                    semicolon_index = new_line.index(';')
                    new_line = new_line[:semicolon_index] + ' FMAX ' + new_line[semicolon_index:]

            return 'L ' + new_line

        def circular_move(line: str, clockwise: bool = True):
            current_move = 'R-' if clockwise else 'R+'
            cc_pos = {'X': None, 'Y': None, 'Z': None}

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
            new_line = "CC "
            for axis in cc_pos:
                if cc_pos[axis] is not None:
                    new_line += f"{axis}{cc_pos[axis]:.3f} "
            new_line += "\nC "
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
            new_line += f"{current_move} "
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

        for i in range(len(lines)):
            if lines[i].startswith('(') and lines[i].endswith(')'):
                lines[i] = lines[i][1:-1]  # Remove parentheses
                lines[i] = self.writeComment(lines[i])
            elif lines[i].startswith(('G0', 'G00')):
                lines[i] = linear_move(lines[i], rapid=True)
            elif lines[i].startswith(('G1', 'G01')):
                lines[i] = linear_move(lines[i], rapid=False)
            elif lines[i].startswith(('G2', 'G02')):
                lines[i] = circular_move(lines[i], clockwise=True)
            elif lines[i].startswith(('G3', 'G03')):
                lines[i] = circular_move(lines[i], clockwise=False)
            elif lines[i].startswith(('X', 'Y', 'Z')):
                lines[i] = linear_move(lines[i], rapid=None)

            retour.append(lines[i])
        return '\n'.join(retour)

    def toolChange(self, tool, cam_project):
        tool_id = getattr(tool, 'Id', None)
        spindle = getattr(tool, 'Speed', None).Value
        Feed = getattr(tool, 'Feed', None).Value
        return f"TOOL CALL {tool_id} Z S{spindle} DL+0 DR+0\nL R0 F{format_float(Feed)} M3\n"

    def G81(self, obj):
        geom = obj.DrillGeometry
        points = []
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions
        safe_z = getattr(obj, 'SafeHeight', 5.0).Value
        final_z = getattr(obj, 'FinalDepth', -5.0).Value

        gcode_lines = ""
        gcode_lines += (f"CYCL DEF 200 PERCAGE \n\
            Q200={safe_z};DISTANCE D'APPROCHE\n\
            Q201={final_z};PROFONDEUR\n\
            Q206=250;AVANCE PLONGÉE PROF.\n\
            Q202={math.fabs(final_z)};PROFONDEUR DE PASSE\n\
            Q210=0;TEMPO. EN HAUT\n\
            Q203=+0;COORD. SURFACE PIÈCE\n\
            Q204=100;SAUT DE BRID\n\
            Q211=0.1;TEMPO. AU FOND\n")
        for pt in points:
            gcode_lines += (f"L X{pt.x:.3f} Y{pt.y:.3f} FMAX M99\n")

        return gcode_lines
