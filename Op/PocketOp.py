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
from Tool.ToolsGUI import ToolTaskPanel
from utils import BQuantitySpinBox, GcodeWriter
from utils import Log as Log
from utils.Contour import getFirstPoint, edgeToGcode

if True:
    Log.setLevel(Log.Level.DEBUG, Log.thisModule())
else:
    Log.setLevel(Log.Level.INFO, Log.thisModule())

pocketFillMode = ["offset", "zigzag", "spirale"]

Direction = ["Climb (Avalant)", "Conventional (opposition)"]

Plongee = ["Directe", "Helicoidale", "Rampante"]


def shift_wire_local(wire: Part.Wire, new_start_point: App.Vector, tol: float = 1e-6) -> Part.Wire:
    """Reordonne un wire pour démarrer à new_start_point sans dépendre de utils.Contour.shiftWire."""
    if not wire or not getattr(wire, "Edges", None):
        return wire

    edges = list(wire.Edges)
    is_closed = wire.isClosed()

    target_idx = -1
    for i, edge in enumerate(edges):
        try:
            if edge.distToShape(Part.Vertex(new_start_point))[0] < tol:
                target_idx = i
                break
        except Exception:
            continue

    if target_idx < 0:
        return wire

    target = edges[target_idx]
    u1, u2 = target.ParameterRange

    try:
        param = target.Curve.parameter(new_start_point)
    except Exception:
        # Fallback: si impossible de projeter, choisir l'extrémité la plus proche.
        d_start = (target.Vertexes[0].Point - new_start_point).Length
        d_end = (target.Vertexes[-1].Point - new_start_point).Length
        param = u1 if d_start <= d_end else u2

    # Si point au voisinage d'une extrémité, rotation simple.
    if abs(param - u1) < tol:
        ordered = edges[target_idx:] + edges[:target_idx]
        try:
            return Part.Wire(ordered)
        except Exception:
            return wire
    if abs(param - u2) < tol:
        ordered = edges[(target_idx + 1):] + edges[:(target_idx + 1)]
        try:
            return Part.Wire(ordered)
        except Exception:
            return wire

    try:
        first_part = target.Curve.trim(u1, param).toShape()
        second_part = target.Curve.trim(param, u2).toShape()
    except Exception:
        return wire

    if is_closed:
        # En fermé, on conserve la continuité en terminant par la partie "avant".
        ordered = [second_part] + edges[(target_idx + 1):] + edges[:target_idx] + [first_part]
    else:
        # En ouvert, on parcourt seulement vers l'avant depuis le nouveau point.
        ordered = [second_part] + edges[(target_idx + 1):]

    try:
        return Part.Wire(ordered)
    except Exception:
        return wire


def shift_node_wire_local(node: noeud, new_start_point: App.Vector) -> Part.Wire:
    """Décale le wire d'un nœud en local, sans appeler node.shiftWire()."""
    node.wires = shift_wire_local(node.wires, new_start_point)
    if hasattr(node, "hasChangend"):
        node.hasChangend = True
    return node.wires


