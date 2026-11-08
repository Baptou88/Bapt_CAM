
import FreeCAD as App
import Part
from utils.GcodeWriter import GcodeWriter


def getFirstPoint(edges):
    """
    Get the indice of the first point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    # edges = wire.Edges

    if len(edges) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if edges[0].Vertexes[-1].Point.distanceToPoint(edges[1].Vertexes[0].Point) < 1e-6:
        return 0
    elif edges[0].Vertexes[-1].Point.distanceToPoint(edges[1].Vertexes[-1].Point) < 1e-6:
        return 0
    elif edges[0].Vertexes[0].Point.distanceToPoint(edges[1].Vertexes[0].Point) < 1e-6:
        return -1
    elif edges[0].Vertexes[0].Point.distanceToPoint(edges[1].Vertexes[-1].Point) < 1e-6:
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0


def getLastPoint(edges):
    """
    Get the indice of the last point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    # edges = wire.Edges

    if len(edges) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if edges[-1].Vertexes[-1].Point.distanceToPoint(edges[-2].Vertexes[0].Point) < 1e-6:
        return 0
    elif edges[-1].Vertexes[-1].Point.distanceToPoint(edges[-2].Vertexes[-1].Point) < 1e-6:
        return 0
    elif edges[-1].Vertexes[0].Point.distanceToPoint(edges[-2].Vertexes[0].Point) < 1e-6:
        return -1
    elif edges[-1].Vertexes[0].Point.distanceToPoint(edges[-2].Vertexes[-1].Point) < 1e-6:
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0


