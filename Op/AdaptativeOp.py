import math
import FreeCAD as App
import FreeCADGui as Gui
import Part
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import BaptPreferences
import BaptUtilities
from Op import BaseOp
from Tool.ToolTaskPannel import ToolTaskPanel
from utils import Log, GcodeWriter
from utils.BQuantitySpinBox import BQuantitySpinBox
from utils.Contour import shiftWire


if True:
    Log.setLevel(Log.Level.DEBUG, Log.thisModule())
else:
    Log.setLevel(Log.Level.INFO, Log.thisModule())

Stock = ["Stock", "PreviousOp"]

Direction = ["Climb (Avalant)", "Conventional (opposition)"]
Plongee = ["Directe", "Helicoidale"]


class AdaptativeOp(BaseOp.baseOp):
    """
    Opération d'usinage adaptatif par pelure (peel milling).
    Usine la matière entre le brut (stock bounding box) et un contour fini
    par des passes concentriques avec engagement radial (ae) contrôlé.
    """
    Type = "AdaptativeOp"

    def __init__(self, obj):
        super().__init__(obj)

        self.initProperties(obj)
        obj.Proxy = self

    def initProperties(self, obj):
        if not hasattr(obj, "Contour"):
            obj.addProperty("App::PropertyLink", "Contour", "Adaptive",
                            "ContourGeometry de la pièce finie")

        if not hasattr(obj, "ToolDiameter"):
            obj.addProperty("App::PropertyFloat", "ToolDiameter", "Adaptive",
                            "Diamètre outil (mm)").ToolDiameter = 6.0

        if not hasattr(obj, "StepDown"):
            obj.addProperty("App::PropertyFloat", "StepDown", "Adaptive",
                            "Profondeur de passe (mm)").StepDown = 20.0

        if not hasattr(obj, "EngagementRadial"):
            obj.addProperty("App::PropertyFloat", "EngagementRadial", "Adaptive",
                            "Engagement radial max (ae) en mm").EngagementRadial = 1.0

        if not hasattr(obj, "SurepAxiale"):
            obj.addProperty("App::PropertyFloat", "SurepAxiale", "Adaptive",
                            "Surépaisseur axiale (mm)").SurepAxiale = 0.0

        if not hasattr(obj, "SurepRadiale"):
            obj.addProperty("App::PropertyFloat", "SurepRadiale", "Adaptive",
                            "Surépaisseur radiale (mm)").SurepRadiale = 0.0

        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Adaptive",
                            "Direction d'usinage").Direction = Direction
            obj.Direction = Direction[0]

        if not hasattr(obj, "PlungeType"):
            obj.addProperty("App::PropertyEnumeration", "PlungeType", "Adaptive",
                            "Type de plongée").PlungeType = Plongee
            obj.PlungeType = Plongee[0]

        if not hasattr(obj, "Entree"):
            obj.addProperty("App::PropertyLength", "Entree", "Adaptive",
                            "Longueur de la ligne d'entrée (mm)").Entree = 5.0

        if not hasattr(obj, "Sortie"):
            obj.addProperty("App::PropertyLength", "Sortie", "Adaptive",
                            "Longueur de la ligne de sortie (mm)").Sortie = 2.0

        if not hasattr(obj, "BaseGeometry"):
            obj.addProperty("App::PropertyLink", "BaseGeometry", "Adaptive",
                            "Géométrie de référence pour les opérations de contour")
            obj.BaseGeometry = None

        if not hasattr(obj, "debugMode"):
            obj.addProperty("App::PropertyBool", "debugMode", "General",
                            "Activer le mode debug").debugMode = False

        self.installToolProp(obj)

    def onChanged(self, obj, prop):
        if prop in ["Contour", "ToolDiameter", "StepDown", "EngagementRadial",
                    "SurepAxiale", "SurepRadiale", "Direction", "PlungeType",
                    "Entree", "Sortie", "BaseGeometry", "debugMode"]:
            self.execute(obj)

    def onDocumentRestored(self, obj):
        self.__init__(obj)  # Réinitialiser les propriétés et le proxy après restauration
        # self.initProperties(obj)

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return

        super().execute(obj)  # Appelle la logique de base (vérifications, etc.)

        try:
            shape = obj.Contour.Shape if obj.Contour and hasattr(obj.Contour, "Shape") else None
            if not shape:
                App.Console.PrintWarning("AdaptativeOp: Aucun contour sélectionné.\n")
                obj.Shape = Part.Shape()
                return

            base_shape = self._getBaseGeometryShape(obj)

            tool_diam = obj.ToolDiameter
            tool_radius = tool_diam / 2.0
            ae = obj.EngagementRadial  # engagement radial max
            surep_rad = obj.SurepRadiale

            # Contour fini = offset du contour pièce par (rayon outil + surépaisseur radiale)
            # Extraire un Wire depuis la Shape (qui peut être Wire, Edge, ou Compound)
            if shape.ShapeType == 'Wire':
                contour_wire = shape
            elif shape.ShapeType == 'Edge':
                contour_wire = Part.Wire([shape])
            elif shape.Wires:
                contour_wire = shape.Wires[0]
            else:
                App.Console.PrintWarning(
                    "AdaptativeOp: La shape du contour n'est ni un Wire ni un Edge.\n")
                obj.Shape = Part.Shape()
                return

            finish_offset = tool_radius + surep_rad
            try:
                finish_wire = contour_wire.makeOffset2D(finish_offset, join=0,
                                                        fill=False, openResult=False)
            except Exception:
                App.Console.PrintWarning(
                    "AdaptativeOp: Impossible de créer l'offset du contour fini.\n")
                obj.Shape = Part.Shape()
                return

            # Sens de rotation — usinage extérieur :
            # Avalant (Climb) = CW, Opposition (Conventional) = CCW
            want_ccw = (obj.Direction != Direction[0])

            # Générer le parcours pelure
            path_shapes = self._generate_path(obj,
                                              finish_wire, base_shape, ae, want_ccw)

            if not path_shapes:
                App.Console.PrintWarning("AdaptativeOp: Aucun parcours généré.\n")
                obj.Shape = Part.Shape()
                return

            # Génération du G-code
            gcodeWriter = GcodeWriter.GcodeWriter()

            step_down = abs(obj.StepDown)
            final_depth = obj.Contour.depth if hasattr(obj.Contour, "depth") else -5.0
            final_depth += obj.SurepAxiale
            start_depth = obj.Contour.Zref if hasattr(obj.Contour, "Zref") else 0.0
            feed_rate = float(obj.FeedRate.getValueAs('mm/min')) if hasattr(obj, 'FeedRate') else 1000.0
            safe_z = start_depth + 5.0

            total_depth = abs(final_depth - start_depth)
            num_passes = max(1, math.ceil(total_depth / step_down))

            # Premier point du parcours (basé sur la connectivité)
            start_pt = self._wire_start_point(path_shapes[0])

            for pass_num in range(num_passes):
                current_z = final_depth if pass_num == num_passes - 1 \
                    else start_depth - (pass_num + 1) * step_down

                gcodeWriter.comment(
                    f"Passe {pass_num + 1}/{num_passes} Z={current_z:.3f}")

                # Positionnement rapide
                gcodeWriter.linearMove({'X': start_pt.x, 'Y': start_pt.y}, rapid=True)
                gcodeWriter.linearMove({'Z': safe_z}, rapid=True)

                # Plongée
                if obj.PlungeType == "Directe":
                    gcodeWriter.linearMove({'Z': current_z}, feed=feed_rate)
                elif obj.PlungeType == "Helicoidale":
                    dz = safe_z - current_z
                    nbtour = max(1, math.ceil(dz / 1.0))
                    prise = (dz / nbtour) / 2
                    diam = tool_diam * 1.5
                    gcodeWriter.linearMove(
                        {'X': start_pt.x + diam / 2, 'Y': start_pt.y,
                         'Z': safe_z}, feed=feed_rate)
                    for i in range(nbtour):
                        z1 = safe_z - ((i + 1) * prise + i * prise)
                        z2 = safe_z - ((i + 1) * prise * 2)
                        gcodeWriter.arcMove(
                            {'X': start_pt.x - diam / 2, 'Y': start_pt.y,
                             'Z': z1, 'CCW': True, 'I': -diam / 2, 'J': 0},
                            feed=feed_rate)
                        gcodeWriter.arcMove(
                            {'X': start_pt.x + diam / 2, 'Y': start_pt.y,
                             'Z': z2, 'CCW': True, 'I': diam / 2, 'J': 0},
                            feed=feed_rate)
                    gcodeWriter.linearMove(
                        {'X': start_pt.x, 'Y': start_pt.y, 'Z': current_z},
                        feed=feed_rate)

                # Parcourir les segments du chemin
                # Identifier les transitions Z retract grâce aux lignes
                # de liaison (Part.makeLine) insérées par _generate_path
                transition_idx = 0
                transitions = getattr(self, '_pass_transitions', [])
                current_pos = App.Vector(start_pt)

                for seg_i, segment in enumerate(path_shapes):
                    seg_start = self._wire_start_point(segment)

                    # Si on n'est pas au bon endroit, c'est une transition
                    d_to_seg = (current_pos - seg_start).Length
                    if d_to_seg > 0.5 and transition_idx < len(transitions):
                        transition_type = transitions[transition_idx]
                        transition_idx += 1

                        if transition_type == 'z_retract':
                            # Dégagement Z, rapide vers le segment suivant, replongée
                            gcodeWriter.comment("Dégagement Z")
                            gcodeWriter.linearMove({'Z': safe_z}, rapid=True)
                            gcodeWriter.linearMove(
                                {'X': seg_start.x, 'Y': seg_start.y},
                                rapid=True)
                            gcodeWriter.linearMove(
                                {'Z': current_z}, feed=feed_rate)
                            current_pos = seg_start
                        # 'perp' => la ligne de liaison est dans le path,
                        # elle sera usinée normalement

                    for edge in segment.Edges:
                        d0 = (edge.Vertexes[0].Point - current_pos).Length
                        d1 = (edge.Vertexes[-1].Point - current_pos).Length
                        bonSens = d0 <= d1

                        if edge.Curve.TypeId == 'Part::GeomCircle':
                            circle = edge.Curve
                            center = circle.Center
                            if bonSens:
                                sp = edge.Vertexes[0].Point
                                ep = edge.Vertexes[-1].Point
                            else:
                                sp = edge.Vertexes[-1].Point
                                ep = edge.Vertexes[0].Point

                            is_ccw = circle.Axis.z > 0
                            if not bonSens:
                                is_ccw = not is_ccw

                            gcodeWriter.arcMove({
                                'X': ep.x, 'Y': ep.y,
                                'I': center.x - sp.x,
                                'J': center.y - sp.y,
                                'CCW': is_ccw}, feed=feed_rate)
                            current_pos = ep
                        else:
                            ep = edge.Vertexes[-1].Point if bonSens \
                                else edge.Vertexes[0].Point
                            gcodeWriter.linearMove(
                                {'X': ep.x, 'Y': ep.y}, feed=feed_rate)
                            current_pos = ep

                gcodeWriter.linearMove({'Z': safe_z}, rapid=True)

            obj.Gcode = "\n".join(gcodeWriter.lines)
            obj.TimeEstimate = gcodeWriter.time_estimate
            obj.LastCoordinate = App.Vector(gcodeWriter.current_position['X'], gcodeWriter.current_position['Y'], gcodeWriter.current_position['Z'])

            Log.baptDebug(f"G-code adaptatif: {len(obj.Gcode)} caractères")

            # Shape de visualisation : matière restante après usinage.
            # On offsette finish_wire (centre outil) vers l'intérieur de
            # tool_radius. L'aller-retour d'offset arrondit les coins
            # inaccessibles à l'outil (zones trop étroites).
            # Le signe dépend de l'orientation du wire (CCW/CW) :
            # on teste comme dans _generate_path.
            try:
                fw = finish_wire.Wires[0] if finish_wire.Wires else finish_wire
                fw_diag = fw.BoundBox.DiagonalLength

                # Tester si +tool_radius va vers l'extérieur ou l'intérieur
                test_wire = fw.makeOffset2D(tool_radius, join=0,
                                            fill=False, openResult=False)
                if test_wire and test_wire.Edges:
                    test_diag = test_wire.BoundBox.DiagonalLength
                    # On veut réduire → aller vers l'intérieur
                    if test_diag < fw_diag:
                        # + réduit déjà → utiliser +tool_radius
                        inward_offset = tool_radius
                    else:
                        # + agrandit → utiliser -tool_radius
                        inward_offset = -tool_radius
                else:
                    inward_offset = -tool_radius
                Log.baptDebug(f"Inward offset: {inward_offset}")
                remaining_wire = fw.makeOffset2D(
                    inward_offset, join=0, fill=False, openResult=False)
                obj.Shape = remaining_wire
            except Exception as e:
                Log.baptDebug(
                    f"Offset matière restante échoué: {e}, "
                    f"fallback sur contour_wire")
                obj.Shape = contour_wire

        except Exception as e:
            import sys
            App.Console.PrintError(f"AdaptativeOp erreur: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")

    # ==========================================================================
    # Méthodes internes
    # ==========================================================================

    def _getBaseGeometryShape(self, obj):
        """Récupère la shape de la géométrie de référence (BaseGeometry) si définie."""
        if obj.BaseGeometry and hasattr(obj.BaseGeometry, "Shape"):
            return obj.BaseGeometry.Shape

        elif obj.BaseGeometry is None:
            # Récupérer le stock (bounding box)
            stock_shape = self._getStockShape(obj)
            if stock_shape is None:
                App.Console.PrintWarning("AdaptativeOp: Aucun stock trouvé.\n")
                obj.Shape = Part.Shape()
                return None
            # Wire du stock (rectangle de la bounding box en XY)
            bb = stock_shape.BoundBox
            stock_wire = Part.makePolygon([
                App.Vector(bb.XMin, bb.YMin, 0),
                App.Vector(bb.XMax, bb.YMin, 0),
                App.Vector(bb.XMax, bb.YMax, 0),
                App.Vector(bb.XMin, bb.YMax, 0),
                App.Vector(bb.XMin, bb.YMin, 0),
            ])
            return stock_wire
        return None

    def _getStockShape(self, obj):
        """Récupère la shape du stock depuis le projet CAM."""
        camProject = BaptUtilities.find_cam_project(obj)
        if not camProject:
            return None
        stock = camProject.Proxy.getStock(camProject)
        if stock and hasattr(stock, 'Shape'):
            return stock.Shape
        return None

    def _point_on_wire(self, wire, dist_along):
        """Retourne (point, tangent) sur le wire à la distance donnée depuis le début."""
        cumulative = 0.0
        for edge in wire.Edges:
            edge_len = edge.Length
            if cumulative + edge_len >= dist_along - 1e-6:
                local_dist = max(0, dist_along - cumulative)
                param = edge.getParameterByLength(local_dist)
                point = edge.valueAt(param)
                tangent = edge.tangentAt(param)
                return point, tangent
            cumulative += edge_len
        # Au-delà du wire : dernier point
        last_edge = wire.Edges[-1]
        param = last_edge.LastParameter
        return last_edge.valueAt(param), last_edge.tangentAt(param)

    def _generate_path(self, obj, finish_wire, stock_wire,
                       ae, want_ccw):
        """
        Algorithme de pelure (peel milling).

        Principe :
        1. Partir du contour fini (finish_wire).
        2. Générer des offsets successifs vers l'extérieur, espacés de ae.
        3. Pour chaque offset, vérifier si le wire est entièrement dans le stock
           (complet) ou partiellement (clippé).
        4. Wires complets : usiner en entier avec transition perpendiculaire
           vers la passe suivante.
        5. Wires clippés : ne garder que les edges à l'intérieur du stock,
           avec dégagement Z entre les segments disjoints.
        6. Usiner de l'extérieur vers l'intérieur.

        Retourne une liste de Part.Shape.
        self._pass_transitions contient les marqueurs de transition pour le G-code.
        """
        # Extraire le wire du finish
        fw = finish_wire.Wires[0] if hasattr(finish_wire, 'Wires') \
            and finish_wire.Wires else finish_wire

        # Extraire le wire du stock
        sw = stock_wire.Wires[0] if hasattr(stock_wire, 'Wires') \
            and stock_wire.Wires else stock_wire
        margin = 0.01  # tolérance

        # ---- Alignement Z unique + création face stock ------------------
        # Le stock polygon est souvent à Z=0 alors que les offsets sont
        # au Z du contour. On aligne une seule fois au lieu de copier/
        # translater à chaque appel de _clip_wire_to_stock.
        fw_z = fw.Vertexes[0].Point.z if fw.Vertexes else 0.0
        sw_z = sw.Vertexes[0].Point.z if sw.Vertexes else 0.0
        if abs(fw_z - sw_z) > 1e-6:
            sw = sw.copy()
            sw.translate(App.Vector(0, 0, fw_z - sw_z))
            Log.baptDebug(
                f"Alignement Z stock {sw_z:.3f} → {fw_z:.3f}")

        # Créer la face une seule fois pour tous les appels de clip
        stock_face = None
        face_ok = False
        try:
            stock_face = Part.Face(sw)
            center = sw.BoundBox.Center
            center_z = App.Vector(center.x, center.y, fw_z)
            face_ok = stock_face.isInside(center_z, margin, True)
            if not face_ok:
                try:
                    stock_face = stock_face.complement()
                    face_ok = stock_face.isInside(center_z, margin, True)
                except Exception:
                    face_ok = False
            if not face_ok:
                Log.baptDebug(
                    "WARNING: stock face isInside échoue, "
                    "fallback BoundBox")
        except Exception as e:
            Log.baptDebug(f"Création face stock échouée: {e}")

        # BoundBox pour les logs
        bb = sw.BoundBox
        bb_finish = fw.BoundBox

        Log.baptDebug(
            f"Stock BB: X[{bb.XMin:.2f}, {bb.XMax:.2f}] "
            f"Y[{bb.YMin:.2f}, {bb.YMax:.2f}]")
        Log.baptDebug(
            f"Finish BB: X[{bb_finish.XMin:.2f}, {bb_finish.XMax:.2f}] "
            f"Y[{bb_finish.YMin:.2f}, {bb_finish.YMax:.2f}]")
        Log.baptDebug(
            f"Finish wire: isClosed={fw.isClosed()}, "
            f"isCCW={self._is_ccw(fw) if fw.isClosed() else 'N/A'}, "
            f"Length={fw.Length:.2f}, Edges={len(fw.Edges)}")

        # Déterminer le signe correct pour que l'offset aille vers l'extérieur
        # (vers le stock). makeOffset2D(+) va à gauche du wire:
        # - Wire CCW => + = outward
        # - Wire CW  => + = inward
        # On veut aller vers l'extérieur (agrandir la BoundBox).
        offset_sign = 1.0
        try:
            test_ow = fw.makeOffset2D(ae, join=0, fill=False, openResult=False)
            if test_ow and test_ow.Edges:
                test_bb = test_ow.BoundBox
                test_diag = test_bb.DiagonalLength
                fw_diag = bb_finish.DiagonalLength
                if test_diag < fw_diag:
                    # L'offset positif réduit la taille → il faut inverser
                    offset_sign = -1.0
                    Log.baptDebug(
                        "Offset positif va vers l'intérieur, "
                        "inversion du signe")
                else:
                    Log.baptDebug(
                        "Offset positif va vers l'extérieur (OK)\n")
        except Exception as e:
            Log.baptDebug(f"Test d'offset échoué: {e}")

        # ---- 1. Générer les offsets et les classifier --------------------
        # Boucle while : on s'arrête quand l'offset est entièrement
        # hors du stock (aucune portion clippée à l'intérieur).
        pass_data = []
        i = 0

        while True:
            offset = (i + 1) * ae * offset_sign
            i += 1

            try:
                ow = fw.makeOffset2D(offset, join=0,
                                     fill=False, openResult=False)
            except Exception as e:
                Log.baptDebug(f"Offset {i} (d={offset:.2f}) échoué: {e}")
                break

            if not ow or not ow.Edges:
                Log.baptDebug(f"Offset {i} vide")
                break

            offset_wire = ow.Wires[0] if ow.Wires else ow

            ow_bb = offset_wire.BoundBox
            Log.baptDebug(
                f"Offset {i} (d={offset:.2f}): BB X[{ow_bb.XMin:.2f}, "
                f"{ow_bb.XMax:.2f}] Y[{ow_bb.YMin:.2f}, {ow_bb.YMax:.2f}] "
                f"Edges={len(offset_wire.Edges)}")

            # NE PAS appliquer _ensure_wire_direction avant le clipping
            # car les edges reversées cassent edge.Curve.toShape(p1, p2).
            # La direction sera appliquée après dans l'étape 3.

            # Classifier en clippant directement avec le shape du stock
            clipped = self._clip_wire_to_stock(
                offset_wire, sw, margin, stock_face, face_ok, fw_z)

            if not clipped:
                # Rien dans le stock → l'offset est entièrement dehors, on arrête
                Log.baptDebug(
                    f"Offset {i} (d={offset:.2f}): entièrement hors stock, arrêt")
                break

            # Vérifier si le wire est entièrement dans le stock
            # en comparant la longueur clippée vs originale
            clipped_length = sum(w.Length for w in clipped)
            is_complete = (abs(clipped_length - offset_wire.Length) <
                           margin * 10)

            if is_complete:
                pass_data.append((offset_wire, True, [offset_wire]))
                Log.baptDebug(
                    f"Offset {i} (d={offset:.2f}): complet (dans stock)")
            else:
                pass_data.append((offset_wire, False, clipped))
                Log.baptDebug(
                    f"Offset {i} (d={offset:.2f}): "
                    f"clippé en {len(clipped)} segment(s)")

        Log.baptDebug(f"Passes générées: {len(pass_data)}")

        if not pass_data:
            return []

        # ---- 2. Inverser l'ordre (extérieur → intérieur) + contour fini --
        pass_data.reverse()
        # Le finish wire n'est pas clippé → on peut appliquer la direction ici
        fw_directed = self._ensure_wire_direction(fw, want_ccw)
        pass_data.append((fw_directed, True, [fw_directed]))

        # ---- 3. Construire le parcours avec transitions ------------------
        path = []
        # Stocker les infos pour le G-code
        self._pass_transitions = []  # liste de 'perp' ou 'z_retract'

        prev_wire = None
        prev_end = None

        for pass_idx, (orig_wire, is_complete, sub_wires) in enumerate(pass_data):

            if is_complete:
                # Appliquer la direction APRÈS clipping (ou directement
                # si le wire est complet et non clippé)
                wire = self._ensure_wire_direction(sub_wires[0], want_ccw)

                # Transition perpendiculaire depuis la passe précédente
                if prev_end is not None:
                    # Chercher le point le plus proche sur ce wire
                    nearest_pt = self._nearest_point_on_wire(wire, prev_end)
                    if nearest_pt is not None:
                        # Réorganiser le wire pour démarrer au point le plus proche
                        try:
                            wire = shiftWire(wire, nearest_pt)
                        except Exception as e:
                            Log.baptDebug(
                                f"shiftWire échoué passe {pass_idx}: {e}")

                        # Transition perpendiculaire (ligne courte)
                        d = (prev_end - nearest_pt).Length
                        if d > 0.01:
                            path.append(Part.makeLine(prev_end, nearest_pt))
                            self._pass_transitions.append('perp')

                # Ajouter le wire complet
                path.append(wire)

                # Déterminer le point de fin du wire
                # Après _ensure_wire_direction, Edges[0].Vertexes[0]
                # est le début du wire
                wire_start = self._wire_start_point(wire)
                wire_end = self._wire_end_point(wire)
                is_closed = (wire_start - wire_end).Length < 0.01
                prev_end = wire_start if is_closed else wire_end
                prev_wire = wire

                Log.baptDebug(
                    f"Passe {pass_idx}: complet, L={wire.Length:.1f}")

            else:
                # Déterminer si les segments clippés doivent être inversés
                # pour correspondre à la direction d'usinage voulue
                needs_reverse = False
                if orig_wire.isClosed():
                    is_ccw = self._is_ccw(orig_wire)
                    needs_reverse = (is_ccw != want_ccw)

                effective_wires = []
                for seg_wire in sub_wires:
                    if needs_reverse:
                        try:
                            rev_edges = [e.reversed()
                                         for e in reversed(seg_wire.Edges)]
                            seg_wire = Part.Wire(rev_edges)
                        except Exception:
                            pass
                    effective_wires.append(seg_wire)

                if needs_reverse:
                    effective_wires.reverse()

                # Passe clippée : segments disjoints avec Z retract entre eux
                for seg_idx, seg_wire in enumerate(effective_wires):
                    seg_start = self._wire_start_point(seg_wire)
                    seg_end = self._wire_end_point(seg_wire)

                    # Marquer un dégagement Z avant ce segment
                    if prev_end is not None:
                        d = (prev_end - seg_start).Length
                        if d > 0.01:
                            self._pass_transitions.append('z_retract')

                    # Mouvement d'entrée (ligne droite tangente)
                    entry_dir = self._wire_tangent_at_start(seg_wire)
                    entry_edge = self._build_entry_move(
                        seg_start, entry_dir, length=obj.Entree)
                    if entry_edge is not None:
                        path.append(Part.Wire([entry_edge]))

                    # Segment usiné
                    path.append(seg_wire)

                    # Mouvement de sortie : on le supprime uniquement si
                    # la passe suivante est complète (transition perpendiculaire).
                    # Sinon (autre passe clippée ou fin du parcours), on prolonge.
                    is_last_seg = (seg_idx == len(effective_wires) - 1)
                    next_is_perp = False
                    if is_last_seg and pass_idx + 1 < len(pass_data):
                        next_is_perp = pass_data[pass_idx + 1][1]  # is_complete

                    if not is_last_seg or not next_is_perp:
                        exit_dir = self._wire_tangent_at_end(seg_wire)
                        exit_edge = self._build_exit_move(
                            seg_end, exit_dir, length=obj.Sortie)
                        if exit_edge is not None:
                            path.append(Part.Wire([exit_edge]))
                            prev_end = exit_edge.Vertexes[-1].Point
                        else:
                            prev_end = seg_end
                    else:
                        prev_end = seg_end

                Log.baptDebug(
                    f"Passe {pass_idx}: clippé, "
                    f"{len(effective_wires)} segment(s)")

        return path

    def _clip_wire_to_stock(self, wire, stock_wire, margin,
                            stock_face=None, face_ok=False, wire_z=None):
        """
        Découpe un wire en ne gardant que les portions à l'intérieur
        du stock_wire (forme quelconque : rectangle, contour arrondi, etc.).

        Stratégie optimisée :
        - Pré-test BoundBox par wire entier (court-circuit rapide)
        - Pré-test BoundBox par edge (skip les edges triviales)
        - Bisection fiable pour les intersections (section() est
          trop peu fiable pour des shapes coplanaires)

        Paramètres optionnels (pré-calculés par _generate_path) :
            stock_face : Part.Face déjà alignée en Z
            face_ok    : True si isInside fonctionne sur stock_face
            wire_z     : coordonnée Z commune pour les tests isInside
        """
        tol = 1e-6

        # Si pas de face pré-calculée, en créer une (appel autonome)
        if stock_face is None:
            wire_z = wire.Vertexes[0].Point.z if wire.Vertexes else 0.0
            stock_z = stock_wire.Vertexes[0].Point.z \
                if stock_wire.Vertexes else 0.0
            if abs(wire_z - stock_z) > tol:
                stock_wire = stock_wire.copy()
                stock_wire.translate(App.Vector(0, 0, wire_z - stock_z))
            try:
                stock_face = Part.Face(stock_wire)
                center = stock_wire.BoundBox.Center
                face_ok = stock_face.isInside(
                    App.Vector(center.x, center.y, wire_z), margin, True)
                if not face_ok:
                    try:
                        stock_face = stock_face.complement()
                        face_ok = stock_face.isInside(
                            App.Vector(center.x, center.y, wire_z),
                            margin, True)
                    except Exception:
                        face_ok = False
            except Exception:
                face_ok = False

        if wire_z is None:
            wire_z = wire.Vertexes[0].Point.z if wire.Vertexes else 0.0

        # BoundBox du stock (réutilisée partout, évite de recalculer)
        sbb = stock_wire.BoundBox
        sx_min = sbb.XMin - margin
        sx_max = sbb.XMax + margin
        sy_min = sbb.YMin - margin
        sy_max = sbb.YMax + margin

        def point_inside(pt):
            """Test si un point est à l'intérieur du stock."""
            # Pré-filtre BoundBox ultra-rapide (pas d'appel OCCT)
            if pt.x < sx_min or pt.x > sx_max \
                    or pt.y < sy_min or pt.y > sy_max:
                return False
            if face_ok and stock_face is not None:
                return stock_face.isInside(
                    App.Vector(pt.x, pt.y, wire_z), margin, True)
            # Fallback BoundBox pur (quand face OCCT indisponible)
            return True

        # ---- Court-circuit : wire entièrement dans le stock ? ------------
        wbb = wire.BoundBox
        if (wbb.XMin >= sx_min and wbb.XMax <= sx_max and
                wbb.YMin >= sy_min and wbb.YMax <= sy_max):
            if not (face_ok and stock_face is not None):
                # Stock rectangulaire → BBox suffit
                return [wire]
            # Face non-rectangulaire → vérifier vertices ET milieux d'edges
            all_in = True
            for edge in wire.Edges:
                mid = edge.valueAt(
                    (edge.FirstParameter + edge.LastParameter) / 2.0)
                if not point_inside(mid):
                    all_in = False
                    break
            if all_in:
                return [wire]

        # ---- Court-circuit : wire entièrement hors du stock ? ------------
        if (wbb.XMax < sx_min or wbb.XMin > sx_max or
                wbb.YMax < sy_min or wbb.YMin > sy_max):
            return []

        def find_intersection_params(edge):
            """Trouve les paramètres où l'edge croise la frontière du stock.

            Bisection pure : échantillonnage régulier + dichotomie
            pour localiser précisément chaque transition in/out.
            """
            fp = edge.FirstParameter
            lp = edge.LastParameter

            # Pré-test rapide : edge entièrement dans la BBox du stock ?
            ebb = edge.BoundBox
            edge_in_bbox = (ebb.XMin >= sx_min and ebb.XMax <= sx_max and
                            ebb.YMin >= sy_min and ebb.YMax <= sy_max)

            if edge_in_bbox and not (face_ok and stock_face is not None):
                # Stock rectangulaire + edge dans la BBox → pas d'intersection
                return []

            N = 32  # résolution fiable pour tous types d'edges

            params = []
            prev_inside = point_inside(edge.valueAt(fp))
            for j in range(1, N + 1):
                t = fp + (lp - fp) * j / N
                curr_inside = point_inside(edge.valueAt(t))
                if curr_inside != prev_inside:
                    # Transition détectée — bisection pour localiser
                    lo = fp + (lp - fp) * (j - 1) / N
                    hi = t
                    for _ in range(30):
                        mid = (lo + hi) / 2
                        if point_inside(edge.valueAt(mid)) == prev_inside:
                            lo = mid
                        else:
                            hi = mid
                    params.append((lo + hi) / 2)
                prev_inside = curr_inside

            # Trier et dédupliquer
            params.sort()
            unique = []
            for p in params:
                if not unique or abs(p - unique[-1]) > tol * 10:
                    unique.append(p)
            return unique

        # ---- Traiter chaque edge -----------------------------------------
        all_inside_edges = []

        for edge in wire.Edges:
            fp = edge.FirstParameter
            lp = edge.LastParameter

            # Pré-test BoundBox par edge : si entièrement hors stock, skip
            ebb = edge.BoundBox
            if (ebb.XMax < sx_min or ebb.XMin > sx_max or
                    ebb.YMax < sy_min or ebb.YMin > sy_max):
                continue

            params = find_intersection_params(edge)

            if not params:
                # Pas d'intersection : tester le milieu
                mid_pt = edge.valueAt((fp + lp) / 2.0)
                if point_inside(mid_pt):
                    all_inside_edges.append(edge)
            else:
                # Diviser l'edge aux paramètres d'intersection
                cut_params = [fp] + params + [lp]
                for k in range(len(cut_params) - 1):
                    p1 = cut_params[k]
                    p2 = cut_params[k + 1]
                    if p2 - p1 < tol:
                        continue
                    mid_pt = edge.valueAt((p1 + p2) / 2.0)
                    if point_inside(mid_pt):
                        try:
                            sub_edge = edge.Curve.toShape(p1, p2)
                            all_inside_edges.append(sub_edge)
                        except Exception:
                            pass

        if not all_inside_edges:
            return []

        # ---- Regrouper les edges consécutives en wires continus ----------
        result = []
        current_edges = [all_inside_edges[0]]

        for i in range(1, len(all_inside_edges)):
            prev = current_edges[-1]
            curr = all_inside_edges[i]

            # Tester les 4 combinaisons de vertices pour la connexion
            dists = [
                prev.Vertexes[-1].Point.distanceToPoint(
                    curr.Vertexes[0].Point),
                prev.Vertexes[-1].Point.distanceToPoint(
                    curr.Vertexes[-1].Point),
                prev.Vertexes[0].Point.distanceToPoint(
                    curr.Vertexes[0].Point),
                prev.Vertexes[0].Point.distanceToPoint(
                    curr.Vertexes[-1].Point),
            ]

            if min(dists) < 0.1:
                current_edges.append(curr)
            else:
                try:
                    result.append(Part.Wire(current_edges))
                except Exception:
                    pass
                current_edges = [curr]

        if current_edges:
            try:
                result.append(Part.Wire(current_edges))
            except Exception:
                pass

        return result

    def _wire_start_point(self, wire):
        """Retourne le point de départ du wire en tenant compte
        de la connectivité entre edges (pas seulement Vertexes[0])."""
        edges = wire.Edges
        if len(edges) == 1:
            return edges[0].Vertexes[0].Point
        # Déterminer quelle extrémité de la 1ère edge connecte à la 2ème
        e0, e1 = edges[0], edges[1]
        d00 = e0.Vertexes[0].Point.distanceToPoint(e1.Vertexes[0].Point)
        d01 = e0.Vertexes[0].Point.distanceToPoint(e1.Vertexes[-1].Point)
        d10 = e0.Vertexes[-1].Point.distanceToPoint(e1.Vertexes[0].Point)
        d11 = e0.Vertexes[-1].Point.distanceToPoint(e1.Vertexes[-1].Point)
        # L'extrémité de e0 qui connecte à e1 est la FIN du wire pour e0
        # Donc le DÉBUT est l'autre extrémité
        if min(d10, d11) < min(d00, d01):
            # e0 se termine à Vertexes[-1] → début = Vertexes[0]
            return e0.Vertexes[0].Point
        else:
            # e0 se termine à Vertexes[0] → début = Vertexes[-1]
            return e0.Vertexes[-1].Point

    def _wire_end_point(self, wire):
        """Retourne le point de fin du wire en tenant compte
        de la connectivité entre edges."""
        edges = wire.Edges
        if len(edges) == 1:
            return edges[-1].Vertexes[-1].Point
        # Déterminer quelle extrémité de la dernière edge connecte à l'avant-dernière
        e_last = edges[-1]
        e_prev = edges[-2]
        d00 = e_last.Vertexes[0].Point.distanceToPoint(e_prev.Vertexes[0].Point)
        d01 = e_last.Vertexes[0].Point.distanceToPoint(e_prev.Vertexes[-1].Point)
        d10 = e_last.Vertexes[-1].Point.distanceToPoint(e_prev.Vertexes[0].Point)
        d11 = e_last.Vertexes[-1].Point.distanceToPoint(e_prev.Vertexes[-1].Point)
        # L'extrémité de e_last qui connecte à e_prev est le DÉBUT dans le wire
        # Donc la FIN est l'autre extrémité
        if min(d00, d01) < min(d10, d11):
            # e_last commence à Vertexes[0] → fin = Vertexes[-1]
            return e_last.Vertexes[-1].Point
        else:
            # e_last commence à Vertexes[-1] → fin = Vertexes[0]
            return e_last.Vertexes[0].Point

    def _wire_tangent_at_start(self, wire):
        """Retourne le vecteur tangent unitaire au début du wire,
        orienté dans le sens de parcours du wire."""
        edges = wire.Edges
        e0 = edges[0]
        start_pt = self._wire_start_point(wire)
        d0 = (e0.Vertexes[0].Point - start_pt).Length
        if d0 < 0.01:
            # Le wire commence par Vertexes[0] de la 1ère edge
            tangent = e0.tangentAt(e0.FirstParameter)
        else:
            # Le wire commence par Vertexes[-1] → sens inversé
            tangent = e0.tangentAt(e0.LastParameter) * -1.0
        tangent.normalize()
        return tangent

    def _wire_tangent_at_end(self, wire):
        """Retourne le vecteur tangent unitaire à la fin du wire,
        orienté dans le sens de parcours du wire."""
        edges = wire.Edges
        e_last = edges[-1]
        end_pt = self._wire_end_point(wire)
        d_last = (e_last.Vertexes[-1].Point - end_pt).Length
        if d_last < 0.01:
            # Le wire finit par Vertexes[-1] de la dernière edge
            tangent = e_last.tangentAt(e_last.LastParameter)
        else:
            # Le wire finit par Vertexes[0] → sens inversé
            tangent = e_last.tangentAt(e_last.FirstParameter) * -1.0
        tangent.normalize()
        return tangent

    def _build_entry_move(self, entry_point, direction, length=2.0):
        """
        Construit le mouvement d'entrée dans un segment clippé.

        Pour l'instant, génère une ligne droite d'approche le long de
        la direction d'usinage (en amont du point d'entrée).

        Parameters:
            entry_point : App.Vector
                Point d'entrée sur le contour (à la frontière du stock).
            direction : App.Vector
                Vecteur direction tangent au contour au point d'entrée
                (dans le sens d'usinage).
            length : float
                Longueur du mouvement d'entrée (mm).

        Returns:
            Part.Edge – ligne d'approche menant au point d'entrée,
            ou None si length <= 0.
        """
        if length <= 1e-9:
            return None
        d = App.Vector(direction)
        if d.Length > 1e-9:
            d.normalize()
        approach_point = entry_point - d * length
        return Part.makeLine(approach_point, entry_point)

    def _build_exit_move(self, exit_point, direction, length=2.0):
        """
        Construit le mouvement de sortie d'un segment clippé.

        Pour l'instant, génère une ligne droite de dégagement le long de
        la direction d'usinage (en aval du point de sortie).

        Parameters:
            exit_point : App.Vector
                Point de sortie du contour (à la frontière du stock).
            direction : App.Vector
                Vecteur direction tangent au contour au point de sortie
                (dans le sens d'usinage).
            length : float
                Longueur du mouvement de sortie (mm).

        Returns:
            Part.Edge – ligne de dégagement partant du point de sortie,
            ou None si length <= 0.
        """
        if length <= 1e-9:
            return None
        d = App.Vector(direction)
        if d.Length > 1e-9:
            d.normalize()
        depart_point = exit_point + d * length
        return Part.makeLine(exit_point, depart_point)

    def _nearest_point_on_wire(self, wire, point):
        """
        Trouve le point le plus proche sur un wire depuis un point donné.
        Retourne le App.Vector le plus proche ou None.
        """
        best_pt = None
        best_dist = float('inf')

        for edge in wire.Edges:
            try:
                dist, pts, _ = edge.distToShape(Part.Vertex(point))
                if dist < best_dist:
                    best_dist = dist
                    best_pt = pts[0][0]  # Premier point de la paire
            except Exception:
                continue

        return best_pt

    def _is_ccw(self, wire):
        """Vérifie si un wire fermé est dans le sens anti-horaire (CCW)
        en utilisant la formule du lacet (shoelace)."""
        pts = [v.Point for v in wire.Vertexes]
        area = 0.0
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            area += pts[i].x * pts[j].y
            area -= pts[j].x * pts[i].y
        return area > 0

    def _ensure_wire_direction(self, wire, want_ccw):
        """S'assure que le wire fermé est dans le sens voulu
        (CCW si want_ccw=True, CW sinon).
        Pour un wire ouvert, retourne le wire inchangé."""
        if not wire.isClosed():
            return wire
        is_ccw = self._is_ccw(wire)
        if is_ccw == want_ccw:
            return wire
        try:
            reversed_edges = [e.reversed() for e in reversed(wire.Edges)]
            new_wire = Part.Wire(reversed_edges)
            direction_str = 'CCW' if want_ccw else 'CW'
            Log.baptDebug(f'Wire inversé pour {direction_str}')
            return new_wire
        except Exception as e:
            App.Console.PrintWarning(
                f'Inversion de sens échouée: {e}\n')
            return wire