class PocketOperation(BaseOp.baseOp):
    """
    Opération d'usinage de poche basée sur ContourGeometry.
    Génère un chemin d'usinage à partir du centre avec un facteur de recouvrement.
    """
    initialized = False
    Type = "PocketOperation"

    def __init__(self, obj):
        super().__init__(obj)
        self.initProperties(obj)
        obj.Proxy = self
        self.initialized = True
        Log.baptDebug("PocketOperation initialized.")

        Log.baptDebug(f"{isinstance(obj.Proxy, PocketOperation)}")

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
        obj.addProperty("App::PropertyFloat", "SurepAxiale", "Pocket", "Surépaisseur axiale").SurepAxiale = 0.0

        obj.addProperty("App::PropertyFloat", "SurepRadiale", "Toolpath", "Surépaisseur radiale")
        obj.SurepRadiale = 0.0

        obj.addProperty("App::PropertyEnumeration", "FillMode", "Pocket", "Mode de remplissage").FillMode = pocketFillMode
        obj.FillMode = pocketFillMode[0]

        obj.addProperty("App::PropertyEnumeration", "PlungeType", "Pocket", "Type de plongée").PlungeType = Plongee
        obj.PlungeType = Plongee[0]

        obj.addProperty("Part::PropertyPartShape", "Path", "Pocket", "Chemin d'usinage généré")

        obj.addProperty("App::PropertyInteger", "maxGeneration", "Pocket", "Nombre maximum de générations d'offset").maxGeneration = 2

        obj.addProperty("App::PropertyBool", "useMiddleofFirstEdge", "Pocket", "Utiliser le milieu de la première arête").useMiddleofFirstEdge = False
        obj.addProperty("App::PropertyBool", "debugMode", "General", "Activer le mode debug").debugMode = False

        obj.addProperty("App::PropertyEnumeration", "Direction", "Pocket", "Direction d'usinage").Direction = Direction
        obj.Direction = Direction[0]

        self.installToolProp(obj)

    def onChanged(self, obj, prop):
        # Log.baptDebug(f"{prop}")
        if prop in ["Overlap", "ToolDiameter", "StepDown", "FillMode", "Contour", "maxGeneration", "useMiddleofFirstEdge", "SurepAxiale", "SurepRadiale", "debugMode", "Direction", "PlungeType"]:
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
        edges = obj.Proxy.getEdges(obj)
        # Collecter toutes les arêtes sélectionnées
        # edges = []
        # for sub in obj.Edges:
        #     obj_ref = sub[0]  # L'objet référencé
        #     sub_names = sub[1]  # Les noms des sous-éléments (arêtes)

        #     for sub_name in sub_names:
        #         if "Edge" in sub_name:
        #             try:
        #                 edge = obj_ref.Shape.getElement(sub_name)
        #                 edges.append(edge)
        #                 # App.Console.PrintMessage(f"Arête ajoutée: {sub_name} de {obj_ref.Name}\n")
        #             except Exception as e:
        #                 App.Console.PrintError(f"Execute : Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
        #                 exc_type, exc_obj, exc_tb = sys.exc_info()
        #                 App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
        # App.Console.PrintMessage(f'nb collecté {len(edges)}\n')
        return edges

    def onDocumentRestored(self, obj):
        pass
        # self.__init__(obj)  # Réinitialiser les propriétés et le proxy après restauration

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return

        super().execute(obj)  # Appelle la logique de base (vérifications, etc.)

        try:

            shape = obj.Contour.Shape if obj.Contour and hasattr(obj.Contour, "Shape") else None

            if not shape:
                App.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
                obj.Shape = Part.Shape()
                return

            if not self.is_shape_valid(shape):
                App.Console.PrintError("PocketOperation: Shape du parent ContourGeometry invalide ou non fermée.\n")
                obj.Path = Part.Shape()
                return

            tool_diam = obj.ToolDiameter
            overlap = obj.Overlap

            gcodeWriter = GcodeWriter.GcodeWriter()

            # spheres pour marquer le debut du contour
            spheres = []

            # Génération du chemin selon le mode choisi
            if hasattr(obj, 'FillMode') and obj.FillMode == "zigzag":
                path = self.generate_zigzag_path(shape, tool_diam, overlap)

            elif hasattr(obj, 'FillMode') and obj.FillMode == "offset":
                edges = self.collectEdges(obj.Contour)
                if not edges:
                    App.Console.PrintError("Aucune arête trouvée pour l'offset.\n")
                    return
                # Utilisation de la nouvelle classe independante pour "offset"
                want_ccw = (obj.Direction == Direction[0])  # Climb = CCW

                step_over = tool_diam * (1 - overlap)
                # step_over = overlap
                surep = obj.SurepRadiale if hasattr(obj, 'SurepRadiale') else 0.0
                first_offset_dist = tool_diam / 2.0 + surep

                algo = PocketOffsetAlgorithm(tool_diam, first_offset_dist, step_over, obj.maxGeneration, want_ccw, obj.useMiddleofFirstEdge)

                try:
                    source_wire = Part.Wire(edges)
                    path = algo.run(source_wire)
                except Exception as e:
                    App.Console.PrintError(f"Erreur PocketOffsetAlgorithm: {e}\n")
                    path = []

                if obj.debugMode:
                    for s in path:
                        if hasattr(s, "Edges"):
                            for edge in s.Edges:
                                u1, v1 = edge.ParameterRange
                                mid_param = u1 + (v1 - u1) / 2
                                sphere = Part.makeSphere(tool_diam / 4, edge.valueAt(mid_param))
                                spheres.append(sphere)

            else:
                path = self.generate_spiral_path(shape, tool_diam, overlap)
            # obj.Path = path if path else Part.Shape()

            if path is None:
                App.Console.PrintError("PocketOperation: Échec de la génération du chemin d'usinage.\n")
                obj.Shape = Part.Shape()
                if hasattr(obj, 'Gcode'):
                    obj.Gcode = ""
                return

            # Normaliser le chemin en liste de segments exploitables.
            if isinstance(path, list):
                path_segments = list(path)
            elif hasattr(path, "Edges"):
                path_segments = [path]
            else:
                path_segments = []

            # Génération G-code commune à tous les FillMode.
            try:
                step_down = abs(obj.StepDown)
                if step_down < 1e-6:
                    App.Console.PrintError("PocketOperation: StepDown est nul ou trop petit.\n")
                    obj.Gcode = ""
                else:
                    start_depth, final_depth = obj.Contour.Proxy.getDepths()
                    final_depth += obj.SurepAxiale
                    feed_rate = float(obj.FeedRate.getValueAs('mm/min')) if hasattr(obj, 'FeedRate') else 1000.0
                    safe_z = start_depth + 5.0

                    total_depth = abs(final_depth - start_depth)
                    num_passes = max(1, math.ceil(total_depth / step_down))

                    first_edge = None
                    for segment in path_segments:
                        if hasattr(segment, "Edges") and segment.Edges:
                            first_edge = segment.Edges[0]
                            break

                    if first_edge is not None:
                        start_pt = first_edge.Vertexes[0].Point

                        for pass_num in range(num_passes):
                            if pass_num == num_passes - 1:
                                current_z = final_depth
                            else:
                                current_z = start_depth - (pass_num + 1) * step_down

                            gcodeWriter.comment(f"Passe {pass_num + 1}/{num_passes} à Z={current_z:.3f}")
                            gcodeWriter.linearMove({'X': start_pt.x, 'Y': start_pt.y}, rapid=True)
                            gcodeWriter.linearMove({'Z': safe_z}, rapid=True)

                            if obj.PlungeType == "Helicoidale":
                                dz = safe_z - current_z
                                diam = tool_diam * 1.5
                                nbtour = max(1, math.ceil(dz / 1.0))
                                prisePasse = (dz / nbtour) / 2
                                gcodeWriter.linearMove({'X': start_pt.x + diam / 2, 'Y': start_pt.y, 'Z': safe_z}, feed=feed_rate)
                                for i in range(nbtour):
                                    gcodeWriter.arcMove({'X': start_pt.x - diam / 2, 'Y': start_pt.y, 'Z': safe_z - ((i + 1) * prisePasse + i * prisePasse), 'CCW': True, 'I': -diam / 2, 'J': 0}, feed=feed_rate)
                                    gcodeWriter.arcMove({'X': start_pt.x + diam / 2, 'Y': start_pt.y, 'Z': safe_z - ((i + 1) * (prisePasse * 2)), 'CCW': True, 'I': diam / 2, 'J': 0}, feed=feed_rate)
                                gcodeWriter.linearMove({'X': start_pt.x, 'Y': start_pt.y, 'Z': current_z}, feed=feed_rate)
                            else:
                                gcodeWriter.linearMove({'Z': current_z}, feed=feed_rate, rapid=False)

                            current_pos = App.Vector(start_pt)
                            for segment in path_segments:
                                if not hasattr(segment, "Edges"):
                                    continue
                                for edge in segment.Edges:
                                    d0 = (edge.Vertexes[0].Point - current_pos).Length
                                    d1 = (edge.Vertexes[-1].Point - current_pos).Length
                                    bonSens = d0 <= d1
                                    edgeToGcode(
                                        edge,
                                        bonSens=bonSens,
                                        current_z=current_z,
                                        rapid=False,
                                        feed_rate=feed_rate,
                                        gcodeWriter=gcodeWriter,
                                    )
                                    current_pos = edge.Vertexes[-1].Point if bonSens else edge.Vertexes[0].Point

                            gcodeWriter.linearMove({'Z': safe_z}, rapid=True)

                    obj.Gcode = "\n".join(gcodeWriter.lines)
                    obj.TimeEstimate = gcodeWriter.time_estimate
                    obj.LastCoordinate = App.Vector(
                        gcodeWriter.current_position['X'],
                        gcodeWriter.current_position['Y'],
                        gcodeWriter.current_position['Z'],
                    )
            except Exception as e_gcode:
                App.Console.PrintWarning(f"PocketOperation: génération G-code échouée: {e_gcode}\n")
                obj.Gcode = ""

            a = list(path_segments)
            for s in spheres:
                a.append(s)
            compound = Part.makeCompound(a) if a else Part.Shape()
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
        y = ymin + tool_diam / 2
        direction = 1
        while y <= ymax - tool_diam / 2:
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
                    App.Console.PrintWarning("PocketOperation: Offset invalide ou vide.\n")
                    break

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

    # ===================================================================
    #  ALGORITHME D'ÉVIDEMENT DE POCHE - Méthodes utilitaires
    # ===================================================================

    @staticmethod
    def _build_parent_map(root_node: noeud) -> dict:
        """Construit un dictionnaire noeud → parent pour tout l'arbre."""
        parent_map = {root_node: None}
        queue = deque([root_node])
        while queue:
            node = queue.popleft()
            for child in node.children:
                parent_map[child] = node
                queue.append(child)
        return parent_map

    @staticmethod
    def _find_deepest_leaf(root_node: noeud) -> noeud:
        """Trouve la feuille la plus profonde (premier DFS)."""
        best = root_node
        best_depth = 0

        def dfs(node, depth):
            nonlocal best, best_depth
            if depth > best_depth:
                best = node
                best_depth = depth
            for child in node.children:
                dfs(child, depth + 1)

        dfs(root_node, 0)
        return best

    @staticmethod
    def _get_chain_to_root(node: noeud, parent_map: dict) -> list[noeud]:
        """Retourne la liste [node, parent, grandparent, ..., root]."""
        chain = []
        current = node
        while current is not None:
            chain.append(current)
            current = parent_map.get(current)
        return chain

    def _find_perp_intersection(self, source_point: App.Vector,
                                source_edge: Part.Edge, source_param: float,
                                target_wire: Part.Wire, offset_dist: float):
        """
        Depuis un point sur une arête source, calcule la perpendiculaire
        et cherche l'intersection avec le wire cible à ~offset_dist.
        Retourne le point d'intersection (App.Vector) ou None.
        """
        tangent = source_edge.tangentAt(source_param)
        tangent_xy = App.Vector(tangent.x, tangent.y, 0)
        if tangent_xy.Length < 1e-10:
            return None
        tangent_xy.normalize()

        normal = tangent_xy.cross(App.Vector(0, 0, 1))
        normal.normalize()

        best_point = None
        best_diff = float('inf')

        for direction in (normal, normal * -1):
            ray = Part.Line(source_point,
                            source_point + direction * offset_dist * 3)

            for target_edge in target_wire.Edges:
                try:
                    intersections = ray.intersect(target_edge.Curve)
                except Exception:
                    continue

                for p in intersections:
                    target_pt = App.Vector(p.X, p.Y, p.Z)
                    d = (target_pt - source_point).Length
                    diff = abs(d - offset_dist)

                    if diff < best_diff and diff < offset_dist * 0.2:
                        # Vérifier que le point est bien SUR l'arête cible
                        try:
                            dist_check = target_edge.distToShape(
                                Part.Vertex(target_pt))[0]
                            if dist_check < 1e-2:
                                best_point = target_pt
                                best_diff = diff
                        except Exception:
                            pass

        return best_point

    def _find_climb_transition(self, child_wire: Part.Wire,
                               parent_wire: Part.Wire,
                               offset_dist: float) -> dict | None:
        """
        Transition de remontée : depuis le point de départ de l'enfant
        (fin du tour = début du wire fermé) vers le parent.
        Essaie d'abord depuis le point logique de début du wire,
        puis échantillonne le long du wire en fallback.
        Retourne {'point_on_source', 'point_on_target'} ou None.
        """
        # 1) Essayer depuis le point de début du wire (position de l'outil après le tour)
        edge = child_wire.Edges[0]
        u1, u2 = edge.ParameterRange

        if len(child_wire.Edges) > 1:
            idx = getFirstPoint(child_wire.Edges)
            start_point = edge.Vertexes[idx].Point
            param = u1 if idx == 0 else u2
        else:
            start_point = edge.Vertexes[0].Point
            param = u1

        target_pt = self._find_perp_intersection(
            start_point, edge, param, parent_wire, offset_dist)

        if target_pt:
            return {
                'point_on_source': start_point,
                'point_on_target': target_pt,
            }

        # 2) Fallback : échantillonner le long de tout le wire
        for edge in child_wire.Edges:
            u1, u2 = edge.ParameterRange
            samples = max(5, int(edge.Length / (offset_dist * 0.3)))

            for s in range(samples + 1):
                param = u1 + (u2 - u1) * s / samples
                source_pt = edge.valueAt(param)

                target_pt = self._find_perp_intersection(
                    source_pt, edge, param, parent_wire, offset_dist)

                if target_pt:
                    return {
                        'point_on_source': source_pt,
                        'point_on_target': target_pt,
                    }

        return None

    def _find_interrupt_transition(self, parent_wire: Part.Wire,
                                   child_wire: Part.Wire,
                                   offset_dist: float) -> dict | None:
        """
        Transition d'interruption : parcourt les arêtes du parent et
        retourne le PREMIER point depuis lequel une perpendiculaire
        intersecte le wire enfant à ~offset_dist.
        Retourne {'edge_idx', 'param', 'point_on_source', 'point_on_target'}
        ou None.
        """
        for edge_idx, edge in enumerate(parent_wire.Edges):
            u1, u2 = edge.ParameterRange
            # Echantillonner le long de l'arête
            samples = max(5, int(edge.Length / (offset_dist * 0.3)))

            for s in range(samples + 1):
                param = u1 + (u2 - u1) * s / samples
                source_pt = edge.valueAt(param)

                target_pt = self._find_perp_intersection(
                    source_pt, edge, param, child_wire, offset_dist)

                if target_pt:
                    return {
                        'edge_idx': edge_idx,
                        'param': param,
                        'point_on_source': source_pt,
                        'point_on_target': target_pt,
                    }

        return None

    def _ensure_direction(self, node: noeud, want_ccw: bool):
        """S'assure que le wire du nœud et de tous ses enfants est dans le sens
        voulu : CCW si want_ccw=True (Climb/Avalant), CW sinon (Conventional).
        Inverse l'ordre des arêtes ET l'orientation de chaque arête."""
        is_ccw = node.isCCW()
        needs_flip = (want_ccw and not is_ccw) or (not want_ccw and is_ccw)
        if needs_flip:
            try:
                # Inverser l'ordre des arêtes et l'orientation de chacune
                reversed_edges = [e.reversed() for e in reversed(list(node.wires.Edges))]
                node.wires = Part.Wire(reversed_edges)
                direction_str = 'CCW' if want_ccw else 'CW'
                Log.baptDebug(f'Wire inversé pour {direction_str} : {node}')
                # Vérification post-inversion
                if node.isCCW() != want_ccw:
                    App.Console.PrintWarning(
                        f'Sens incorrect après inversion pour {node}\n')
            except Exception as e:
                App.Console.PrintWarning(
                    f'Inversion de sens échouée pour {node}: {e}\n')
        for child in node.children:
            self._ensure_direction(child, want_ccw)

    def _machine_node(self, obj, node: noeud, offset_dist: float,
                      visited: set, path: list):
        """
        Usine un nœud. Si le nœud a des enfants non visités, le wire est
        interrompu à l'endroit où une transition perpendiculaire vers un
        enfant est possible. Le sous-arbre enfant est alors traité
        récursivement, puis le wire reprend là où il avait été interrompu.
        """
        visited.add(id(node))

        unvisited = [c for c in node.children if id(c) not in visited]

        # ------ Cas simple : pas d'enfant non visité → tour complet ------
        if not unvisited:
            path.append(node.wires)
            Log.baptDebug(f'Usinage complet : {node}')
            return

        # ------ Cas avec interruptions ------
        # Trouver les points d'interruption pour chaque enfant
        transitions = []
        for child in unvisited:
            tp = self._find_interrupt_transition(
                node.wires, child.wires, offset_dist)
            if tp:
                transitions.append((child, tp))
            else:
                App.Console.PrintWarning(
                    f'Pas de transition trouvée pour enfant {child}\n')

        if not transitions:
            # Aucune transition possible → tour complet quand même
            path.append(node.wires)
            Log.baptDebug(f'Usinage complet (pas de transitions) : {node}')
            return

        # Trier par position le long du wire (edge_idx, puis param)
        transitions.sort(key=lambda t: (t[1]['edge_idx'], t[1]['param']))

        Log.baptDebug(
            f'Usinage avec {len(transitions)} interruption(s) : {node}')

        # Parcourir le wire avec interruptions
        wire_edges = list(node.wires.Edges)
        collected_edges = []     # arêtes accumulées avant la prochaine interruption
        current_start_idx = 0   # index de la première arête pas encore consommée

        for child, tp in transitions:
            edge_idx = tp['edge_idx']
            param = tp['param']
            pt_source = tp['point_on_source']
            pt_target = tp['point_on_target']

            # 1) Ajouter les arêtes complètes avant l'arête d'interruption
            for ei in range(current_start_idx, edge_idx):
                collected_edges.append(wire_edges[ei])

            # 2) Couper l'arête d'interruption au paramètre
            trans_edge = wire_edges[edge_idx]
            eu1, eu2 = trans_edge.ParameterRange
            has_before = abs(param - eu1) > 1e-6
            has_after = abs(param - eu2) > 1e-6

            if has_before:
                try:
                    first_part = trans_edge.Curve.trim(eu1, param).toShape()
                    collected_edges.append(first_part)
                except Exception as exc:
                    App.Console.PrintWarning(
                        f'trim avant interruption échoué : {exc}\n')

            # 3) Émettre le segment accumulé (avant l'interruption)
            if collected_edges:
                try:
                    path.append(Part.Wire(collected_edges))
                except Exception:
                    for e in collected_edges:
                        path.append(e)
                collected_edges = []

            # 4) Transition vers l'enfant (G1 X Y, Z constant)
            path.append(Part.makeLine(pt_source, pt_target))
            Log.baptDebug(
                f'  Interruption → enfant {child}, '
                f'dist={(pt_target - pt_source).Length:.3f}')

            # 5) Décaler le wire enfant pour qu'il commence à pt_target
            shift_node_wire_local(child, pt_target)

            # 6) Traiter récursivement le sous-arbre enfant
            self._machine_node(obj, child, offset_dist, visited, path)

            # 7) Transition retour enfant → parent
            #    (après le tour complet de l'enfant on est revenu à pt_target)
            path.append(Part.makeLine(pt_target, pt_source))

            # 8) Préparer la suite : la seconde moitié de l'arête coupée
            if has_after:
                try:
                    second_part = trans_edge.Curve.trim(param, eu2).toShape()
                    collected_edges.append(second_part)
                except Exception as exc:
                    App.Console.PrintWarning(
                        f'trim après interruption échoué : {exc}\n')

            current_start_idx = edge_idx + 1

        # 9) Émettre les arêtes restantes du wire (après la dernière interruption)
        for ei in range(current_start_idx, len(wire_edges)):
            collected_edges.append(wire_edges[ei])

        if collected_edges:
            try:
                path.append(Part.Wire(collected_edges))
            except Exception:
                for e in collected_edges:
                    path.append(e)

        Log.baptDebug(f'  Fin usinage {node}')


