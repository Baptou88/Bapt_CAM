# from Mod/Cam/Path/Op/Util.py by sliptonic"""

# utility functions for offset operations"""

import math
import enum
import FreeCAD as App
import Part

# class enum Side:
#     None = 0
#     Left = 1
#     Right = 2


class Side(enum.Enum):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    INSIDE = 3
    OUTSIDE = 4

    def __repr__(self):
        return self.name


def material_side_to_tool_side(material_side: str) -> Side:
    """Retourne le côté outil opposé au côté matière.

    Convention actuelle:
    - matière à droite du parcours -> outil à gauche
    - matière à gauche du parcours -> outil à droite
    """
    if material_side == "Droite":
        return Side.LEFT
    if material_side == "Gauche":
        return Side.RIGHT
    return Side.NONE


def offset_sign_from_material_side(material_side: str) -> float:
    """Retourne le signe de décalage 2D à appliquer selon le côté matière."""
    return 1.0 if material_side == "Droite" else -1.0


def is_conventional(machining_mode: str) -> bool:
    """Indique si le sens de parcours doit être inversé.

    Climb conserve le sens du wire courant, Conventional l'inverse.
    """
    return machining_mode == "Conventional"


def offset_sign_from_side(side: Side) -> float:
    """Retourne le signe de décalage pour makeOffset2D selon le côté outil."""
    if side in (Side.RIGHT, Side.OUTSIDE):
        return 1.0
    if side in (Side.LEFT, Side.INSIDE):
        return -1.0
    return 1.0


def _circle_offset_radius(edge: Part.Edge, curve: Part.Circle, distance: float, forward: bool, side: Side) -> float:
    """Calcule le nouveau rayon pour un cercle/arc selon côté et sens de parcours.

    La décision intérieur/extérieur est déduite localement:
    - tangente au point de départ (dans le sens de parcours demandé)
    - normale gauche de cette tangente
    - comparaison avec le radial (centre -> point)
    """
    if side in (Side.NONE,):
        return curve.Radius

    p_start = edge.valueAt(edge.FirstParameter)
    tangent = edge.tangentAt(edge.FirstParameter)
    tangent = App.Vector(tangent.x, tangent.y, 0)
    if tangent.Length < 1e-9:
        return curve.Radius

    if not forward:
        tangent = tangent * -1.0
    tangent.normalize()

    left_normal = App.Vector(-tangent.y, tangent.x, 0)

    radial = App.Vector(
        p_start.x - curve.Center.x,
        p_start.y - curve.Center.y,
        0,
    )
    if radial.Length < 1e-9:
        return curve.Radius
    radial.normalize()

    # True si la gauche du parcours pointe vers l'extérieur du cercle.
    left_is_outside = left_normal.dot(radial) > 0

    if side == Side.INSIDE:
        go_outside = False
    elif side == Side.OUTSIDE:
        go_outside = True
    elif side == Side.LEFT:
        go_outside = left_is_outside
    elif side == Side.RIGHT:
        go_outside = not left_is_outside
    else:
        go_outside = False

    new_radius = curve.Radius + distance if go_outside else curve.Radius - distance
    # Evite les rayons nuls/négatifs qui rendent l'arc invalide.
    return max(new_radius, 1e-9)


def _project_point_on_circle_radius(point: App.Vector, center: App.Vector, new_radius: float) -> App.Vector:
    """Projette un point d'un cercle sur un nouveau rayon, en conservant la direction radiale."""
    radial = App.Vector(point.x - center.x, point.y - center.y, point.z - center.z)
    if radial.Length < 1e-9:
        return App.Vector(center.x + new_radius, center.y, center.z)
    radial.normalize()
    return App.Vector(
        center.x + radial.x * new_radius,
        center.y + radial.y * new_radius,
        center.z + radial.z * new_radius,
    )


