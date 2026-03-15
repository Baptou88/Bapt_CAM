import BaptUtilities
import FreeCAD as App
import FreeCADGui as Gui


from ContourBaseGeom import ContourBaseGeom
import Part


class contour25DGeom(ContourBaseGeom):
    def __init__(self, obj):
        super().__init__(obj)

        self.Object = obj

        if not hasattr(obj, "Sketch"):
            obj.addProperty("App::PropertyLink", "Sketch", "Base", "Sketch associé à la géométrie")
        if not hasattr(obj, "Sketch2"):
            obj.addProperty("App::PropertyLink", "Sketch2", "Base", "Deuxième sketch associé à la géométrie")

        for s in [obj.Sketch, obj.Sketch2]:
            if not s:
                sketch = App.ActiveDocument.addObject("Sketcher::SketchObject", obj.Name + "_Sketch")
                s = sketch
                obj.addObject(sketch)

        obj.Proxy = self

    def getDepths(self):
        """Retourne la profondeur de ref et finale en fonction du mode"""
        Zref = self.Object.Sketch.Placement.Base.z
        Zfinal = self.Object.Sketch2.Placement.Base.z
        return Zref, Zfinal

    def onDocumentRestored(self, obj):
        self.Object = obj

    def execute(self, obj):
        # Créer les faces entre les arêtes correspondantes
        # Créer le fil à Zref

        if not obj.Sketch or not obj.Sketch2:
            obj.Shape = Part.Shape()
            return

        faces = []
        if len(obj.Sketch.Shape.Edges) != len(obj.Sketch2.Shape.Edges):
            App.Console.PrintError("Les listes d'arêtes ajustées n'ont pas la même taille, impossible de créer les faces.\n")
            return
        for i in range(len(obj.Sketch.Shape.Edges)):
            try:
                face = Part.makeRuledSurface(obj.Sketch.Shape.Edges[i], obj.Sketch2.Shape.Edges[i])
                faces.append(face)
            except Exception as e:
                App.Console.PrintError(f"Impossible de créer une face entre les arêtes {i}: {str(e)}\n")
        if faces:
            compound = Part.makeCompound(faces)
            obj.Shape = compound
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderContour25DGeometry:
    """Affichage pour Contour25DGeometry"""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        return BaptUtilities.getIconPath("ContourEditable.svg")
        return ":/icons/Sketcher_NewSketch.svg"

    def attach(self, vobj):
        vobj.LineColor = (1.0, 0.5, 0.0)
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
        for s in ["Sketch", "Sketch2"]:
            if hasattr(self.Object, s) and getattr(self.Object, s):
                App.ActiveDocument.removeObject(getattr(self.Object, s).Name)
        return True


def createContour25DGeom(cam_project):
    doc = App.ActiveDocument

    # Créer l'objet avec le bon type pour avoir une Shape
    obj = doc.addObject("Part::FeaturePython", "Contour25DGeometry")
    obj.addExtension("App::GroupExtensionPython")
    contour25DGeom(obj)

    # Ajouter le ViewProvider
    if App.GuiUp and obj.ViewObject:
        obj.ViewObject.addExtension("Gui::ViewProviderGroupExtensionPython")
        ViewProviderContour25DGeometry(obj.ViewObject)

    # Placer l'objet dans le même groupe que les autres géométries du projet
    cam_project.Proxy.getGeometryGroup(cam_project).addObject(obj)

    return obj
