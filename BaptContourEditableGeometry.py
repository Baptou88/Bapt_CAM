
import BaptUtilities
from ContourBaseGeom import ContourBaseGeom
import FreeCAD as App
import FreeCADGui as Gui


class ContourEditableGeometry(ContourBaseGeom):
    """Contour éditable via Sketcher"""

    def __init__(self, obj):
        super().__init__(obj)
        self.Type = "ContourEditableGeometry"
        self.Object = obj
        if not hasattr(obj, "Sketch"):
            obj.addProperty("App::PropertyLink", "Sketch", "Base", "Sketch associé à la géométrie")

        if not hasattr(obj, "depth"):
            obj.addProperty("App::PropertyFloat", "depth", "Contour", "Hauteur finale")
            obj.depth = 0.0

        self.createSketch(obj)
        obj.Proxy = self

    def createSketch(self, obj):
        """Crée un Sketch si besoin"""
        if not obj.Sketch:
            sketch = App.ActiveDocument.addObject("Sketcher::SketchObject", obj.Name + "_Sketch")
            obj.Sketch = sketch
            # Optionnel : placer le sketch dans le même groupe que la géométrie
            if hasattr(obj, "Group"):

                obj.addObject(sketch)

    def getEdges(self, obj):
        """Retourne les edges du sketch"""
        if obj.Sketch and obj.Sketch.Shape and len(obj.Sketch.Shape.Edges) > 0:
            return obj.Sketch.Shape.Edges
        return []

    def getDepths(self):
        """Retourne la profondeur de ref et finale en fonction du mode"""
        if not self.Object.Sketch:
            return 0.0, 0.0
        Zref = self.Object.Sketch.Placement.Base.z
        if self.Object.DepthMode == "Relatif":
            return Zref, Zref - self.Object.depth
        else:  # Absolu
            return Zref, self.Object.depth

    def execute(self, obj):
        """Met à jour la forme à partir du Sketch via ContourBaseGeom"""
        if not obj.Sketch or not obj.Sketch.Shape or not obj.Sketch.Shape.Edges:
            import Part
            obj.Shape = Part.Shape()
            return
        super().execute(obj)

    def onDocumentRestored(self, obj):
        """Restaure les liens après le chargement du document"""
        self.Object = obj
        self.__init__(obj)

    def onChanged(self, obj, prop):
        """Synchronise la forme si le Sketch change"""

        if prop in ["Sketch", "depth", "Direction", "DepthMode", "CoteMatiere"]:
            self.execute(obj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class ViewProviderContourEditableGeometry:
    """Affichage pour ContourEditableGeometry"""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        return BaptUtilities.getIconPath("ContourEditable.svg")
        return ":/icons/Sketcher_NewSketch.svg"

    def attach(self, vobj):
        vobj.LineColor = (1.0, 0.0, 0.5)
        self.Object = vobj.Object

    def doubleClicked(self, vobj):
        """Ouvre le Sketch en édition"""
        if hasattr(self.Object, "Sketch") and self.Object.Sketch:
            Gui.activeDocument().setEdit(self.Object.Sketch.Name)
            return True
        return False

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit Sketch")
        action.triggered.connect(lambda: self.setEditSketch(vobj))

    def setEditSketch(self, vobj):
        """Ouvre le Sketch en édition"""
        if hasattr(self.Object, "Sketch") and self.Object.Sketch:
            Gui.activeDocument().setEdit(self.Object.Sketch.Name)

    def onDelete(self, vobj, subelements):
        """Nettoyage lors de la suppression"""
        if hasattr(self.Object, "Sketch") and self.Object.Sketch:
            App.ActiveDocument.removeObject(self.Object.Sketch.Name)
        return True


def createContourEditableGeometry(cam_project):
    """Crée une nouvelle géométrie de contour dans le projet CAM"""
    doc = App.ActiveDocument

    # Créer l'objet avec le bon type pour avoir une Shape
    obj = doc.addObject("Part::FeaturePython", "ContourEditableGeometry")
    obj.addExtension("App::GroupExtensionPython")
    ContourEditableGeometry(obj)

    # Ajouter le ViewProvider
    if App.GuiUp and obj.ViewObject:
        obj.ViewObject.addExtension("Gui::ViewProviderGroupExtensionPython")
        ViewProviderContourEditableGeometry(obj.ViewObject)

    # Placer l'objet dans le même groupe que les autres géométries du projet
    cam_project.Proxy.getGeometryGroup(cam_project).addObject(obj)

    return obj