def edgeToGcode(edge, bonSens: bool = True, current_z: float = 0.0, rapid: bool = False, feed_rate: float = None, gcodeWriter: GcodeWriter = None):
    """
    Convert an edge to G-code.
    :param edge: The edge to convert.
    :param bonSens: Boolean indicating the orientation of the edge.
    :param current_z: The current Z height.
    :param rapid: Boolean indicating if the movement is rapid (G0) or linear (G1).
    :return: G-code string for the edge.
    """
    gcode = ""

    if bonSens:
        start_point = edge.Vertexes[0].Point
        end_point = edge.Vertexes[-1].Point
    else:
        start_point = edge.Vertexes[-1].Point
        end_point = edge.Vertexes[0].Point

    if edge.Curve.TypeId == 'Part::GeomLine':
        # Line handling can be added here if needed
        # Move to start point
        # if rapid:
        #     gcode += f"G0 X{start_point.x:.3f} Y{start_point.y:.3f} Z{current_z:.3f}\n"
        # else:
        #     gcode += f"G1 X{start_point.x:.3f} Y{start_point.y:.3f} Z{current_z:.3f} F{feed_rate}\n"

        # Move to end point
        if rapid:
            gcode += f"G0 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f}\n"
        else:
            gcode += f"G1 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f} "
            gcode += f"F{feed_rate}\n" if feed_rate is not None else "\n"
        if gcodeWriter:
            gcodeWriter.linearMove({'X': end_point.x, 'Y': end_point.y, 'Z': current_z}, feed=feed_rate, rapid=rapid)

    elif edge.Curve.TypeId == 'Part::GeomCircle':
        circle = edge.Curve
        center = circle.Center

        # 3. Prendre en compte l'orientation de l'axe du cercle
        # Si l'axe pointe vers le bas (z < 0), inverser la logique
        axis_z = circle.Axis.z

        # Determine direction
        # if  u2-u1 > math.pi :
        #     # if angle_end < angle_start:
        #     #     angle_end += 2 * math.pi
        #     if  is_offset_inward:
        #         arc = "G3"  # Clockwise
        #     else:
        #         arc = "G2"
        # else:
        #     if not is_offset_inward:
        #         arc = "G3"
        #     else:
        #         arc = "G2"
        # if edge.Curve.Axis.z > 0:
        #     arc = "G2" if arc == "G3" else "G3"

        # # Normaliser l'angle dans [0, 2π]
        # if arc_angle < 0:
        #     arc_angle += 2 * math.pi

        # 5. Déterminer si c'est CCW ou CW dans le plan XY
        # Logique de base : cross_product.z * axis_z > 0 → CCW, sinon CW
        is_ccw = (axis_z) > 0

        # App.Console.PrintMessage(f'O {edge.Orientation} dir {edge.Curve.Axis} {bonSens} u1:{u1:.3f} u2:{u2:.3f} {cross_product.z} {axis_z} {is_offset_inward}\n')

        # 6. Ajuster selon l'angle de l'arc
        # Si l'arc fait plus de 180°, le produit vectoriel peut être trompeur
        # if arc_angle > math.pi:
        #     # Pour les arcs > 180°, vérifier le point médian
        #     mid_param = (u1 + u2) / 2
        #     mid_point = edge.valueAt(mid_param)
        #     vec_mid = mid_point.sub(center)

        #     # Recalculer avec le point médian
        #     cross_mid = vec_start.cross(vec_mid)
        #     is_ccw = (cross_mid.z * axis_z) > 0

        if not bonSens:
            is_ccw = not is_ccw
        if is_ccw:
            arc = "G3"  # Counter-clockwise
        else:
            arc = "G2"  # Clockwise

        gcode += f"{arc} X{end_point.x:.3f} Y{end_point.y:.3f} I{center.x - start_point.x:.3f} J{center.y - start_point.y:.3f} "
        gcode += f"F{feed_rate}\n" if feed_rate is not None else "\n"
        if gcodeWriter:
            gcodeWriter.arcMove({'X': end_point.x, 'Y': end_point.y, 'Z': current_z, 'CCW': is_ccw, 'I': center.x - start_point.x, 'J': center.y - start_point.y}, feed=feed_rate)

    elif edge.Curve.TypeId == 'Part::GeomBSplineCurve':  # More specific BSpline handling if possible
        # raise NotImplementedError(f"Edge type {edge.Curve.TypeId} not implemented in G-code generation.")
        gcodeWriter.comment(f"Warning: Edge type {edge.Curve.TypeId} partially implemented in G-code generation.")
        try:
            bs_points = []
            num_samples = 20  # Or from a property
            for i in range(num_samples + 1):
                param = edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * i / num_samples
                pt_on_curve = edge.valueAt(param)
                bs_points.append(App.Vector(pt_on_curve.x, pt_on_curve.y, current_z))
            if len(bs_points) >= 2:
                bspline_at_z = Part.BSplineCurve()
                bspline_at_z.interpolate(bs_points)
                if gcodeWriter:
                    gcodeWriter.linearMove({'X': end_point.x, 'Y': end_point.y, 'Z': current_z}, feed=feed_rate, rapid=rapid)
        except Exception as e_bspline:
            App.Console.PrintError(f"Failed to transform BSpline for Z={current_z}: {e_bspline}\n")
    elif edge.Curve.TypeId == 'Part::GeomOffsetCurve':
        basis = edge.Curve.BasisCurve
        if basis.TypeId == 'Part::GeomLine':
            # Offset d'une ligne = ligne parallèle → G1
            if rapid:
                gcode += f"G0 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f}\n"
            else:
                gcode += f"G1 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f} "
                gcode += f"F{feed_rate}\n" if feed_rate is not None else "\n"
            if gcodeWriter:
                gcodeWriter.linearMove({'X': end_point.x, 'Y': end_point.y, 'Z': current_z}, feed=feed_rate, rapid=rapid)

        elif basis.TypeId == 'Part::GeomCircle':
            # Offset d'un cercle = cercle concentrique → G2/G3, même centre
            center = basis.Center
            axis_z = basis.Axis.z
            is_ccw = axis_z > 0
            if not bonSens:
                is_ccw = not is_ccw
            arc = "G3" if is_ccw else "G2"
            gcode += f"{arc} X{end_point.x:.3f} Y{end_point.y:.3f} I{center.x - start_point.x:.3f} J{center.y - start_point.y:.3f} "
            gcode += f"F{feed_rate}\n" if feed_rate is not None else "\n"
            if gcodeWriter:
                gcodeWriter.arcMove({'X': end_point.x, 'Y': end_point.y, 'Z': current_z, 'CCW': is_ccw, 'I': center.x - start_point.x, 'J': center.y - start_point.y}, feed=feed_rate)

        else:
            # Autre courbe de base → discrétisation en segments G1
            num_samples = 20
            span = edge.LastParameter - edge.FirstParameter
            for i in range(1, num_samples + 1):
                t = i / num_samples
                if bonSens:
                    param = edge.FirstParameter + span * t
                else:
                    param = edge.LastParameter - span * t
                pt = edge.valueAt(param)
                gcode += f"G1 X{pt.x:.3f} Y{pt.y:.3f} Z{current_z:.3f} "
                gcode += f"F{feed_rate}\n" if feed_rate is not None else "\n"
                if gcodeWriter:
                    gcodeWriter.linearMove({'X': pt.x, 'Y': pt.y, 'Z': current_z}, feed=feed_rate, rapid=False)
    else:
        gcodeWriter.comment(f"Warning: Edge type {edge.Curve.TypeId} not implemented in G-code generation.")
        raise NotImplementedError(f"Edge type {edge.Curve.TypeId} not implemented in G-code generation.")
    return gcode


