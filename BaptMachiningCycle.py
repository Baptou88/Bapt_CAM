import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Base

class ContournageCycle:
    """Représente un cycle d'usinage de contournage"""
    
    def __init__(self, obj):
        """Initialise l'objet de cycle de contournage"""
        # Ajouter les propriétés
        obj.Proxy = self
        self.Type = "ContournageCycle"
        
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
        
        # Utiliser PropertyString au lieu de PropertyLink pour éviter la dépendance circulaire
        if not hasattr(obj, "ContourGeometryName"):
            obj.addProperty("App::PropertyString", "ContourGeometryName", "Contour", "Nom de la géométrie du contour")
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["ToolDiameter", "CutDepth", "StepDown", "Direction", "ContourGeometryName"]:
            self.execute(obj)
    
    def execute(self, obj):
        """Mettre à jour le cycle d'usinage"""
        
        # Vérifier si le nom de la géométrie du contour est défini
        if not hasattr(obj, "ContourGeometryName") or not obj.ContourGeometryName:
            App.Console.PrintError("Aucune géométrie de contour définie.\n")
            return
        if not hasattr(obj, "ToolDiameter") or not obj.ToolDiameter:
            App.Console.PrintError("Aucun diamètre d'outil défini.\n")
            return

        if not hasattr(obj,"CutDepth") or not obj.CutDepth:
            App.Console.PrintError("Aucune profondeur de coupe définie.\n")
            return
        
        App.Console.PrintMessage(f"Exécution du cycle de contournage avec diamètre d'outil: {obj.ToolDiameter} et profondeur de coupe: {obj.CutDepth}\n")
        
        # Récupérer la géométrie du contour par son nom
        doc = obj.Document
        contour = None
        for o in doc.Objects:
            if o.Name == obj.ContourGeometryName:
                contour = o
                break
        
        if not contour:
            App.Console.PrintError(f"Impossible de trouver la géométrie du contour '{obj.ContourGeometryName}'.\n")
            return
        
        if not hasattr(contour, "Shape") or not contour.Shape:
            App.Console.PrintError("La géométrie du contour n'a pas de forme valide.\n")
            return
        
        # Créer une représentation visuelle du chemin d'usinage
        try:
            # Récupérer le fil (wire) du contour
            wire = contour.Shape
            
            # Calculer le décalage en fonction du rayon de l'outil
            offset = obj.ToolDiameter / 2.0
            
            # Déterminer la direction du décalage
            # Pour l'usinage en avalant (Climb), le décalage est vers l'intérieur pour un contour horaire
            # Pour l'usinage en opposition (Conventional), le décalage est vers l'extérieur pour un contour horaire
            direction_contour = contour.Direction
            direction_usinage = obj.Direction
            
            # Déterminer si le décalage est vers l'intérieur ou l'extérieur
            decalage_interieur = False
            if (direction_contour == "Horaire" and direction_usinage == "Climb") or \
               (direction_contour == "Anti-horaire" and direction_usinage == "Conventional"):
                decalage_interieur = True
            
            # Vérifier si le contour est fermé
            is_closed = False
            if hasattr(contour, "IsClosed"):
                is_closed = contour.IsClosed
            
            # Créer le chemin d'outil avec le décalage approprié
            path_shape = None
            
            # Si le contour est fermé, utiliser makeOffset2D
            if is_closed:
                try:
                    # Pour un décalage vers l'intérieur, la valeur est négative
                    offset_value = -offset if decalage_interieur else offset
                    
                    # Normaliser et simplifier le wire avant de tenter le décalage
                    try:
                        # Vérifier l'orientation du wire
                        is_clockwise = wire.isClockwise()
                        App.Console.PrintMessage(f"Wire original est {'horaire' if is_clockwise else 'anti-horaire'}\n")
                        
                        # Réordonner les arêtes pour s'assurer qu'elles sont connectées correctement
                        sorted_edges = Part.__sortEdges__(wire.Edges)
                        
                        # Simplifier le wire en fusionnant les segments colinéaires
                        simplified_edges = []
                        i = 0
                        while i < len(sorted_edges):
                            current_edge = sorted_edges[i]
                            # Chercher des arêtes consécutives qui peuvent être fusionnées
                            j = i + 1
                            while j < len(sorted_edges):
                                next_edge = sorted_edges[j]
                                # Vérifier si les deux arêtes sont des lignes droites
                                if (isinstance(current_edge.Curve, Part.Line) and 
                                    isinstance(next_edge.Curve, Part.Line)):
                                    # Vérifier si elles sont colinéaires
                                    v1 = current_edge.Vertexes[1].Point.sub(current_edge.Vertexes[0].Point).normalize()
                                    v2 = next_edge.Vertexes[1].Point.sub(next_edge.Vertexes[0].Point).normalize()
                                    # Si les vecteurs sont parallèles (produit scalaire proche de 1 ou -1)
                                    dot_product = abs(v1.dot(v2))
                                    if dot_product > 0.999:  # Presque parallèles
                                        # Fusionner les arêtes
                                        start_point = current_edge.Vertexes[0].Point
                                        end_point = next_edge.Vertexes[1].Point
                                        current_edge = Part.makeLine(start_point, end_point)
                                        j += 1
                                        continue
                                break
                            simplified_edges.append(current_edge)
                            i = j
                        
                        # Recréer le wire avec les arêtes simplifiées
                        if simplified_edges:
                            simplified_wire = Part.Wire(simplified_edges)
                            # Vérifier si le wire simplifié est valide
                            if simplified_wire.isClosed():
                                wire = simplified_wire
                                App.Console.PrintMessage(f"Wire simplifié créé avec {len(simplified_edges)} arêtes (original: {len(sorted_edges)})\n")
                            else:
                                App.Console.PrintMessage("Le wire simplifié n'est pas fermé, utilisation du wire original\n")
                        
                        # S'assurer que le wire a l'orientation correcte pour le décalage
                        if (decalage_interieur and not is_clockwise) or (not decalage_interieur and is_clockwise):
                            wire.reverse()
                            App.Console.PrintMessage("Wire inversé pour correspondre à la direction de décalage\n")
                    
                    except Exception as e_prep:
                        App.Console.PrintMessage(f"Erreur lors de la préparation du wire: {str(e_prep)}\n")
                    
                    # Essayer d'abord avec makeOffset2D
                    try:
                        path_shape = wire.makeOffset2D(offset_value, fill=False, join=2, openResult = True, intersection=True)
                        App.Console.PrintMessage(f"Décalage créé pour contour fermé avec makeOffset2D: {offset_value} mm\n")
                    except Exception as e1:
                        App.Console.PrintMessage(f"makeOffset2D a échoué, tentative avec Wire.makeOffset: {str(e1)}\n")
                        # Si makeOffset2D échoue, essayer avec Wire.makeOffset
                        try:
                            # Vérifier si le wire est fermé
                            if wire.isClosed():
                                # Créer une face à partir du fil
                                try:
                                    # Vérifier si le wire est planaire avant de créer une face
                                    if wire.isPlanar():
                                        face = Part.Face(wire)
                                        # Créer un fil décalé
                                        offset_wire = face.makeOffset(offset_value)
                                        if isinstance(offset_wire, list):
                                            # Si plusieurs fils sont retournés, prendre le premier
                                            if offset_wire:
                                                path_shape = offset_wire[0]
                                            else:
                                                raise Exception("Aucun fil retourné par makeOffset")
                                        else:
                                            path_shape = offset_wire
                                        App.Console.PrintMessage(f"Décalage créé pour contour fermé avec Wire.makeOffset: {offset_value} mm\n")
                                    else:
                                        # Si le wire n'est pas planaire, projeter sur le plan XY
                                        App.Console.PrintMessage("Wire non planaire détecté, projection sur le plan XY\n")
                                        projected_edges = []
                                        for edge in wire.Edges:
                                            # Projeter chaque point de l'arête sur le plan XY (z=0)
                                            if isinstance(edge.Curve, Part.Line):
                                                # Pour les lignes droites
                                                p1 = edge.Vertexes[0].Point
                                                p2 = edge.Vertexes[1].Point
                                                p1_proj = Base.Vector(p1.x, p1.y, 0)
                                                p2_proj = Base.Vector(p2.x, p2.y, 0)
                                                projected_edges.append(Part.makeLine(p1_proj, p2_proj))
                                            else:
                                                # Pour les courbes, échantillonner et projeter
                                                points = edge.discretize(20)  # Échantillonner 20 points
                                                projected_points = [Base.Vector(p.x, p.y, 0) for p in points]
                                                if len(projected_points) >= 2:
                                                    # Créer une B-spline à partir des points projetés
                                                    projected_edges.append(Part.BSplineCurve(projected_points).toShape())
                                        
                                        # Créer un nouveau wire à partir des arêtes projetées
                                        if projected_edges:
                                            projected_wire = Part.Wire(Part.__sortEdges__(projected_edges))
                                            if projected_wire.isClosed():
                                                # Créer une face à partir du wire projeté
                                                projected_face = Part.Face(projected_wire)
                                                # Créer un fil décalé
                                                offset_wire = projected_face.makeOffset(offset_value)
                                                if isinstance(offset_wire, list):
                                                    path_shape = offset_wire[0] if offset_wire else None
                                                else:
                                                    path_shape = offset_wire
                                                App.Console.PrintMessage(f"Décalage créé pour contour projeté avec Wire.makeOffset: {offset_value} mm\n")
                                            else:
                                                raise Exception("Le wire projeté n'est pas fermé")
                                        else:
                                            raise Exception("Impossible de projeter les arêtes")
                                except Exception as e2a:
                                    # Si la création de face échoue, essayer directement avec wire.makeOffset
                                    App.Console.PrintMessage(f"Création de face a échoué, tentative directe avec wire.makeOffset: {str(e2a)}\n")
                                    offset_wire = wire.makeOffset(offset_value)
                                    path_shape = offset_wire
                                    App.Console.PrintMessage(f"Décalage créé pour contour fermé avec wire.makeOffset direct: {offset_value} mm\n")
                            else:
                                # Pour un wire ouvert, utiliser directement makeOffset
                                offset_wire = wire.makeOffset(offset_value)
                                path_shape = offset_wire
                                App.Console.PrintMessage(f"Décalage créé pour contour ouvert avec wire.makeOffset: {offset_value} mm\n")
                        except Exception as e2:
                            App.Console.PrintMessage(f"Wire.makeOffset a échoué, tentative avec approche manuelle: {str(e2)}\n")
                            # Si les deux méthodes échouent, utiliser l'approche manuelle
                            edges = wire.Edges
                            offset_edges = []
                            
                            for edge in edges:
                                if isinstance(edge.Curve, Part.Line):
                                    # Pour une ligne droite
                                    p1 = edge.Vertexes[0].Point
                                    p2 = edge.Vertexes[1].Point
                                    direction = p2.sub(p1)
                                    normal = Base.Vector(-direction.y, direction.x, 0).normalize()
                                    
                                    # Inverser la normale si nécessaire
                                    if not decalage_interieur:
                                        normal = normal.negative()
                                    
                                    # Créer l'arête décalée
                                    offset_p1 = p1.add(normal.multiply(offset))
                                    offset_p2 = p2.add(normal.multiply(offset))
                                    offset_edge = Part.makeLine(offset_p1, offset_p2)
                                    offset_edges.append(offset_edge)
                                else:
                                    # Pour les courbes, convertir en Wire puis utiliser makeOffset
                                    try:
                                        # Créer un Wire à partir de l'arête individuelle
                                        temp_wire = Part.Wire([edge])
                                        # Appliquer le décalage au Wire (qui a la méthode makeOffset)
                                        offset_wire = temp_wire.makeOffset(offset_value)
                                        # Ajouter les arêtes du wire décalé
                                        for offset_edge in offset_wire.Edges:
                                            offset_edges.append(offset_edge)
                                    except Exception as e3:
                                        App.Console.PrintError(f"Erreur lors du décalage d'une courbe: {str(e3)}\n")
                                        # En cas d'erreur, utiliser l'arête originale
                                        offset_edges.append(edge)
                            
                            # Créer un fil à partir des arêtes décalées
                            try:
                                path_shape = Part.Wire(Part.__sortEdges__(offset_edges))
                                App.Console.PrintMessage("Décalage créé pour contour fermé avec approche manuelle\n")
                            except Exception as e4:
                                App.Console.PrintError(f"Erreur lors de la création du fil: {str(e4)}\n")
                                path_shape = wire.copy()
                except Exception as e:
                    App.Console.PrintError(f"Erreur lors de la création du décalage pour contour fermé: {str(e)}\n")
                    # En cas d'erreur, utiliser le contour original
                    path_shape = wire.copy()
            # Si le contour n'est pas fermé, créer un décalage manuel
            else:
                try:
                    # Créer un nouveau fil avec des arêtes décalées
                    edges = wire.Edges
                    offset_edges = []
                    
                    for edge in edges:
                        # Calculer le vecteur normal à l'arête
                        if isinstance(edge.Curve, Part.Line):
                            # Pour une ligne droite
                            p1 = edge.Vertexes[0].Point
                            p2 = edge.Vertexes[1].Point
                            direction = p2.sub(p1)
                            normal = Base.Vector(-direction.y, direction.x, 0).normalize()
                            
                            # Inverser la normale si nécessaire
                            if not decalage_interieur:
                                normal = normal.negative()
                            
                            # Créer l'arête décalée
                            offset_p1 = p1.add(normal.multiply(offset))
                            offset_p2 = p2.add(normal.multiply(offset))
                            offset_edge = Part.makeLine(offset_p1, offset_p2)
                            offset_edges.append(offset_edge)
                        else:
                            # Pour les courbes, convertir en Wire puis utiliser makeOffset
                            try:
                                # Créer un Wire à partir de l'arête individuelle
                                temp_wire = Part.Wire([edge])
                                # Appliquer le décalage au Wire (qui a la méthode makeOffset)
                                offset_wire = temp_wire.makeOffset(offset_value)
                                # Ajouter les arêtes du wire décalé
                                for offset_edge in offset_wire.Edges:
                                    offset_edges.append(offset_edge)
                            except Exception as e:
                                App.Console.PrintError(f"Erreur lors du décalage d'une courbe: {str(e)}\n")
                                # En cas d'erreur, utiliser l'arête originale
                                offset_edges.append(edge)
                    
                    # Créer un fil à partir des arêtes décalées
                    path_shape = Part.Wire(Part.__sortEdges__(offset_edges))
                    App.Console.PrintMessage("Décalage créé pour contour ouvert\n")
                except Exception as e:
                    App.Console.PrintError(f"Erreur lors de la création du décalage pour contour ouvert: {str(e)}\n")
                    # En cas d'erreur, utiliser le contour original
                    path_shape = wire.copy()
            
            # Assigner la forme au cycle de contournage
            obj.Shape = path_shape
            App.Console.PrintMessage("Chemin d'usinage créé avec succès.\n")
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la création du chemin d'usinage: {str(e)}\n")
    
    def __getstate__(self):
        """Appelé lors de la sauvegarde"""
        return {
            "Type": self.Type,
            "ContourGeometryName": getattr(self.Object, "ContourGeometryName", "")
        }
    
    def __setstate__(self, state):
        """Appelé lors du chargement"""
        if state:
            self.Type = state.get("Type", "ContournageCycle")
        return None


