import FreeCAD as App
import FreeCADGui as Gui
import Part
import math

import BaptUtilities
from Op.BaseOp import baseOp, baseOpViewProviderProxy
from utils.GcodeWriter import GcodeWriter
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore


class SpiraleOp(baseOp):
    """
    Classe représentant l'opération d'usinage de trous en spirale.
    """

    def __init__(self, obj):
        super().__init__(obj)

        if not hasattr(obj, "DrillGeometry"):
            obj.addProperty("App::PropertyLink", "DrillGeometry", "Base", "Drill geometry for the spirale")

        if not hasattr(obj, "Diameter"):
            obj.addProperty("App::PropertyLength", "Diameter", "Base", "Diameter").Diameter = 20.0

        # Paramètres de profondeur — PropertyDistance accepte les valeurs négatives
        if not hasattr(obj, "FinalDepth"):
            obj.addProperty("App::PropertyDistance", "FinalDepth", "Depth", "Final depth of drilling")
            obj.FinalDepth = -10.0  # -10mm par défaut (coordonnée Z absolue)

        if not hasattr(obj, "Ap"):
            obj.addProperty("App::PropertyDistance", "Ap", "Base", "Depth of cut per pass")
            obj.Ap = 1.0  # 1mm par défaut

        if not hasattr(obj, "SurepAxiale"):
            obj.addProperty("App::PropertyDistance", "SurepAxiale", "Base", "Axial overcut")
            obj.SurepAxiale = 0.0

        super().installToolProp(obj)
        obj.Proxy = self

    def onChanged(self, obj, prop):
        if prop in ["DrillGeometry", "Diameter", "FinalDepth", "Ap", "SurepAxiale"]:
            self.execute(obj)
        pass

    def onDocumentRestored(self, obj):
        super().__init__(obj)
        super().onDocumentRestored(obj)

    def calculatePasse(self, obj, start, end, passeEquilibre=True) -> list:
        """
        Calcule le nombre de passes nécessaires pour atteindre la profondeur finale.
        """

        ap = obj.Ap.Value  # Profondeur de passe par passe
        if ap <= 0:
            raise ValueError("Ap (depth of cut per pass) must be greater than zero.")

        prise = obj.Ap.Value  # Profondeur de passe par passe
        surep = obj.SurepAxiale.Value  # Surépaisseur axiale
        dz = start - (end + surep)

        passes = []

        if start < end:  # TODO
            App.Console.PrintError(f"La hauteur de référence ({start}) est inférieure à la profondeur de coupe ({end}).\n")
            return []

        if passeEquilibre:
            nbPasses = math.ceil(math.fabs(dz) / prise)
            prise = math.fabs(dz) / nbPasses
            for i in range(nbPasses):
                passes.append(start - (i + 1) * prise)
        else:
            while True:
                if dz >= end + prise:
                    passes.append(end)
                    end -= prise
                    break
                else:
                    passes.append(end)

        return passes

    def execute(self, obj):
        # Vérification de la géométrie de perçage
        if App.ActiveDocument.Restoring:
            return
        if not obj.DrillGeometry:
            raise ValueError("Drill geometry is not set.")
            return

        if not hasattr(obj, "Tool") or obj.Tool is None:
            raise ValueError("Tool is not set.")
            return

        # Récupération des paramètres
        tool = obj.Tool
        diameter = obj.Diameter.Value
        final_depth = obj.FinalDepth.Value  # Valeur absolue de la profondeur finale

        aeMax = 0.5 * tool.Radius.Value * 2  # prise de passe latérale maximale (en mm)
        # Calcul de la spirale sur plan XY
        App.Console.PrintMessage(f'aeMax {aeMax}\n')
        # Calcul du Nombre de Tours
        final_diameter = diameter - (2 * tool.Radius.Value)
        if final_diameter <= 0:
            raise ValueError("Final diameter must be greater than zero.")

        delta_diameter = final_diameter - (2 * tool.Radius.Value)
        App.Console.PrintMessage(f'delta_diam {delta_diameter}\n')
        num_turns = math.ceil(final_diameter / (aeMax / 2))  # Nombre de tours complets pour atteindre le diamètre final
        App.Console.PrintMessage(f'num_turns: {num_turns}\n')
        prise_de_passe = final_diameter / num_turns  # Prise de passe latérale par tour
        App.Console.PrintMessage(f'prise passe {prise_de_passe}\n')

        positions = obj.DrillGeometry.DrillPositions
        if not positions:
            raise ValueError("No drill positions defined in DrillGeometry.")
        shapes = []

        if not positions:
            obj.Shape = Part.Shape()  # Crée une forme vide pour éviter les erreurs
            raise ValueError("No drill positions defined in DrillGeometry.")

        gcodeWriter = GcodeWriter()

        for pos in positions:
            depth = abs(pos.z - final_depth)  # Profondeur absolue pour le perçage
            cylinder = Part.makeCylinder(diameter / 2, depth, pos, App.Vector(0, 0, -1))
            shapes.append(cylinder)

        p0 = positions[0]
        safe_height = p0.z + 2.0  # Hauteur de sécurité pour le déplacement rapide
        gcodeWriter.linearMove({'X': p0.x, 'Y': p0.y}, rapid=True)  #
        gcodeWriter.linearMove({'Z': safe_height}, rapid=True)  # Déplacement rapide à la hauteur de sécurité
        gcodeWriter.addLabel(obj.Label)
        gcodeWriter.raw("G91")

        passes = self.calculatePasse(obj, p0.z, final_depth, passeEquilibre=True)
        current_z = safe_height
        for _, z in enumerate(passes):
            gcodeWriter.linearMove({'Z': z - current_z}, feed=1000, force=True)
            current_z = z

            a = 0
            b = 0
            for i in range(int(num_turns / 2)):
                a = math.fabs(a) + prise_de_passe
                gcodeWriter.arcMove({'X': -a, 'Y': 0, 'I': -a / 2, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale
                b = a
                a = math.fabs(a) + prise_de_passe
                gcodeWriter.arcMove({'X': a, 'Y': 0, 'I': a / 2, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale
                b = a

            gcodeWriter.arcMove({'X': -a, 'Y': 0, 'I': -a / 2, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale
            # gcodeWriter.arcMove({'X': a, 'Y': 0, 'I': a / 2, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale

            App.Console.PrintMessage(f"SpiraleOp: num_turns={num_turns}, prise_de_passe={prise_de_passe}, final_diameter={final_diameter}, delta_diameter={delta_diameter}\n")
            gcodeWriter.linearMove({'X': final_diameter / 2}, feed=1000)
        gcodeWriter.raw("G90")
        gcodeWriter.linearMove({'Z': safe_height}, rapid=True)  # Remonter à la hauteur de sécurité
        gcodeWriter.endLabel()

        for i in range(1, len(positions)):
            pt = positions[i]
            gcodeWriter.linearMove({'X': pt.x, 'Y': pt.y, 'Z': safe_height}, rapid=True)
            # if obj.CycleType == "Contournage":
            gcodeWriter.raw(f"REPEAT {obj.Label} {obj.Label}_FIN P=1")

        obj.Gcode = "\n".join(gcodeWriter.lines)
        obj.TimeEstimate = gcodeWriter.time_estimate

        if shapes:
            compound = Part.makeCompound(shapes)
            obj.Shape = compound

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderSpiraleOp(baseOpViewProviderProxy):
    """Classe représentant le fournisseur de vue pour l'opération SpiraleOp."""

    def __init__(self, vobj):
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object

    def attach(self, vobj):
        """Attache le fournisseur de vue à l'objet."""
        self.Object = vobj.Object
        return super().attach(vobj)

    def getIcon(self):
        """Retourne l'icône"""
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Tree_Drilling.svg")

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)

        viewGcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "View G-code", menu)
        QtCore.QObject.connect(viewGcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(viewGcode)
        return True