def shiftWire(wire: Part.Wire, new_start_point: App.Vector) -> Part.Wire:
    """
    Reconstruct a wire starting from a specified point.
    This function takes a wire and a new starting point, then rebuilds the wire
    by reordering its edges so that the wire begins at the specified point.
    If the starting point lies on an edge (not at a vertex), that edge is split
    at the point, with the portion after the point becoming the first edge.
    Args:
        wire (Part.Wire): The wire to be shifted/reordered.
        new_start_point (App.Vector): The point where the reconstructed wire should start.
                                       Must be on or very close to the wire (tolerance: 1e-6).
    Returns:
        Part.Wire: A new wire with edges reordered to start from new_start_point.
                   If new_start_point lies on an edge, that edge is trimmed accordingly.
    Raises:
        Logs critical errors to console if edge operations fail, but continues processing
        with the original edge.
    Note:
        - Tolerance for point matching: 1e-6 units
        - If new_start_point is not found on the wire, the original wire is returned unchanged
        - The function handles edge orientation based on connectivity with the next edge
    """
    """reconstruit le wire en commençant par new_start_point"""
    first_edge = []
    next_edges = []

    i = 0
    for i, e in enumerate(wire.Edges):
        # if edge.isSame(e):
        try:
            if e.distToShape(Part.Vertex(new_start_point))[0] < 1e-6:
                # parameter = edge.parameterAt(Part.Vertex(new_start_point)) #FIXME
                parameter = e.Curve.parameter(new_start_point)  # FIXME
                App.Console.PrintMessage(f'parameter: {parameter}\n')
                next_edge = wire.Edges[(i + 1) % len(wire.Edges)]
                if e.Vertexes[-1].Point.distanceToPoint(next_edge.Vertexes[0].Point) < 1e-6 or \
                   e.Vertexes[-1].Point.distanceToPoint(next_edge.Vertexes[-1].Point) < 1e-6:

                    first = e.Curve.trim(e.FirstParameter, parameter).toShape()
                    second = e.Curve.trim(parameter, e.LastParameter).toShape()
                else:
                    first = e.Curve.trim(parameter, e.LastParameter).toShape()
                    second = e.Curve.trim(e.FirstParameter, parameter).toShape()
                first_edge.append(first)
                next_edges.append(second)
                break
            else:
                first_edge.append(e)
        except Exception as e:
            App.Console.PrintCritical(f"shiftWire: {e}\n")
            first_edge.append(e)
            continue

    for j in range(i + 1, len(wire.Edges)):
        next_edges.append(wire.Edges[j])
    # App.Console.PrintMessage(f'shiftWire: found start at edge {i}\n')
    # App.Console.PrintMessage(f'{len(next_edges)} {len(first_edge)}\n')
    wires = next_edges + first_edge
    for i, edge in enumerate(wires):
        print(f"Edge {i}: {edge.Vertexes[0].Point} to {edge.Vertexes[-1].Point}")

    return Part.Wire(wires)
