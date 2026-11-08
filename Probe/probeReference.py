# -*- coding: utf-8 -*-

import FreeCAD as App
import FreeCADGui as Gui
from Op.BaseOp import baseOp, baseOpViewProviderProxy
from PySide import QtCore, QtGui
import BaptUtilities


class ProbeReference(baseOp):
    """Feature complémentaire pour le palpage multi-points.

    Contrairement à probeFace, cette feature mémorise plusieurs points
    sélectionnés sur la pièce, ainsi que les paramètres UV et la direction
    associée à chaque point mesuré.
    """

    def __init__(self, obj):
        super().__init__(obj)

        if not hasattr(obj, "Points"):
            obj.addProperty("App::PropertyVectorList", "Points", "Base", "Points mesurés")
        if not hasattr(obj, "UVs"):
            obj.addProperty("App::PropertyVectorList", "UVs", "Base", "Paramètres UV par point")
        if not hasattr(obj, "Directions"):
            obj.addProperty("App::PropertyVectorList", "Directions", "Base", "Directions associées à chaque point")

        if not hasattr(obj, "distApproache"):
            obj.addProperty("App::PropertyFloat", "distApproche", "Base", "Distance d'approche pour le palpage")
            obj.distApproche = 10.0  # Valeur par défaut

        if not hasattr(obj, "Mode"):
            obj.addProperty("App::PropertyEnumeration", "Mode", "Base", "Type de palpage détecté")
            obj.Mode = ["empty", "single_point", "two_points", "three_points", "four_points", "multiple_points"]
            obj.Mode = "empty"

        if not hasattr(obj, "Result"):
            obj.addProperty("App::PropertyEnumeration", "Result", "Base", "Résultat de calcul")
            obj.Result = ["correction systeme coordonne", "Correction outils", "Affichage", "Rien"]
            obj.Result = "correction systeme coordonne"

        if not hasattr(obj, "Correction"):
            obj.addProperty("App::PropertyString", "Correction", "Base", "numero d'origine ou numero d'outil à corriger")
            obj.Correction = "G55"

        if not hasattr(obj, "CorrectionX"):
            obj.addProperty("App::PropertyBool", "CorrectionX", "Base", "Correction sur X")
            obj.CorrectionX = True
        if not hasattr(obj, "CorrectionY"):
            obj.addProperty("App::PropertyBool", "CorrectionY", "Base", "Correction sur Y")
            obj.CorrectionY = True
        if not hasattr(obj, "CorrectionZ"):
            obj.addProperty("App::PropertyBool", "CorrectionZ", "Base", "Correction sur Z")
            obj.CorrectionZ = True

        if not hasattr(obj, "CorrectionC"):
            obj.addProperty("App::PropertyBool", "CorrectionC", "Base", "Correction sur C")
            obj.CorrectionC = True

        obj.Proxy = self
        self.installToolProp(obj)

        self.execute(obj)

    def vectorIsPerpendicular(self, v1, v2, tolerance=1e-6):
        """Vérifie si deux vecteurs sont perpendiculaires en utilisant le produit scalaire."""
        dot_product = v1.dot(v2)
        return abs(dot_product) < tolerance

    def vectorIsOpposite(self, v1, v2, tolerance=1e-6):
        """Vérifie si deux vecteurs sont opposés en utilisant le produit scalaire."""
        dot_product = v1.dot(v2)
        return abs(dot_product + 1) < tolerance  # Si le produit scalaire est proche de -1, ils sont opposés

    def _convert_num_origine_to_gcode(self, num):
        """Convertit un numéro d'origine en code G correspondant."""
        if isinstance(num, int):
            if 1 <= num <= 6:
                return 2, num  # Retourner le code G correspondant
            else:
                raise ValueError("Numéro d'origine invalide. Doit être entre 1 et 6.")
        elif isinstance(num, str):
            if num.upper() in ["G54", "G55", "G56", "G57", "G58", "G59"]:
                L_number = int(num[1:])  # Extraire le numéro après 'G' et le convertir en entier
                return 2, L_number - 53  # Retourner le code G correspondant
            else:
                raise ValueError("Numéro d'origine invalide. Doit être G54 à G59.")
        else:
            raise TypeError("Le numéro d'origine doit être un entier ou une chaîne de caractères.")

    def addPoint(self, obj, point, uv, direction, face=None, element=None):
        """Ajoute un point avec les informations de surface associées."""
        points = list(obj.Points) if obj.Points else []
        uvs = list(obj.UVs) if obj.UVs else []
        directions = list(obj.Directions) if obj.Directions else []

        points.append(point)
        uvs.append(uv)
        directions.append(direction)

        obj.Points = points
        obj.UVs = uvs
        obj.Directions = directions
        self.execute(obj)

    def _detect_mode(self, points, directions):
        count = len(points)

        if count == 0:
            return "empty", "Aucun point sélectionné"
        if count == 1:
            return "single_point", "Mesure simple / point unique"
        if count == 2:
            if self.vectorIsOpposite(directions[0], directions[1]):
                return "two_points", "Mesure de 2 points (opposés)"
            elif self.vectorIsPerpendicular(directions[0], directions[1]):
                return "two_points", "Mesure de 2 points (perpendiculaires)"
            return "two_points", "Mesure de 2 points"
        if count == 3:
            return "three_points", "Mesure de 3 points (coin / angle)"
        if count == 4:
            return "four_points", "Mesure de 4 points (rectangle / poche)"
        return "multiple_points", f"Mesure multi-points ({count} points)"

    def _build_gcode(self, obj, mode, points, directions):
        lines = []
        lines.append("; --- ProbeReference ---")
        lines.append(f"; mode: {mode}")
        lines.append("G155")

        for idx, point in enumerate(points, start=1):
            lines.append(f"; P{idx}: X{point.x:.3f} Y{point.y:.3f} Z{point.z:.3f}")

        if mode == "single_point":
            p = points[0]
            approach = p + directions[0] * obj.distApproche
            lines.append("; single point detection")
            lines.append(f"G0 X{approach.x:.3f} Y{approach.y:.3f} ")
            lines.append(f"G0 Z{approach.z:.3f}")
            lines.append(f"G155 I{-directions[0].x:.3f} J{-directions[0].y:.3f} K{-directions[0].z:.3f}")
            lines.append('#1 = #516')  # X
            lines.append('#2 = #517')  # Y
            lines.append('#3 = #518')  # Z

            lines.append("G0 Z50")  # juste pour tester, à remplacer par htsecu

            if obj.Result == "correction systeme coordonne":

                c = []
                if obj.CorrectionX and directions[0].x != 0:
                    c.append("X#1")
                if obj.CorrectionY and directions[0].y != 0:
                    c.append("Y#2")
                if obj.CorrectionZ and directions[0].z != 0:
                    c.append("Z#3")

                if c:
                    lines.append(f"G10 L2 P1 {' '.join(c)}")
        elif mode == "two_points":
            p1 = points[0]
            p2 = points[1]
            approach1 = p1 + directions[0] * obj.distApproche
            approach2 = p2 + directions[1] * obj.distApproche
            lines.append("; two points detection")
            lines.append(f"G0 X{approach1.x:.3f} Y{approach1.y:.3f} Z{approach1.z:.3f}")
            lines.append(f"G155 I{-directions[0].x if directions[0].x != 0 else 0:.3f} J{-directions[0].y if directions[0].y != 0 else 0:.3f} K{-directions[0].z if directions[0].z != 0 else 0:.3f}")
            if obj.Result == "correction systeme coordonne":
                c = []
                if obj.CorrectionX and directions[0].x != 0:
                    c.append("#1 = #516")  # X
                if obj.CorrectionY and directions[0].y != 0:
                    c.append("#2 = #517")  # Y
                # if obj.CorrectionZ and directions[0].z != 0:
                #     c.append("Z#3")

            lines.append(f"G0 X{approach2.x:.3f} Y{approach2.y:.3f} Z{approach2.z:.3f}")
            lines.append(f"G155 I{-directions[1].x if directions[1].x != 0 else 0:.3f} J{-directions[1].y if directions[1].y != 0 else 0:.3f} K{-directions[1].z if directions[1].z != 0 else 0:.3f}")
            if obj.Result == "correction systeme coordonne":
                c = []
                if obj.CorrectionX and directions[1].x != 0:
                    c.append("X[[#1 + #516] /2] + #5220")  # Moyenne des deux points pour X + valeur X du G54
                if obj.CorrectionY and directions[1].y != 0:
                    c.append("Y[[#2 + #517] / 2] + #5221")  # moyenne des Y + valeur Y du G54
                # if obj.CorrectionZ and directions[1].z != 0:
                #     c.append("Z#3")

                if c:
                    lines.append(f"G10 L2 P1 {' '.join(c)}")
            elif obj.Result == "Correction outils":
                diff = points[1] - points[0]
                lines.append(f"G10 G91 L10 P'num_outils' D'difference'")

        return "\n".join(lines)

    def execute(self, obj):
        if App.ActiveDocument and App.ActiveDocument.Restoring:
            return

        points = list(obj.Points) if obj.Points else []
        directions = list(obj.Directions) if obj.Directions else []
        mode, description = self._detect_mode(points, directions)
        obj.Mode = mode
        obj.Result = description
        obj.Gcode = self._build_gcode(obj, mode, points, directions)

        if not points:
            obj.ProbeParams = []
            return

    def onChanged(self, obj, prop):
        if prop in ["Points", "UVs", "Directions", "Mode", "Result"]:
            self.execute(obj)

    def onDocumentRestored(self, obj):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class ProbeReferenceTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.ui = QtGui.QWidget()
        self.ui.setWindowTitle("Palpage multipoints")
        layout = QtGui.QVBoxLayout(self.ui)

        self.addPointButton = QtGui.QPushButton("Sélectionner un point")
        self.addPointButton.clicked.connect(self.selectPoint)
        layout.addWidget(self.addPointButton)

        self.infoLabel = QtGui.QLabel("Aucun point sélectionné")
        layout.addWidget(self.infoLabel)

        self.summaryLabel = QtGui.QLabel("")
        layout.addWidget(self.summaryLabel)

        self.updateSummary()

    def updateSummary(self):
        points = list(self.obj.Points) if self.obj.Points else []
        if not points:
            self.infoLabel.setText("Aucun point sélectionné")
            self.summaryLabel.setText("")
            return

        self.infoLabel.setText(f"{len(points)} point(s) enregistré(s)")
        lines = []
        for i, pt in enumerate(points, start=1):
            uv = App.Vector(0, 0, 0)
            direction = App.Vector(0, 0, 0)
            if self.obj.UVs and i - 1 < len(self.obj.UVs):
                uv = self.obj.UVs[i - 1]
            if self.obj.Directions and i - 1 < len(self.obj.Directions):
                direction = self.obj.Directions[i - 1]
            lines.append(f"P{i}: pos=({pt.x:.3f}, {pt.y:.3f}, {pt.z:.3f}) | uv=({uv.x:.3f}, {uv.y:.3f}) | dir=({direction.x:.3f}, {direction.y:.3f}, {direction.z:.3f})")
        self.summaryLabel.setText("\n".join(lines))

    def selectPoint(self):
        self.selectionObserver = PointSelectionObserver(self.onSelection)
        self.selectionObserver.enable()

    def onSelection(self, document, objName, sub, position, uv, direction):
        doc = App.getDocument(document)
        if doc is None:
            return

        shape_obj = doc.getObject(objName)
        if shape_obj is None:
            return

        self.obj.Proxy.addPoint(self.obj, position, uv, direction)
        self.updateSummary()

    def reject(self):
        if hasattr(self, "selectionObserver"):
            self.selectionObserver.disable()
        Gui.Control.closeDialog()

    def accept(self):
        if hasattr(self, "selectionObserver"):
            self.selectionObserver.disable()
        Gui.Control.closeDialog()