class ViewProviderContournageCycle:
    """Classe pour gérer l'affichage du cycle de contournage"""
    
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
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
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Contournage.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # Configuration de l'affichage
        vobj.LineColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.PointColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.LineWidth = 2.0
        vobj.PointSize = 4.0
    
    def updateData(self, obj, prop):
        """Appelé lorsqu'une propriété de l'objet est modifiée"""
        # Mettre à jour l'affichage si une propriété liée à la trajectoire change
        if prop in ["ToolDiameter", "Direction", "ContourGeometryName"]:
            # Recalculer la trajectoire
            obj.Proxy.execute(obj)
    
    def onChanged(self, vobj, prop):
        """Appelé lorsqu'une propriété du ViewProvider est modifiée"""
        # Mettre à jour l'affichage si une propriété d'affichage change
        if prop in ["ShowToolPath", "PathColor", "PathWidth"]:
            # Appliquer les nouvelles propriétés d'affichage
            if hasattr(vobj, "LineColor") and hasattr(vobj, "PathColor"):
                vobj.LineColor = vobj.PathColor
            
            if hasattr(vobj, "LineWidth") and hasattr(vobj, "PathWidth"):
                vobj.LineWidth = vobj.PathWidth
    
    def claimChildren(self):
        """Retourne les enfants de cet objet"""
        # Ne pas réclamer la géométrie du contour comme enfant
        # car c'est le contour qui doit être l'enfant de la géométrie
        return []
    
    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâche pour l'édition"""
        import BaptContournageTaskPanel
        taskd = BaptContournageTaskPanel.ContournageTaskPanel(self.Object)
        Gui.Control.showDialog(taskd)
        return True
    
    def unsetEdit(self, vobj, mode=0):
        """Ferme le panneau de tâche"""
        Gui.Control.closeDialog()
        return True
    
    def doubleClicked(self, vobj):
        """Appelé lorsque l'objet est double-cliqué"""
        # Ouvrir le panneau de tâche pour l'édition
        self.setEdit(vobj)
        return True
    
    def getDisplayModes(self, vobj):
        """Retourne les modes d'affichage disponibles"""
        return ["Flat Lines", "Shaded", "Wireframe"]
    
    def getDefaultDisplayMode(self):
        """Retourne le mode d'affichage par défaut"""
        return "Flat Lines"
    
    def setDisplayMode(self, mode):
        """Définit le mode d'affichage"""
        return mode
    
    def __getstate__(self):
        """Appelé lors de la sauvegarde"""
        return {"ObjectName": self.Object.Name if self.Object else None}
    
    def __setstate__(self, state):
        """Appelé lors du chargement"""
        if state and "ObjectName" in state and state["ObjectName"]:
            self.Object = App.ActiveDocument.getObject(state["ObjectName"])
        return None
