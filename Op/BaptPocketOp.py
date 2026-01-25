from collections import deque
import math
from BaptPath import GcodeEditorTaskPanel
import BaptPreferences
import FreeCAD as App
import FreeCADGui as Gui
from Op import BaseOp
from Op.PocketNode import noeud
import Part
from PySide import QtGui, QtCore
import sys
import traceback
import BaptUtilities
from utils import BQuantitySpinBox
from utils import Log as Log
from utils.Contour import getFirstPoint, getLastPoint, shiftWire, edgeToGcode

if True:
    Log.setLevel(Log.Level.DEBUG, Log.thisModule())
else:
    Log.setLevel(Log.Level.INFO, Log.thisModule())

pocketFillMode = ["offset", "offset2", "zigzag", "spirale"]


class PocketOperation(BaseOp.baseOp):
    """
    Opération d'usinage de poche basée sur ContourGeometry.
    Génère un chemin d'usinage à partir du centre avec un facteur de recouvrement.
    """
    initialized = False

    def __init__(self, obj):
        super().__init__(obj)
        self.Type = "PocketOperation"
        self.initProperties(obj)
        obj.Proxy = self
        self.initialized = True
        Log.baptDebug("PocketOperation initialized.")

        Log.baptDebug(f"{isinstance(obj.Proxy, PocketOperation)}\n")

        # try:
        #     a = 1/0
        # except Exception as e:
        #     Log.baptDebug(f"PocketOperation init error: {e}\n")
        #     # exc_type, exc_obj, exc_tb = sys.exc_info()
        #     # Log.baptDebug(f'Line {exc_tb.tb_lineno}\n')

    def initProperties(self, obj):
        obj.addProperty("App::PropertyLink", "Contour", "Pocket", "ContourGeometry de la poche")
        obj.addProperty("App::PropertyFloat", "Overlap", "Pocket", "Facteur de recouvrement (0.1-0.9)").Overlap = 0.5
        obj.addProperty("App::PropertyFloat", "ToolDiameter", "Pocket", "Diamètre outil (mm)").ToolDiameter = 6.0
        obj.addProperty("App::PropertyFloat", "StepDown", "Pocket", "Profondeur de passe (mm)").StepDown = 2.0
        obj.addProperty("App::PropertyFloat", "FinalDepth", "Pocket", "Profondeur finale (mm)").FinalDepth = -10.0

        obj.addProperty("App::PropertyEnumeration", "FillMode", "Pocket", "Mode de remplissage").FillMode = pocketFillMode
        obj.FillMode = pocketFillMode[1]

        obj.addProperty("Part::PropertyPartShape", "Path", "Pocket", "Chemin d'usinage généré")

        obj.addProperty("App::PropertyInteger", "maxGeneration", "Pocket", "Nombre maximum de générations d'offset").maxGeneration = 2

        obj.addProperty("App::PropertyBool", "useMiddleofFirstEdge", "Pocket", "Utiliser le milieu de la première arête").useMiddleofFirstEdge = False
        obj.addProperty("App::PropertyBool", "debugMode", "General", "Activer le mode debug").debugMode = False

        self.installToolProp(obj)

    def onChanged(self, obj, prop):
        Log.baptDebug(f"{prop}")
        if prop in ["Overlap", "ToolDiameter", "StepDown", "FinalDepth", "FillMode", "Contour", "maxGeneration", "useMiddleofFirstEdge"]:
            self.execute(obj)

    def is_shape_valid(self, shape: Part.Shape):
        # Vérifie que la shape est utilisable pour le pocketing
        if not shape:
            return False
        if not hasattr(shape, 'BoundBox') or not shape.BoundBox:
            App.Console.PrintError("PocketOperation: pas de boundBox.\n")
            return False
        if hasattr(shape, 'Wires') and shape.Wires:
            for wire in shape.Wires:
                if wire.isClosed():
                    return True
            return False
        return False

    def collectEdges(self, obj) -> list[Part.Edge]:
        # Collecter toutes les arêtes sélectionnées
        edges = []
        for sub in obj.Edges:
            obj_ref = sub[0]  # L'objet référencé
            sub_names = sub[1]  # Les noms des sous-éléments (arêtes)

            for sub_name in sub_names:
                if "Edge" in sub_name:
                    try:
                        edge = obj_ref.Shape.getElement(sub_name)
                        edges.append(edge)
                        # App.Console.PrintMessage(f"Arête ajoutée: {sub_name} de {obj_ref.Name}\n")
                    except Exception as e:
                        App.Console.PrintError(f"Execute : Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
        # App.Console.PrintMessage(f'nb collecté {len(edges)}\n')
        return edges

    def execute(self, obj):
        # Chercher le parent ContourGeometry dans l'arborescence
        if not self.initialized:
            Log.baptDebug("execute ignored")
            return
        Log.baptDebug("execute")
        try:
            # parent = None
            # for p in obj.InList:
            #     if hasattr(p, "Proxy") and getattr(p.Proxy, "Type", "") == "ContourGeometry":
            #         parent = p
            #         break

            # if not parent or not hasattr(parent, "Shape"):
            #     App.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
            #     obj.Path = None
            #     return

            # shape = parent.Shape

            shape = obj.Contour.Shape if obj.Contour and hasattr(obj.Contour, "Shape") else None

            if not shape:
                App.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
                obj.Shape = None
                return

            if not self.is_shape_valid(shape):
                App.Console.PrintError("PocketOperation: Shape du parent ContourGeometry invalide ou non fermée.\n")
                obj.Path = None
                return

            tool_diam = obj.ToolDiameter
            overlap = obj.Overlap

            # spheres pour marquer le debut du contour
            spheres = []

            # Génération du chemin selon le mode choisi
            if hasattr(obj, 'FillMode') and obj.FillMode == "zigzag":
                path = self.generate_zigzag_path(shape, tool_diam, overlap)

            elif hasattr(obj, 'FillMode') and obj.FillMode == "offset":
                edges = self.collectEdges(obj.Contour)

                path = self.generate_offset_path(edges, tool_diam, overlap, obj.maxGeneration)

                if obj.debugMode:
                    for i in range(len(path)):
                        for j in range(len(path[i].Wires)):
                            edge = path[i].Wires[j].Edges[0]
                            # recupere le premier point
                            start_point = edge.Vertexes[0].Point
                            end_point = edge.Vertexes[-1].Point
                            u1, v1 = edge.ParameterRange
                            mid_param = (u1 + v1)/2
                            mid_point = edge.valueAt(mid_param)
                            # ajoute une sphere au millieu
                            # App.Console.PrintMessage(f"start {start_point}, end {end_point} mid {mid_point}\n")
                            sphere = Part.makeSphere(tool_diam/4, mid_point)
                            spheres.append(sphere)

            elif hasattr(obj, 'FillMode') and obj.FillMode == "offset2":
                edges = self.collectEdges(obj.Contour)

                path = []
                nodes = self.generate_offset_path2(edges, tool_diam, overlap, obj.maxGeneration)

                if not nodes:
                    App.Console.PrintError("Aucun offset généré\n")
                    obj.Shape = Part.Shape()
                    return

                # Parcours récursif en profondeur depuis la racine
                # Les transitions entre frères passent par le parent commun
                def traverse_depth_first(node: noeud, is_first_child=True):
                    """
                    Parcours récursif en profondeur.
                    Pour chaque nœud :
                    1. Descendre récursivement vers les enfants les plus profonds
                    2. Usiner chaque enfant
                    3. Remonter au nœud courant via transition
                    4. Usiner le nœud courant
                    """
                    # Si le nœud a des enfants, les traiter d'abord (du plus profond vers le haut)
                    for idx, child in enumerate(node.children):
                        traverse_depth_first(child, is_first_child=(idx == 0))
                        # Après avoir usiné l'enfant, créer transition vers le parent (nœud courant)
                        if self.makeTransitionToParent(obj, child, node):
                            Log.baptDebug(f'Transition enfant→parent OK\n')

                    # Ajouter le wire du nœud courant au parcours
                    path.append(node.wires)
                    Log.baptDebug(f'Ajout nœud: {node}\n')

                # Traitement spécial pour le premier nœud le plus profond
                root = nodes[0]
                parent, depth, levels = buildParentDepthLevel(root)
                max_depth = max(levels.keys())

                # Trouver le premier nœud le plus profond et décaler si demandé
                if obj.useMiddleofFirstEdge and max_depth in levels and levels[max_depth]:
                    deepest_node = levels[max_depth][0]
                    edge = deepest_node.wires.Edges[0]
                    u1, v1 = edge.ParameterRange
                    mid_param = (u1 + v1)/2
                    mid_point = edge.valueAt(mid_param)
                    Log.baptDebug(f'Décalage au milieu de la première arête: {mid_point}\n')
                    deepest_node.shiftWire(mid_point)

                App.Console.PrintMessage(f'Profondeur maximale: {max_depth}, Racines: {len(nodes)}\n')

                # Parcourir tous les arbres (si plusieurs racines)
                for root_node in nodes:
                    traverse_depth_first(root_node, is_first_child=True)

                # Génération du G-code à partir du parcours
                strGcode = ""

                # Paramètres d'usinage
                step_down = abs(obj.StepDown)
                final_depth = obj.FinalDepth
                start_depth = 0.0  # On suppose que la surface est à Z=0
                feed_rate = obj.FeedRate.Value if hasattr(obj, 'FeedRate') else 1000.0
                safe_z = 5.0  # Hauteur de sécurité

                # Calculer le nombre de passes en profondeur
                total_depth = abs(final_depth - start_depth)
                num_passes = math.ceil(total_depth / step_down)

                Log.baptDebug(f"Génération G-code: {num_passes} passes, step={step_down}, final={final_depth}\n")

                # Générer le G-code pour chaque passe en profondeur
                for pass_num in range(num_passes):
                    # Calculer la profondeur de cette passe
                    if pass_num == num_passes - 1:
                        # Dernière passe : aller exactement à la profondeur finale
                        current_z = final_depth
                    else:
                        current_z = start_depth - (pass_num + 1) * step_down

                    strGcode += f"; Passe {pass_num + 1}/{num_passes} à Z={current_z:.3f}\n"

                    # Pour chaque wire du parcours
                    first_wire = True
                    for wire_compound in path:
                        for wire in wire_compound.Wires:
                            # Première position : mouvement rapide en Z safe puis au point de départ
                            first_edge = wire.Edges[0]
                            start_pt = first_edge.Vertexes[0].Point

                            if first_wire:
                                strGcode += f"G0 Z{safe_z:.3f}\n"
                                strGcode += f"G0 X{start_pt.x:.3f} Y{start_pt.y:.3f}\n"
                                strGcode += f"G1 Z{current_z:.3f} F{feed_rate:.3f}\n"
                                first_wire = False
                            else:
                                # Liaison rapide vers le wire suivant
                                strGcode += f"G0 Z{safe_z:.3f}\n"
                                strGcode += f"G0 X{start_pt.x:.3f} Y{start_pt.y:.3f}\n"
                                strGcode += f"G1 Z{current_z:.3f} F{feed_rate:.3f}\n"

                            # Convertir chaque edge en G-code
                            for edge in wire.Edges:
                                edge_gcode = edgeToGcode(edge, bonSens=True, current_z=current_z,
                                                         rapid=False, feed_rate=feed_rate)
                                strGcode += edge_gcode

                    # Remonter en sécurité après chaque passe
                    strGcode += f"G0 Z{safe_z:.3f}\n"
                obj.Gcode = strGcode
                Log.baptDebug(f"G-code généré: {len(strGcode)} caractères\n")

                # for n in nodes:
                #     wires = n.getWires()
                #     path.extend(wires)
                if obj.debugMode:
                    for i in range(len(path)):
                        for j in range(len(path[i].Wires)):
                            edge = path[i].Wires[j].Edges[0]
                            # recupere le premier point
                            start_point = edge.Vertexes[0].Point
                            end_point = edge.Vertexes[-1].Point
                            u1, v1 = edge.ParameterRange
                            # mid_param = (u1 + v1)/2
                            mid_param = u1 + (v1 - u1)/4
                            mid_point = edge.valueAt(mid_param)
                            # ajoute une sphere au millieu
                            # App.Console.PrintMessage(f"start {start_point}, end {end_point} mid {mid_point}\n")
                            sphere = Part.makeSphere(tool_diam/4, mid_point)
                            spheres.append(sphere)
            else:
                path = self.generate_spiral_path(shape, tool_diam, overlap)
            # obj.Path = path if path else None

            if path is None:
                App.Console.PrintError("PocketOperation: Échec de la génération du chemin d'usinage.\n")
                obj.Shape = Part.Shape()
                return
            a = path
            for s in spheres:
                a.append(s)
            compound = Part.makeCompound(a)
            # Part.show(compound)
            obj.Shape = compound
        except Exception as e:
            App.Console.PrintError(f"Erreur offset: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")

    def generate_zigzag_path(self, shape, tool_diam, overlap):
        # On suppose une poche plane, contour fermé
        if not shape or not shape.BoundBox:
            return None
        bbox = shape.BoundBox
        xmin, xmax = bbox.XMin, bbox.XMax
        ymin, ymax = bbox.YMin, bbox.YMax
        pas = tool_diam * (1 - overlap)
        lines = []
        y = ymin + tool_diam/2
        direction = 1
        while y <= ymax - tool_diam/2:
            # Cherche intersections entre la ligne y et la poche
            section = shape.slice(App.Vector(0, 0, 1), y)
            if section and hasattr(section, 'Edges'):
                for edge in section.Edges:
                    p1, p2 = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
                    if direction == 1:
                        lines.append(Part.makeLine(p1, p2))
                    else:
                        lines.append(Part.makeLine(p2, p1))
            y += pas
            direction *= -1
        if lines:
            return Part.Wire(lines)
        return None

    def offsetting(self, wires, offset_dist, maxGen, parentNode=None, generation=0):
        """Fonction récursive pour générer les offsets et construire l'arbre des offsets"""
        node: list[noeud] = []
        for wire in wires.Wires:
            try:
                o = wire.makeOffset2D(-offset_dist, join=0, fill=False, openResult=False)
                for j, w in enumerate(o.Wires):
                    n = noeud(generation, j, w)
                    node.append(n)
                    if parentNode is not None:
                        parentNode.addChild(n)
                    self.offsetting(w, offset_dist, maxGen, n, generation+1)
            except Exception as e:
                print(f"Offsetting generation {generation} échouée: {e}\n")
                pass

        return node

    def generate_offset_path2(self, shape: Part.Shape, tool_diam: float, overlap: float, maxGen: int):
        # Génère un offset intérieur de la forme
        path_edges = []
        try:
            current = Part.Wire(shape)

            offset_dist = tool_diam * (1 - overlap)
            generation = 0

            nodes = self.offsetting(current, offset_dist, maxGen)

            # print de l'arbre
            for n in nodes:
                n.printTree()

            if False:
                deepest_nodes = findDeepestNodes(nodes)
                App.Console.PrintMessage(f"Deepest nodes: {len(deepest_nodes)}\n")
                App.Console.PrintMessage(f'Deepest {deepest_nodes[0]}\n')

                arbore_nodes = arbore(nodes)
                App.Console.PrintMessage(f"Arbore nodes: {len(arbore_nodes)}\n")
                for n in arbore_nodes:
                    App.Console.PrintMessage(f'Arbore {n}\n')

            # for n in nodes:
            #     wires = n.getWires()
            #     # for w in wires:
            #     path_edges.append(wires)

            # App.Console.PrintMessage(f"Offset généré: nb {len(path_edges)}\n")
            return nodes

        except Exception as e:
            App.Console.PrintError(f"Erreur offset gen: {generation}: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return path_edges

    def generate_offset_path(self, shape, tool_diam, overlap, maxGen):
        # Génère un offset intérieur de la forme
        path_edges = []
        try:

            current = Part.Wire(shape)

            offset_dist = tool_diam * (1 - overlap)
            generation = 0
            while True:
                generation += 1
                offset = current.makeOffset2D(-offset_dist, join=0, fill=False, openResult=False)

                current = offset

                # on arrete si l'offset n'est plus fermé ou trop petit
                if offset is None:
                    App.Console.PrintMessage("Offset nul, fin de génération.\n")
                    break

                if not offset or not hasattr(offset, 'Wires') or not offset.Wires:
                    App.Console.Warning("PocketOperation: Offset invalide ou vide.\n")
                    break
                    return None

                path_edges.append(offset)

                if generation >= maxGen:
                    break

            App.Console.PrintMessage(f"Offset généré: nb {len(path_edges)}\n")
            return path_edges

        except Exception as e:
            # import json
            # j = json.loads(e)
            # if  j['sErrMsg'] == "makeOffset2D: offset result has no wires.":
            #     App.Console.PrintMessage(f"Erreur offset gen: {generation}: {e.sErrMsg}\n")
            #     return path_edges
            App.Console.PrintError(f"Erreur offset gen: {generation}: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return path_edges

    def generate_spiral_path(self, shape, tool_diam, overlap):
        # Génère une série d'offsets intérieurs, connecte chaque boucle à la suivante par le point le plus proche
        try:
            offset_dist = tool_diam * (1 - overlap)
            loops = []
            current = shape
            while True:
                # offset = current.makeOffset2D(-offset_dist, fill=False, join=0, openResult=True)

                face = Part.Face(current)
                offset = face.makeOffset(-offset_dist)

                # On arrête si l'offset n'est plus fermé ou trop petit
                if not offset or not hasattr(offset, 'Wires') or not offset.Wires:
                    break
                # Prend la plus grande wire (pour éviter les artefacts)
                main_wire = max(offset.Wires, key=lambda w: w.Length)
                if main_wire.Length < tool_diam:
                    break
                loops.append(main_wire)
                current = main_wire
            # On connecte les boucles entre elles
            if not loops:
                return None
            path_edges = []
            prev_wire = shape.Wires[0] if hasattr(shape, 'Wires') and shape.Wires else shape
            for wire in loops:
                # Trouver le point le plus proche entre la fin du wire précédent et le wire courant
                p_start = prev_wire.Vertexes[-1].Point
                min_dist = None
                min_vert = None
                for v in wire.Vertexes:
                    dist = (p_start - v.Point).Length
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        min_vert = v.Point
                # Décale le wire courant pour commencer à ce point
                reordered = wire.copy()
                reordered.rotate(reordered.CenterOfMass, App.Vector(0, 0, 1), 0)  # dummy to force copy
                reordered = reordered
                # Ajoute une liaison
                path_edges.append(Part.makeLine(p_start, min_vert))
                # Ajoute le wire courant
                path_edges.extend(reordered.Edges)
                prev_wire = wire
            # Retourne un wire unique
            return Part.Wire(path_edges)
        except Exception as e:
            App.Console.PrintError(f"Erreur spirale: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return None

    def makeTransitionToParent(self, obj, childNode: noeud, parentNode: noeud):
        """
        Crée une transition perpendiculaire entre un noeud enfant et son parent
        La transition est perpendiculaire à la première arête du wire enfant

        :param obj: L'objet PocketOperation
        :param childNode: Noeud enfant (intérieur)
        :param parentNode: Noeud parent (extérieur)
        """

        offset_dist = obj.ToolDiameter * (1 - obj.Overlap)

        childWire = childNode.wires
        parentWire = parentNode.wires
        try:
            is_ccw = childNode.isCCW()  # TODO: à implémenter le sens de fraisage

            edge = childWire.Edges[0]
            indice_start_point = getFirstPoint(childWire.Edges)
            u1, u2 = edge.ParameterRange
            if is_ccw:

                start_point: App.Vector = edge.Vertexes[indice_start_point].Point
                end_point: App.Vector = edge.Vertexes[-1 if indice_start_point == 0 else 0].Point
                Log.baptDebug(f'start_point: {start_point} is ccw: {is_ccw}\n')
                # for i,e in enumerate(childWire.Edges):
                #     Log.baptDebug(f'Edge {i}: {e.Vertexes[0].Point} to {e.Vertexes[-1].Point}\n')

            else:
                Log.baptDebug("Inverse le sens de l'arête pour CCW")
                # Inverse le sens de l'arête
                start_point: App.Vector = edge.Vertexes[-1 if indice_start_point == 0 else 0].Point
                end_point: App.Vector = edge.Vertexes[0 if indice_start_point == 0 else -1].Point
                utemp = u1
                u1 = u2
                u2 = utemp

            Log.baptDebug(f'start_point: {start_point}, end_point: {end_point}, is_ccw: {is_ccw}\n')
            # perpendiculaire à l'arête de début du childWire
            if edge.Curve.TypeId == 'Part::GeomLine':
                edge_normal = edge.tangentAt(u1).cross(App.Vector(0, 0, 1))
            elif edge.Curve.TypeId == 'Part::GeomCircle':

                if is_ccw:
                    edge_normal = edge.tangentAt(edge.Curve.parameter(start_point)).cross(App.Vector(0, 0, 1))
                else:
                    # start_point = childWire.Edges[0].Vertexes[-1].Point
                    edge_normal = edge.tangentAt(edge.Curve.parameter(start_point)).cross(App.Vector(0, 0, 1))

            edge_normal.normalize()
            candidates = []
            ray: Part.Line = Part.Line(start_point, start_point + edge_normal*100 if is_ccw else start_point - edge_normal*100)

            # Trouve le point le plus proche sur le parentWire
            for i, e in enumerate(parentWire.Edges):
                # calul le point d'intersection entre la droite perpendiculaire et l'arête

                # inter = ray.distToShape(e)
                inter: list[Part.Point] = ray.intersect(e.Curve)

                def pointToVector(p: Part.Point) -> App.Vector:
                    return App.Vector(p.X, p.Y, p.Z)

                new_start: App.Vector = None
                for i, p in enumerate(inter):
                    # Part.show(Part.makeSphere(0.5, pointToVector(p)))
                    d = (pointToVector(p) - start_point).Length
                    if math.fabs(d - offset_dist) < 1e-6:
                        # candidates.append((inter[1][0][1], i))
                        if obj.debugMode:
                            Part.show(Part.makeSphere(0.5, pointToVector(p)))
                        new_start = pointToVector(p)
                        if obj.debugMode:
                            Part.show(Part.makeLine(start_point, new_start))
                        # Décaler le parent pour commencer au point trouvé
                        parentNode.shiftWire(new_start)
                        # Ajouter la ligne de transition au wire enfant
                        transition_line = Part.makeLine(start_point, new_start)
                        childNode.wires.add(transition_line)
                        Log.baptDebug(f'Transition vers parent: distance={d:.3f}mm\n')
                        return True

            # Si aucune intersection trouvée à la distance exacte, chercher la plus proche
            Log.baptDebug(f'Recherche transition approximative...\n')
            min_dist_diff = float('inf')
            best_intersection = None

            for i, e in enumerate(parentWire.Edges):
                inter: list[Part.Point] = ray.intersect(e.Curve)
                for p in inter:
                    point = pointToVector(p)
                    d = (point - start_point).Length
                    dist_diff = abs(d - offset_dist)
                    if dist_diff < min_dist_diff:
                        min_dist_diff = dist_diff
                        best_intersection = point

            if best_intersection and min_dist_diff < offset_dist * 0.2:  # Tolérance 20%
                parentNode.shiftWire(best_intersection)
                transition_line = Part.makeLine(start_point, best_intersection)
                childNode.wires.add(transition_line)
                Log.baptDebug(f'Transition approximative: diff={min_dist_diff:.3f}mm\n')
                return True

            App.Console.PrintWarning(f'Aucune transition trouvée pour {childNode}\n')
            return False

        except Exception as e:
            line_nr = traceback.extract_tb(sys.exc_info()[2])[-1][1]
            App.Console.PrintError(f"makeTransitionToParent : {e} at line {line_nr}\n")
            return False


class PocketOperationTaskPanel():
    def __init__(self, obj):

        self.obj = obj
        self.form = Gui.PySideUic.loadUi(BaptUtilities.getPanel("PocketOp.ui"))

        self.overlapSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="Overlap", widget=self.form.overlapSpin)
        self.toolSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="ToolDiameter", widget=self.form.toolSpin)
        self.depthSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="FinalDepth", widget=self.form.depthSpin)
        self.nbGenSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="maxGeneration", widget=self.form.nbGenSpin)

        self.form.useMiddleofFirstEdge.setChecked(obj.useMiddleofFirstEdge if hasattr(obj, 'useMiddleofFirstEdge') else False)
        self.form.useMiddleofFirstEdge.stateChanged.connect(self.updateObj)

        for i, mode in enumerate(pocketFillMode):
            self.form.modeCombo.addItem(mode)

        self.form.modeCombo.setCurrentText(obj.FillMode if hasattr(obj, 'FillMode') else "spirale")

        self.form.modeCombo.currentTextChanged.connect(self.updateObj)

    def updateObj(self):

        self.obj.FillMode = self.form.modeCombo.currentText()
        self.obj.useMiddleofFirstEdge = self.form.useMiddleofFirstEdge.isChecked()
        self.obj.touch()
        App.ActiveDocument.recompute()


