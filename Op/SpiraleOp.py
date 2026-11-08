import FreeCAD as App
import FreeCADGui as Gui
import Part
import math

import BaptUtilities
from Op.BaseOp import baseOp, baseOpViewProviderProxy
from utils.GcodeWriter import GcodeWriter
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore


class toolNotSetException(Exception):
    def __init__(self, message):
        super().__init__(self, message)
        self.message = message

    def __str__(self):
        return self.message

    pass


class SpiraleOp(baseOp):
    """
    Classe représentant l'opération d'usinage de trous en spirale.
    """

    def __init__(self, obj, cam_proj=None):
        super().__init__(obj, cam_proj)

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

        if not hasattr(obj, "SurepRadiale"):
            obj.addProperty("App::PropertyDistance", "SurepRadiale", "Base", "Radial overcut")
            obj.SurepRadiale = 0.0

        if not hasattr(obj, "aeMax"):
            obj.addProperty("App::PropertyDistance", "aeMax", "Base", "Maximum radial depth of cut")
            obj.aeMax = 6.0

        if not hasattr(obj, "PlungeType"):
            obj.addProperty("App::PropertyEnumeration", "PlungeType", "Base", "Plunge type")
            obj.PlungeType = ["Direct", "Helical"]
            obj.PlungeType = "Direct"

        super().installToolProp(obj)
        super().installSecurePlane(obj)
        obj.Proxy = self

    def onChanged(self, obj, prop):
        if prop in ["DrillGeometry", "Diameter", "FinalDepth", "Ap", "SurepAxiale", "SurepRadiale", "aeMax", "PlungeType", "Tool", "SecurePlane"]:
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
            raise toolNotSetException("Tool is not set.")
            return

        # Récupération des paramètres
        tool = obj.Tool
        diameter = obj.Diameter.Value
        final_depth = obj.FinalDepth.Value  # Valeur absolue de la profondeur finale

        # Calcul de la spirale sur plan XY

        # Calcul du Nombre de Tours
        final_diameter = diameter - obj.SurepRadiale.Value - (2 * tool.Radius.Value)
        App.Console.PrintMessage(f'final_diameter {final_diameter}\n')
        if final_diameter <= 0:
            raise ValueError("Final diameter must be greater than zero.")

        num_turns = math.ceil((final_diameter / 2) / obj.aeMax.Value)  # Nombre de tours complets pour atteindre le diamètre final
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
        safe_height = p0.z + obj.SecurePlane.Value  # Hauteur de sécurité pour le déplacement rapide
        gcodeWriter.linearMove({'X': p0.x, 'Y': p0.y}, rapid=True)  #
        gcodeWriter.linearMove({'Z': safe_height}, rapid=True)  # Déplacement rapide à la hauteur de sécurité
        gcodeWriter.addLabel(obj.Label)
        gcodeWriter.raw("G91")

        passes = self.calculatePasse(obj, p0.z, final_depth, passeEquilibre=True)
        current_z = safe_height
        for _, z in enumerate(passes):
            if obj.PlungeType == "Direct":
                gcodeWriter.linearMove({'Z': z - current_z}, feed=1000, force=True)
            elif obj.PlungeType == "Helical":
                dz = z - current_z
                plunge_max = 1.0  # Profondeur maximale par tour pour le plongeon hélicoïdal
                num_plunge_turns = math.ceil(abs(dz) / plunge_max)
                gcodeWriter.linearMove({'X': obj.aeMax.Value})
                for _ in range(num_plunge_turns):
                    gcodeWriter.arcMove({'X': -obj.aeMax.Value * 2, 'Y': 0, 'I': -obj.aeMax.Value, 'J': 0, 'Z': dz / (2 * num_plunge_turns), 'F': 500, 'CCW': True})
                    gcodeWriter.arcMove({'X': obj.aeMax.Value * 2, 'Y': 0, 'I': obj.aeMax.Value, 'J': 0, 'Z': dz / (2 * num_plunge_turns), 'F': 500, 'CCW': True})
                gcodeWriter.linearMove({'X': -obj.aeMax.Value})

            current_z = z

            a = 0

            for i in range(int(num_turns)):
                a = math.fabs(a) + prise_de_passe
                gcodeWriter.arcMove({'X': -a / 2, 'Y': 0, 'I': -a / 4, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale

                a = math.fabs(a) + prise_de_passe
                gcodeWriter.arcMove({'X': a / 2, 'Y': 0, 'I': a / 4, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale

            gcodeWriter.arcMove({'X': -a / 2, 'Y': 0, 'I': -a / 4, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale
            # gcodeWriter.arcMove({'X': a/2, 'Y': 0, 'I': a / 4, 'J': 0, 'F': 500, 'CCW': True})  # Mouvement circulaire en spirale

            App.Console.PrintMessage(f"SpiraleOp: num_turns={num_turns}, prise_de_passe={prise_de_passe}, final_diameter={final_diameter}\n")
            gcodeWriter.linearMove({'X': final_diameter / 2}, feed=1000)
        gcodeWriter.raw("G90")
        gcodeWriter.linearMove({'Z': safe_height}, rapid=True)  # Remonter à la hauteur de sécurité
        gcodeWriter.endLabel()

        for i in range(1, len(positions)):
            pt = positions[i]
            gcodeWriter.linearMove({'X': pt.x, 'Y': pt.y, 'Z': safe_height}, rapid=True, force=True)
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
