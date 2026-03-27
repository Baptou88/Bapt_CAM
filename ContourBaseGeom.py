import FreeCAD as App
import Part
import sys

DEBUG = False


class ContourBaseGeom:
    def __init__(self, obj):
        self.Object = obj

        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyEnumeration", "DepthMode", "Contour", "Mode de profondeur (Absolu ou Relatif)")
            obj.DepthMode = ["Absolu", "Relatif"]
            obj.DepthMode = "Absolu"

        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Contour", "Direction de parcours du contour")
            obj.Direction = ["Horaire", "Anti-horaire"]
            obj.Direction = "Horaire"

        if not hasattr(obj, "CoteMatiere"):
            obj.addProperty("App::PropertyEnumeration", "CoteMatiere", "Contour",
                            "Côté matière par rapport au sens de parcours du contour")
            obj.CoteMatiere = ["Gauche", "Droite"]
            obj.CoteMatiere = "Droite"

            # proprité read only pour savoir si un contour est fermé
        if not hasattr(obj, "IsClosed"):
            obj.addProperty("App::PropertyBool", "IsClosed", "Contour", "Indique si le contour est fermé")
            obj.IsClosed = False

        if not hasattr(obj, "testShape"):
            obj.addProperty("Part::PropertyPartShape", "testShape", "Subsection", "Description for tooltip")
            obj.testShape = Part.Shape()

        if not hasattr(obj, "debugArrow"):
            obj.addProperty("App::PropertyBool", "debugArrow", "debug", "Description for tooltip")
            obj.debugArrow = True

    def getEdges(self, obj):
        raise NotImplementedError("La méthode getEdges doit être implémentée dans la classe dérivée.")

    def getDepths(self):
        raise NotImplementedError("La méthode getDepths doit être implémentée dans la classe dérivée.")

    def getWireAtZ(self, obj, z):
        """Retourne le wire 2D correspondant à une profondeur z.

        Par défaut, retourne le wire à Zref (profil constant quelle que soit Z).
        Les classes dérivées avec profil variable (ex. Contour25DGeom) surchargent.
        """
        zref = self.getDepths()[0]
        if not obj.Shape or not obj.Shape.Wires:
            return None
        for w in obj.Shape.Wires:
            if w.Edges and abs(w.Edges[0].Vertexes[0].Point.z - zref) < 1e-3:
                return w
        return obj.Shape.Wires[0] if obj.Shape.Wires else None

    def execute(self, obj):
        """Mettre à jour la représentation visuelle du contour"""
        if App.ActiveDocument.Restoring:
            return

        try:

            edges = self.getEdges(obj)

            if not edges:
                # App.Console.PrintError("Aucune arête valide trouvée.\n")
                return

            # App.Console.PrintMessage(f"Nombre d'arêtes collectées: {len(edges)}\n")

            # Vérifier si une arête est sélectionnée
            # selected_index = -1
            # if hasattr(obj, "SelectedEdgeIndex"):
            #     selected_index = obj.SelectedEdgeIndex

            # Créer des arêtes ajustées à la hauteur Zref et à depth
            adjusted_edges_zref = []
            adjusted_edges_depth = []

            # Créer des flèches pour indiquer la direction
            direction_arrows = []

            if obj.Direction == "Anti-horaire":
                edges.reverse()

            # sorted_edges = self.order_edges(edges)  # Trier les arêtes par ordre croissant de edges
            # sorted_edges = Part.__sortEdges__(edges)
            sorted_edges = Part.sortEdges(list(edges))[0]  # https://github.com/FreeCAD/FreeCAD/commit/1031644fa
            # sorted_edges = Part.getSortedClusters(list(edges))[0]
            # sorted_edges = edges.copy()  # Faire une copie des arêtes pour le tri
            # sorted_edges = edges

            if obj.Direction == "Anti-horaire":
                sorted_edges.reverse()

            if DEBUG:
                self.debugEdges(sorted_edges, "Sorted Edges")

            if not sorted_edges:
                App.Console.PrintError("Aucune arête valide après le tri.\n")
                obj.Shape = Part.Shape()  # Shape vide
                obj.testShape = Part.Shape()
                obj.IsClosed = False
                return

            depths = self.getDepths()

            for i, edge in enumerate(sorted_edges):
                # Créer des arêtes ajustées avec des couleurs différentes selon la sélection
                # Pour l'arête sélectionnée, utiliser une couleur différente et une largeur plus grande

                # if edge.Vertexes[0].Orientation == "Reversed":
                #     App.Console.PrintMessage(f"Edge {i} est inversée, inversion de l'arête pour correspondre au sens.\n")
                #     edge = edge.reversed()
                current_edge = edge
                bon_sens = None
                if i < len(sorted_edges) - 1:
                    next_edge = sorted_edges[i + 1]
                    if current_edge.Vertexes[-1].Point.distanceToPoint(next_edge.Vertexes[0].Point) < 1e-6:
                        bon_sens = True
                        # App.Console.PrintMessage(f"Edge {i} est dans le bon sens.\n")
                    elif current_edge.Vertexes[-1].Point.distanceToPoint(next_edge.Vertexes[-1].Point) < 1e-6:
                        bon_sens = True
                        # App.Console.PrintMessage(f"Edge {i} Ok ,Edge {i+1} est inversée, inversion de l'arête pour correspondre au sens.\n")
                    elif current_edge.Vertexes[0].Point.distanceToPoint(next_edge.Vertexes[-1].Point) < 1e-6:
                        bon_sens = False
                        # App.Console.PrintMessage(f"Edge {i} et Edge {i+1} sont inversées, inversion de l'arête pour correspondre au sens.\n")
                    elif current_edge.Vertexes[0].Point.distanceToPoint(next_edge.Vertexes[0].Point) < 1e-6:
                        bon_sens = False
                        # App.Console.PrintMessage(f"Edge {i} est inversée, inversion de l'arête pour correspondre au sens.\n")
                    else:
                        # App.Console.PrintMessage(f"Edge {i} n'est pas connectée à l'arête suivante, le contour ne sera pas fermé.\n")
                        pass
                else:
                    prev_edge = sorted_edges[i - 1]

                    if prev_edge.Vertexes[-1].Point.distanceToPoint(current_edge.Vertexes[0].Point) < 1e-6:
                        bon_sens = True
                        # App.Console.PrintMessage(f"Edge {i} est dans le bon sens.\n")
                    elif prev_edge.Vertexes[-1].Point.distanceToPoint(current_edge.Vertexes[-1].Point) < 1e-6:
                        bon_sens = False
                        # App.Console.PrintMessage(f"Edge {i} NOk ,Edge {i-1} est inversée, inversion de l'arête pour correspondre au sens.\n")
                    elif prev_edge.Vertexes[0].Point.distanceToPoint(current_edge.Vertexes[-1].Point) < 1e-6:
                        bon_sens = False
                        # App.Console.PrintMessage(f"Edge {i} et Edge {i-1} sont inversées, inversion de l'arête pour correspondre au sens.\n")
                    elif prev_edge.Vertexes[0].Point.distanceToPoint(current_edge.Vertexes[0].Point) < 1e-6:
                        bon_sens = True
                        # App.Console.PrintMessage(f"Edge {i} Ok, inversion de l'arête pour correspondre au sens.\n")
                    else:
                        # App.Console.PrintMessage(f"Edge {i} n'est pas connectée à l'arête suivante, le contour ne sera pas fermé.\n")
                        pass

                if DEBUG:
                    self.debugEdge(edge, i, "")

                # Créer une flèche pour indiquer la direction de l'arête
                arrow = self._create_direction_arrow(obj, edge, depths[0], size=2.0, invert_direction=(bon_sens is not None and not bon_sens))
                if arrow:
                    direction_arrows.append(arrow)

                edge_zref = edge.copy().translate(App.Vector(0, 0, depths[0] - edge.Vertexes[0].Z))

                edge_zfinal = edge.copy().translate(App.Vector(0, 0, depths[0] - edge.Vertexes[0].Z - depths[1] if obj.DepthMode == "Relatif" else depths[1] - edge.Vertexes[0].Z))
                adjusted_edges_zref.append(edge_zref)
                adjusted_edges_depth.append(edge_zfinal)

            # self.debugEdge(adjusted_edges_zref, "Zref")

            try:
                # Créer le fil à Zref
                wire_zref = Part.Wire(adjusted_edges_zref)

                # Créer le fil à depth
                wire_zfinal = Part.Wire(adjusted_edges_depth)

                # Créer les faces entre les arêtes correspondantes
                faces = []
                if len(adjusted_edges_zref) == len(adjusted_edges_depth):
                    for i in range(len(adjusted_edges_zref)):
                        try:
                            face = Part.makeRuledSurface(adjusted_edges_zref[i], adjusted_edges_depth[i])
                            faces.append(face)
                        except Exception as e:
                            App.Console.PrintError(f"Impossible de créer une face entre les arêtes {i}: {str(e)}\n")
                else:
                    App.Console.PrintError("Les listes d'arêtes ajustées n'ont pas la même taille, impossible de créer les faces.\n")

                first_point = wire_zref.Edges[0].Vertexes[0].Point
                sph = Part.makeSphere(2, first_point)

                # Créer un compound contenant les deux fils, les flèches et les faces
                shapes = [wire_zref, wire_zfinal]
                # shapes = [wire_zref]

                if obj.debugArrow:
                    shapes.extend(direction_arrows)
                    shapes.append(sph)

                shapes.extend(faces)  # Ajouter les faces ici
                compound = Part.makeCompound(shapes)
                obj.Shape = compound
                obj.testShape = compound

                # Vérifier si le fil est fermé (utiliser le fil à Zref pour cette vérification)
                if wire_zref.isClosed():
                    obj.IsClosed = True
                else:
                    obj.IsClosed = False

                # prefs = BaptPreferences()

                # autoRecomputeChildren = prefs.getAutoChildUpdate()
                # if autoRecomputeChildren:
                #     for child in obj.Group:
                #         child.recompute()

            except Exception as e:
                App.Console.PrintError(f"Impossible de créer un fil à partir des arêtes sélectionnées: {str(e)}\n")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                line_number = exc_traceback.tb_lineno
                App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
                App.Console.PrintError("[DEBUG] Les arêtes transmises à Part.Wire ne sont pas chaînées ou sont invalides.\n")
                # Essayer de créer une forme composite si le fil échoue
                try:
                    all_edges = adjusted_edges_zref
                    all_edges.extend(adjusted_edges_depth)
                    compound = Part.makeCompound(all_edges)
                    obj.Shape = compound
                    obj.testShape = compound
                    # App.Console.PrintMessage("Forme composite créée à la place du fil.\n")
                    return
                except Exception:
                    # App.Console.PrintError(f"Impossible de créer une forme composite: {str(e2)}\n")
                    return

        except Exception as e:
            App.Console.PrintError(f"Erreur lors de l'exécution: {str(e)}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")

    def _create_direction_arrow(self, obj, edge, zref, size=2.0, invert_direction=False):
        """Crée une petite flèche au milieu de l'arête pour indiquer la direction

        Args:
            edge: L'arête d'origine
            size: Taille de la flèche en mm
            invert_direction: Si True, inverse la direction de la flèche

        Returns:
            Shape représentant la flèche
        """
        try:
            # Point milieu paramétrique
            mid_param = (edge.FirstParameter + edge.LastParameter) / 2.0
            mid_point = edge.valueAt(mid_param)
            mid_point_z = App.Vector(mid_point.x, mid_point.y, zref)

            # Tangente au point milieu (direction géométrique de l'arête)
            tangent = edge.tangentAt(mid_param)
            if tangent.Length < 1e-9:
                tangent = App.Vector(1, 0, 0)
            tangent = tangent.normalize()

            # Appliquer l'inversion pour la direction de parcours réelle
            if invert_direction:
                tangent = App.Vector(-tangent.x, -tangent.y, -tangent.z)

            # Tangente projetée XY (direction réelle de parcours)
            tangent_z = App.Vector(tangent.x, tangent.y, 0.0)
            if tangent_z.Length < 1e-9:
                tangent_z = App.Vector(1, 0, 0)
            tangent_z = tangent_z.normalize()

            # Normale (perpendiculaire gauche) basée sur la direction de parcours réelle
            # Utilisée pour les pointes de flèche
            normal_xy = App.Vector(-tangent_z.y, tangent_z.x, 0.0)
            if normal_xy.Length < 1e-9:
                normal_xy = App.Vector(0, 1, 0)
            normal_xy = normal_xy.normalize()

            # Décalage côté matière : basé sur la direction de parcours réelle
            # normal_xy = perpendiculaire GAUCHE du sens de parcours
            # Les flèches sont placées CÔTÉ MATIÈRE pour visualisation :
            #   CoteMatiere Droite → matière à droite → flèches à droite (offset négatif = -normal_xy)
            #   CoteMatiere Gauche → matière à gauche → flèches à gauche (offset positif = normal_xy)
            offset_distance = size * 0.6
            if hasattr(obj, "CoteMatiere") and obj.CoteMatiere == "Droite":
                offset_distance = -offset_distance

            # Point milieu décalé le long de la normale
            shifted_mid = mid_point_z.add(App.Vector(normal_xy.x * offset_distance,
                                                     normal_xy.y * offset_distance,
                                                     0.0))

            # Construire la flèche centrée sur shifted_mid, orientée selon la tangente de parcours
            half_t = App.Vector(tangent_z.x * size / 2.0, tangent_z.y * size / 2.0, 0.0)
            start_point = shifted_mid - half_t
            end_point = shifted_mid + half_t

            arrow_line = Part.makeLine(start_point, end_point)

            # Pointe de la flèche (petites lignes perpendiculaires)
            third_t = App.Vector(tangent_z.x * size / 3.0, tangent_z.y * size / 3.0, 0.0)
            quarter_n = App.Vector(normal_xy.x * size / 4.0, normal_xy.y * size / 4.0, 0.0)

            arrow_p1 = end_point - third_t + quarter_n
            arrow_p2 = end_point - third_t - quarter_n

            # perp_line = Part.makeLine(mid_point, shifted_mid )

            arrow_line1 = Part.makeLine(end_point, arrow_p1)
            arrow_line2 = Part.makeLine(end_point, arrow_p2)

            arrow_shape = Part.makeCompound([arrow_line, arrow_line1, arrow_line2])
            return arrow_shape

        except Exception as e:
            App.Console.PrintWarning(f"Erreur lors de la création de la flèche: {str(e)}\n")
            return None
