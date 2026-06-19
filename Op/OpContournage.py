import enum
import sys
import math

import FreeCAD as App
import FreeCADGui as Gui
import Part  # type: ignore

import PySide.QtGui as QtGui  # type: ignore
import PySide.QtCore as QtCore  # type: ignore

from BaptPath import GcodeEditorTaskPanel
import BaptUtilities
from utils import Contour, GcodeWriter, Log, formatFloat
from Op.offset import Side, material_side_to_tool_side, offsetWire, is_conventional
from Op.Gui.ContournageTaskPanel import ContournageTaskPanel
from Op.BaseOp import baseOp, baseOpViewProviderProxy


# compensation = ["Ordinateur", "Machine", "Ordinateur + G41/G42", "Aucune"]


class Compensation(enum.Enum):
    Ordinateur = 0
    Machine = 1
    Ordinateur_G41_G42 = 2
    Aucune = 3

    def __repr__(self):
        return f"{self.name}"


approach_types = ["Tangentielle", "Perpendiculaire", "Perp+Arc", "Hélicoïdale"]
retract_types = ["Tangentielle", "Perpendiculaire", "Verticale"]


class ContournageCycle(baseOp):
    """Représente un cycle d'usinage de contournage"""

    def __init__(self, obj):
        """Initialise l'objet de cycle de contournage"""
        # Ajouter les propriétés

        self.Type = "ContournageCycle"
        super().__init__(obj)

        # Propriétés pour les paramètres d'usinage
        if not hasattr(obj, "ToolDiameter"):
            obj.addProperty("App::PropertyLength", "ToolDiameter", "Tool", "Diamètre de l'outil")
            obj.ToolDiameter = 6.0

        if not hasattr(obj, "CutDepth"):
            obj.addProperty("App::PropertyLength", "CutDepth", "Cut", "Profondeur de coupe")
            obj.CutDepth = 5.0

        if not hasattr(obj, "StepDown"):
            obj.addProperty("App::PropertyLength", "StepDown", "Cut", "Profondeur par passe")
            obj.StepDown = 2.0

        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Contour", "Direction d'usinage")
            obj.Direction = ["Climb", "Conventional"]
            obj.Direction = "Climb"

        # Lien vers la géométrie du contour
        if not hasattr(obj, "ContourGeometry"):
            obj.addProperty("App::PropertyLink", "ContourGeometry", "Contour", "Géométrie du contour")
        # Migration : convertir l'ancien PropertyString en PropertyLink
        if hasattr(obj, "ContourGeometryName"):
            if obj.ContourGeometryName and not obj.ContourGeometry:
                old_geom = obj.Document.getObject(obj.ContourGeometryName)
                if old_geom:
                    obj.ContourGeometry = old_geom
            obj.removeProperty("ContourGeometryName")

        # Ajout des types d'approche et de sortie
        if not hasattr(obj, "ApproachType"):
            obj.addProperty("App::PropertyEnumeration", "ApproachType", "Approche", "Type d'approche du contour")
            obj.ApproachType = approach_types
            obj.ApproachType = approach_types[0]
        if not hasattr(obj, "RetractType"):
            obj.addProperty("App::PropertyEnumeration", "RetractType", "Sortie", "Type de sortie du contour")
            obj.RetractType = retract_types
            obj.RetractType = retract_types[0]

        # Longueur personnalisable pour l'approche/sortie
        if not hasattr(obj, "ApproachRetractLength"):
            obj.addProperty("App::PropertyLength", "ApproachRetractLength", "Approche", "Longueur de l'approche/sortie")
            obj.ApproachRetractLength = 12.0  # Valeur par défaut en mm

        if not hasattr(obj, "Compensation"):
            obj.addProperty("App::PropertyEnumeration", "Compensation", "Toolpath", "Type de compensation d'outil")
            obj.Compensation = list(Compensation.__members__.keys())
            obj.Compensation = Compensation.Ordinateur.name

        if not hasattr(obj, "SurepAxiale"):
            obj.addProperty("App::PropertyFloat", "SurepAxiale", "Toolpath", "Surépaisseur axiale")
            obj.SurepAxiale = 0.0

        if not hasattr(obj, "SurepRadiale"):
            obj.addProperty("App::PropertyFloat", "SurepRadiale", "Toolpath", "Surépaisseur radiale")
            obj.SurepRadiale = 0.0

        super().installToolProp(obj)

        obj.Proxy = self

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["ToolDiameter", "CutDepth", "StepDown", "Direction", "ContourGeometry", "ApproachType", "RetractType", "ApproachRetractLength", "ApproachRetractLength", "desactivated", "Compensation", "SurepAxiale", "SurepRadiale"]:
            self.execute(obj)

    def execute(self, obj):
        """Calcule le parcours outil de contournage et génère le G-code.

        Algorithme :
        1. Récupérer le wire de base depuis ContourGeometry à Z=Zref
        2. Pour chaque passe Z :
           a. Copier le wire à Z courant
           b. Appliquer makeOffset2D pour décaler du rayon outil (+surep)
           c. Détecter GÉOMÉTRIQUEMENT le côté outil (gauche/droite du parcours)
           d. Construire approche / sortie du bon côté
           e. Générer le G-code

        Conventions offset :
          makeOffset2D(+d) = GAUCHE du sens de parcours du wire
          makeOffset2D(-d) = DROITE du sens de parcours du wire
        Signe de l'offset :
          CoteMatiere=Droite → matière à droite → outil à gauche → +R
          CoteMatiere=Gauche → matière à gauche → outil à droite → -R
          Climb → signe inchangé   |   Conventional → signe inversé
        """
        if App.ActiveDocument.Restoring:
            return
        super().execute(obj)

        all_shapes = []
        gcode = GcodeWriter.GcodeWriter()

        # ── 1. Récupérer la géométrie de base ──────────────────────────────

        contour_geom = self.getContourGeometry(obj)
        if not contour_geom:
            return

        if not getattr(contour_geom, "Shape", None) or not contour_geom.Shape.Wires:
            App.Console.PrintError("[Contournage] Pas de wire dans la géométrie.\n")
            return

        depth = contour_geom.Proxy.getDepths()
        zref = depth[0]

        # Trouver le wire à Zref
        base_wire = None
        for w in contour_geom.Shape.Wires:
            if w.Edges and abs(w.Edges[0].Vertexes[0].Point.z - zref) < 1e-3:
                base_wire = w
                break
        if not base_wire:
            if contour_geom.Shape.Wires:
                base_wire = contour_geom.Shape.Wires[0]
            else:
                return

        # ── 2. Paramètres d'usinage ────────────────────────────────────────

        tool_radius = obj.ToolDiameter.Value / 2.0
        cote_matiere = getattr(contour_geom, "CoteMatiere", "NC")
        direction_usinage = obj.Direction  # Climb / Conventional
        is_closed = base_wire.isClosed()
        rapid_z = zref + 2.0
        feed = float(obj.FeedRate.getValueAs('mm/min'))
        passes = self.calculatePasse(obj)

        if cote_matiere == "NC":
            App.Console.PrintWarning("CoteMatiere is not defined for contour geometry, defaulting to 'Droite'.\n")
            cote_matiere = "Droite"

        # ── 3. Calcul du signe d'offset ────────────────────────────────────

        offset_value = tool_radius
        machining_side = material_side_to_tool_side(cote_matiere)
        _is_conventional = is_conventional(direction_usinage)
        self._tool_side_is_left = not _is_conventional

        reverse_path = (_is_conventional and machining_side == Side.LEFT) or (not _is_conventional and machining_side == Side.RIGHT)

        App.Console.PrintMessage(
            f"[Contournage] CoteMatiere={cote_matiere} {machining_side}, Dir={direction_usinage}, "
            f"{'fermé' if is_closed else 'ouvert'}, "
            f"({offset_value:.3f}) {'reverse' if reverse_path else 'normal'}\n")

        App.Console.PrintMessage(
            f"[Contournage] outil côté "
            f"{'GAUCHE' if self._tool_side_is_left else 'DROITE'} \n")

        # ── 4. Boucle sur les passes ───────────────────────────────────────

        prev_end_pt = None

        for p, pass_z in enumerate(passes):
            # Utiliser base_wire directement — NE PAS reconstruire avec Part.Wire()
            # car Part.Wire() peut inverser la direction du wire pour les contours ouverts.
            # base_wire vient de ContourGeometry qui respecte déjà la Direction.

            # Obtenir le wire à la profondeur de passe via polymorphisme
            wire_z = contour_geom.Proxy.getWireAtZ(contour_geom, pass_z)
            # if reverse_path:
            #     # Inverser le sens du wire pour cette passe si nécessaire
            #     wire_z = Part.Wire(reversed(wire_z.Edges))
            #     _orientEdges(wire_z.Edges)  # Réorienter les edges pour que les Vertexes soient dans le bon ordre
            if wire_z is None:
                Log.baptError(f"Pas de wire à Z={pass_z}")
                continue
            is_closed = wire_z.isClosed()

            # Règle de sens effective pour cette passe.
            reverse_path_pass = reverse_path

            # ── 4a. Appliquer l'offset outil ───────────────────────────────

            if offset_value > 0:
                offset_with_surep = offset_value + obj.SurepRadiale
            else:
                offset_with_surep = offset_value - obj.SurepRadiale

            def _to_wire(shape):
                if getattr(shape, "Wires", None):
                    return shape.Wires[0]
                if getattr(shape, "Edges", None):
                    return Part.Wire(shape.Edges)
                return None

            offset_wire = None

            # Utiliser la nouvelle méthode d'offset en priorité quand possible.

            side_for_offset = machining_side

            if side_for_offset == Side.NONE:
                App.Console.PrintWarning(f'No machining side specified, using default based on offset: {offset_with_surep}\n')
                side_for_offset = Side.LEFT if offset_with_surep >= 0 else Side.RIGHT

            try:
                App.Console.PrintMessage(f'Applying compensation offset dist {offset_with_surep} forward={not reverse_path_pass}\n')

                offset_wire = offsetWire(
                    wire_z,
                    offset_with_surep,
                    not reverse_path_pass,
                    side=side_for_offset,

                )

                if offset_wire is None:
                    Log.baptError(f"Pas de résultat d'offset Z={pass_z}")
                    continue

                if obj.Compensation == Compensation.Machine.name:
                    # Compensation machine : offset complet puis contre-offset du rayon.
                    # La CNC appliquera G41/G42 pour le rayon outil.
                    # comp_result = offset_wire.makeOffset2D(
                    #     -offset_value,
                    #     openResult=not is_closed)
                    App.Console.PrintMessage(f'Applying machine compensation offset dist {offset_value}\n')
                    comp_result = offsetWire(
                        offset_wire,
                        offset_value,
                        forward=True,
                        # side=Side.LEFT if machining_side == Side.RIGHT else Side.RIGHT,
                        side=Side.LEFT if side_for_offset == Side.RIGHT else Side.RIGHT,
                    )
                    offset_wire = _to_wire(comp_result)
                    if offset_wire is None:
                        Log.baptError(f"Pas de résultat de compensation machine Z={pass_z}")
                        continue

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                Log.baptError(
                    f"Erreur offset Z={pass_z}: ligne {exc_tb.tb_lineno} - {e}")
                continue

            offset_edges = list(offset_wire.Edges)

            # ── 4b. Contour fermé : décaler le point de départ ─────────────
            #   Couper le 1er edge au milieu et placer la 1re moitié à la fin
            #   pour que approche et sortie soient au milieu d'un segment.

            if is_closed and len(offset_edges) > 0:
                first = offset_edges[0]
                mid = (first.FirstParameter + first.LastParameter) / 2.0
                try:
                    half_a = first.Curve.toShape(first.FirstParameter, mid)
                    half_b = first.Curve.toShape(mid, first.LastParameter)
                except Exception:
                    half_a = first.Curve.trim(first.FirstParameter, mid).toShape()
                    half_b = first.Curve.trim(mid, first.LastParameter).toShape()
                offset_edges = [half_b] + offset_edges[1:] + [half_a]

            # ── 4b2. Conventional : inverser le sens de parcours ───────────

            # if is_conventional:
            #     offset_edges.reverse()

            # ── 4c. Points de départ/fin et tangentes ──────────────────────

            if len(offset_edges) == 1:
                # Cas mono-arête: forcer l'inversion des points en Conventional.
                if False and reverse_path_pass:
                    idx_first, idx_last = -1, 0
                else:
                    idx_first, idx_last = 0, -1
            else:
                idx_first = Contour.getFirstPoint(offset_edges)
                idx_last = Contour.getLastPoint(offset_edges)

            first_edge = offset_edges[0]
            last_edge = offset_edges[-1]
            start_pt = first_edge.Vertexes[idx_first].Point
            end_pt = last_edge.Vertexes[idx_last].Point

            # Tangente au départ (dans le sens de parcours)
            if idx_first == 0:
                tangent_start = first_edge.tangentAt(first_edge.FirstParameter)
            else:
                tangent_start = first_edge.tangentAt(first_edge.LastParameter) * -1.0
            tangent_start.z = 0
            tangent_start.normalize()

            # Tangente à la fin (dans le sens de parcours)
            if idx_last == -1:
                tangent_end = last_edge.tangentAt(last_edge.LastParameter)
            else:
                tangent_end = last_edge.tangentAt(last_edge.FirstParameter) * -1.0
            tangent_end.z = 0
            if tangent_end.Length > 1e-6:
                tangent_end.normalize()
            else:
                tangent_end = App.Vector(tangent_start)

            # # En Conventional mono-arête, l'orientation interne de l'edge peut rester
            # # opposée au sens d'usinage utilisé pour le G-code. On réaligne ici
            # # uniquement les vecteurs d'approche/sortie.
            # if len(offset_edges) == 1 and reverse_path_pass:
            #     tangent_start = tangent_start * -1.0
            #     tangent_end = tangent_end * -1.0

            # ── 4d. Détection géométrique du côté outil ────────────────────
            #   distToShape(vertex) → (dist, [(pt_sur_self, pt_sur_other), ...], ...)
            #     [1][0][0] = point le plus proche sur self (= wire_z)
            #     [1][0][1] = point le plus proche sur other (= le vertex passé)
            if False:
                dist_info = wire_z.distToShape(Part.Vertex(start_pt))
                closest_on_wire = dist_info[1][0][0]  # Point sur le wire original
                toward_tool = App.Vector(
                    start_pt.x - closest_on_wire.x,
                    start_pt.y - closest_on_wire.y, 0)
                left_normal = App.Vector(-tangent_start.y, tangent_start.x, 0)
                tool_is_left = toward_tool.dot(left_normal) > 0

                self._tool_side_is_left = tool_is_left

            # ── 4e. Approche ───────────────────────────────────────────────

            approach_pt, approach_edges = self._build_approach(
                obj, start_pt, tangent_start)

            gcode.comment(f"Pass at Z={formatFloat.format_float(pass_z, 3)}")
            gcode.linearMove({'X': approach_pt.x, 'Y': approach_pt.y}, rapid=True)
            gcode.linearMove({'Z': rapid_z}, rapid=True)
            gcode.linearMove({'Z': pass_z + 2}, rapid=True)
            gcode.linearMove({'Z': pass_z}, feed=feed, rapid=False)

            comp = "G40"
            if obj.Compensation in [Compensation.Machine.name,
                                    Compensation.Ordinateur_G41_G42.name]:
                comp = "G41" if self._tool_side_is_left else "G42"

            if p == 0:
                gcode.lines.append(f"{obj.Label}_start:")

            if obj.ApproachType == "Perp+Arc":
                r = 1
                a = float(obj.ApproachRetractLength) - r
                angle = math.asin(r / a)
                D = App.Vector(
                    ((a * a - r * r) / a) * math.cos(angle),
                    -((r / a) * math.sqrt(a * a - r * r)) * math.sin(angle), 0)
                gcode.linearMove(
                    {'X': approach_pt.x + D.x, 'Y': approach_pt.y + D.y},
                    feed=feed)
                gcode.arcMove(
                    {'X': start_pt.x, 'Y': start_pt.y, 'R': r, 'CCW': True},
                    feed=feed)
            else:
                gcode.linearMove(
                    {'X': start_pt.x, 'Y': start_pt.y, 'comp': comp},
                    feed=feed)

            # ── 4f. Parcours des edges ─────────────────────────────────────

            for i, edge in enumerate(offset_edges):
                if len(offset_edges) == 1:
                    bon_sens = self._edge_direction(offset_edges, i)
                    # if reverse_path_pass:
                    #     bon_sens = not bon_sens
                else:
                    # Pour les wires multi-arêtes, conserver l'orientation native
                    # du wire offseté est plus robuste que la détection locale.
                    bon_sens = True
                try:
                    Contour.edgeToGcode(edge, bonSens=bon_sens, current_z=pass_z,
                                        rapid=False, gcodeWriter=gcode)
                except Exception as e:
                    App.Console.PrintError(f"message {str(e)}\n")
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
                    Log.baptDebug(f"message {str(e)}")
                    continue

            # ── 4g. Sortie ─────────────────────────────────────────────────

            retract_pt, retract_edges = self._build_retract(
                obj, end_pt, tangent_end)

            if retract_edges:
                gcode.linearMove(
                    {'X': retract_pt.x, 'Y': retract_pt.y, 'comp': 'G40'},
                    feed=feed)

            gcode.linearMove({'Z': rapid_z}, rapid=True)

            if p == 0:
                gcode.lines.append(f"{obj.Label}_end:")

            # ── 4h. Shapes pour visualisation ──────────────────────────────

            traj_start = (approach_edges[0].Vertexes[0].Point
                          if approach_edges else start_pt)

            if prev_end_pt:
                p1 = prev_end_pt
                p2 = App.Vector(p1.x, p1.y, rapid_z)
                p3 = App.Vector(traj_start.x, traj_start.y, rapid_z)
                p4 = traj_start
                all_shapes.append(Part.makeLine(p1, p2))
                if p2.distanceToPoint(p3) > 1e-6:
                    all_shapes.append(Part.makeLine(p2, p3))
                all_shapes.append(Part.makeLine(p3, p4))

            all_shapes.extend(approach_edges)
            all_shapes.extend(offset_wire.Edges)
            all_shapes.extend(retract_edges)

            prev_end_pt = (retract_edges[-1].Vertexes[-1].Point
                           if retract_edges else end_pt)

        # ── 5. Finalisation ────────────────────────────────────────────────

        if all_shapes:
            try:
                obj.Shape = Part.makeCompound(all_shapes)
            except Exception as e:
                App.Console.PrintError(f"[Contournage] Erreur compound: {e}\n")
                obj.Shape = Part.Shape()
        else:
            obj.Shape = Part.Shape()

        obj.Gcode = '\n'.join(gcode.lines)
        obj.TimeEstimate = gcode.time_estimate
        obj.LastCoordinate = App.Vector(
            gcode.current_position['X'],
            gcode.current_position['Y'],
            gcode.current_position['Z'])

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _edge_direction(edges, index):
        """Détermine si l'edge[index] doit être parcourue en sens direct (True)
        ou inverse (False), en comparant la connectivité avec l'edge adjacente."""
        TOL = 1e-6
        edge = edges[index]

        if len(edges) == 1:
            return True

        if index < len(edges) - 1:
            other = edges[index + 1]
            if edge.Vertexes[-1].Point.distanceToPoint(other.Vertexes[0].Point) < TOL:
                return True
            if edge.Vertexes[-1].Point.distanceToPoint(other.Vertexes[-1].Point) < TOL:
                return True
            if edge.Vertexes[0].Point.distanceToPoint(other.Vertexes[-1].Point) < TOL:
                return False
            if edge.Vertexes[0].Point.distanceToPoint(other.Vertexes[0].Point) < TOL:
                return False
        else:
            other = edges[index - 1]
            if other.Vertexes[-1].Point.distanceToPoint(edge.Vertexes[0].Point) < TOL:
                return True
            if other.Vertexes[-1].Point.distanceToPoint(edge.Vertexes[-1].Point) < TOL:
                return False
            if other.Vertexes[0].Point.distanceToPoint(edge.Vertexes[-1].Point) < TOL:
                return False
            if other.Vertexes[0].Point.distanceToPoint(edge.Vertexes[0].Point) < TOL:
                return True

        return None

    def _build_approach(self, obj, entry_point, travel_direction):
        """Construit le mouvement d'approche vers le contour.

        L'approche part du côté outil (côté libre) et se dirige vers le contour.
        Le côté outil est déterminé par self._tool_side_is_left.
        """
        approach_type = obj.ApproachType
        length = float(obj.ApproachRetractLength)
        t = travel_direction
        tool_left = getattr(self, '_tool_side_is_left', 'NC')
        App.Console.PrintMessage(f'_build_approach travel_direction {travel_direction}, tool_left={tool_left}\n')

        if tool_left == 'NC':
            App.Console.PrintWarning('Tool side is not defined, defaulting to left for approach.\n')
            tool_left = True
        # App.Console.PrintMessage(f'Building approach: type={approach_type}, length={length}, tool_left={tool_left}\n')
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

    def _build_retract(self, obj, exit_point, travel_direction):
        """Construit le mouvement de sortie du contour.

        La sortie part du contour vers le côté outil (côté libre).
        Le côté outil est déterminé par self._tool_side_is_left.
        """
        retract_type = obj.RetractType
        length = float(obj.ApproachRetractLength)
        t = travel_direction
        tool_left = getattr(self, '_tool_side_is_left', True)
        App.Console.PrintMessage(f'_build_retract travel_direction {travel_direction}, tool_left={tool_left}\n')

        if retract_type == "Tangentielle":
            pt = exit_point + t * length
            return pt, [Part.makeLine(exit_point, pt)]

        elif retract_type == "Perpendiculaire":
            if tool_left:
                perp = App.Vector(-t.y, t.x, 0)
            else:
                perp = App.Vector(t.y, -t.x, 0)
            perp.normalize()
            pt = exit_point + perp * length
            return pt, [Part.makeLine(exit_point, pt)]

        elif retract_type == "Verticale":
            return exit_point, []

        return exit_point, []

    def reorder_wire(self, shape):
        """
        Trie et oriente les edges d'un wire ou shape, retourne un wire ordonné.
        """
        if hasattr(shape, "Edges"):
            sorted_edges = Part.__sortEdges__(list(shape.Edges))
            wire = Part.Wire(sorted_edges)
            # Afficher la séquence ordonnée des points
            ordered_points = []
            for edge in wire.Edges:
                for v in edge.Vertexes:
                    pt = (round(v.Point.x, 5), round(v.Point.y, 5), round(v.Point.z, 5))
                    if not ordered_points or pt != ordered_points[-1]:
                        ordered_points.append(pt)

            return wire
        return shape

    def calculatePasse(self, obj, passeEquilibre=True):
        geom = self.getContourGeometry(obj)
        if not geom:
            return []

        depths = geom.Proxy.getDepths()
        Zref = depths[0]
        Zfinal = depths[1]
        prise = obj.StepDown
        surep = obj.SurepAxiale
        dz = Zref - (Zfinal + surep)

        passes = []

        # if geom.DepthMode == "Relatif":
        #     depth = geom.Zref + geom.depth + obj.SurepAxiale
        # else:
        #     depth = geom.depth + obj.SurepAxiale

        if Zref < Zfinal:  # TODO
            App.Console.PrintError(f"La hauteur de référence ({Zref}) est inférieure à la profondeur de coupe ({Zfinal}).\n")
            return []

        if passeEquilibre:
            nbPasses = math.ceil(math.fabs(dz) / prise)
            prise = math.fabs(dz) / nbPasses
            for i in range(nbPasses):
                passes.append(Zref - (i + 1) * prise)
        else:
            while True:
                if dz >= Zfinal + prise:
                    passes.append(Zfinal)
                    Zfinal -= prise
                    break
                else:
                    passes.append(Zfinal)

        return passes

    def getContourGeometry(self, obj):
        """Récupérer la géométrie du contour associée"""
        if not hasattr(obj, "ContourGeometry") or not obj.ContourGeometry:
            return None
        return obj.ContourGeometry

    # def __getstate__(self):
    #     """Appelé lors de la sauvegarde"""
    #     return None
    #     # return {
    #     #     "Type": self.Type,
    #     #     "ContourGeometryName": getattr(self.Object, "ContourGeometryName", "")
    #     # }

    # def __setstate__(self, state):
    #     """Appelé lors du chargement"""
    #     return None

    #     # if state:
    #     #     self.Type = state.get("Type", "ContournageCycle")
    #     # return None


