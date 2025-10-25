# https://forum.freecad.org/viewtopic.php?t=100312&sid=a77831c5cae7ee6feb8cf340f0e19dc6
from collections import deque
import math
import FreeCAD as App
import FreeCADGui
from pivy import coin
from enum import Enum 
from PySide import QtGui,QtCore


"""
Gcode  | Heidenhain | Description
-------|------------|----------------------------------------------
G0     | L    FMAX  | Rapid positioning
G1     | L          | Linear interpolation (feed)
G2     | C          | Circular interpolation, cw
G3     | CC         | Circular interpolation, ccw
G17    | PLANE XY   | Select XY plane for circular interpolation
G18    | PLANE XZ   | Select XZ plane for circular interpolation
G19    | PLANE YZ   | Select YZ plane for circular interpolation
G40    | R0         | Cutter compensation off 
G41    | RL         | Cutter compensation left
G42    | RR         | Cutter compensation right
G90    |            | Absolute programming
G91    | I          | Incremental programming


CHF    |CHF         | Chanfrein
RND    |RND         | Rounding
LABEL  |LBL         | Label declaration
REPEAT |CALL        | Repeat block
"""

class comp(Enum):
    G40 = 0
    G41 = 1
    G42 = 2

class absinc(Enum):
    G90 = 0
    G91 = 1

class baseOp:
    
    def __init__(self,obj):
        App.Console.PrintMessage("Initializing baseOp object proxy for: {}\n".format(__class__.__name__))
        if not hasattr(obj, "Gcode"):
            obj.addProperty("App::PropertyString", "Gcode", "Gcode", "Gcode").Gcode = ""
            #obj.Gcode ="G0 X0 Y-20 Z50\nG0 Z2\nG1 Z0 F500\nG1 Y-10\nG3 X-10 Y0 I-10 J0\nG1 X-48\nG2 X-50 Y2 I0 J2\nG1 Y20\nG91\nG1 X5\nG0 Z50\n"
            
        # obj.Proxy = self
        
    def onChanged(self, fp, prop):
        self.execute(fp)

    def execute(self,obj):
        pass
    def __getstate__(self):
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None
    
