import math

import FreeCAD as App
import Part  # type: ignore

from BaptPreferences import BaptPreferences

from Tool.SqliteToolRepository import SqliteToolRepository
from Tool.TlsToolRepository import TlsToolRepository  # type: ignore


def create_tool_obj(Tid=0, name="New Tool", diameter=10.0, speed=1000.0, feed=500.0,
                    tool_type="Fraise", torus_radius=0.0, length=50.0, point_angle=118.0):
    """Create a tool document object with the correct 3D shape.

    Parameters
    ----------
    tool_type : str
        One of "Fraise", "Fraise torique", "Foret", "Taraud", "Autre".
    torus_radius : float
        Corner radius for bull-nose / torus end mills (mm).
    point_angle : float
        Drill point angle in degrees (default 118).
    """
    new_tool = App.ActiveDocument.addObject("Part::FeaturePython", f"{name}")
    new_tool.addProperty("App::PropertyInteger", "Id", "Tool", "Tool ID").Id = Tid
    new_tool.addProperty("App::PropertySpeed", "Speed", "Tool", "Tool Speed").Speed = f"{speed} mm/min"
    new_tool.addProperty("App::PropertySpeed", "Feed", "Tool", "Tool Feed").Feed = f"{feed} mm/min"
    new_tool.addProperty("App::PropertyLength", "Radius", "Tool", "Tool Radius").Radius = diameter / 2.0
    new_tool.addProperty("App::PropertyLength", "Height", "Tool", "Tool Height").Height = length
    new_tool.addProperty("App::PropertyString", "ToolType", "Tool", "Tool Type").ToolType = tool_type
    new_tool.addProperty("App::PropertyFloat", "TorusRadius", "Tool", "Torus corner radius").TorusRadius = torus_radius
    new_tool.addProperty("App::PropertyFloat", "PointAngle", "Tool", "Drill point angle (degrees)").PointAngle = point_angle

    new_tool.Proxy = ToolShapeProxy(new_tool)
    if App.GuiUp:
        ToolShapeViewProvider(new_tool.ViewObject)

    # Force first shape computation
    new_tool.Proxy.execute(new_tool)
    return new_tool


class ToolShapeProxy:
    """Proxy that keeps the 3D shape in sync with tool parameters."""

    def __init__(self, obj):
        obj.Proxy = self

    def execute(self, obj):
        radius = obj.Radius.Value
        height = obj.Height.Value if obj.Height.Value > 0 else 50.0
        tool_type = obj.ToolType if hasattr(obj, "ToolType") else "Fraise"
        torus_r = obj.TorusRadius if hasattr(obj, "TorusRadius") else 0.0
        point_angle = obj.PointAngle if hasattr(obj, "PointAngle") else 118.0

        try:
            if tool_type == "Foret":
                shape = _make_drill_bit(radius, height, point_angle)
            elif tool_type == "Fraise torique" and torus_r > 0 and torus_r < radius:
                shape = _make_torus_endmill(radius, height, torus_r)
            else:
                shape = Part.makeCylinder(radius, height)

            obj.Shape = shape
        except Exception as e:
            App.Console.PrintError(f"[ToolShapeProxy] Error creating shape for '{tool_type}' "
                                   f"(R={radius}, H={height}, angle={point_angle}): {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc() + "\n")
            obj.Shape = Part.makeCylinder(radius if radius > 0 else 1.0, height)

    def onChanged(self, obj, prop):
        """Called when a property changes. We need to recompute the shape if any of the parameters change."""
        if prop in ["Radius", "Height", "ToolType", "TorusRadius", "PointAngle"]:
            self.execute(obj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def _make_torus_endmill(radius, height, torus_r):
    """Build a bull-nose end mill shape: cylinder + torus fillet at the bottom.

    The profile is revolved around Z:
        - vertical line from top to ``torus_r`` above the bottom
        - quarter-circle arc of radius ``torus_r``
        - horizontal line from arc end to the centre

    The shape sits with its base at Z=0, extending upward.
    """

    # Key dimensions
    flat_radius = radius - torus_r          # radius of the flat bottom part

    # Profile points (in the XZ half-plane, revolved around Z)
    p1 = App.Vector(radius, 0, height)      # top outer edge
    p2 = App.Vector(radius, 0, torus_r)     # where fillet starts
    p3 = App.Vector(flat_radius, 0, 0)      # bottom of fillet
    p4 = App.Vector(0, 0, 0)                # centre bottom
    p5 = App.Vector(0, 0, height)           # centre top

    # Build the profile wire
    e1 = Part.makeLine(p1, p2)              # outer wall
    e2 = Part.Arc(p2, App.Vector(radius - torus_r * (1 - 0.7071), 0, torus_r * (1 - 0.7071)), p3).toShape()  # fillet arc
    e3 = Part.makeLine(p3, p4)              # bottom flat
    e4 = Part.makeLine(p4, p5)              # centre line
    e5 = Part.makeLine(p5, p1)              # top cap

    wire = Part.Wire([e1, e2, e3, e4, e5])
    face = Part.Face(wire)
    shape = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)
    return shape


def _make_drill_bit(radius, height, point_angle):
    """Build a drill bit shape: cylinder body + conical tip.

    The shape sits with its base at Z=0, extending upward.
    The conical tip points downward at Z=0.

    Uses a profile revolution to avoid Part.makeCone(0, ...) which
    fails in FreeCAD when the first radius is zero.

    Parameters
    ----------
    radius : float
        Drill radius (mm).
    height : float
        Total tool length (mm).
    point_angle : float
        Full point angle in degrees (e.g. 118).
    """

    half_angle = math.radians(point_angle / 2.0)
    # Height of the conical tip
    tip_height = radius / math.tan(half_angle)

    if tip_height >= height:
        # Tool is shorter than the tip — just a truncated cone
        actual_radius = math.tan(half_angle) * height
        # Profile: triangle  (apex at origin, opening upward)
        p1 = App.Vector(0, 0, 0)               # tip (centre)
        p2 = App.Vector(actual_radius, 0, height)  # outer edge at top
        p3 = App.Vector(0, 0, height)           # centre top
        e1 = Part.makeLine(p1, p2)
        e2 = Part.makeLine(p2, p3)
        e3 = Part.makeLine(p3, p1)
        wire = Part.Wire([e1, e2, e3])
        face = Part.Face(wire)
        shape = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)
    else:
        # Cone tip + cylinder body — single profile revolution
        # Profile (XZ half-plane):
        #   p1 = (0, 0, 0)              — apex
        #   p2 = (radius, 0, tip_height) — junction cone/cylinder
        #   p3 = (radius, 0, height)     — top outer edge
        #   p4 = (0, 0, height)          — top centre
        p1 = App.Vector(0, 0, 0)
        p2 = App.Vector(radius, 0, tip_height)
        p3 = App.Vector(radius, 0, height)
        p4 = App.Vector(0, 0, height)
        e1 = Part.makeLine(p1, p2)   # cone flank
        e2 = Part.makeLine(p2, p3)   # cylinder wall
        e3 = Part.makeLine(p3, p4)   # top face
        e4 = Part.makeLine(p4, p1)   # centre axis
        wire = Part.Wire([e1, e2, e3, e4])
        face = Part.Face(wire)
        shape = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)

    return shape