class ViewProviderContournageCycle(baseOpViewProviderProxy):
    """Classe pour gérer l'affichage du cycle de contournage"""

    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        super().__init__(vobj)
        self.deleteOnReject = True
        vobj.Proxy = self
        self.Object = vobj.Object
        self.panel = None
        # Ajouter des propriétés pour l'affichage
        if not hasattr(vobj, "ShowToolPath"):
            vobj.addProperty("App::PropertyBool", "ShowToolPath", "Display", "Afficher la trajectoire d'outil")
            vobj.ShowToolPath = True

        if not hasattr(vobj, "PathColor"):
            vobj.addProperty("App::PropertyColor", "PathColor", "Display", "Couleur de la trajectoire")
            vobj.PathColor = (0.0, 0.0, 1.0)  # Bleu par défaut

        if not hasattr(vobj, "PathWidth"):
            vobj.addProperty("App::PropertyFloat", "PathWidth", "Display", "Épaisseur de la trajectoire")
            vobj.PathWidth = 2.0

    def getIcon(self):
        """Retourne l'icône"""

        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Contournage.svg")

    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        self.panel = None
        # Configuration de l'affichage
        vobj.LineColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.PointColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.LineWidth = 2.0
        vobj.PointSize = 4.0

        return super().attach(vobj)

    # def setupContextMenu(self, vobj, menu):
    #     """Configuration du menu contextuel"""
    #     action = menu.addAction("Edit")
    #     action.triggered.connect(lambda: self.setEdit(vobj))

    #     action2 = menu.addAction("Activate" if vobj.Object.desactivated else "Desactivate")
    #     action2.triggered.connect(lambda: self.setDesactivate(vobj))
    #     return True
    def deleteObjectOnReject(self):
        return hasattr(self, "deleteOnReject") and self.deleteOnReject

    def onChanged(self, vobj, prop):
        """Appelé lorsqu'une propriété du ViewProvider est modifiée"""
        super().onChanged(vobj, prop)
        # Mettre à jour l'affichage si une propriété d'affichage change
        if prop in ["ShowToolPath", "PathColor", "PathWidth"]:
            # Appliquer les nouvelles propriétés d'affichage
            if hasattr(vobj, "LineColor") and hasattr(vobj, "PathColor"):
                vobj.LineColor = vobj.PathColor

            if hasattr(vobj, "LineWidth") and hasattr(vobj, "PathWidth"):
                vobj.LineWidth = vobj.PathWidth

    # def claimChildren(self):
    #     """Retourne les enfants de cet objet"""
    #     # Ne pas réclamer la géométrie du contour comme enfant
    #     # car c'est le contour qui doit être l'enfant de la géométrie
    #     return []

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)

        viewGcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "View G-code", menu)
        QtCore.QObject.connect(viewGcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(viewGcode)
        return True

    def viewGcode(self, vobj):
        """Afficher le G-code dans une boîte de dialogue"""
        taskPanel = GcodeEditorTaskPanel(vobj.Object)
        Gui.Control.showDialog(taskPanel)

    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâche pour l'édition"""
        if mode == 0:
            self.panel = ContournageTaskPanel(self.Object, self.deleteObjectOnReject)
            Gui.Control.showDialog(self.panel)
            self.deleteOnReject = False
            # self.panel.setupUi()
            return True
        return False

    def unsetEdit(self, vobj, mode=0):
        """Ferme le panneau de tâche"""
        if self.panel:
            self.panel.reject()
            self.panel = None
        Gui.Control.closeDialog()
        return True

    def closeTaskPanel(self):
        """Ferme le panneau de tâche si ouvert."""
        if self.panel:
            self.panel = None

    # def getDisplayModes(self, vobj):
    #     """Retourne les modes d'affichage disponibles"""
    #     return ["Flat Lines", "Shaded", "Wireframe", "Path"]

    # def getDefaultDisplayMode(self):
    #     """Retourne le mode d'affichage par défaut"""
    #     return "Flat Lines"

    # def setDisplayMode(self, mode):
    #     """Définit le mode d'affichage"""
    #     return mode
    def updateData(self, fp_object, prop):
        """Forwards property changes from the object to the active TaskPanel."""
        super().updateData(fp_object, prop)
        if self.panel:
            self.panel.updateData(fp_object, prop)

    def __getstate__(self):
        """Appelé lors de la sauvegarde"""
        return None
        return {"ObjectName": self.Object.Name if self.Object else None}

    def __setstate__(self, state):
        """Appelé lors du chargement"""
        return None
        if state and "ObjectName" in state and state["ObjectName"]:
            self.Object = App.ActiveDocument.getObject(state["ObjectName"])
        return None