class baseOpViewProviderProxy:
    def __init__(self, obj):
        "Set this object as the proxy object of the actual view provider"
        App.Console.PrintMessage("Initializing baseOpViewProviderProxy for: {}\n".format(__class__.__name__))
        self.deleteOnReject = True
        self.pick_radius = 5  # pixels

        if not hasattr(obj, "Rapid"):
            obj.addProperty("App::PropertyColor", "Rapid", "Gcode", "Color for rapid moves")
            obj.Rapid = (1.0, 0.0, 0.0)

        if not hasattr(obj, "Feed"):
            obj.addProperty("App::PropertyColor", "Feed", "Gcode", "Color for feed moves")
            obj.Feed = (0.0, 1.0, 0.0)

        self.colors = {"red": (1.0, 0.0, 0.0),
                       "green": (0.0, 1.0, 0.0),
                       "blue": (0.0, 0.0, 1.0)}
        
        
        # self.Object = obj.Object
        # obj.Proxy = self

    def onChanged(self, vp, prop):
        ''' Print the name of the property that has changed '''
        #App.Console.PrintMessage("Change property: " + str(prop) + "\n")

    def __getstate__(self):
        ''' When saving the document this object gets stored using Python's cPickle module.
		Since we have some un-pickable here -- the Coin stuff -- we must define this method
		to return a tuple of all pickable objects or None.
		'''
        return None

    def __setstate__(self,state):
        ''' When restoring the pickled object from document we have the chance to set some
		internals here. Since no data were pickled nothing needs to be done here.
		'''
        return None
    
    def attach(self, obj):
        App.Console.PrintMessage("Attaching view provider proxy to object: {}\n".format(__class__.__name__))
        self.pick_radius = 5
        self.my_displaymode = coin.SoGroup()

        self.rapid_group = coin.SoSeparator()
        self.rapid_color = coin.SoBaseColor()
        self.rapid_points = coin.SoCoordinate3()
        self.rapid_lines = coin.SoIndexedLineSet()
        self.rapid_group.addChild(self.rapid_color)
        self.rapid_group.addChild(self.rapid_points)
        self.rapid_group.addChild(self.rapid_lines)

        self.feed_group = coin.SoSeparator()
        self.feed_color = coin.SoBaseColor()
        self.feed_points = coin.SoCoordinate3()
        self.feed_lines = coin.SoIndexedLineSet()
        self.feed_group.addChild(self.feed_color)
        self.feed_group.addChild(self.feed_points)
        self.feed_group.addChild(self.feed_lines)

        # Créer le groupe pour le cône de direction
        self.direction_group = coin.SoSeparator()
        self.direction_switch = coin.SoSwitch()  # Pour montrer/cacher le cône
        self.direction_translation = coin.SoTranslation()
        self.direction_rotation = coin.SoRotation()
        self.direction_color = coin.SoBaseColor()
        
        # Créer le cône
        self.direction_cone = coin.SoCone()
        self.direction_cone.height = 2
        self.direction_cone.bottomRadius = 0.5
        
        # Assembler le groupe du cône
        self.direction_group.addChild(self.direction_translation)
        self.direction_group.addChild(self.direction_rotation)
        self.direction_group.addChild(self.direction_color)
        self.direction_group.addChild(self.direction_cone)
        self.direction_switch.addChild(self.direction_group)
        self.direction_switch.whichChild = coin.SO_SWITCH_NONE  # Cacher par défaut
        
        # Ajouter les événements de souris
        self.mouse_cb = coin.SoEventCallback()
        #self.mouse_cb.setCallback(self.mouse_event_cb)
        self.mouse_cb.addEventCallback(coin.SoLocation2Event.getClassTypeId(), self.mouse_event_cb)

        self.my_displaymode.addChild(self.rapid_group)
        self.my_displaymode.addChild(self.feed_group)

        self.my_displaymode.addChild(self.direction_switch)
        self.my_displaymode.addChild(self.mouse_cb)

        # self.color = coin.SoBaseColor()
        # self.points = coin.SoCoordinate3()
        # self.lines = coin.SoIndexedLineSet()
        # self.my_displaymode.addChild(self.points)
        # self.my_displaymode.addChild(self.color)
        # self.my_displaymode.addChild(self.lines)

        obj.addDisplayMode(self.my_displaymode, "My_Display_Mode")

    def mouse_event_cb(self, user_data, event_callback):
        event = event_callback.getEvent()
        if not hasattr(self, "rapid_coords"):
            return
        if isinstance(event, coin.SoLocation2Event):
            pos = event.getPosition()
            view = FreeCADGui.ActiveDocument.ActiveView
            renderer = view.getViewer().getSoRenderManager().getViewportRegion()
            picking = coin.SoRayPickAction(renderer)
            picking.setPoint(pos)
            picking.setRadius(self.pick_radius)

            # appliquer le pick sur le groupe complet
            picking.apply(self.my_displaymode)

            pp = picking.getPickedPoint()
            if pp is not None:
                detail = pp.getDetail()
                path = pp.getPath()  # SoPath
                tail = None
                try:
                    tail = path.getTail()
                except:
                    tail = None

                # déterminer si la ligne appartient à rapid ou feed en regardant le tail node
                if tail is self.rapid_lines:
                    pts = getattr(self, "rapid_coords", [])
                    color = (1.0, 0.0, 0.0)
                elif tail is self.feed_lines:
                    pts = getattr(self, "feed_coords", [])
                    color = (0.0, 1.0, 0.0)
                else:
                    # fallback : essayer de deviner via lineIndex (ancienne méthode)
                    if hasattr(self, "rapid_coords") and isinstance(detail, coin.SoLineDetail):
                        li = detail.getLineIndex()
                        if li < (len(self.rapid_coords) // 2):
                            pts = self.rapid_coords
                            color = (1.0, 0.0, 0.0)
                        else:
                            pts = getattr(self, "feed_coords", [])
                            color = (0.0, 1.0, 0.0)
                    else:
                        pts = []
                        color = (1.0, 1.0, 0.0)

                if isinstance(detail, coin.SoLineDetail):
                    pt1_idx = detail.getPoint0Index()
                    pt2_idx = detail.getPoint1Index()

                    if pt1_idx < len(pts) and pt2_idx < len(pts):
                        pt1 = pts[pt1_idx]
                        pt2 = pts[pt2_idx]

                        mid_point = ((pt1[0] + pt2[0]) / 2.0,
                                     (pt1[1] + pt2[1]) / 2.0,
                                     (pt1[2] + pt2[2]) / 2.0)
                        self.direction_translation.translation.setValue(mid_point[0], mid_point[1], mid_point[2])

                        # orienter le cône dans la direction de la ligne
                        direction = (pt2[0] - pt1[0], pt2[1] - pt1[1], pt2[2] - pt1[2])
                        length = (direction[0]**2 + direction[1]**2 + direction[2]**2) ** 0.5
                        if length > 1e-9:
                            dir_norm = (direction[0]/length, direction[1]/length, direction[2]/length)
                            rot = coin.SbRotation(coin.SbVec3f(0, 0, 1), coin.SbVec3f(*dir_norm))
                            self.direction_rotation.rotation.setValue(rot)

                            # agrandir le cône pour qu'on le voie bien et adapter le rayon
                            h = max(length * 0.6, 2.0)
                            r = max(h * 0.25, 0.2)
                            try:
                                self.direction_cone.height = h
                                self.direction_cone.bottomRadius = r
                            except:
                                pass

                            # couleur
                            self.direction_color.rgb.setValues(0, 1, [color])

                            # afficher le cône
                            self.direction_switch.whichChild = 0
                            return

            # cacher si aucune ligne trouvée
            self.direction_switch.whichChild = coin.SO_SWITCH_NONE

    def updateData(self, fp, prop):

        # if no Gcode property, nothing to do
        if not hasattr(self.Object, "Gcode"):
            return

        gcode_text = str(self.Object.Gcode or "")
        self.lines = [l.strip() for l in gcode_text.splitlines() if l.strip()]

        def parse_xyz(line, prev,absinc_mode=absinc.G90):
            """helper to parse coords in a G-code line (X Y Z)"""
            x, y, z = prev
            
            for token in line.split():
                if token.upper().startswith("X"):
                    try:
                        x = float(token[1:]) if absinc_mode == absinc.G90 else prev[0] + float(token[1:])
                    except:
                        pass
                elif token.upper().startswith("Y"):
                    try:
                        y = float(token[1:]) if absinc_mode == absinc.G90 else prev[1] + float(token[1:])
                    except:
                        pass
                elif token.upper().startswith("Z"):
                    try:
                        z = float(token[1:]) if absinc_mode == absinc.G90 else prev[2] + float(token[1:])
                    except:
                        pass
            return (x, y, z)
        
        # build coordinate lists and index arrays for each group
        rapid_coords = []
        rapid_idx = []
        feed_coords = []
        feed_idx = []

        # current position (start at origin)
        self.cur = (0.0, 0.0, 0.0)

        self.ordered_segments = []

        self.comp_mode = comp.G40  # default cutter compensation off
        self.absinc_mode = absinc.G90  # default absolute mode
        self.mem = memory()
        self.line = 0

        def parse_ijr(line):
            """helper to parse I/J/R (center offsets or radius)"""
            I = J = R = None
            for token in line.split():
                t = token.upper()
                if t.startswith("I"):
                    try:
                        I = float(token[1:])
                    except:
                        pass
                elif t.startswith("J"):
                    try:
                        J = float(token[1:])
                    except:
                        pass
                elif t.startswith("R"):
                    try:
                        R = float(token[1:])
                    except:
                        pass
            return I, J, R
        
        def centers_from_radius(p0, p1, R):
            """compute circle centers from radius R (returns one center that matches direction if requested)"""
            (x1, y1) = (p0[0], p0[1])
            (x2, y2) = (p1[0], p1[1])
            dx = x2 - x1
            dy = y2 - y1
            d2 = dx*dx + dy*dy
            if d2 == 0.0:
                return None  # identical points
            d = math.sqrt(d2)
            if d > 2.0 * R + 1e-12:
                return None  # impossible with given radius
            # midpoint
            mx = (x1 + x2) / 2.0
            my = (y1 + y2) / 2.0
            # distance from midpoint to center
            h = math.sqrt(max(R*R - (d/2.0)*(d/2.0), 0.0))
            ux = -dy / d
            uy = dx / d
            c1 = (mx + ux * h, my + uy * h)
            c2 = (mx - ux * h, my - uy * h)
            return c1, c2
        
        def append_segment(coords_list, idx_list, a, b):
            """helper to append a segment to a group's arrays"""
            i = len(coords_list)
            coords_list.append(a)
            coords_list.append(b)
            idx_list.extend([i, i+1, -1])
            self.ordered_segments.append(("rapid" if coords_list is rapid_coords else "feed", a, b))
        def processGcode():
            while self.line < len(self.lines):

                if len(self.mem.queue) > 0:
                    #App.Console.PrintMessage("Checking memory queue for line {}\n".format(self.line))
                    if self.line == self.mem.queue[0] :
                        self.mem.queue.popleft()
                        break

                ln = self.lines[self.line]
                #App.Console.PrintMessage("Processing line {}: {}\n".format(self.line, ln))
                self.line += 1
                up = ln.upper()
                # consider only movement commands G0/G00 and G1/G01
                if up.startswith("G0") or up.startswith("G00"):
                    new = parse_xyz(ln, self.cur, self.absinc_mode)
                    append_segment(rapid_coords, rapid_idx, self.cur, new)
                    self.cur = new
                elif up.startswith("G1") or up.startswith("G01"):
                    new = parse_xyz(ln, self.cur, self.absinc_mode)
                    append_segment(feed_coords, feed_idx, self.cur, new)
                    self.cur = new
                elif up.startswith("G2") or up.startswith("G3"):
                    # Circular interpolation. Prefer I/J (center offsets). If only R given, compute center(s).
                    is_ccw = up.startswith("G3")
                    end = parse_xyz(ln, self.cur)
                    I, J, R = parse_ijr(ln)

                    # if no XY endpoint given, skip (cannot handle)
                    if (end[0], end[1]) == (self.cur[0], self.cur[1]):
                        # nothing to do if no movement in XY
                        self.cur = (end[0], end[1], end[2])
                        continue

                    center = None
                    radius = None
                    if I is not None or J is not None:
                        # center relative to start
                        i_val = I or 0.0
                        j_val = J or 0.0
                        cx = self.cur[0] + i_val
                        cy = self.cur[1] + j_val
                        center = (cx, cy)
                        radius = math.hypot(self.cur[0] - cx, self.cur[1] - cy)
                    elif R is not None:
                        # compute possible centers from R
                        cs = centers_from_radius(self.cur, end, R)
                        if cs is None:
                            # fallback to linear if impossible
                            append_segment(feed_coords, feed_idx, self.cur, end)
                            self.cur = end
                            continue
                        # choose center that yields correct direction (G2 cw => negative sweep)
                        c1, c2 = cs
                        # compute sweeps for both centers
                        def compute_sweep(c):
                            sx = math.atan2(cur[1]-c[1], cur[0]-c[0])
                            ex = math.atan2(end[1]-c[1], end[0]-c[0])
                            sweep = ex - sx
                            return sweep, sx, ex
                        s1, s1s, s1e = compute_sweep(c1)
                        s2, s2s, s2e = compute_sweep(c2)
                        # normalize sweeps
                        def norm_sweep(s):
                            if is_ccw:
                                if s <= 0:
                                    s += 2*math.pi
                            else:
                                if s >= 0:
                                    s -= 2*math.pi
                            return s
                        ns1 = norm_sweep(s1)
                        ns2 = norm_sweep(s2)
                        # choose the center with smaller absolute normalized sweep
                        if abs(ns1) <= abs(ns2):
                            center = c1
                            radius = R
                        else:
                            center = c2
                            radius = R
                    else:
                        # no center info -> fallback to linear
                        append_segment(feed_coords, feed_idx, self.cur, end)
                        self.cur = end
                        continue

                    # now we have center and radius
                    cx, cy = center

                    r = radius
                    if r <= 1e-12:
                        append_segment(feed_coords, feed_idx, self.cur, end)
                        self.cur = end
                        continue

                    # compute start and end angles
                    start_ang = math.atan2(self.cur[1] - cy, self.cur[0] - cx)
                    end_ang = math.atan2(end[1] - cy, end[0] - cx)
                    # compute sweep based on direction
                    if is_ccw:
                        sweep = end_ang - start_ang
                        if sweep <= 0:
                            sweep += 2 * math.pi
                    else:
                        sweep = end_ang - start_ang
                        if sweep >= 0:
                            sweep -= 2 * math.pi

                    # choose segment density: ~5° per segment or more for large arcs
                    seg_angle = math.radians(5.0)
                    nseg = max(1, int(math.ceil(abs(sweep) / seg_angle)))
                    z0 = self.cur[2]
                    z1 = end[2]
                    for i in range(1, nseg + 1):
                        ang = start_ang + sweep * (i / float(nseg))
                        x = cx + r * math.cos(ang)
                        y = cy + r * math.sin(ang)
                        z = z0 + (z1 - z0) * (i / float(nseg))
                        new_pt = (x, y, z)
                        append_segment(feed_coords, feed_idx, self.cur, new_pt)
                        self.cur = new_pt

                    # ensure final endpoint exact
                    if (abs(self.cur[0]-end[0]) > 1e-9) or (abs(self.cur[1]-end[1]) > 1e-9) or (abs(self.cur[2]-end[2]) > 1e-9):
                        append_segment(feed_coords, feed_idx, self.cur, end)
                        self.cur = end

                elif up.startswith("G40"):
                    self.comp_mode = comp.G40
                elif up.startswith("G41"):
                    self.comp_mode = comp.G41
                elif up.startswith("G42"):
                    self.comp_mode = comp.G42

                elif up.startswith("G90") :
                    self.absinc_mode = absinc.G90
                elif up.startswith("G91") :
                    self.absinc_mode = absinc.G91

                elif up.startswith("M30"):
                    # program end
                    break

                
                
                elif up[0].isalpha() and up.endswith(":"):
                    # label declaration
                    label = up[:-1]
                    # store label with current line number
                    self.mem.addLabel(label, self.line)
                
                elif up.startswith("REPEAT"):
                    # repeat command
                    parts = up.split()
                    label_begin = None
                    n_times = 1
                    label_end = None

                    if len(parts) == 2:
                        label_begin = parts[1] if len(parts) > 1 else None
                        n_times = 1
                    elif len(parts) == 3:
                        label_begin = parts[1] if len(parts) > 1 else None

                        n_times = parts[2].removeprefix("P=")
                        if n_times.isdigit():
                            n_times = int(n_times)
                        elif n_times.startswith("R"):
                            var_name = "R{}".format(n_times[1:])
                            if var_name in self.mem.variables:
                                n_times = int(self.mem.variables[var_name])
                            else:
                                raise Exception("Variable {} not defined for REPEAT".format(var_name))
                    else:
                        pass
                    #App.Console.PrintMessage("REPEAT command found: label={} times={}\n".format(label_begin, n_times))
                    
                    if label_begin is not None and label_begin in self.mem.labels:
                        start_line = self.mem.labels[label_begin]
                        #App.Console.PrintMessage("REPEAT label {} found at line {}\n".format(label_begin, start_line))
                        for _ in range(n_times):
                            # reset line to start_line and process until we reach the label_end or original line
                            
                            saved_line = self.line
                            self.line = start_line

                            self.mem.queue.append(saved_line-1)
                           
                            processGcode()
                            self.line = saved_line  # restore original line after repeat
                        pass
                    else:
                        App.Console.PrintMessage("REPEAT label {} not found\n".format(label_begin))
                        raise Exception("REPEAT label {} not found".format(label_begin))
                
                elif up.startswith("R"):
                    # variable
                    #up.removeprefix("R")
                    number = int(up[1:up.index("=")])
                    value = float(up[up.index("=")+1:])
                    # if not hasattr(fp, "R{}".format(number)):
                    #     App.Console.PrintMessage("Adding property R{} to object\n".format(number))
                    try:
                        #fp.addProperty("App::PropertyFloat", "R{}".format(number), "Gcode", "Variable R{}".format(number))
                        #setattr(fp, "R{}".format(number), value)
                        self.mem.variables["R{}".format(number)] = value
                    except:
                        pass

                    pass  
                else:
                    # other lines may still change position if they contain coords
                    App.Console.PrintMessage("Ignoring line: {}\n".format(ln))
                    if any(t.upper().startswith(("X","Y","Z")) for t in ln.split()):
                        new = parse_xyz(ln, cur)
                        cur = new
        
        
        
        processGcode()

        # store coords for callbacks/picking
        self.rapid_coords = rapid_coords
        self.feed_coords = feed_coords

        # set rapid nodes
        self.rapid_lines.coordIndex.setValue(0)
        self.rapid_points.point.setValues(0, 0, [])
        if rapid_coords:
            self.rapid_points.point.setValues(0, len(rapid_coords), rapid_coords)
            self.rapid_lines.coordIndex.setValues(0, len(rapid_idx), rapid_idx)
            # set single color for rapid group from object's property
            color = getattr(self.Object.ViewObject, "Rapid", getattr(self.Object, "Rapid", (1.0,0.0,0.0)))
            self.rapid_color.rgb.setValues(0, 1, [color])
        else:
            # clear
            self.rapid_points.point.setValues(0, 0, [])
            self.rapid_lines.coordIndex.setValues(0, 0, [])

        # set feed nodes
        self.feed_lines.coordIndex.setValue(0)
        self.feed_points.point.setValues(0, 0, [])
        if feed_coords:
            self.feed_points.point.setValues(0, len(feed_coords), feed_coords)
            self.feed_lines.coordIndex.setValues(0, len(feed_idx), feed_idx)
            color = getattr(self.Object.ViewObject, "Feed", getattr(self.Object, "Feed", (0.0,1.0,0.0)))
            self.feed_color.rgb.setValues(0, 1, [color])
        else:
            self.feed_points.point.setValues(0, 0, [])
            self.feed_lines.coordIndex.setValues(0, 0, [])
            
    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))

        action2 = menu.addAction("Simulate Toolpath")
        action2.triggered.connect(lambda: self.startSimulation(vobj))
        return True
    
    def setDeleteOnReject(self, val):
        self.deleteOnReject = val
        return self.deleteOnReject
    
    def setEdit(self, vobj):
        """Open the editor for the Gcode property"""
        App.Gui.activateWorkbench("DraftWorkbench")
        App.Gui.showEdit(vobj.Object, "Gcode")
        self.deleteOnReject = False

    def startSimulation(self, vobj):
        """Start the G-code simulation animation"""
        vp = vobj.Proxy
        vp.animator = GcodeAnimator(vp)
        vp.animator.load_paths(include_rapid=True)
        vp.animator.start(speed_mm_s=20.0)

        control = GcodeAnimationControl(vp.animator)
        #control.show()
        FreeCADGui.Control.showDialog(control)

    def doubleClicked(self, vobj):
        self.setEdit(vobj)
        return True
     
    def getDisplayModes(self, obj):
        "Return a list of display modes."
        modes = ["My_Display_Mode"]
        return modes

    def getDefaultDisplayMode(self):
        "Return the name of the default display mode. It must be defined in getDisplayModes."
        return "My_Display_Mode"

    def setDisplayMode(self, mode):
        return mode

