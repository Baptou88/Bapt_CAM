import math
import FreeCAD as App

def getFirstPoint(wire):
    """
    Get the indice of the first point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    edges = wire.Edges
    if len(edges) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if edges[0].Vertexes[-1].Point.distanceToPoint(edges[1].Vertexes[0].Point) <  1e-6 :
        return 0
    elif edges[0].Vertexes[-1].Point.distanceToPoint(edges[1].Vertexes[-1].Point) <  1e-6 :
        return 0
    elif edges[0].Vertexes[0].Point.distanceToPoint(edges[1].Vertexes[0].Point) <  1e-6 :
        return -1   
    elif edges[0].Vertexes[0].Point.distanceToPoint(edges[1].Vertexes[-1].Point) <  1e-6 :
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0

def getLastPoint(wire):
    """
    Get the indice of the last point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    edges = wire.Edges
    if len(edges) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if edges[-1].Vertexes[-1].Point.distanceToPoint(edges[-2].Vertexes[0].Point) <  1e-6 :
        return 0
    elif edges[-1].Vertexes[-1].Point.distanceToPoint(edges[-2].Vertexes[-1].Point) <  1e-6 :
        return 0
    elif edges[-1].Vertexes[0].Point.distanceToPoint(edges[-2].Vertexes[0].Point) <  1e-6 :
        return -1   
    elif edges[-1].Vertexes[0].Point.distanceToPoint(edges[-2].Vertexes[-1].Point) <  1e-6 :
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0
    
def edgeToGcode(edge, bonSens=True, current_z=0.0, rapid=False, feed_rate=1000):
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
        if rapid:
            gcode += f"G0 X{start_point.x:.3f} Y{start_point.y:.3f} Z{current_z:.3f}\n"
        else:
            gcode += f"G1 X{start_point.x:.3f} Y{start_point.y:.3f} Z{current_z:.3f} F{feed_rate}\n"

        # Move to end point
        if rapid:
            gcode += f"G0 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f}\n"
        else:
            gcode += f"G1 X{end_point.x:.3f} Y{end_point.y:.3f} Z{current_z:.3f} F{feed_rate}\n"

    elif edge.Curve.TypeId == 'Part::GeomCircle':
        circle = edge.Curve
        center = circle.Center
        radius = circle.Radius

        # Determine start and end angles
        vec_start = start_point.sub(center)
        vec_end = end_point.sub(center)
        angle_start = vec_start.getAngle(App.Vector(1, 0, 0))
        angle_end = vec_end.getAngle(App.Vector(1, 0, 0))

        # Determine direction
        if bonSens:
            if angle_end < angle_start:
                angle_end += 2 * math.pi
            gcode += f"G2 X{end_point.x:.3f} Y{end_point.y:.3f} I{center.x - start_point.x:.3f} J{center.y - start_point.y:.3f} F{feed_rate}\n"
        else:
            if angle_start < angle_end:
                angle_start += 2 * math.pi
            gcode += f"G3 X{end_point.x:.3f} Y{end_point.y:.3f} I{center.x - start_point.x:.3f} J{center.y - start_point.y:.3f} F{feed_rate}\n"
    elif edge.CurveType == 'BSplineCurve': # More specific BSpline handling if possible
        raise NotImplementedError(f"Edge type {edge.Curve.TypeId} not implemented in G-code generation.")
        try:
            bs_points = []
            num_samples = 20 # Or from a property
            for i in range(num_samples + 1):
                param = edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * i / num_samples
                pt_on_curve = edge.valueAt(param)
                bs_points.append(App.Vector(pt_on_curve.x, pt_on_curve.y, pass_z))
            if len(bs_points) >=2:
                bspline_at_z = Part.BSplineCurve()
                bspline_at_z.interpolate(bs_points)
                edges_for_current_pass_z.append(bspline_at_z.toShape())
        except Exception as e_bspline:
            App.Console.PrintError(f"Failed to transform BSpline for pass Z={pass_z}: {e_bspline}\n")
    else:
        raise NotImplementedError(f"Edge type {edge.Curve.TypeId} not implemented in G-code generation.")
    return gcode