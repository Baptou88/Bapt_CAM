# -*- coding: utf-8 -*-
"""
BaptPostProcess.py
Génère un programme G-code à partir des opérations du projet CAM
"""
from BaptPreferences import BaptPreferences
import FreeCAD as App
from PySide import QtGui
import os

def list_machining_operations(obj):
    """
    Parcourt récursivement toute l'arborescence de obj (Group, enfants, etc.)
    et retourne la liste de tous les objets d'usinage (ContournageCycle, DrillOperation, etc.).
    """
    if hasattr(obj, 'Label'):
        App.Console.PrintMessage(f"Objet: {obj.Label}\n")
    ops = []
    if hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and obj.Proxy.Type in [
        'ContournageCycle', 'DrillOperation', 'Surfacage']:
        ops.append(obj)
    # Parcours récursif des groupes/enfants
    if hasattr(obj, 'Group') and obj.Group:
        for child in obj.Group:
            ops.extend(list_machining_operations(child))
    return ops

def generate_gcode(cam_project):
    """
    Parcourt les opérations du projet CAM et génère du G-code (contournage, cycles de perçage, changements d'outil).
    Retourne le G-code sous forme de string.
    """
    gcode_lines = ["(Programme généré par BaptPostProcess)", "G21 (unit: mm)", "G90 (abs mode)"]
    current_tool = None
    current_spindle = None
    current_feed = None
    machining_ops = list_machining_operations(cam_project)
    App.Console.PrintMessage(f"Nombre d'opérations d'usinage: {len(machining_ops)}\n")
    for obj in machining_ops:
        if hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type'):
            # --- Surfacage ---
            if obj.Proxy.Type == 'Surfacage' and hasattr(obj, 'Shape'):
                # Gestion du changement d'outil si ToolId présent
                tool_id = getattr(obj, 'ToolId', None)
                tool_name = getattr(obj, 'ToolName', None)
                spindle = getattr(obj, 'SpindleSpeed', None)
                feed = getattr(obj, 'FeedRate', None)
                if tool_id is not None and tool_id != current_tool:
                    gcode_lines.append(f"(Changement d'outil: {tool_name if tool_name else ''})")
                    gcode_lines.append(f"M6 T{tool_id}")
                    if spindle:
                        gcode_lines.append(f"S{spindle} M3")
                        current_spindle = spindle
                    if feed:
                        gcode_lines.append(f"F{feed}")
                        current_feed = feed
                    current_tool = tool_id
                gcode_lines.append(f"(Surfacage: {obj.Label})")
                last_pt = None
                for edge in obj.Shape.Edges:
                    v1 = edge.Vertexes[0].Point
                    v2 = edge.Vertexes[1].Point
                    # Premier point: déplacement rapide (G0)
                    if last_pt is None or (v1.x != last_pt.x or v1.y != last_pt.y or v1.z != last_pt.z):
                        gcode_lines.append(f"G0 X{v1.x:.3f} Y{v1.y:.3f} Z{v1.z:.3f}")
                    # Arc de cercle ?
                    if hasattr(edge, 'Curve') and edge.Curve and edge.Curve.TypeId == 'Part::GeomCircle':
                        circle = edge.Curve
                        center = circle.Center
                        # Calculer I, J (relatifs au point de départ)
                        I = center.x - v1.x
                        J = center.y - v1.y
                        # Sens horaire/anti-horaire
                        if edge.Orientation == 'Forward':
                            gcode_cmd = 'G2'  # Horaire
                        else:
                            gcode_cmd = 'G3'  # Anti-horaire
                        gcode_lines.append(f"{gcode_cmd} X{v2.x:.3f} Y{v2.y:.3f} I{I:.3f} J{J:.3f} Z{v2.z:.3f}")
                    else:
                        # Usinage (G1)
                        gcode_lines.append(f"G1 X{v2.x:.3f} Y{v2.y:.3f} Z{v2.z:.3f}")
                    last_pt = v2
            # --- Contournage ---
            if obj.Proxy.Type == 'ContournageCycle' and hasattr(obj, 'Shape'):
                # Gestion du changement d'outil si ToolId présent
                tool_id = getattr(obj, 'ToolId', None)
                tool_name = getattr(obj, 'ToolName', None)
                spindle = getattr(obj, 'SpindleSpeed', None)
                feed = getattr(obj, 'FeedRate', None)
                if tool_id is not None and tool_id != current_tool:
                    gcode_lines.append(f"(Changement d'outil: {tool_name if tool_name else ''})")
                    gcode_lines.append(f"M6 T{tool_id}")
                    if spindle:
                        gcode_lines.append(f"S{spindle} M3")
                        current_spindle = spindle
                    if feed:
                        gcode_lines.append(f"F{feed}")
                        current_feed = feed
                    current_tool = tool_id
                gcode_lines.append(f"(Contournage: {obj.Label})")
                last_pt = None
                for edge in obj.Shape.Edges:
                    v1 = edge.Vertexes[0].Point
                    v2 = edge.Vertexes[1].Point
                    # Premier point: déplacement rapide (G0)
                    if last_pt is None or (v1.x != last_pt.x or v1.y != last_pt.y or v1.z != last_pt.z):
                        gcode_lines.append(f"G0 X{v1.x:.3f} Y{v1.y:.3f} Z{v1.z:.3f}")
                    # Arc de cercle ?
                    if hasattr(edge, 'Curve') and edge.Curve and edge.Curve.TypeId == 'Part::GeomCircle':
                        circle = edge.Curve
                        center = circle.Center
                        # Calculer I, J (relatifs au point de départ)
                        I = center.x - v1.x
                        J = center.y - v1.y
                        # Sens horaire/anti-horaire
                        if edge.Orientation == 'Forward':
                            gcode_cmd = 'G2'  # Horaire
                        else:
                            gcode_cmd = 'G3'  # Anti-horaire
                        gcode_lines.append(f"{gcode_cmd} X{v2.x:.3f} Y{v2.y:.3f} I{I:.3f} J{J:.3f} Z{v2.z:.3f}")
                    else:
                        # Usinage (G1)
                        gcode_lines.append(f"G1 X{v2.x:.3f} Y{v2.y:.3f} Z{v2.z:.3f}")
                    last_pt = v2
            # --- Perçage ---
            elif obj.Proxy.Type == 'DrillOperation':
                tool_id = getattr(obj, 'ToolId', None)
                tool_name = getattr(obj, 'ToolName', None)
                spindle = getattr(obj, 'SpindleSpeed', None)
                feed = getattr(obj, 'FeedRate', None)
                safe_z = getattr(obj, 'SafeHeight', 10.0)
                final_z = getattr(obj, 'FinalDepth', -5.0)
                cycle = getattr(obj, 'CycleType', "Simple")
                dwell = getattr(obj, 'DwellTime', 0.5)
                peck = getattr(obj, 'PeckDepth', 2.0)
                retract = getattr(obj, 'Retract', 1.0)
                # Changement d'outil si nécessaire
                if tool_id is not None and tool_id != current_tool:
                    gcode_lines.append(f"(Changement d'outil: {tool_name if tool_name else ''})")
                    gcode_lines.append(f"M6 T{tool_id}")
                    if spindle:
                        gcode_lines.append(f"S{spindle} M3")
                        current_spindle = spindle
                    if feed:
                        gcode_lines.append(f"F{feed}")
                        current_feed = feed
                    current_tool = tool_id
                gcode_lines.append(f"(Perçage: {obj.Label})")
                # Récupérer les points de perçage
                points = []
                if hasattr(obj, 'DrillGeometryName'):
                    doc = App.ActiveDocument
                    geom = doc.getObject(obj.DrillGeometryName)
                    if geom and hasattr(geom, 'DrillPositions'):
                        points = geom.DrillPositions
                # Générer le cycle G-code
                if cycle == "Simple":
                    gcode_lines.append(f"(Cycle: G81 - Simple)")
                    for pt in points:
                        gcode_lines.append(f"G0 X{pt.x} Y{pt.y} Z{safe_z}")
                        #gcode_lines.append(f"G81 X{pt.x:.3f} Y{pt.y:.3f} Z{final_z:.3f} R{safe_z:.3f} F{feed}")
                        gcode_lines.append(f"G80")
                elif cycle == "Peck":
                    gcode_lines.append(f"(Cycle: G83 - Perçage par reprise)")
                    for pt in points:
                        gcode_lines.append(f"G0 X{pt.x:.3f} Y{pt.y:.3f} Z{safe_z:.3f}")
                        gcode_lines.append(f"G83 X{pt.x:.3f} Y{pt.y:.3f} Z{final_z:.3f} R{safe_z:.3f} Q{peck:.3f} F{feed}")
                        gcode_lines.append(f"G80")
                elif cycle == "Tapping":
                    gcode_lines.append(f"(Cycle: G84 - Taraudage)")
                    for pt in points:
                        gcode_lines.append(f"G0 X{pt.x:.3f} Y{pt.y:.3f} Z{safe_z:.3f}")
                        gcode_lines.append(f"G84 X{pt.x:.3f} Y{pt.y:.3f} Z{final_z:.3f} R{safe_z:.3f} F{feed}")
                        gcode_lines.append(f"G80")
                elif cycle == "Boring":
                    gcode_lines.append(f"(Cycle: G85 - Alésage)")
                    for pt in points:
                        gcode_lines.append(f"G0 X{pt.x:.3f} Y{pt.y:.3f} Z{safe_z:.3f}")
                        gcode_lines.append(f"G85 X{pt.x:.3f} Y{pt.y:.3f} Z{final_z:.3f} R{safe_z:.3f} F{feed}")
                        gcode_lines.append(f"G80")
                elif cycle == "Reaming":
                    gcode_lines.append(f"(Cycle: G85 - Alésage/finition)")
                    for pt in points:
                        gcode_lines.append(f"G0 X{pt.x:.3f} Y{pt.y:.3f} Z{safe_z:.3f}")
                        gcode_lines.append(f"G85 X{pt.x:.3f} Y{pt.y:.3f} Z{final_z:.3f} R{safe_z:.3f} F{feed}")
                        gcode_lines.append(f"G80")
    gcode_lines.append("M30 (fin programme)")
    return '\n'.join(gcode_lines)


def postprocess_gcode():
    doc = App.ActiveDocument
    if not doc:
        App.Console.PrintError("Aucun document actif !\n")
        return
    # Chercher le projet CAM principal
    cam_project = None
    for obj in doc.Objects:
        if hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and obj.Proxy.Type == 'CamProject':
            cam_project = obj
            break
    if not cam_project:
        App.Console.PrintError("Aucun projet CAM trouvé !\n")
        return
    gcode = generate_gcode(cam_project)
    # Demander où sauvegarder le fichier
    prefs = BaptPreferences()
    filename, _ = QtGui.QFileDialog.getSaveFileName(None, "Enregistrer le G-code", prefs.getGCodeFolderPath(), "Fichiers G-code (*.nc *.gcode *.tap);;Tous les fichiers (*)")
    if not filename:
        App.Console.PrintMessage("Sauvegarde annulée.\n")
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode)
        App.Console.PrintMessage(f"G-code généré et sauvegardé dans : {filename}\n")
    except Exception as e:
        App.Console.PrintError(f"Erreur lors de la sauvegarde du G-code : {str(e)}\n")