class path(baseOp):
    def __init__(self, obj):
        App.Console.PrintMessage("Initializing path object proxy for: {}\n".format(__class__.__name__))
        super().__init__(obj)
        obj.Proxy = self
    def execute(self, obj):
        return super().execute(obj)
        
    def onChanged(self, fp, prop):
        return super().onChanged(fp, prop)
    
    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        App.Console.PrintMessage("Restoring document for object: {}\n".format(obj.Name))
        self.__init__(obj)

class pathViewProviderProxy(baseOpViewProviderProxy):
    def __init__(self, obj):
        App.Console.PrintMessage("Initializing path view provider proxy for: {}\n".format(__class__.__name__))
        super().__init__(obj)

        self.Object = obj.Object
        obj.Proxy = self
    
    def attach(self, obj):
        App.Console.PrintMessage("Attaching view provider proxy to object: {}\n".format(__class__.__name__))
        self.Object = obj.Object
        return super().attach(obj)
    
    # def setupContextMenu(self, vobj, menu):
    #     return super().setupContextMenu(vobj, menu)
    
    def getDefaultDisplayMode(self):
        return super().getDefaultDisplayMode()
    
    def setDisplayMode(self, mode):
        return super().setDisplayMode(mode)
    
    def getDisplayModes(self, obj):
        return super().getDisplayModes(obj)

    
    
    def setEdit(self, vobj):
        #return super().setEdit(vobj)
        taskPanel = GcodeEditorTaskPanel(vobj.Object)
        FreeCADGui.Control.showDialog(taskPanel)
        
        return True
    