class PointSelectionObserver:
    def __init__(self, callback):
        self.callback = callback
        self.active = False

    def enable(self):
        self.active = True
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Face")
        Gui.Selection.addObserver(self)
        App.Console.PrintMessage("Observer activé. Sélectionnez un point sur une face.\n")

    def disable(self):
        self.active = False
        Gui.Selection.removeObserver(self)
        Gui.Selection.removeSelectionGate()
        App.Console.PrintMessage("Observer désactivé.\n")

    def addSelection(self, document, object_name, element, position):
        if not self.active:
            return

        point = App.Vector(position[0], position[1], position[2])
        doc = App.getDocument(document)
        if doc is None:
            return

        shape_obj = doc.getObject(object_name)
        if shape_obj is None:
            return

        try:
            surface = shape_obj.Shape.getElement(element)
            u, v = surface.Surface.parameter(point)
            direction = surface.normalAt(u, v)
            self.callback(document, object_name, element, point, App.Vector(u, v, 0), direction)
        except Exception as exc:
            App.Console.PrintWarning(f"Erreur lors de la récupération de UV/direction: {exc}\n")


class ViewProviderProbeReference(baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        return BaptUtilities.getIconPath("ProbeSurface.svg")

    def attach(self, vobj):
        super().attach(vobj)
        self.Object = vobj.Object

    def setEdit(self, vobj, mode=0):
        Gui.Control.showDialog(ProbeReferenceTaskPanel(vobj.Object))
        return True

    def unsetEdit(self, vobj):
        Gui.Control.closeDialog()
        return True

    def doubleClicked(self, vobj):
        self.setEdit(vobj)
        return True