def _wire_start_and_tangent_xy(wire: Part.Wire):
    """Retourne le point de départ et la tangente XY d'un wire."""
    edges = list(wire.Edges)
    if not edges:
        return None, None
    if len(edges) == 1:
        idx_first = 0
    else:
        idx_first = 0
        first = edges[0]
        if len(edges) > 1:
            last = first.valueAt(first.LastParameter)
            second = edges[1]
            if not pointsCoincident(last, second.valueAt(second.FirstParameter)) and not pointsCoincident(last, second.valueAt(second.LastParameter)):
                first = flipEdge(first)
                edges[0] = first
        if len(edges) > 1:
            # Recalcule après orientation initiale.
            if pointsCoincident(edges[0].valueAt(edges[0].LastParameter), edges[1].valueAt(edges[1].FirstParameter)):
                idx_first = 0
            else:
                idx_first = 0
    first_edge = edges[0]
    start_pt = first_edge.Vertexes[idx_first].Point
    if idx_first == 0:
        tangent = first_edge.tangentAt(first_edge.FirstParameter)
    else:
        tangent = first_edge.tangentAt(first_edge.LastParameter) * -1.0
    tangent_xy = App.Vector(tangent.x, tangent.y, 0)
    if tangent_xy.Length > 1e-9:
        tangent_xy.normalize()
    else:
        tangent_xy = App.Vector(1, 0, 0)
    return start_pt, tangent_xy


def offsetWire(wire: Part.Wire, distance: float, forward: bool, side: Side = Side.NONE) -> Part.Wire:
    """
    Helper function to offset a wire by a given distance in the specified direction and side.
    Keyword arguments:
    side -- cote usinage
    """

    # App.Console.PrintMessage(f'Offsetting line  {side} {forward}\n')

    # wire = orientwire(wire, forward=forward)

    # 1: on test si wire contient 1 seul edge
    if len(wire.Edges) == 1:
        edge = wire.Edges[0]
        curve = edge.Curve
        if isinstance(curve, Part.Line) or isinstance(curve, Part.LineSegment):
            # Pour une ligne, on peut simplement décaler la ligne
            App.Console.PrintMessage(f'Offsetting line with direction {curve.Direction} \n')
            App.Console.PrintMessage(f'Offsetting line  {edge.Vertexes[0].Point} -> {edge.Vertexes[-1].Point} \n')
            direction = curve.Direction

            if side == Side.RIGHT:
                offset_direction = direction.cross(App.Vector(0, 0, 1)).normalize()
            else:
                offset_direction = direction.cross(App.Vector(0, 0, -1)).normalize()

            App.Console.PrintMessage(f'{offset_direction}\n')
            offset_vector = offset_direction.multiply(distance)
            new_start = edge.Vertexes[0].Point.add(offset_vector)
            new_end = edge.Vertexes[-1].Point.add(offset_vector)
            if not forward:
                # Le sens de parcours dépend uniquement de `forward`, jamais du côté.
                new_start, new_end = new_end, new_start
            new_line = Part.LineSegment(new_start, new_end)
            return Part.Wire([new_line.toShape()])

        elif isinstance(curve, Part.Circle) and wire.isClosed():
            # Cercle complet: choix intérieur/extérieur via côté + sens de parcours.
            new_radius = _circle_offset_radius(edge, curve, distance, forward, side)
            new_circle = Part.Circle(curve.Center, curve.Axis, new_radius)
            new_edge = Part.Edge(new_circle)
            if not forward:
                new_edge = new_edge.reversed()
            return Part.Wire([new_edge])

        elif isinstance(curve, Part.Circle) and not wire.isClosed():
            # Arc de cercle: même logique intérieur/extérieur que cercle complet.
            new_radius = _circle_offset_radius(edge, curve, distance, forward, side)

            # Re-construire l'arc via 3 points évite les erreurs liées aux paramètres.
            p_start = edge.valueAt(edge.FirstParameter)
            p_mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) * 0.5)
            p_end = edge.valueAt(edge.LastParameter)

            new_start = _project_point_on_circle_radius(p_start, curve.Center, new_radius)
            new_mid = _project_point_on_circle_radius(p_mid, curve.Center, new_radius)
            new_end = _project_point_on_circle_radius(p_end, curve.Center, new_radius)

            new_edge = Part.ArcOfCircle(new_start, new_mid, new_end).toShape()
            if not forward:
                new_edge = new_edge.reversed()
            return Part.Wire([new_edge])

        elif isinstance(curve, Part.Ellipse):
            # Pour une ellipse, on peut ajuster les deux rayons
            center = curve.Center
            major_radius = curve.MajorRadius
            minor_radius = curve.MinorRadius
            if forward:
                new_major_radius = major_radius + distance
                new_minor_radius = minor_radius + distance
            else:
                new_major_radius = major_radius - distance
                new_minor_radius = minor_radius - distance
            new_ellipse = Part.Ellipse(center, curve.Axis, new_major_radius, new_minor_radius)
            return Part.Wire([new_ellipse.toShape()])

        else:
            raise NotImplementedError("Type de courbe non supporté pour l'offset.")

    # raise NotImplementedError("Offset de wire avec plusieurs edges n'est pas encore implémenté.")

    # 2: on test si wire est fermé ou pas

    if wire.isClosed():
        offset_distance = offset_sign_from_side(side) * distance

        wire_offset = wire.makeOffset2D(offset_distance, join=0, fill=False, openResult=False)

        return Part.Wire(orientwire(wire_offset, forward=forward))

    # 3 ...

    wire_offset = wire.makeOffset2D(distance * offset_sign_from_side(side), join=0, fill=False, openResult=True)

    # return Part.Wire(orientwire(wire_offset, forward=not forward))
    return Part.Wire(orientwire(wire_offset, forward=not forward if side in (Side.RIGHT, Side.INSIDE) else forward))  # presque
    pass


