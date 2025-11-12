import FreeCAD as App

def getFirstPoint(contourList):
    """
    Get the indice of the first point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    if len(contourList) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if contourList[0].Vertexes[-1].Point.distanceToPoint(contourList[1].Vertexes[0].Point) <  1e-6 :
        return 0
    elif contourList[0].Vertexes[-1].Point.distanceToPoint(contourList[1].Vertexes[-1].Point) <  1e-6 :
        return 0
    elif contourList[0].Vertexes[0].Point.distanceToPoint(contourList[1].Vertexes[0].Point) <  1e-6 :
        return -1   
    elif contourList[0].Vertexes[0].Point.distanceToPoint(contourList[1].Vertexes[-1].Point) <  1e-6 :
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0

def getLastPoint(contourList):
    """
    Get the indice of the last point in a contour list.
    :param contourList: List of contours, where each contour is a list of edges.
    :return: 0 or -1 depending on the orientation of the contour.
    """
    if len(contourList) < 2:
        App.Console.PrintError("Error: Contour list must contain at least two contours.\n")
        return 0  # Not enough points to determine orientation

    if contourList[-1].Vertexes[-1].Point.distanceToPoint(contourList[-2].Vertexes[0].Point) <  1e-6 :
        return 0
    elif contourList[-1].Vertexes[-1].Point.distanceToPoint(contourList[-2].Vertexes[-1].Point) <  1e-6 :
        return 0
    elif contourList[-1].Vertexes[0].Point.distanceToPoint(contourList[-2].Vertexes[0].Point) <  1e-6 :
        return -1   
    elif contourList[-1].Vertexes[0].Point.distanceToPoint(contourList[-2].Vertexes[-1].Point) <  1e-6 :
        return -1
    else:
        App.Console.PrintError("Error: Contour edges are not connected properly.\n")
        return 0