class memory():
    def __init__(self):
        #labels tableau de string et int
        self.labels = {}
        self.queue = deque()
        self.variables = {}

    def addLabel(self, key, value):
        self.labels[key]= value

class GcodeEditorTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Gcode Editor")
        layout = QtGui.QVBoxLayout(self.form)

        self.textEdit = QtGui.QPlainTextEdit()
        self.textEdit.setPlainText(self.obj.Gcode)
        layout.addWidget(self.textEdit)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept(self):
        self.obj.Gcode = self.textEdit.toPlainText()
        FreeCADGui.Control.closeDialog()

    def reject(self):
        FreeCADGui.Control.closeDialog()

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return int(QtGui.QDialogButtonBox.Ok |
                   QtGui.QDialogButtonBox.Apply |
                  QtGui.QDialogButtonBox.Cancel)
    

    
class GcodeAnimator:
    """
    Simule le parcours d'usinage en déplaçant un marqueur (sphere) le long des segments
    feed (optionnellement rapid). Utilise QTimer (PySide2) pour l'animation.
    Usage:
      anim = GcodeAnimator(view_provider)
      anim.load_paths(include_rapid=False)   # lit les listes du view provider
      anim.start(speed_mm_s=20.0)
      anim.pause()
      anim.stop()
      anim.step()                            # avance d'un pas de timer
    """
    def __init__(self, view_provider):
        from PySide2 import QtCore
        self.vp = view_provider
        self.timer = QtCore.QTimer()
        self.timer.setInterval(30)  # ms, ~33 FPS default
        self.timer.timeout.connect(self._on_timer)
        self.speed = 20.0  # mm / sec
        self.include_rapid = False

        # animation state
        self.segments = []      # list of (p0,p1) tuples
        self.seg_index = 0
        self.seg_pos = 0.0      # distance along current segment
        self.seg_len = 0.0
        self.running = False

        # create a marker in the scene (small sphere)
        self._create_marker()

    def _create_marker(self):
        # marker group: switch to show/hide
        self.marker_switch = coin.SoSwitch()
        self.marker_switch.whichChild = coin.SO_SWITCH_NONE

        self.marker_sep = coin.SoSeparator()
        self.marker_trans = coin.SoTranslation()
        self.marker_color = coin.SoBaseColor()
        self.marker_sphere = coin.SoSphere()
        self.marker_sphere.radius = 1.0

        # default color yellow
        self.marker_color.rgb.setValues(0,1,[(1.0,1.0,0.0)])

        self.marker_sep.addChild(self.marker_trans)
        self.marker_sep.addChild(self.marker_color)
        self.marker_sep.addChild(self.marker_sphere)
        self.marker_switch.addChild(self.marker_sep)

        # attach to view provider display group if available
        try:
            self.vp.my_displaymode.addChild(self.marker_switch)
        except Exception:
            pass

    def load_paths(self, include_rapid=False):
        """
        Construit la liste de segments à partir des feed_coords (et éventuellement rapid_coords)
        en respectant l'ordre d'origine du programme si disponible (self.vp.ordered_segments).
        """
        self.include_rapid = include_rapid
        segs = []
        vp = self.vp
        # prefer ordered_segments if provided by the view provider (keeps original program order)
        if hasattr(vp, "ordered_segments") and vp.ordered_segments:
            for typ, a, b in vp.ordered_segments:
                if typ == "rapid" and not include_rapid:
                    continue
                segs.append((a, b))
        else:
            # fallback: keep previous behavior (rapid then feed)
            if include_rapid and hasattr(vp, "rapid_coords"):
                rc = getattr(vp, "rapid_coords") or []
                for i in range(0, len(rc), 2):
                    if i+1 < len(rc):
                        segs.append((rc[i], rc[i+1]))
            if hasattr(vp, "feed_coords"):
                fc = getattr(vp, "feed_coords") or []
                for i in range(0, len(fc), 2):
                    if i+1 < len(fc):
                        segs.append((fc[i], fc[i+1]))
        self.segments = segs
        self.stop()  # reset indices

    def start(self, speed_mm_s=20.0):
        self.speed = float(speed_mm_s)
        if not self.segments:
            self.load_paths(self.include_rapid)
        if not self.segments:
            return
        self.running = True
        # initialize first segment
        self.seg_index = 0
        self._prepare_segment(0)
        self.marker_switch.whichChild = 0  # show marker
        self.timer.start()

    def pause(self):
        self.running = False
        self.timer.stop()

    def stop(self):
        self.pause()
        self.seg_index = 0
        self.seg_pos = 0.0
        self.seg_len = 0.0
        # hide marker
        try:
            self.marker_switch.whichChild = coin.SO_SWITCH_NONE
        except Exception:
            pass

    def step(self):
        """Avance d'un tick (utile pour debug ou pas-à-pas)."""
        if not self.segments:
            return
        self._on_timer()

    def set_speed(self, speed_mm_s):
        self.speed = float(speed_mm_s)

    def _prepare_segment(self, idx):
        if idx < 0 or idx >= len(self.segments):
            self.seg_len = 0.0
            return
        p0, p1 = self.segments[idx]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dz = p1[2] - p0[2]
        self.seg_len = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.seg_pos = 0.0
        self._set_marker_position(p0)

    def _set_marker_position(self, point):
        # set translation to point (x,y,z)
        try:
            self.marker_trans.translation.setValue(point[0], point[1], point[2])
        except Exception:
            pass

    def _on_timer(self):
        # single step of animation based on timer interval and speed
        if not self.running or not self.segments or self.seg_index >= len(self.segments):
            self.stop()
            return

        interval_s = max(0.001, self.timer.interval() / 1000.0)
        distance = self.speed * interval_s

        # ensure current segment prepared
        if self.seg_len <= 0.0:
            self._prepare_segment(self.seg_index)

        while distance > 0 and self.seg_index < len(self.segments):
            p0, p1 = self.segments[self.seg_index]
            if self.seg_len <= 1e-12:
                # zero-length segment -> advance
                self.seg_index += 1
                if self.seg_index < len(self.segments):
                    self._prepare_segment(self.seg_index)
                continue

            remaining = self.seg_len - self.seg_pos
            if distance < remaining:
                # advance within current segment
                t = (self.seg_pos + distance) / self.seg_len
                x = p0[0] + (p1[0]-p0[0]) * t
                y = p0[1] + (p1[1]-p0[1]) * t
                z = p0[2] + (p1[2]-p0[2]) * t
                self.seg_pos += distance
                self._set_marker_position((x,y,z))
                distance = 0
            else:
                # jump to end of segment
                self._set_marker_position(p1)
                distance -= remaining
                self.seg_index += 1
                if self.seg_index < len(self.segments):
                    self._prepare_segment(self.seg_index)
                else:
                    # finished all segments
                    self.stop()
                    return

    def is_running(self):
        return self.running

