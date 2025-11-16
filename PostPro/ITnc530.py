import math
import FreeCAD as App

Name = "ITnc530"

Ext = "h"

def blockForm(stock):
    bb = stock.Shape.BoundBox
    blk = f"BLK FORM 01 X{bb.XMin:.3f} Y{bb.YMin:.3f} Z{bb.ZMin:.3f}\n"
    blk += f"BLK FORM 02 X{bb.XMax:.3f} Y{bb.YMax:.3f} Z{bb.ZMax:.3f}\n"
    return blk

def toolChange(tool, cam_project):
    tool_id = getattr(tool, 'Id', None)
    tool_name = getattr(tool, 'Label', None)
    spindle = getattr(tool, 'SpindleSpeed', None)
    return f"TOOL CALL Z {tool_id} S{spindle} DL+0 DR+0\nM3\n"


def G81(obj):
    doc = App.ActiveDocument
    geom = doc.getObject(obj.DrillGeometryName)
    if geom and hasattr(geom, 'DrillPositions'):
        points = geom.DrillPositions
    safe_z = getattr(obj, 'SafeHeight', 5.0).Value
    final_z = getattr(obj, 'FinalDepth', -5.0).Value

    gcode_lines = ""
    gcode_lines +=(f"CYCL DEF 200 PERCAGE \n\
                       \tQ200={safe_z};DISTANCE D'APPROCHE\n\
                       \tQ201={final_z};PROFONDEUR\n\
                       \tQ206=250;AVANCE PLONGÉE PROF.\n\
                       \tQ202={math.fabs(final_z)};PROFONDEUR DE PASSE\n\
                       \tQ210=0;TEMPO. EN HAUT\n\
                       \tQ203=+0;COORD. SURFACE PIÈCE\n\
                       \tQ204=100;SAUT DE BRID\n\
                       \tQ211=0.1;TEMPO. AU FOND\n")
    for pt in points:
        gcode_lines += (f"L X{pt.x:.3f} Y{pt.y:.3f} FMAX M99\n")
        
    
    return gcode_lines