class ViewProviderPocketOperation(BaseOp.baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        self.Object = vobj.Object
        vobj.Proxy = self
        # vobj.Transparency = 90  # Définit la transparence pour mieux voir le chemin

    def attach(self, vobj):
        self.Object = vobj.Object

        return super().attach(vobj)

    def getIcon(self):
        """Retourne l'icône"""

        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Pocket.svg")

    def setupContextMenu(self, vobj, menu):
        #     """Configuration du menu contextuel"""
        super().setupContextMenu(vobj, menu)

        action_edit_gcode = QtGui.QAction(Gui.getIcon("Std_TransformManip.svg"), "edit Gcode", menu)
        QtCore.QObject.connect(action_edit_gcode, QtCore.SIGNAL("triggered()"), lambda: self.EditGcode(vobj))
        menu.addAction(action_edit_gcode)
        #     action = menu.addAction("Edit")
        #     action.triggered.connect(lambda: self.setEdit(vobj))

        #     action2 = menu.addAction("Activate" if vobj.Object.desactivated else "Desactivate")
        #     action2.triggered.connect(lambda: self.setDesactivate(vobj))
        return True

    def EditGcode(self, vobj):
        taskPanel = GcodeEditorTaskPanel(vobj.Object)
        Gui.Control.showDialog(taskPanel)

    # def setDesactivate(self, vobj):
    #     """Désactive l'objet"""
    #     vobj.Object.desactivated = not vobj.Object.desactivated
    #     if vobj.Object.desactivated:
    #         vobj.Object.ViewObject.Visibility = False
    #     else:
    #         vobj.Object.ViewObject.Visibility = True

    # def updateData(self, fp, prop):
    #     pass

    # def getDisplayModes(self, vobj):
    #     return ["Flat Lines", "Shaded", "Wireframe"]

    # def getDefaultDisplayMode(self):
    #     return "FlatLines"

    # def setDisplayMode(self, vobj, mode=None):
    #     if mode is None:
    #         return self.getDefaultDisplayMode()
    #     return mode
    # def getDefaultDisplayMode(self):
    #     return super().getDefaultDisplayMode()

    # def setDisplayMode(self, mode):
    #     return super().setDisplayMode(mode)

    # def getDisplayModes(self, vobj):
    #     return super().getDisplayModes(vobj)

    # def onDelete(self, vobj, subelements):
    #     return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâches pour l'opération de poche"""
        Gui.Control.showDialog(PocketOperationTaskPanel(vobj.Object))
        return True

    def doubleClicked(self, vobj):
        """Gère le double-clic pour ouvrir le panneau de tâches"""
        self.setEdit(vobj)
        return True


def createPocketOperation(contour=None) -> Part.Feature:
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "PocketOperation")

    PocketOperation(obj)
    ViewProviderPocketOperation(obj.ViewObject)

    if contour:
        obj.Contour = contour
        # Ajoute PocketOperation comme enfant de ContourGeometry dans l'arborescence
        # if hasattr(contour, "addObject"):
        #     contour.addObject(obj)
        # if hasattr(contour, "Group") and obj not in contour.Group:
        #     contour.Group.append(obj)

        pref = BaptPreferences.BaptPreferences()
        modeAjout = pref.getModeAjout()

        # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
        # 1 = ajouter à la géométrie comme enfant (pas conseillé)
        # 2 = ajouter au groupe opérations du projet CAM

        if modeAjout == 1 or modeAjout == 0:

            # Ajouter le contournage comme enfant de la géométrie du contour
            contour.addObject(obj)
            contour.Group.append(obj)

        if modeAjout == 2 or modeAjout == 0:
            camProject = BaptUtilities.find_cam_project(contour)
            if camProject:
                operations_group = camProject.Proxy.getOperationsGroup(camProject)
                if modeAjout == 2:
                    operations_group.addObject(obj)
                    operations_group.Group.append(obj)
                elif modeAjout == 0:
                    link = doc.addObject('App::Link', f'Link_{obj.Label}')
                    link.setLink(obj)
                    operations_group.addObject(link)
                    operations_group.Group.append(link)

    if hasattr(obj, "ViewObject"):
        obj.ViewObject.Proxy.setEdit(obj.ViewObject)
    return obj


def findDeepestNodes(rootNodes: list[noeud]):
    deepest_nodes = []
    max_depth = -1

    queue = deque()
    for root in rootNodes:
        queue.append((root, 0))  # (node, depth)

    while queue:
        node, depth = queue.popleft()

        if depth > max_depth:
            max_depth = depth
            deepest_nodes = [node]
        elif depth == max_depth:
            deepest_nodes.append(node)

        for child in node.children:
            queue.append((child, depth + 1))

    return deepest_nodes


def arbore(rootNodes):
    result = []

    def visite(n):
        result.append(n)
        for c in n.children:
            visite(c)
    for r in rootNodes:
        visite(r)
    return result


def buildParentDepthLevel(node):
    """
    Docstring for buildParentDepthLevel

    :param node: node of the tree to start from
    :return: parent, depth, levels
    """
    parent = {node: None}
    depth = {node: 0}
    levels = {}
    q = deque([node])
    while q:
        current = q.popleft()
        d = depth[current]
        levels.setdefault(d, []).append(current)
        for child in current.children:
            parent[child] = current
            depth[child] = d + 1
            q.append(child)
    return parent, depth, levels