def pointsCoincident(p1: App.Vector, p2: App.Vector, tol=1e-6) -> bool:
    return p1.distanceToPoint(p2) < tol


def flipEdge(edge: Part.Edge) -> Part.Edge:
    if type(edge.Curve) is Part.Line and not edge.Vertexes:
        return Part.Edge(Part.Line(edge.valueAt(edge.LastParameter), edge.valueAt(edge.FirstParameter)))

    elif type(edge.Curve) is Part.Line or type(edge.Curve) is Part.LineSegment:
        return Part.Edge(Part.LineSegment(edge.Vertexes[-1].Point, edge.Vertexes[0].Point))

    elif type(edge.Curve) is Part.Circle:
        # Create an inverted circle
        circle = Part.Circle(edge.Curve.Center, -edge.Curve.Axis, edge.Curve.Radius)
        # Rotate the circle appropriately so it starts at edge.valueAt(edge.LastParameter)
        circle.rotate(
            App.Placement(
                circle.Center,
                circle.Axis,
                180 - math.degrees(edge.LastParameter + edge.Curve.AngleXU),
            )
        )
        # Now the edge always starts at 0 and LastParameter is the value range
        arc = Part.Edge(circle, 0, edge.LastParameter - edge.FirstParameter)
        return arc

    elif type(edge.Curve) in [Part.BSplineCurve, Part.BezierCurve]:
        if Part.BSplineCurve is type(edge.Curve):
            spline = edge.Curve
        else:
            spline = edge.Curve.toBSpline()

        mults = spline.getMultiplicities()
        weights = spline.getWeights()
        knots = spline.getKnots()
        poles = spline.getPoles()
        perio = spline.isPeriodic()
        ratio = spline.isRational()
        degree = spline.Degree

        ma = max(knots)
        mi = min(knots)
        knots = [ma + mi - k for k in knots]

        mults.reverse()
        weights.reverse()
        poles.reverse()
        knots.reverse()

        flipped = Part.BSplineCurve()
        flipped.buildFromPolesMultsKnots(poles, mults, knots, perio, degree, weights, ratio)

        return Part.Edge(flipped, ma + mi - edge.LastParameter, ma + mi - edge.FirstParameter)
    elif type(edge.Curve) is Part.OffsetCurve:
        return edge.reversed()
    else:
        raise NotImplementedError(f"flipEdge not implemented for curve type {type(edge.Curve)}")


def flipWire(wire: Part.Wire) -> Part.Wire:
    flipped_edges = [flipEdge(e) for e in reversed(wire.Edges)]
    return Part.Wire(flipped_edges)


def _orientEdges(inEdges: list[Part.Edge]) -> list[Part.Edge]:
    e0 = inEdges[0]
    if len(inEdges) > 1:
        last = e0.valueAt(e0.LastParameter)
        e1 = inEdges[1]
        if not pointsCoincident(last, e1.valueAt(e1.FirstParameter)) and not pointsCoincident(last, e1.valueAt(e1.LastParameter)):
            e0 = flipEdge(e0)
    edges = [e0]
    last = e0.valueAt(e0.LastParameter)
    for e in inEdges[1:]:
        edge = (e if pointsCoincident(last, e.valueAt(e.FirstParameter)) else flipEdge(e))
        edges.append(edge)
        last = edge.valueAt(edge.LastParameter)
    return edges


def orientwire(wire: Part.Wire, forward=True) -> Part.Wire:
    if not forward:
        wire = flipWire(Part.Wire(wire.Edges))
    edges = _orientEdges(list(wire.Edges))
    return Part.Wire(edges)