class ToolShapeViewProvider:
    """View provider for the tool shape, to set display properties."""

    def __init__(self, vobj):
        self.vobj = vobj
        vobj.Proxy = self
        self.setDisplayProperties(vobj)

    def setDisplayProperties(self, vobj):
        vobj.ShapeColor = (0.8, 0.8, 0.0)  # yellow
        vobj.Transparency = 50
        # vobj.DisplayMode = "Shaded"

    def attach(self, vobj):
        self.vobj = vobj

        self.setDisplayProperties(vobj)

    # def getDisplayModes(self, obj):
    #     '''Return a list of display modes.'''
    #     modes = []
    #     modes.append("Flat Lines")
    #     modes.append("Shaded")
    #     modes.append("Wireframe")
    #     return modes

    def getDefaultDisplayMode(self):
        '''Return the name of the default display mode. It must be defined in getDisplayModes.'''
        return "Shaded"

    def setDisplayMode(self, mode):
        '''Map the display mode defined in attach with those defined in getDisplayModes.\
                Since they have the same names nothing needs to be done. This method is optional'''
        return mode

    def getIcon(self):
        '''Return the icon in XPM format which will appear in the tree view. This method is\
                optional and if not defined a default icon is shown.'''
        return """
            /* XPM */
            static const char * ViewProviderBox_xpm[] = {
            "16 16 6 1",
            "   c None",
            ".  c #141010",
            "+  c #615BD2",
            "@  c #C39D55",
            "#  c #000000",
            "$  c #57C355",
            "        ........",
            "   ......++..+..",
            "   .@@@@.++..++.",
            "   .@@@@.++..++.",
            "   .@@  .++++++.",
            "  ..@@  .++..++.",
            "###@@@@ .++..++.",
            "##$.@@$#.++++++.",
            "#$#$.$$$........",
            "#$$#######      ",
            "#$$#$$$$$#      ",
            "#$$#$$$$$#      ",
            "#$$#$$$$$#      ",
            " #$#$$$$$#      ",
            "  ##$$$$$#      ",
            "   #######      "};
            """

    def dumps(self):
        return None

    def loads(self, state):
        return None


def get_tool_repository():
    """Retourne le bon ToolRepository selon les préférences.

    - Si le chemin pointe vers un fichier .tls  -> TlsToolRepository
    - Sinon (vide, .db, ou autre)               -> SqliteToolRepository
    """
    prefs = BaptPreferences()
    path = prefs.getToolsDbPath()
    if path and path.lower().endswith('.tls'):
        return TlsToolRepository(path)
    return SqliteToolRepository()