class ViewProviderAdaptiveOp(BaseOp.baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        self.Object = vobj.Object
        vobj.Proxy = self
        self.panel = None
        self.deleteOnReject = True

    def attach(self, vobj):
        self.Object = vobj.Object
        self.panel = None
        return super().attach(vobj)

    def updateData(self, fp, prop):
        # Log.baptDebug(f"updateData VP : prop={prop}")
        if self.panel:
            self.panel.updateData(fp, prop)
        return super().updateData(fp, prop)

    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("AdaptativeOp.svg")

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)

        viewGcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "View G-code", menu)
        QtCore.QObject.connect(viewGcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(viewGcode)
        return True

    def deleteObjectOnReject(self):
        return hasattr(self, "deleteOnReject") and self.deleteOnReject

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâches pour l'opération adaptive."""
        if mode == 0:

            self.panel = AdaptativeOpTaskPanel(vobj.Object, self.deleteObjectOnReject())
            Gui.Control.showDialog(self.panel)
            self.deleteOnReject = False
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

    def doubleClicked(self, vobj):
        self.setEdit(vobj)
        return True


class AdaptativeOpTaskPanel():
    """Panneau de tâches pour l'opération de fraisage Adaptatif."""

    def __init__(self, obj, deleteOnReject):

        self.obj = obj
        self.deleteOnReject = deleteOnReject
        App.activeDocument().openTransaction("Edit Adaptative Parameters")
        self.ui1 = Gui.PySideUic.loadUi(
            BaptUtilities.getPanel("AdaptativeOp.ui"))
        self.uiTool = ToolTaskPanel(obj)
        self.form = [self.ui1, self.uiTool.getForm()]
        self.toolDiamSpin = BQuantitySpinBox(obj, "ToolDiameter", self.ui1.toolDiamSpin)
        self.stepDownSpin = BQuantitySpinBox(obj, "StepDown", self.ui1.stepDownSpin)
        self.aeSpin = BQuantitySpinBox(obj, "EngagementRadial", self.ui1.aeSpin)
        self.surepAxialeSpin = BQuantitySpinBox(obj, "SurepAxiale", self.ui1.surepAxialeSpin)
        self.surepRadialeSpin = BQuantitySpinBox(obj, "SurepRadiale", self.ui1.surepRadialeSpin)
        self.entreeSpin = BQuantitySpinBox(obj, "Entree", self.ui1.entreeSpin)
        self.sortieSpin = BQuantitySpinBox(obj, "Sortie", self.ui1.sortieSpin)

        for d in Direction:
            self.ui1.directionCombo.addItem(d)
        self.ui1.directionCombo.setCurrentText(
            obj.Direction if hasattr(obj, 'Direction') else Direction[0])

        for p in Plongee:
            self.ui1.plungeCombo.addItem(p)
        self.ui1.plungeCombo.setCurrentText(
            obj.PlungeType if hasattr(obj, 'PlungeType') else Plongee[0])

        # Connexions

        self.ui1.toolDiamSpin.editingFinished.connect(lambda: self.getFields(obj))
        self.ui1.stepDownSpin.editingFinished.connect(lambda: self.getFields(obj))
        self.ui1.aeSpin.editingFinished.connect(lambda: self.getFields(obj))
        self.ui1.surepAxialeSpin.editingFinished.connect(lambda: self.getFields(obj))
        self.ui1.surepRadialeSpin.editingFinished.connect(lambda: self.getFields(obj))

        self.ui1.directionCombo.currentTextChanged.connect(self.updateObj)
        self.ui1.plungeCombo.currentTextChanged.connect(self.updateObj)

    def setFields(self, obj):
        self.toolDiamSpin.updateWidget()
        self.stepDownSpin.updateWidget()
        self.aeSpin.updateWidget()
        self.surepAxialeSpin.updateWidget()
        self.surepRadialeSpin.updateWidget()
        self.entreeSpin.updateWidget()
        self.sortieSpin.updateWidget()

    def getFields(self, obj):
        self.toolDiamSpin.updateProperty()
        self.stepDownSpin.updateProperty()
        self.aeSpin.updateProperty()
        self.surepAxialeSpin.updateProperty()
        self.surepRadialeSpin.updateProperty()
        self.entreeSpin.updateProperty()
        self.sortieSpin.updateProperty()

    def updateData(self, obj, prop):
        Log.baptDebug(f"updateData TP : prop={prop}")
        if prop in ["ToolDiameter", "StepDown", "EngagementRadial", "SurepAxiale",
                    "SurepRadiale", "Entree", "Sortie", "Direction", "PlungeType"]:
            self.setFields(obj)

    def updateObj(self):
        try:
            self.obj.ToolDiameter = self.ui1.toolDiamSpin.value()
            self.obj.StepDown = self.ui1.stepDownSpin.value()
            self.obj.EngagementRadial = self.ui1.aeSpin.value()
            self.obj.SurepAxiale = self.ui1.surepAxialeSpin.value()
            self.obj.SurepRadiale = self.ui1.surepRadialeSpin.value()
            self.obj.Direction = self.ui1.directionCombo.currentText()
            self.obj.PlungeType = self.ui1.plungeCombo.currentText()
            self.obj.touch()
            App.ActiveDocument.recompute()
        except Exception as e:
            App.Console.PrintError(f"AdaptativeOp updateObj: {e}\n")

    def accept(self):
        self.preCleanup()
        Gui.Control.closeDialog()
        self.obj.recompute()
        App.activeDocument().commitTransaction()

    def reject(self):
        self.preCleanup()
        App.ActiveDocument().abortTransaction()

        if self.deleteOnReject():
            pass
            # App.ActiveDocument.removeObject(self.obj.Name)

        Gui.Control.closeDialog()

    def preCleanup(self):
        if self.obj.Tool:
            self.obj.Tool.Visibility = False
        self.obj.ViewObject.Proxy.closeTaskPanel()


def createAdaptativeOperation(contour=None) -> Part.Feature:
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "AdaptativeOperation")

    AdaptativeOp(obj)

    if contour is not None:

        obj.Contour = contour

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
    ViewProviderAdaptiveOp(obj.ViewObject)
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.Proxy.setEdit(obj.ViewObject)
    return obj
