
import math

import FreeCAD as App
import FreeCADGui as Gui
import Part  # type: ignore
import PySide.QtGui as QtGui  # type: ignore
import PySide.QtCore as QtCore  # type: ignore


import BaptUtilities
from Op.BaseOp import baseOp, baseOpViewProviderProxy
from utils.GcodeWriter import GcodeWriter


cycleType = ["Simple", "Peck", "Tapping", "Boring", "Reaming", "Contournage"]


class DrillOperation(baseOp):
    """Classe représentant une opération d'usinage de perçage"""

    def __init__(self, obj):
        """Ajoute les propriétés"""
        super().__init__(obj)

        self.Type = "DrillOperation"

        # Référence à la géométrie de perçage (PropertyLink)
        if not hasattr(obj, "DrillGeometry"):
            obj.addProperty("App::PropertyLink", "DrillGeometry", "Base", "Drill geometry to machine")
        # Migration : convertir l'ancien PropertyString en PropertyLink
        if hasattr(obj, "DrillGeometryName"):
            if obj.DrillGeometryName and not obj.DrillGeometry:
                old_geom = obj.Document.getObject(obj.DrillGeometryName)
                if old_geom:
                    obj.DrillGeometry = old_geom
            obj.removeProperty("DrillGeometryName")

        # Type de cycle
        if not hasattr(obj, "CycleType"):
            obj.addProperty("App::PropertyEnumeration", "CycleType", "Cycle", "Type of drilling cycle")
            obj.CycleType = cycleType
            obj.CycleType = "Simple"  # Valeur par défaut

        # Paramètres spécifiques au cycle de perçage profond (Peck)
        if not hasattr(obj, "PeckDepth"):
            obj.addProperty("App::PropertyLength", "PeckDepth", "Peck", "Depth of each peck")
            obj.PeckDepth = 2.0  # 2mm par défaut

        if not hasattr(obj, "Retract"):
            obj.addProperty("App::PropertyLength", "Retract", "Peck", "Retract distance after each peck")
            obj.Retract = 1.0  # 1mm par défaut

        # Paramètres spécifiques au cycle de taraudage
        if not hasattr(obj, "ThreadPitch"):
            obj.addProperty("App::PropertyLength", "ThreadPitch", "Tapping", "Thread pitch")
            obj.ThreadPitch = 1.0  # 1mm par défaut

        # Paramètres spécifiques au cycle d'alésage
        if not hasattr(obj, "DwellTime"):
            obj.addProperty("App::PropertyFloat", "DwellTime", "Boring", "Dwell time at bottom in seconds")
            obj.DwellTime = 0.5  # 0.5s par défaut

        # Paramètres de sécurité
        if not hasattr(obj, "SafeHeight"):
            obj.addProperty("App::PropertyLength", "SafeHeight", "Safety", "Safe height for rapid moves")
            obj.SafeHeight = 2  # 10mm par défaut

        # Paramètres de profondeur — PropertyDistance accepte les valeurs négatives
        if not hasattr(obj, "FinalDepth"):
            obj.addProperty("App::PropertyDistance", "FinalDepth", "Depth", "Final depth of drilling")
            obj.FinalDepth = -10.0  # -10mm par défaut (coordonnée Z absolue)
        else:
            # Migration : ancien PropertyFloat → PropertyDistance
            if obj.getTypeIdOfProperty("FinalDepth") == "App::PropertyFloat":
                old_val = obj.FinalDepth
                obj.removeProperty("FinalDepth")
                obj.addProperty("App::PropertyDistance", "FinalDepth", "Depth", "Final depth of drilling")
                obj.FinalDepth = old_val

        # Mode de profondeur (absolu ou relatif)
        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyString", "DepthMode", "Depth", "Depth mode (Absolute or Relative)")
            obj.DepthMode = "Absolute"  # Valeur par défaut

        # Référence Z pour le mode relatif
        if not hasattr(obj, "ZReference"):
            obj.addProperty("App::PropertyLength", "ZReference", "Depth", "Z reference for relative depth mode")
            obj.ZReference = 0.0  # 0mm par défaut

        if not hasattr(obj, "Diam"):
            obj.addProperty("App::PropertyFloat", "Diam", "Contournage", "Diametre")
            obj.Diam = 20
        if not hasattr(obj, "Ap"):
            obj.addProperty("App::PropertyFloat", "Ap", "Contournage", "Prise de Passe Max")
            obj.Ap = 0.5

        super().installToolProp(obj)
        obj.Proxy = self

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        # super().onChanged(obj, prop)
        if prop == "Tool" and obj.Tool:
            pass
            # self.updateToolInfo(obj)
        elif prop == "CycleType":
            self.updateVisibleProperties(obj)
            self.execute(obj)
        elif prop == "DrillGeometry" and obj.DrillGeometry:
            self.updateFromGeometry(obj)

        elif prop == "DrillGeometry":
            self.updateFromGeometry(obj)
        elif prop in ["SafeHeight", "FinalDepth", "Diam", "Ap", "PeckDepth", "Retract", "ThreadPitch", "DwellTime"]:
            self.execute(obj)

    def updateVisibleProperties(self, obj):
        """Met à jour la visibilité des propriétés en fonction du type de cycle"""
        # Cacher toutes les propriétés spécifiques
        obj.setEditorMode("PeckDepth", 2)  # caché
        obj.setEditorMode("Retract", 2)  # caché
        obj.setEditorMode("ThreadPitch", 2)  # caché
        obj.setEditorMode("DwellTime", 2)  # caché
        obj.setEditorMode("Diam", 2)
        obj.setEditorMode("Ap", 2)

        # Afficher les propriétés spécifiques au cycle sélectionné
        if obj.CycleType == "Simple":
            obj.setEditorMode("DwellTime", 0)  # visible
        if obj.CycleType == "Peck":
            obj.setEditorMode("PeckDepth", 0)  # visible
            obj.setEditorMode("Retract", 0)  # visible
            obj.setEditorMode("DwellTime", 0)  # visible
        elif obj.CycleType == "Tapping":
            obj.setEditorMode("ThreadPitch", 0)  # visible
        elif obj.CycleType == "Boring":
            obj.setEditorMode("DwellTime", 0)  # visible
        elif obj.CycleType == "Contournage":
            obj.setEditorMode("Diam", 0)
            obj.setEditorMode("Ap", 0)

    def updateFromGeometry(self, obj):
        """Met à jour les paramètres en fonction de la géométrie sélectionnée"""
        if not obj.DrillGeometry:
            return

        geom = obj.DrillGeometry
        if hasattr(geom, "DrillDiameter"):
            App.Console.PrintMessage(f"Diamètre détecté: {geom.DrillDiameter.Value}mm\n")

        if hasattr(geom, "DrillDepth"):
            obj.FinalDepth = -abs(geom.DrillDepth.Value)
            App.Console.PrintMessage(f"Profondeur détectée: {obj.FinalDepth.Value}mm\n")

    def _computeFinalZ(self, obj):
        """Retourne la coordonnée Z absolue du fond du trou."""
        if obj.DepthMode == "Absolute":
            return obj.FinalDepth.Value
        else:
            return obj.ZReference.Value + obj.FinalDepth.Value

    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        if App.ActiveDocument.Restoring:
            return
        super().execute(obj)  # Appelle la logique de base (vérifications, etc.)

        if not obj.DrillGeometry or not hasattr(obj.DrillGeometry, "DrillPositions"):
            obj.Shape = Part.Shape()  # Shape vide
            return
        # App.Console.PrintMessage(f'{BaptUtilities.find_cam_project(obj).Label}\n')
        # Obtenir les positions de perçage
        drill_geometry = obj.DrillGeometry
        positions = drill_geometry.DrillPositions
        feed = obj.FeedRate.getValueAs("mm/min").Value

        if not positions:
            obj.Shape = Part.Shape()  # Shape vide
            return

        # Créer une représentation d'outil pour chaque position
        tool_shapes = []

        # Récupérer les informations sur l'outil sélectionné
        # tool_info = self.getToolInfo(obj)
        final_z = self._computeFinalZ(obj)

        if obj.Tool is None:
            # Aucun outil sélectionné, utiliser une représentation par défaut
            for pos in positions:
                depth = abs(pos.z - final_z)
                if depth < 0.01:
                    continue
                cylinder = Part.makeCylinder(2.0, depth, pos, App.Vector(0, 0, -1))
                tool_shapes.append(cylinder)
        else:
            # Créer une représentation réaliste de l'outil pour chaque position
            for pos in positions:
                tool_shape = self.createToolShape(obj, pos)
                tool_shapes.append(tool_shape)

        gcodeWriter = GcodeWriter()
        if len(positions) > 0:
            p0 = positions[0]
            safe_z_0 = p0.z + obj.SafeHeight.Value

            gcodeWriter.linearMove({'X': p0.x, 'Y': p0.y}, rapid=True)
            gcodeWriter.linearMove({'Z': p0.z}, rapid=True)

            if obj.CycleType == "Simple":
                gcodeWriter.raw(f"G81 Z{obj.FinalDepth.Value} R{safe_z_0} F{feed}")  # FIXME

            elif obj.CycleType == "Peck":
                gcodeWriter.raw(f"G83 Z{obj.FinalDepth.Value} R{safe_z_0} Q{obj.PeckDepth.Value} F{feed}")  # FIXME

            elif obj.CycleType == "Tapping":
                # FIXME verifier la presence d'un outil de taraudage et son pas
                gcodeWriter.raw(f"G84 Z{obj.FinalDepth.Value} R{safe_z_0}")

            elif obj.CycleType == "Contournage":
                d = obj.Diam - obj.Tool.Radius.Value * 2
                r = d / 2
                # profTotale = distance verticale du plan R au fond (toujours positive)
                profTotale = abs(safe_z_0 - final_z)

                nbTour = math.ceil(profTotale / obj.Ap)
                prisePasse = (profTotale / nbTour) / 2

                gcodeWriter.addLabel(obj.Label)
                gcodeWriter.raw("G91")
                gcodeWriter.linearMove({'X': r}, feed=feed)  # TODO add feed
                for _ in range(nbTour):
                    gcodeWriter.arcMove({'X': -d, 'Y': 0, 'Z': -prisePasse, 'I': -r, 'J': 0, 'CCW': True})
                    gcodeWriter.arcMove({'X': d, 'Y': 0, 'Z': -prisePasse, 'I': r, 'J': 0, 'CCW': True})

                gcodeWriter.arcMove({'X': -d, 'Y': 0, 'I': -r, 'J': 0, 'CCW': True})
                gcodeWriter.arcMove({'X': d, 'Y': 0, 'I': r, 'J': 0, 'CCW': True})
                gcodeWriter.linearMove({'X': -r}, feed=None)
                gcodeWriter.linearMove({'Z': profTotale}, rapid=True)
                gcodeWriter.raw("G90")
                gcodeWriter.endLabel()
            else:
                raise Exception(f"Unsupported Cycle Type : {obj.CycleType}")

            for i in range(1, len(positions)):
                pt = positions[i]
                gcodeWriter.linearMove({'X': pt.x, 'Y': pt.y, 'Z': pt.z + obj.SafeHeight.Value}, rapid=True)
                if obj.CycleType == "Contournage":
                    gcodeWriter.raw(f"REPEAT {obj.Label} {obj.Label}_FIN P=1")

            if obj.CycleType != "Contournage":
                gcodeWriter.raw("G80")

        obj.Gcode = "\n".join(gcodeWriter.lines)
        obj.TimeEstimate = gcodeWriter.time_estimate

        # # Créer un fil qui relie tous les trous
        # wires = []
        # if obj.ShowPathLine and len(positions) > 1:
        #     points = []
        #     for pos in positions:
        #         # Ajouter un point au-dessus de chaque trou avec la hauteur supplémentaire
        #         elevated_pos = App.Vector(pos.x, pos.y, pos.z + obj.SafeHeight.Value)
        #         points.append(elevated_pos)

        #     # Créer une polyligne avec tous les points
        #     polyline = Part.makePolygon(points)
        #     wires.append(polyline)

        # Fusionner les formes d'outils et le fil
        shapes = tool_shapes  # + wires
        if shapes:
            compound = Part.makeCompound(shapes)
            obj.Shape = compound

    def createToolShape(self, obj, position):
        """Crée une représentation visuelle de l'outil en fonction de son type"""
        tool = obj.Tool

        # Coordonnée Z absolue du fond du trou
        final_z = self._computeFinalZ(obj)

        # Position du fond du trou
        bottom_pos = App.Vector(position.x, position.y, final_z)

        # Diamètre de l'outil
        diameter = obj.Tool.Radius.Value * 2

        # Profondeur de perçage (toujours positive)
        depth = abs(position.z - final_z)
        if depth < 0.01 or diameter < 0.01:
            # Profondeur ou diamètre nul → rien à dessiner
            return Part.Shape()

        if obj.CycleType == "Contournage":
            diameter = obj.Diam
            return Part.makeCylinder(diameter / 2, depth, bottom_pos, App.Vector(0, 0, 1))

        # Type d'outil (fallback pour anciens outils sans ToolType)
        tool_type = getattr(tool, "ToolType", "Fraise").lower()

        # Créer une forme différente selon le type d'outil
        try:
            if tool_type == "foret":
                point_angle = getattr(tool, "PointAngle", 118.0)
                if point_angle <= 0 or point_angle >= 180:
                    point_angle = 118.0
                return self.createDrillBit(position, bottom_pos, diameter, depth, point_angle)
            elif tool_type == "taraud":
                thread_pitch = getattr(tool, "ThreadPitch", 1.0)
                return self.createTapBit(position, bottom_pos, diameter, depth, thread_pitch)
            elif tool_type in ("fraise", "fraise torique"):
                torus_radius = getattr(tool, "TorusRadius", 0.0)
                return self.createEndMill(position, bottom_pos, diameter, depth, torus_radius)
            else:
                return self.createSimpleTool(position, bottom_pos, diameter, depth)
        except Exception as e:
            App.Console.PrintError(f"[DrillOp] Error creating tool shape for '{tool_type}' "
                                   f"(D={diameter}, depth={depth}): {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc() + "\n")
            # Fallback : cylindre simple
            return Part.makeCylinder(diameter / 2, depth, bottom_pos, App.Vector(0, 0, 1))

    def createDrillBit(self, top_pos, bottom_pos, diameter, depth, point_angle):
        """Crée une représentation d'un foret avec une pointe conique.

        La forme va de top_pos (surface) vers le bas jusqu'à bottom_pos.
        Le foret se compose d'un cylindre + un cône dont la pointe est en bas.

        Géométrie (vue en coupe) :

            top_pos (Z haut)
            ┌───────────┐
            │ cylindre  │  body_height = depth - tip_height
            │  R=radius │
            └─────┬─────┘  Z = bottom_pos.z + tip_height
                  ╲   ╱
                   ╲ ╱     tip_height
                    V
            bottom_pos (Z bas)
        """
        radius = diameter / 2.0
        half_angle_rad = math.radians(point_angle / 2.0)
        # Hauteur théorique de la pointe conique complète
        tip_height = radius / math.tan(half_angle_rad)

        if depth < 0.01:
            return Part.Shape()

        if depth <= tip_height:
            # Le trou est moins profond que la pointe → cône tronqué
            top_radius = math.tan(half_angle_rad) * depth
            # Construire le profil et le révolver pour éviter les problèmes
            # avec makeCone et rayon nul
            p1 = App.Vector(0, 0, 0)              # pointe (centre bas)
            p2 = App.Vector(top_radius, 0, depth)  # bord haut
            p3 = App.Vector(0, 0, depth)           # centre haut
            e1 = Part.makeLine(p1, p2)
            e2 = Part.makeLine(p2, p3)
            e3 = Part.makeLine(p3, p1)
            wire = Part.Wire([e1, e2, e3])
            face = Part.Face(wire)
            shape = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)
            # Déplacer à la position bottom_pos
            shape.translate(bottom_pos)
            return shape
        else:
            # Partie cylindrique + cône
            # body_height = depth - tip_height

            # Construire le profil complet en une seule pièce :
            # triangle de la pointe + rectangle du cylindre → révolution
            p1 = App.Vector(0, 0, 0)                   # pointe (centre bas)
            p2 = App.Vector(radius, 0, tip_height)     # jonction cône/cylindre (bord)
            p3 = App.Vector(radius, 0, depth)           # bord haut
            p4 = App.Vector(0, 0, depth)                # centre haut
            e1 = Part.makeLine(p1, p2)  # flanc du cône
            e2 = Part.makeLine(p2, p3)  # paroi cylindrique
            e3 = Part.makeLine(p3, p4)  # face supérieure
            e4 = Part.makeLine(p4, p1)  # axe central
            wire = Part.Wire([e1, e2, e3, e4])
            face = Part.Face(wire)
            shape = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)
            # Déplacer à la position bottom_pos
            shape.translate(bottom_pos)
            return shape

    def createTapBit(self, top_pos, bottom_pos, diameter, length, thread_pitch):
        """Crée une représentation d'un taraud"""
        # Créer le corps du taraud (cylindre)
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))

        # Ajouter des rainures pour représenter les filets
        # (Simplifié pour la visualisation)
        tap_bit = body

        # Nombre de filets à représenter
        num_threads = min(10, int(length / thread_pitch))

        # Créer des anneaux pour représenter les filets
        for i in range(num_threads):
            z_pos = bottom_pos.z + i * thread_pitch
            ring_pos = App.Vector(top_pos.x, top_pos.y, z_pos)
            ring = Part.makeTorus(diameter / 2, diameter / 10, ring_pos, App.Vector(0, 0, 1))
            tap_bit = tap_bit.fuse(ring)

        return tap_bit

    def createEndMill(self, top_pos, bottom_pos, diameter, length, torus_radius=0):
        """Crée une représentation d'une fraise"""
        # Créer le corps de la fraise (cylindre)
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))

        # Si c'est une fraise torique, ajouter un arrondi au bout
        if torus_radius > 0:
            torus_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z + torus_radius)
            torus = Part.makeTorus(diameter / 2 - torus_radius, torus_radius, torus_pos, App.Vector(0, 0, 1))
            end_mill = body.fuse(torus)
        else:
            # Fraise droite, ajouter un disque plat au bout
            disk_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
            disk = Part.makeCylinder(diameter / 2, 0.1, disk_pos, App.Vector(0, 0, 1))
            end_mill = body.fuse(disk)

        return end_mill

    def createSimpleTool(self, top_pos, bottom_pos, diameter, length):
        """Crée une représentation simple d'un outil (cylindre)"""
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))
        return body

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)
        self.updateVisibleProperties(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderDrillOperation(baseOpViewProviderProxy):
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object
        vobj.ShapeColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.Transparency = 70

    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        return super().attach(vobj)

    def getIcon(self):
        """Retourne l'icône"""
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Tree_Drilling.svg")

    # def updateData(self, obj, prop):
    #     """Appelé quand une propriété de l'objet est modifiée"""
    #     pass

    # def onChanged(self, vobj, prop):
    #     """Appelé quand une propriété du ViewProvider est modifiée"""
    #     pass

    # def doubleClicked(self, vobj):
    #     """Gérer le double-clic"""
    #     self.setEdit(vobj)
    #     return True

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)

        viewGcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "View G-code", menu)
        QtCore.QObject.connect(viewGcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(viewGcode)

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
        from Op.Gui.DrillOpTaskPanel import DrillOperationTaskPanel
        panel = DrillOperationTaskPanel(vobj.Object)
        Gui.Control.showDialog(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Fermer l'éditeur"""
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        return True

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None
