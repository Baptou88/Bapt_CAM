# -*- coding: utf-8 -*-
"""
BaptPostProcess.py
Génère un programme G-code à partir des opérations du projet CAM
"""
import importlib
import os
from BaptPreferences import BaptPreferences
from BaptTaskPanel import PostProcessorTaskPanel
import FreeCAD as App # type: ignore
from PySide import QtGui, QtCore # type: ignore
import BaptUtilities as BaptUtils
def list_machining_operations(obj):
    """
    Parcourt récursivement toute l'arborescence de obj (Group, enfants, etc.)
    et retourne la liste de tous les objets d'usinage (ContournageCycle, DrillOperation, etc.).
    """

    ops = []
    if hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and obj.Proxy.Type in [
        'ContournageCycle', 'DrillOperation', 'Surfacage', 'Path']:
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
    raise NotImplementedError("Cette fonction est obsolète. Utilisez generate_gcode_for_ops à la place.")
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

def generate_gcode_for_ops(ops, cam_project=None, module=None):
    """
    Génère le G-code à partir d'une liste ordonnée d'opérations (ops).
    Semblable à generate_gcode mais prend une liste explicite d'objets.
    """
    gcode_lines = ["(Programme généré par BaptPostProcess)", "G21 (unit: mm)", "G90 (abs mode)"]
    current_tool = None
    current_spindle = None
    current_feed = None

    if module is not None and cam_project is not None:
        if hasattr(module, 'blockForm'):
            blockForm = module.blockForm(cam_project.Proxy.getStock(cam_project))
            gcode_lines.append(blockForm)

    App.Console.PrintMessage(f"Nombre d'opérations d'usinage sélectionnées: {len(ops)}\n")
    for obj in ops:
        if not (hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type')):
            continue
        tool = getattr(obj, 'Tool', None)   
        if tool is None:
            App.Console.PrintWarning(f"L'opération {obj.Label} n'a pas d'outil associé !\n")
            gcode_lines.append(f"(Attention: L'opération {obj.Label} n'a pas d'outil associé !)")
            continue
        if current_tool != tool:
            tool_id = getattr(tool, 'Id', None)
            tool_name = getattr(tool, 'Label', None)
            spindle = getattr(tool, 'SpindleSpeed', None)
            feed = getattr(tool, 'FeedRate', None)
            
            gcode_lines.append(f"(Changement d'outil: {tool_name if tool_name else ''})")
            gcode_lines.append(f"M6 T{tool_id}")
            if spindle:
                gcode_lines.append(f"S{spindle} M3")
                current_spindle = spindle
            if feed:
                gcode_lines.append(f"F{feed}")
                current_feed = feed
            current_tool = tool
        # --- Surfacage ---
        if obj.Proxy.Type == 'Surfacage' and hasattr(obj, 'Shape'):
            
            gcode_lines.append(f"(Surfacage: {obj.Label})")
            # last_pt = None
            # for edge in obj.Shape.Edges:
            #     v1 = edge.Vertexes[0].Point
            #     v2 = edge.Vertexes[1].Point
            #     if last_pt is None or (v1.x != last_pt.x or v1.y != last_pt.y or v1.z != last_pt.z):
            #         gcode_lines.append(f"G0 X{v1.x:.3f} Y{v1.y:.3f} Z{v1.z:.3f}")
            #     if hasattr(edge, 'Curve') and edge.Curve and getattr(edge.Curve, "TypeId", "") == 'Part::GeomCircle':
            #         circle = edge.Curve
            #         center = circle.Center
            #         I = center.x - v1.x
            #         J = center.y - v1.y
            #         gcode_cmd = 'G2' if getattr(edge, "Orientation", "") == 'Forward' else 'G3'
            #         gcode_lines.append(f"{gcode_cmd} X{v2.x:.3f} Y{v2.y:.3f} I{I:.3f} J{J:.3f} Z{v2.z:.3f}")
            #     else:
            #         gcode_lines.append(f"G1 X{v2.x:.3f} Y{v2.y:.3f} Z{v2.z:.3f}")
            #     last_pt = v2
            gcode_lines.append(obj.Gcode)

        # --- Contournage ---
        if obj.Proxy.Type == 'ContournageCycle' and hasattr(obj, 'Shape'):
           
            gcode_lines.append(f"(Contournage: {obj.Label})")
            last_pt = None
            for edge in obj.Shape.Edges:
                v1 = edge.Vertexes[0].Point
                v2 = edge.Vertexes[1].Point
                if last_pt is None or (v1.x != last_pt.x or v1.y != last_pt.y or v1.z != last_pt.z):
                    gcode_lines.append(f"G0 X{v1.x:.3f} Y{v1.y:.3f} Z{v1.z:.3f}")
                if hasattr(edge, 'Curve') and edge.Curve and getattr(edge.Curve, "TypeId", "") == 'Part::GeomCircle':
                    circle = edge.Curve
                    center = circle.Center
                    I = center.x - v1.x
                    J = center.y - v1.y
                    gcode_cmd = 'G2' if getattr(edge, "Orientation", "") == 'Forward' else 'G3'
                    gcode_lines.append(f"{gcode_cmd} X{v2.x:.3f} Y{v2.y:.3f} I{I:.3f} J{J:.3f} Z{v2.z:.3f}")
                else:
                    gcode_lines.append(f"G1 X{v2.x:.3f} Y{v2.y:.3f} Z{v2.z:.3f}")
                last_pt = v2

        # --- Perçage ---
        elif obj.Proxy.Type == 'DrillOperation':
            tool_id = getattr(obj, 'ToolId', None)
            tool_name = getattr(obj, 'ToolName', None)
            spindle = getattr(obj, 'SpindleSpeed', None)
            feed = getattr(obj, 'FeedRate', None).Value
            safe_z = getattr(obj, 'SafeHeight').Value
            final_z = getattr(obj, 'FinalDepth', -5.0).Value
            cycle = getattr(obj, 'CycleType', "Simple")
            dwell = getattr(obj, 'DwellTime', 0.5)
            peck = getattr(obj, 'PeckDepth', 2.0).Value
            retract = getattr(obj, 'Retract', 1.0)

            gcode_lines.append(f"(Perçage: {obj.Label})")
            points = []
            if hasattr(obj, 'DrillGeometryName'):
                doc = App.ActiveDocument
                geom = doc.getObject(obj.DrillGeometryName)
                if geom and hasattr(geom, 'DrillPositions'):
                    points = geom.DrillPositions
            if cycle == "Simple":
                gcode_lines.append(f"(Cycle: G81 - Simple)")
                for pt in points:
                    gcode_lines.append(f"G0 X{pt.x} Y{pt.y} Z{safe_z}")
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
            elif cycle == "Contournage":
                gcode_lines.append(f"(Cycle: Contournage personnalisé)")
                gcode_lines.append(obj.Gcode)
                
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
    
    dlg = PostProcessDialog(cam_project)
    dlg.exec_()

    # gcode = generate_gcode(cam_project)
    # # Demander où sauvegarder le fichier
    # prefs = BaptPreferences()
    # filename, _ = QtGui.QFileDialog.getSaveFileName(None, "Enregistrer le G-code", prefs.getGCodeFolderPath(), "Fichiers G-code (*.nc *.gcode *.tap);;Tous les fichiers (*)")
    # if not filename:
    #     App.Console.PrintMessage("Sauvegarde annulée.\n")
    #     return
    # try:
    #     with open(filename, 'w') as f:
    #         f.write(gcode)
    #     App.Console.PrintMessage(f"G-code généré et sauvegardé dans : {filename}\n")
        


    # except Exception as e:
    #     App.Console.PrintError(f"Erreur lors de la sauvegarde du G-code : {str(e)}\n")


class PostProcessDialog(QtGui.QDialog):
    """
    Dialog qui liste les opérations, permet checkbox + réordonner (Up/Down),
    et génère le G-code pour la sélection ordonnée.
    """
    def __init__(self, cam_project, parent=None):
        super(PostProcessDialog, self).__init__(parent)
        self.setWindowTitle("PostProcess - Sélection des opérations")
        self.resize(600, 400)
        self.cam_project = cam_project

        # Disposition principale avec un splitter gauche/droite
        main_layout = QtGui.QHBoxLayout(self)
        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        main_layout.addWidget(splitter)

        # Panneau gauche: liste d'opérations + contrôles
        leftPane = QtGui.QWidget()
        leftLayout = QtGui.QVBoxLayout(leftPane)

        # Liste des opérations avec items checkables
        self.listWidget = QtGui.QListWidget(self)
        self.listWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        leftLayout.addWidget(self.listWidget)

        # Boutons Up/Down sous la liste
        btn_layout = QtGui.QHBoxLayout()
        self.upBtn = QtGui.QPushButton("Up", self)
        self.downBtn = QtGui.QPushButton("Down", self)
        btn_layout.addWidget(self.upBtn)
        btn_layout.addWidget(self.downBtn)
        btn_layout.addStretch(1)
        leftLayout.addLayout(btn_layout)

        # Checkbox: ouvrir le pgm dans un éditeur après création
        self.openInEditorCheck = QtGui.QCheckBox("Ouvrir le programme dans un éditeur de texte après génération", self)
        self.openInEditorCheck.setChecked(True)
        leftLayout.addWidget(self.openInEditorCheck)

        # Boutons en bas
        bottom_layout = QtGui.QHBoxLayout()
        self.generateBtn = QtGui.QPushButton("Générer & Sauvegarder", self)
        self.cancelBtn = QtGui.QPushButton("Annuler", self)
        bottom_layout.addWidget(self.generateBtn)
        bottom_layout.addWidget(self.cancelBtn)
        leftLayout.addLayout(bottom_layout)

        splitter.addWidget(leftPane)

        # Panneau droit: paramètres PostProcessor (réutilise PostProcessorTaskPanel)
        self.postProcPanel = PostProcessorTaskPanel(self.cam_project)
        splitter.addWidget(self.postProcPanel.getForm())

        # Répartition des tailles
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Connects
        self.upBtn.clicked.connect(self.move_item_up)
        self.downBtn.clicked.connect(self.move_item_down)
        self.generateBtn.clicked.connect(self.on_generate)
        self.cancelBtn.clicked.connect(self.reject)

        self.populate_list()

    def populate_list(self):
        self.listWidget.clear()
        ops = list_machining_operations(self.cam_project)
        for op in ops:
            displayText = f"{op.Label} {self._tool_label(op)}"
            item = QtGui.QListWidgetItem(displayText)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Checked if op.Active else QtCore.Qt.Unchecked)
            item.setData(QtCore.Qt.UserRole, op)
            self.listWidget.addItem(item)
            # set icon for the operation
            try:
                icon = self._icon_for_op(op)
                if not icon.isNull():
                    item.setIcon(icon)
            except Exception:
                pass

    def _tool_label(self, op):
        """Retourne une petite chaîne descriptive de l'outil associé à l'opération."""
        try:
            tool_name = op.Tool.Label
            tool_id = getattr(op.Tool, "Id", None)
            if tool_name and tool_id is not None:
                return f"{tool_name} (T{tool_id})"
            if tool_name:
                return tool_name
            if tool_id is not None:
                return f"T{tool_id}"
        except Exception:
            pass
        return "—"

    def _icon_for_op(self, op):
        """
        Retourne un QtGui.QIcon pour l'opération `op`.
        Essaie plusieurs sources (ViewObject.getIcon, ViewObject.Icon), puis un mapping par type.
        """
        try:
            # attempt: ViewObject.getIcon() returns a path or QIcon-compatible value
            vo = getattr(op, "ViewObject", None)
            if vo:
                try:
                    iconpath = vo.getIcon()
                    if iconpath:
                        return QtGui.QIcon(iconpath)
                except Exception:
                    pass
                # some viewproviders expose an 'Icon' attribute
                ico = getattr(vo, "Icon", None)
                if ico:
                    return QtGui.QIcon(ico)
        except Exception:
            pass
        # fallback mapping by Proxy.Type
        try:
            typ = getattr(op, "Proxy", None) and getattr(op.Proxy, "Type", "")
        except Exception:
            typ = ""
        mapping = {
            "Surfacage": ":/icons/Surface.svg",
            "ContournageCycle": ":/icons/Sketcher_Constraint.svg",
            "DrillOperation": ":/icons/drill.png",
        }
        if typ in mapping:
            return QtGui.QIcon(mapping[typ])
        # final fallback: empty icon
        return QtGui.QIcon()

    def move_item_up(self):
        row = self.listWidget.currentRow()
        if row > 0:
            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(row-1, item)
            self.listWidget.setCurrentRow(row-1)

    def move_item_down(self):
        row = self.listWidget.currentRow()
        if row < self.listWidget.count()-1 and row >= 0:
            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(row+1, item)
            self.listWidget.setCurrentRow(row+1)

    def get_selected_ordered_ops(self):
        ops = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                ops.append(item.data(QtCore.Qt.UserRole))
        return ops

    def on_generate(self):
        ops = self.get_selected_ordered_ops()
        if not ops:
            QtGui.QMessageBox.warning(self, "Aucune opération", "Veuillez sélectionner au moins une opération.")
            return
        #load post processing module
        chemin_du_module = f"{BaptUtils.getPostProPath(self.cam_project.PostProcessor[0] + '.py')}"
        nom_du_module = os.path.splitext(os.path.basename(chemin_du_module))[0]
        App.Console.PrintMessage(f'{chemin_du_module}\n')
        App.Console.PrintMessage(f'{nom_du_module}\n')
        try:
            spec = importlib.util.spec_from_file_location(nom_du_module, chemin_du_module)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            App.Console.PrintMessage(f'{module.Name}\n')
        except Exception as e:
            App.Console.PrintError(f"Erreur lors du chargement du module de post-traitement : {e}\n")
            QtGui.QMessageBox.critical(self, "Erreur", f"Impossible de charger le module de post-traitement:\n{e}")
            return
        gcode = generate_gcode_for_ops(ops,self.cam_project, module)
        prefs = BaptPreferences()
        filename, _ = QtGui.QFileDialog.getSaveFileName(self, "Enregistrer le G-code", prefs.getGCodeFolderPath(), "Fichiers G-code (*.nc *.gcode *.tap);;Tous les fichiers (*)")
        if not filename:
            return
        try:
            with open(filename, 'w') as f:
                f.write(gcode)
            App.Console.PrintMessage(f"G-code généré et sauvegardé dans : {filename}\n")
            QtGui.QMessageBox.information(self, "Succès", "G-code généré et sauvegardé.")

            try:
                if self.openInEditorCheck.isChecked():
                    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(filename))
            except Exception as e:
                App.Console.PrintWarning(f"Impossible d'ouvrir le fichier dans l'éditeur: {e}\n")
                
            self.accept()
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la sauvegarde du G-code : {str(e)}\n")
            QtGui.QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le G-code:\n{e}")