class GcodeAnimationControl():
    """Interface graphique pour contrôler GcodeAnimator"""
    def __init__(self, animator, parent=None):
        #super(GcodeAnimationControl, self).__init__(parent)
        self.animator = animator
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Animation Control")
        
        # Layout principal vertical
        layout = QtGui.QVBoxLayout(self.form)
        
        # Boutons de contrôle dans un layout horizontal
        btnLayout = QtGui.QHBoxLayout()
        
        # Bouton Play
        self.playBtn = QtGui.QPushButton()
        self.playBtn.setIcon(QtGui.QIcon(":/icons/media-playback-start.svg"))
        self.playBtn.setToolTip("Play")
        self.playBtn.clicked.connect(self.play)
        
        # Bouton Pause
        self.pauseBtn = QtGui.QPushButton()
        self.pauseBtn.setIcon(QtGui.QIcon(":/icons/media-playback-pause.svg"))
        self.pauseBtn.setToolTip("Pause")
        self.pauseBtn.clicked.connect(self.pause)
        
        # Bouton Stop
        self.stopBtn = QtGui.QPushButton()
        self.stopBtn.setIcon(QtGui.QIcon(":/icons/media-playback-stop.svg"))
        self.stopBtn.setToolTip("Stop")
        self.stopBtn.clicked.connect(self.stop)
        
        # Bouton Step
        self.stepBtn = QtGui.QPushButton()
        self.stepBtn.setIcon(QtGui.QIcon(":/icons/media-skip-forward.svg"))
        self.stepBtn.setToolTip("Single Step")
        self.stepBtn.clicked.connect(self.step)
        
        # Contrôle de vitesse
        speedLayout = QtGui.QHBoxLayout()
        speedLayout.addWidget(QtGui.QLabel("Speed:"))
        self.speedSpinBox = QtGui.QDoubleSpinBox()
        self.speedSpinBox.setRange(0.1, 1000.0)
        self.speedSpinBox.setValue(self.animator.speed)
        self.speedSpinBox.setSuffix(" mm/s")
        self.speedSpinBox.valueChanged.connect(self.speedChanged)
        speedLayout.addWidget(self.speedSpinBox)
        
        # Include Rapid moves checkbox
        self.rapidCheckBox = QtGui.QCheckBox("Include Rapid Moves")
        self.rapidCheckBox.setChecked(self.animator.include_rapid)
        self.rapidCheckBox.stateChanged.connect(self.rapidChanged)
        
        # Ajouter les widgets aux layouts
        btnLayout.addWidget(self.playBtn)
        btnLayout.addWidget(self.pauseBtn)
        btnLayout.addWidget(self.stopBtn)
        btnLayout.addWidget(self.stepBtn)
        
        layout.addLayout(btnLayout)
        layout.addLayout(speedLayout)
        layout.addWidget(self.rapidCheckBox)
        
        # Timer pour mettre à jour l'état des boutons
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.updateButtons)
        self.updateTimer.start(100)  # 10 Hz
        
        self.updateButtons()
    
    def play(self):
        """Démarre ou reprend l'animation"""
        if not self.animator.is_running():
            self.animator.start(self.speedSpinBox.value())
        self.updateButtons()
    
    def pause(self):
        """Met en pause l'animation"""
        self.animator.pause()
        self.updateButtons()
    
    def stop(self):
        """Arrête l'animation"""
        self.animator.stop()
        self.updateButtons()
    
    def step(self):
        """Avance d'un pas"""
        self.animator.step()
        self.updateButtons()
    
    def speedChanged(self, value):
        """Appelé quand la vitesse change"""
        self.animator.set_speed(value)
    
    def rapidChanged(self, state):
        """Appelé quand la case Include Rapid change"""
        include_rapid = (state == QtCore.Qt.Checked)
        self.animator.include_rapid = include_rapid
        self.animator.load_paths(include_rapid)
        
    def updateButtons(self):
        """Met à jour l'état des boutons selon l'état de l'animation"""
        running = self.animator.is_running()
        self.playBtn.setEnabled(not running)
        self.pauseBtn.setEnabled(running)
        self.stopBtn.setEnabled(running)
        self.stepBtn.setEnabled(not running)
    
    def closeEvent(self, event):
        """Arrête l'animation quand on ferme la fenêtre"""
        self.animator.stop()
        self.updateTimer.stop()
        #super(GcodeAnimationControl, self).closeEvent(event)

    def accept(self):
        self.stop()
        FreeCADGui.Control.closeDialog()
        return True
    
    def reject(self):
        self.stop()
        FreeCADGui.Control.closeDialog()
        return False
    
def create():
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument() 
    obj = doc.addObject("App::FeaturePython","Test")

    baseOp(obj)
    #obj.Gcode ="G0 X0 Y-20 Z50\nG0 Z2\nG1 Z0 F500\nG1 Y-10\nG3 X-10 Y0 I-10 J0\nG1 X-48\nG2 X-50 Y2 I0 J2\nG1 Y20\nG91\nG1 X5\nG0 Z50\nREPEAT LABEL1 P=2\n"
    
    obj.Gcode ="R1=10\nG0 X0 Y0 Z10\nG1 Z0 F500\nLABEL1:\nG91\nG1 Z-2\nG90\nG1 X10 Y0\nG1 X10 Y10\nG1 X0 Y10\nG1 X0 Y0\nREPEAT LABEL1 P=R1\nG0 Z10\n"
    baseOpViewProviderProxy(obj.ViewObject)

    vp = obj.ViewObject.Proxy
    vp.animator = GcodeAnimator(vp)
    vp.animator.load_paths(include_rapid=True)

    vp.animator.start(speed_mm_s=20.0)

    doc.recompute()

if __name__ == "__main__":	
    create()