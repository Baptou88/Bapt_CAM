import FreeCAD as App
import FreeCADGui as Gui
import Part

from Op import offset


class opContournageTest:
    """Classe de test pour le contournage"""

    def __init__(self, obj):
        self.Object = obj
        self.Type = "opContournageTest"

        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Contour", "Direction d'usinage")
            obj.Direction = ["Climb", "Conventional"]
            obj.Direction = "Climb"

        # Lien vers la géométrie du contour
        if not hasattr(obj, "ContourGeometry"):
            obj.addProperty("App::PropertyLink", "ContourGeometry", "Contour", "Géométrie du contour")

        obj.Proxy = self

    def onChanged(self, obj, prop):
        """Called when a property has changed"""
        # App.Console.PrintMessage(f'on changed {prop}\n')
        return

    def execute(self, obj):
        """Called when the document is recomputed"""

        App.Console.PrintMessage("opContournageTest executed\n")

        geom = obj.ContourGeometry
        if not geom:
            App.Console.PrintError("No contour geometry linked!\n")
            return

        e = geom.Proxy.getEdges(geom)
        w = Part.Wire(e)
        machiningSide = geom.Proxy.getToolSide(geom)
        is_forward = not offset.reverse_toolpath_for_mode(obj.Direction)

        offset_wire = offset.offsetWire(w, 5.0, forward=is_forward, side=machiningSide)
        edge = offset_wire.Edges[0]
        is_tool_left = machiningSide == offset.Side.LEFT
        _, app = self._build_approach(
            edge.Vertexes[0].Point,
            edge.tangentAt(0),
            tool_left=is_tool_left)
        compound = Part.Compound([app[0], offset_wire])
        obj.Shape = Part.Shape(compound)

    def onDocumentRestored(self, obj):
        """Called when the document is loaded"""
        self.Object = obj
        self.__init__(obj)

    def _build_approach(self, entry_point, travel_direction, tool_left):
        """Construit le mouvement d'approche vers le contour.

        L'approche part du côté outil (côté libre) et se dirige vers le contour.
        Le côté outil est déterminé par self._tool_side_is_left.
        """
        approach_type = "Perpendiculaire"  # ou "Tangentielle", "Perp+Arc"
        length = 10.0
        t = travel_direction

        if approach_type == "Tangentielle":
            pt = entry_point - t * length
            return pt, [Part.makeLine(pt, entry_point)]

        elif approach_type in ["Perpendiculaire", "Perp+Arc"]:
            if tool_left:
                perp = App.Vector(-t.y, t.x, 0)
            else:
                perp = App.Vector(t.y, -t.x, 0)
            perp.normalize()
            pt = entry_point + perp * length
            return pt, [Part.makeLine(pt, entry_point)]

        return entry_point, []

    def dumps(self):
        return None

    def loads(self, state):
        return None


class opContournageTestViewProvider:
    """View provider for opContournageTest"""

    def __init__(self, obj):
        self.Object = obj
        self.Type = "opContournageTestViewProvider"
        obj.Proxy = self

    def attach(self, vobj):
        """Called when the view provider is attached to the object"""
        self.Object = vobj.Object

    def getIcon(self):
        """Return the path to the icon for this object"""
        return ":/icons/Part_Cylinder.svg"

    def dumps(self):
        return None

    def loads(self, state):
        return None


def create(cam_project, name="opContournageTest"):
    """Factory function to create an instance of opContournageTest"""
    obj = cam_project.addObject("Part::FeaturePython", name)
    opContournageTest(obj)
    if App.GuiUp:
        opContournageTestViewProvider(obj.ViewObject)
    return obj