class PocketOperationTaskPanel():
    def __init__(self, obj):

        try:
            self.obj = obj
            self.ui1 = Gui.PySideUic.loadUi(BaptUtilities.getPanel("PocketOp.ui"))
            self.uiTool = ToolTaskPanel(obj)
            self.form = [self.ui1, self.uiTool.getForm()]

            self.overlapSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="Overlap", widget=self.ui1.overlapSpin)
            # self.overlapSpin.widget.setSingleStep(0.05)
            self.toolSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="ToolDiameter", widget=self.ui1.toolSpin)
            self.nbGenSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="maxGeneration", widget=self.ui1.nbGenSpin)
            self.surepAxialeSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="SurepAxiale", widget=self.ui1.surepAxialeSpin)
            self.surepRadialeSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="SurepRadiale", widget=self.ui1.surepRadialeSpin)
            self.stepDownSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="StepDown", widget=self.ui1.stepDownSpin)

            self.ui1.useMiddleofFirstEdge.setChecked(
                obj.useMiddleofFirstEdge if hasattr(obj, 'useMiddleofFirstEdge') else False)
            self.ui1.useMiddleofFirstEdge.stateChanged.connect(self.updateObj)

            for direction in Direction:
                self.ui1.directionCombo.addItem(direction)
            self.ui1.directionCombo.setCurrentText(
                obj.Direction if hasattr(obj, 'Direction') else Direction[0])
            self.ui1.directionCombo.currentTextChanged.connect(self.updateObj)

            for mode in pocketFillMode:
                self.ui1.modeCombo.addItem(mode)
            self.ui1.modeCombo.setCurrentText(
                obj.FillMode if hasattr(obj, 'FillMode') else pocketFillMode[0])
            self.ui1.modeCombo.currentTextChanged.connect(self.updateObj)

            for plunge in Plongee:
                self.ui1.plongeeCombo.addItem(plunge)
            self.ui1.plongeeCombo.setCurrentText(
                obj.PlungeType if hasattr(obj, 'PlungeType') else Plongee[0])
            self.ui1.plongeeCombo.currentTextChanged.connect(self.updateObj)

        except Exception as e:
            App.Console.PrintError(f"PocketOperationTaskPanel init: {str(e)}\n")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            App.Console.PrintMessage(f'ligne {exc_tb.tb_lineno}\n')

    def updateObj(self):
        try:
            self.obj.FillMode = self.ui1.modeCombo.currentText()
            self.obj.Direction = self.ui1.directionCombo.currentText()
            self.obj.useMiddleofFirstEdge = self.ui1.useMiddleofFirstEdge.isChecked()
            self.obj.PlungeType = self.ui1.plongeeCombo.currentText()
            self.obj.touch()
            App.ActiveDocument.recompute()
        except Exception as e:
            App.Console.PrintError(f"PocketOperationTaskPanel updateObj: {str(e)}\n")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            App.Console.PrintMessage(f'ligne {exc_tb.tb_lineno}\n')


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

        action_edit_gcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "edit Gcode", menu)
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
        try:
            tp = PocketOperationTaskPanel(vobj.Object)
            Gui.Control.showDialog(tp)

        except Exception as e:
            App.Console.PrintError(f"message setEdit {str(e)}\n")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
            Log.baptDebug(f"message setEdit {str(e)}")
            return False
        return True

    def doubleClicked(self, vobj):
        """Gère le double-clic pour ouvrir le panneau de tâches"""
        self.setEdit(vobj)
        return True


