import math
from BasePostPro import BasePostPro
import FreeCAD as App

class PostPro(BasePostPro):
    Name = "ITnc530"
    Ext = "h"

    def __init__(self):
        super().__init__()

    def writeHeader(self):
        header = ""
        header += "BEGIN PGM ITNC530 MM\n"

        return header
    
    def writeFooter(self):
        footer = ""
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

        lines = gcode.split('\n')
        retour = []
        for i in range(len(lines)):
            if lines[i].startswith('(') and lines[i].endswith(')'):
                lines[i] = lines[i][1:-1]  # Remove parentheses
                lines[i]  = self.writeComment(lines[i])
            elif lines[i].startswith('G0'):
                lines[i] = lines[i].replace('G0', 'L ')
                lines[i] += ' FMAX'
            elif lines[i].startswith('G1'):
                lines[i] = lines[i].replace('G1', 'L ')
                feed = None
                if 'F' in lines[i]:
                    parts = lines[i].split('F')
                    #remove feed from line
                    lines[i] = parts[0]
                    feed =  parts[1]
                if 'G40' in lines[i]:
                    lines[i] = lines[i].replace('G40', '')
                    lines[i] += ' R0'
                if 'G41' in lines[i]:
                    # parts = lines[i].split('F')
                    # lines[i] = parts[0] + ' F' + parts[1]
                    lines[i] = lines[i].replace('G41', '')
                    lines[i] += ' RL'
                if 'G42' in lines[i]:
                    lines[i] = lines[i].replace('G42', '')
                    lines[i] += ' RR'
                if feed is not None:
                    lines[i] += f' F{feed}'

            retour.append(lines[i])
        return '\n'.join(retour)

    def toolChange(self, tool, cam_project):
        tool_id = getattr(tool, 'Id', None)
        tool_name = getattr(tool, 'Label', None)
        spindle = getattr(tool, 'Speed', None).Value
        Feed = getattr(tool, 'Feed', None).Value
        return f"TOOL CALL {tool_id} Z S{spindle} DL+0 DR+0\nL R0 F{Feed} M3\n"


    def G81(self, obj):
        doc = App.ActiveDocument
        geom = doc.getObject(obj.DrillGeometryName)
        if geom and hasattr(geom, 'DrillPositions'):
            points = geom.DrillPositions
        safe_z = getattr(obj, 'SafeHeight', 5.0).Value
        final_z = getattr(obj, 'FinalDepth', -5.0).Value

        gcode_lines = ""
        gcode_lines +=(f"CYCL DEF 200 PERCAGE \n\
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