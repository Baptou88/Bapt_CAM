import FreeCAD, FreeCADGui
import Part
from PySide import QtGui, QtCore
import sys
import traceback

class PocketOperation:
    """
    Opération d'usinage de poche basée sur ContourGeometry.
    Génère un chemin d'usinage à partir du centre avec un facteur de recouvrement.
    """
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "PocketOperation"
        self.initProperties(obj)

    def initProperties(self, obj):
        obj.addProperty("App::PropertyLink", "Contour", "Pocket", "ContourGeometry de la poche")
        obj.addProperty("App::PropertyFloat", "Overlap", "Pocket", "Facteur de recouvrement (0.1-0.9)").Overlap = 0.5
        obj.addProperty("App::PropertyFloat", "ToolDiameter", "Pocket", "Diamètre outil (mm)").ToolDiameter = 6.0
        obj.addProperty("App::PropertyFloat", "StepDown", "Pocket", "Profondeur de passe (mm)").StepDown = 2.0
        obj.addProperty("App::PropertyFloat", "FinalDepth", "Pocket", "Profondeur finale (mm)").FinalDepth = -10.0
        obj.addProperty("App::PropertyString", "FillMode", "Pocket", "Mode de remplissage: 'spirale' ou 'zigzag'").FillMode = "spirale"
        obj.addProperty("Part::PropertyPartShape", "Path", "Pocket", "Chemin d'usinage généré")

    def is_shape_valid(self, shape):
        # Vérifie que la shape est utilisable pour le pocketing
        if not shape:
            return False
        if not hasattr(shape, 'BoundBox') or not shape.BoundBox:
            FreeCAD.Console.PrintError("PocketOperation: pas de boundBox.\n")
            return False
        if hasattr(shape, 'Wires') and shape.Wires:
            for wire in shape.Wires:
                if wire.isClosed():
                    return True
            return False
        return False

    def execute(self, obj):
        # Chercher le parent ContourGeometry dans l'arborescence
        parent = None
        for p in obj.InList:
            if hasattr(p, "Proxy") and getattr(p.Proxy, "Type", "") == "ContourGeometry":
                parent = p
                break
        if not parent or not hasattr(parent, "Shape"):
            FreeCAD.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
            obj.Path = None
            return
        shape = parent.Shape
        if not self.is_shape_valid(shape):
            FreeCAD.Console.PrintError("PocketOperation: Shape du parent ContourGeometry invalide ou non fermée.\n")
            obj.Path = None
            return
        tool_diam = obj.ToolDiameter
        overlap = obj.Overlap
        # Génération du chemin selon le mode choisi
        if hasattr(obj, 'FillMode') and obj.FillMode == "zigzag":
            path = self.generate_zigzag_path(shape, tool_diam, overlap)
        else:
            path = self.generate_spiral_path(shape, tool_diam, overlap)
        obj.Path = path if path else None

    def generate_zigzag_path(self, shape, tool_diam, overlap):
        # On suppose une poche plane, contour fermé
        if not shape or not shape.BoundBox:
            return None
        bbox = shape.BoundBox
        xmin, xmax = bbox.XMin, bbox.XMax
        ymin, ymax = bbox.YMin, bbox.YMax
        pas = tool_diam * (1 - overlap)
        lines = []
        y = ymin + tool_diam/2
        direction = 1
        while y <= ymax - tool_diam/2:
            # Cherche intersections entre la ligne y et la poche
            section = shape.slice(FreeCAD.Vector(0, 0, 1), y)
            if section and hasattr(section, 'Edges'):
                for edge in section.Edges:
                    p1, p2 = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
                    if direction == 1:
                        lines.append(Part.makeLine(p1, p2))
                    else:
                        lines.append(Part.makeLine(p2, p1))
            y += pas
            direction *= -1
        if lines:
            return Part.Wire(lines)
        return None

    def generate_spiral_path(self, shape, tool_diam, overlap):
        # Génère une série d'offsets intérieurs, connecte chaque boucle à la suivante par le point le plus proche
        try:
            offset_dist = tool_diam * (1 - overlap)
            loops = []
            current = shape
            while True:
                offset = current.makeOffset2D(-offset_dist, fill=False, join=0, openResult=True)
                # On arrête si l'offset n'est plus fermé ou trop petit
                if not offset or not hasattr(offset, 'Wires') or not offset.Wires:
                    break
                # Prend la plus grande wire (pour éviter les artefacts)
                main_wire = max(offset.Wires, key=lambda w: w.Length)
                if main_wire.Length < tool_diam:
                    break
                loops.append(main_wire)
                current = main_wire
            # On connecte les boucles entre elles
            if not loops:
                return None
            path_edges = []
            prev_wire = shape.Wires[0] if hasattr(shape, 'Wires') and shape.Wires else shape
            for wire in loops:
                # Trouver le point le plus proche entre la fin du wire précédent et le wire courant
                p_start = prev_wire.Vertexes[-1].Point
                min_dist = None
                min_vert = None
                for v in wire.Vertexes:
                    dist = (p_start - v.Point).Length
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        min_vert = v.Point
                # Décale le wire courant pour commencer à ce point
                reordered = wire.copy()
                reordered.rotate(reordered.CenterOfMass, FreeCAD.Vector(0,0,1), 0)  # dummy to force copy
                reordered = reordered
                # Ajoute une liaison
                path_edges.append(Part.makeLine(p_start, min_vert))
                # Ajoute le wire courant
                path_edges.extend(reordered.Edges)
                prev_wire = wire
            # Retourne un wire unique
            return Part.Wire(path_edges)
        except Exception as e:
            FreeCAD.Console.PrintError(f"Erreur spirale: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            FreeCAD.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return None

class PocketOperationTaskPanel(QtGui.QWidget):
    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        layout = QtGui.QFormLayout(self)
        self.overlapSpin = QtGui.QDoubleSpinBox()
        self.overlapSpin.setRange(0.1, 0.9)
        self.overlapSpin.setSingleStep(0.05)
        self.overlapSpin.setValue(obj.Overlap)
        self.toolSpin = QtGui.QDoubleSpinBox()
        self.toolSpin.setRange(0.1, 100.0)
        self.toolSpin.setValue(obj.ToolDiameter)
        self.depthSpin = QtGui.QDoubleSpinBox()
        self.depthSpin.setRange(-1000, 0)
        self.depthSpin.setValue(obj.FinalDepth)
        self.modeCombo = QtGui.QComboBox()
        self.modeCombo.addItems(["spirale", "zigzag"])
        self.modeCombo.setCurrentText(obj.FillMode if hasattr(obj, 'FillMode') else "spirale")
        layout.addRow("Recouvrement", self.overlapSpin)
        layout.addRow("Diamètre outil (mm)", self.toolSpin)
        layout.addRow("Profondeur finale (mm)", self.depthSpin)
        layout.addRow("Mode de remplissage", self.modeCombo)
        self.overlapSpin.valueChanged.connect(self.updateObj)
        self.toolSpin.valueChanged.connect(self.updateObj)
        self.depthSpin.valueChanged.connect(self.updateObj)
        self.modeCombo.currentTextChanged.connect(self.updateObj)
    def updateObj(self):
        self.obj.Overlap = self.overlapSpin.value()
        self.obj.ToolDiameter = self.toolSpin.value()
        self.obj.FinalDepth = self.depthSpin.value()
        self.obj.FillMode = self.modeCombo.currentText()
        self.obj.touch()
        FreeCAD.ActiveDocument.recompute()

class ViewProviderPocketOperation:
    def __init__(self, vobj):
        vobj.Proxy = self
    def attach(self, vobj):
        pass
    def updateData(self, fp, prop):
        pass
    def getDisplayModes(self, vobj):
        return ["FlatLines"]
    def getDefaultDisplayMode(self):
        return "FlatLines"
    def setDisplayMode(self, vobj, mode=None):
        if mode is None:
            return self.getDefaultDisplayMode()
        return mode
    def onDelete(self, vobj, subelements):
        return True
    def __getstate__(self):
        return None
    def __setstate__(self, state):
        return None
    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâches pour l'opération de poche"""
        FreeCADGui.Control.showDialog(PocketOperationTaskPanel(vobj.Object))

def createPocketOperation(contour=None):
    doc = FreeCAD.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "PocketOperation")
    PocketOperation(obj)
    ViewProviderPocketOperation(obj.ViewObject)
    if contour:
        obj.Contour = contour
        # Ajoute PocketOperation comme enfant de ContourGeometry dans l'arborescence
        if hasattr(contour, "addObject"):
            contour.addObject(obj)
        if hasattr(contour, "Group") and obj not in contour.Group:
            contour.Group.append(obj)
    return obj