def createPocketOperation(contour=None) -> Part.Feature:
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "PocketOperation")

    PocketOperation(obj)

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

    ViewProviderPocketOperation(obj.ViewObject)
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.Proxy.setEdit(obj.ViewObject)
    return obj


class PocketOffsetAlgorithm:
    def __init__(self, tool_diam, first_offset_dist, step_over, max_gen, want_ccw, use_middle):
        self.tool_diam = tool_diam
        self.first_offset_dist = first_offset_dist
        self.step_over = step_over
        self.max_gen = max_gen
        self.want_ccw = want_ccw
        self.use_middle = use_middle
        self.visited = set()
        self.path = []

    def _wire_is_ccw(self, wire):
        n = noeud(0, 0, wire)
        if hasattr(n, "isCCW"):
            return n.isCCW()
        return True

    def run(self, shape):

        self.visited = set()
        self.path = []
        nodes = self._build_tree(shape)
        if not nodes:
            return []

        for root in nodes:
            self._ensure_direction(root, self.want_ccw)

        for root in nodes:
            deepest = self._find_deepest_leaf(root)
            chain = self._get_chain_to_root(deepest)

            self._link_chain(chain)

            for i, node in enumerate(chain):
                self._process_node(node)
                if i < len(chain) - 1:
                    parent = chain[i + 1]
                    try:
                        pt_child_end = node.wires.Edges[-1].Vertexes[-1].Point
                    except:
                        pt_child_end = node.entry_point
                    self.path.append(Part.makeLine(pt_child_end, parent.entry_point))

        return self.path

    def _build_tree(self, wire):
        nodes = []
        try:
            o = wire.makeOffset2D(-math.fabs(self.first_offset_dist), join=0, fill=False, openResult=False)
            if o and hasattr(o, "Wires"):
                for j, w in enumerate(o.Wires):
                    n = noeud(1, j, w)
                    n.parent_node = None
                    nodes.append(n)
                    self._offsetting(w, n, 2)
        except Exception as e:
            Log.baptDebug(f"PocketOffsetAlgorithm._build_tree err: {e}")
        return nodes

    def _offsetting(self, wire, parent_node, generation):
        if generation > self.max_gen:
            return
        try:
            o = wire.makeOffset2D(-math.fabs(self.step_over), join=0, fill=False, openResult=False)
            if o and hasattr(o, "Wires"):
                for j, w in enumerate(o.Wires):
                    n = noeud(generation, j, w)
                    n.parent_node = parent_node
                    parent_node.addChild(n)
                    self._offsetting(w, n, generation + 1)
        except:
            pass

    def _ensure_direction(self, node, want_ccw):
        is_ccw = node.isCCW()
        if (want_ccw and not is_ccw) or (not want_ccw and is_ccw):
            reversed_edges = [e.reversed() for e in reversed(list(node.wires.Edges))]
            node.wires = Part.Wire(reversed_edges)
        for child in node.children:
            self._ensure_direction(child, want_ccw)

    def _find_deepest_leaf(self, root_node):
        best = root_node
        best_depth = 0

        def dfs(node, depth):
            nonlocal best, best_depth
            if depth > best_depth:
                best = node
                best_depth = depth
            for child in node.children:
                dfs(child, depth + 1)
        dfs(root_node, 0)
        return best

    def _get_chain_to_root(self, node):
        chain = []
        current = node
        while current is not None:
            chain.append(current)
            current = getattr(current, "parent_node", None)
        return chain

    def _link_chain(self, chain):
        for i in range(len(chain) - 1):
            child = chain[i]
            parent = chain[i + 1]
            try:
                if hasattr(child, "entry_point"):
                    pt_child = child.entry_point
                else:
                    if self.use_middle and len(child.wires.Edges) > 0:
                        e0 = child.wires.Edges[0]
                        u1, v1 = e0.ParameterRange
                        pt_child = e0.valueAt((u1 + v1) / 2)
                    else:
                        pt_child = child.wires.Edges[0].Vertexes[0].Point
                    child.entry_point = pt_child
                    shift_node_wire_local(child, pt_child)

                tp = self._find_perp_inter(pt_child, parent.wires)
                if not tp:
                    tp = parent.wires.Edges[0].Vertexes[0].Point

                parent.entry_point = tp
                shift_node_wire_local(parent, tp)
            except Exception as e:
                Log.baptDebug(f"_link_chain err: {e}")

    def _process_node(self, node):
        self.visited.add(id(node))

        unvisited = [c for c in node.children if id(c) not in self.visited]
        if not unvisited:
            self.path.append(node.wires)
            return

        interruptions = []
        for child in unvisited:
            tp = self._find_interruption(node.wires, child.wires)
            if tp:
                interruptions.append((child, tp))

        if not interruptions:
            self.path.append(node.wires)
            return

        interruptions.sort(key=lambda x: (x[1]['edge_idx'], x[1]['param']))

        edges = list(node.wires.Edges)
        collected = []
        current_idx = 0

        for child, tp in interruptions:
            edge_idx = tp['edge_idx']
            param = tp['param']
            pt_parent = tp['pt_parent']
            pt_child = tp['pt_child']

            for i in range(current_idx, edge_idx):
                collected.append(edges[i])

            trans_edge = edges[edge_idx]
            u1, u2 = trans_edge.ParameterRange
            if abs(param - u1) > 1e-4:
                try:
                    collected.append(trans_edge.Curve.trim(u1, param).toShape())
                except:
                    pass

            if collected:
                self._flush(collected)
                collected = []

            self.path.append(Part.makeLine(pt_parent, pt_child))

            child.entry_point = pt_child
            shift_node_wire_local(child, pt_child)

            self._process_node(child)

            try:
                pt_child_end = child.wires.Edges[-1].Vertexes[-1].Point
            except:
                pt_child_end = pt_child
            self.path.append(Part.makeLine(pt_child_end, pt_parent))

            if abs(u2 - param) > 1e-4:
                try:
                    collected.append(trans_edge.Curve.trim(param, u2).toShape())
                except:
                    pass

            current_idx = edge_idx + 1

        for i in range(current_idx, len(edges)):
            collected.append(edges[i])

        if collected:
            self._flush(collected)

    def _flush(self, collected):
        try:
            self.path.append(Part.Wire(collected))
        except:
            self.path.extend(collected)

    def _find_perp_inter(self, source_pt, target_wire):
        try:
            res = target_wire.distToShape(Part.Vertex(source_pt))
            return res[1][0][0]
        except:
            return None

    def _find_interruption(self, parent_wire, child_wire):
        best_tp = None
        best_diff = float('inf')
        for e_idx, e in enumerate(parent_wire.Edges):
            u1, u2 = e.ParameterRange
            samples = max(10, int(e.Length / (self.step_over * 0.2)))
            for s in range(samples + 1):
                param = u1 + (u2 - u1) * s / samples
                try:
                    src_pt = e.valueAt(param)
                    res = child_wire.distToShape(Part.Vertex(src_pt))
                    dist = res[0]
                    diff = abs(dist - self.step_over)
                    if diff < best_diff and diff < self.step_over * 0.6:
                        best_diff = diff
                        best_tp = {
                            'edge_idx': e_idx,
                            'param': param,
                            'pt_parent': src_pt,
                            'pt_child': res[1][0][0]
                        }
                except:
                    pass
        return best_tp
