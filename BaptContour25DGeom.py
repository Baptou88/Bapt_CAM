import FreeCAD as App
import FreeCADGui as Gui
import Part

import BaptUtilities

from ContourBaseGeom import ContourBaseGeom


class contour25DGeom(ContourBaseGeom):
    """Géométrie de contour 2.5D"""

    def __init__(self, obj):
        super().__init__(obj)

        self.Object = obj

        if not hasattr(obj, "Sketch"):
            obj.addProperty("App::PropertyLink", "Sketch", "Base", "Sketch associé à la géométrie")
        if not hasattr(obj, "Sketch2"):
            obj.addProperty("App::PropertyLink", "Sketch2", "Base", "Deuxième sketch associé à la géométrie")

        if not hasattr(obj, "t"):
            obj.addProperty("App::PropertyFloat", "t", "Base", "Paramètre de la courbe, entre 0 et 1")

        for s in ["Sketch", "Sketch2"]:
            if not getattr(obj, s):
                sketch = App.ActiveDocument.addObject("Sketcher::SketchObject", obj.Name + "_" + s)
                setattr(obj, s, sketch)
                obj.addObject(sketch)

        obj.Proxy = self

    def getDepths(self):
        """Retourne la profondeur de ref et finale en fonction du mode"""
        Zref = self.Object.Sketch.Placement.Base.z
        Zfinal = self.Object.Sketch2.Placement.Base.z
        return Zref, Zfinal

    def onDocumentRestored(self, obj):
        self.Object = obj
        self.__init__(obj)

    def getEdges(self, obj):
        """Retourne les arêtes du premier sketch"""
        if obj.Sketch and obj.Sketch.Shape and obj.Sketch.Shape.Edges:
            return list(obj.Sketch.Shape.Edges)
        return []

    def onChanged(self, obj, prop):
        if prop in ["Sketch", "Sketch2", "t", "Direction", "CoteMatiere", "debugArrow"]:
            self.execute(obj)
            return True
        return False

    def getWireAtZ(self, obj, z):
        """Retourne le fil correspondant à une profondeur z donnée"""
        if not self.Object.Sketch or not self.Object.Sketch2:
            return None

        faces = self.getFaces(obj)
        if not faces:
            return None

        compound: Part.Compound = Part.makeCompound(faces)

        Zref, Zfinal = self.getDepths()
        if Zfinal == Zref:
            return None  # Éviter la division par zéro

        # plane = Part.makePlane(1000, 1000, App.Vector(0, 0, midZ), App.Vector(0, 0, 1))
        edges = compound.slice(App.Vector(0, 0, 1), z)
        if not edges:
            return None
        return Part.Wire(edges)

    def getFaces(self, obj):
        if not obj.Sketch or not obj.Sketch2:
            return []
        faces = []
        if len(obj.Sketch.Shape.Edges) != len(obj.Sketch2.Shape.Edges):
            App.Console.PrintError("Les listes d'arêtes ajustées n'ont pas la même taille, impossible de créer les faces.\n")
            return []
        for i in range(len(obj.Sketch.Shape.Edges)):
            try:
                face = Part.makeRuledSurface(obj.Sketch.Shape.Edges[i], obj.Sketch2.Shape.Edges[i])
                faces.append(face)
            except Exception as e:
                App.Console.PrintError(f"Impossible de créer une face entre les arêtes {i}: {str(e)}\n")
        return faces

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return

        if not obj.Sketch or not obj.Sketch2:
            obj.Shape = Part.Shape()
            return

        faces = self.getFaces(obj)
        if not faces:
            obj.Shape = Part.Shape()
            return

        compound = Part.makeCompound(faces)
        shapes = [compound]

        # Wire intermédiaire pour visualisation
        Zref = obj.Sketch.Placement.Base.z
        Zfinal = obj.Sketch2.Placement.Base.z
        t_z = Zref + obj.t * (Zfinal - Zref)
        wire = self.getWireAtZ(obj, t_z)
        if wire:
            shapes.append(wire)
            obj.IsClosed = wire.isClosed()
        else:
            obj.IsClosed = False

        obj.Shape = Part.makeCompound(shapes)

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
