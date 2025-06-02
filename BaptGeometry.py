import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from FreeCAD import Base
from PySide import QtCore, QtGui
import math
import sys
import BaptUtilities

try:
    from pivy import coin
except ImportError:
    App.Console.PrintError("Impossible d'importer le module coin. La mise en surbrillance des arêtes ne fonctionnera pas correctement.\n")

class DrillGeometry:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        
        self.Type = "DrillGeometry"
        
        #obj.addExtension("App::GroupExtensionPython")
        #obj.addExtension("App::DocumentObjectGroupPython")
        #obj.addExtension("App::LinkExtensionPython")
        

        # Référence aux faces sélectionnées
        if not hasattr(obj, "DrillFaces"):
            obj.addProperty("App::PropertyLinkSubList", "DrillFaces", "Drill", "Selected drill faces")
        
        # Liste des positions de perçage
        if not hasattr(obj, "DrillPositions"):
            obj.addProperty("App::PropertyVectorList", "DrillPositions", "Drill", "Drill positions")
        
        # Diamètre des perçages (détecté automatiquement)
        if not hasattr(obj, "DrillDiameter"):
            obj.addProperty("App::PropertyLength", "DrillDiameter", "Drill", "Detected drill diameter")
            obj.setEditorMode("DrillDiameter", 1)  # en lecture seule
        
        # Profondeur des perçages (détectée automatiquement)
        if not hasattr(obj, "DrillDepth"):
            obj.addProperty("App::PropertyLength", "DrillDepth", "Drill", "Detected drill depth")
            obj.setEditorMode("DrillDepth", 1)  # en lecture seule
        
        # Taille des sphères de visualisation
        if not hasattr(obj, "MarkerSize"):
            obj.addProperty("App::PropertyLength", "MarkerSize", "Display", "Size of position markers")
            obj.MarkerSize = 2.0  # 2mm par défaut
        
        # Couleur des sphères
        if not hasattr(obj, "MarkerColor"):
            obj.addProperty("App::PropertyColor", "MarkerColor", "Display", "Color of position markers")
            obj.MarkerColor = (1.0, 0.0, 0.0)  # Rouge par défaut
        
        # Index de la position sélectionnée (-1 si aucune)
        if not hasattr(obj, "SelectedPosition"):
            obj.addProperty("App::PropertyInteger", "SelectedPosition", "Display", "Index of the selected position")
            obj.SelectedPosition = -1
        
        # Couleur de surbrillance pour la position sélectionnée
        if not hasattr(obj, "HighlightColor"):
            obj.addProperty("App::PropertyColor", "HighlightColor", "Display", "Color of the highlighted position")
            obj.HighlightColor = (1.0, 1.0, 0.0)  # Jaune par défaut
        
        # Créer ou obtenir l'objet de visualisation
        #self.getOrCreateVisualObject(obj)

        obj.Proxy = self

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "DrillFaces":
            self.updateDrillParameters(obj)
        elif prop in ["DrillPositions", "MarkerSize", "SelectedPosition"]:
            self.execute(obj)

    def updateDrillParameters(self, obj):
        """Met à jour les paramètres de perçage en fonction des faces sélectionnées"""
        if not obj.DrillFaces:
            return

        positions = []
        diameters = set()
        depths = set()

        for link, subs in obj.DrillFaces:
            # Pour chaque sous-élément dans la liste
            for subname in subs:
                # Obtenir la face
                face = getattr(link.Shape, subname)
                
                if face.Surface.TypeId == 'Part::GeomCylinder':
                    # Récupérer le centre de la face cylindrique
                    center = face.Surface.Center
                    axis = face.Surface.Axis
                    
                    # Trouver le point le plus haut de la face
                    z_max = float('-inf')
                    for vertex in face.Vertexes:
                        if vertex.Point.z > z_max:
                            z_max = vertex.Point.z
                    
                    # Créer le point au sommet en gardant X,Y du centre
                    pos = App.Vector(center.x, center.y, z_max)
                    positions.append(pos)
                    
                    # Récupérer le diamètre
                    diameters.add(face.Surface.Radius * 2)
                    App.Console.PrintMessage(f'diam detected {face.Surface.Radius * 2}\n')
                    # Calculer la profondeur en trouvant la face plane associée
                    # TODO: Implémenter la détection de profondeur
                    depths.add(10.0)  # valeur temporaire

        # Mettre à jour les propriétés
        obj.DrillPositions = positions
        
        # Si tous les perçages ont le même diamètre, le définir
        if len(diameters) == 1:
            obj.DrillDiameter = list(diameters)[0]
        elif len(diameters) > 1:
            #sinon prendre le plus petit
            obj.DrillDiameter = min(diameters)
            
        # Si tous les perçages ont la même profondeur, la définir
        if len(depths) == 1:
            obj.DrillDepth = list(depths)[0]

    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        # Obtenir l'objet de visualisation
        #visual = self.getOrCreateVisualObject(obj)
        
        if not obj.DrillPositions:
            obj.Shape = Part.Shape()  # Shape vide
            return

        # Créer une sphère pour chaque position
        spheres = []
        highlighted_spheres = []  # Liste séparée pour les sphères en surbrillance
        radius = obj.MarkerSize / 2.0  # Rayon = moitié de la taille
        
        for i, pos in enumerate(obj.DrillPositions):
            # Utiliser la couleur de surbrillance pour la position sélectionnée
            if i == obj.SelectedPosition:
                # Créer une sphère légèrement plus grande pour la position sélectionnée
                highlight_radius = radius * 1.5
                sphere = Part.makeSphere(highlight_radius, pos)
                # Stocker l'index pour l'utiliser dans ViewProvider
                sphere.Tag = i  # Utiliser Tag pour stocker l'index
                highlighted_spheres.append(sphere)  # Ajouter à la liste des sphères en surbrillance
            else:
                sphere = Part.makeSphere(radius, pos)
                sphere.Tag = i  # Stocker l'index
                spheres.append(sphere)
        
        # Fusionner toutes les sphères
        if spheres or highlighted_spheres:
            # Créer un compound pour les sphères normales
            normal_compound = Part.makeCompound(spheres) if spheres else Part.Shape()
            
            # Créer un compound pour les sphères en surbrillance
            highlight_compound = Part.makeCompound(highlighted_spheres) if highlighted_spheres else Part.Shape()
            
            # Stocker les deux compounds dans des propriétés de l'objet
            if not hasattr(obj, "NormalSpheres"):
                obj.addProperty("App::PropertyPythonObject", "NormalSpheres", "Visualization", "Normal spheres")
            obj.NormalSpheres = normal_compound
            
            if not hasattr(obj, "HighlightedSpheres"):
                obj.addProperty("App::PropertyPythonObject", "HighlightedSpheres", "Visualization", "Highlighted spheres")
            obj.HighlightedSpheres = highlight_compound
            
            # Combiner les deux compounds
            all_spheres = spheres + highlighted_spheres
            compound = Part.makeCompound(all_spheres)
            obj.Shape = compound

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def onBeforeDelete(self, obj, subelements):
        # Custom logic before deletion
        App.Console.PrintMessage("Object is about to be deleted: " + obj.Name + "\n")
        

class ViewProviderDrillGeometry:
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
    def getIcon(self):
        """Retourne l'icône"""
        return BaptUtilities.getIconPath("Tree_Drilling.svg")
        
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # Définir la couleur de l'objet de visualisation
        self.updateColors()

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True

    def updateData(self, obj, prop):
        """Appelé quand une propriété de l'objet est modifiée"""
        # Si un nouvel objet de visualisation est ajouté, définir sa couleur
        if prop == "Group":
            self.updateColors()
        # Si la position sélectionnée change, mettre à jour les couleurs
        elif prop in ["SelectedPosition", "MarkerColor", "HighlightColor"]:
            self.updateColors()

    def updateColors(self):
        """Met à jour les couleurs des marqueurs visuels"""
        if not hasattr(self, "Object") or not self.Object:
            return
            
        # Vérifier si l'objet visuel existe
        # visual = None
        # for child in self.Object.Group:
        #     if child.Name.startswith("DrillVisual") and hasattr(child, "ViewObject"):
        #         visual = child
        #         break
                
        # if not visual:
        #     return
            
        # Définir les couleurs en fonction de la position sélectionnée
        if hasattr(self.Object, "SelectedPosition") and self.Object.SelectedPosition >= 0:
            # Vérifier si l'objet visuel a des sphères en surbrillance
            if hasattr(self.Object, "HighlightedSpheres") and self.Object.HighlightedSpheres:
                # Utiliser un ShapeColorExtension pour colorer individuellement les sous-éléments
                if hasattr(self.Object.ViewObject, "DiffuseColor"):
                    # Créer une liste de couleurs pour chaque sous-élément
                    colors = []
                    
                    # Couleur normale pour les sphères normales
                    normal_color = self.Object.MarkerColor
                    
                    # Couleur de surbrillance pour les sphères en surbrillance
                    highlight_color = self.Object.HighlightColor
                    
                    # Appliquer les couleurs appropriées
                    if hasattr(self.Object, "NormalSpheres") and self.Object.NormalSpheres:
                        # Nombre de sous-éléments dans les sphères normales
                        if hasattr(self.Object.NormalSpheres, "SubShapes"):
                            normal_count = len(self.Object.NormalSpheres.SubShapes)
                        else:
                            normal_count = 1
                        
                        # Ajouter la couleur normale pour chaque sphère normale
                        colors.extend([normal_color] * normal_count)
                    
                    # Ajouter la couleur de surbrillance pour chaque sphère en surbrillance
                    if hasattr(self.Object, "HighlightedSpheres") and self.Object.HighlightedSpheres:
                        if hasattr(self.Object.HighlightedSpheres, "SubShapes"):
                            highlight_count = len(self.Object.HighlightedSpheres.SubShapes)
                        else:
                            highlight_count = 1
                        
                        colors.extend([highlight_color] * highlight_count)
                    
                    # Appliquer les couleurs
                    self.Object.ViewObject.DiffuseColor = colors
            else:
                # Aucune sphère en surbrillance, utiliser la couleur normale pour tout
                self.Object.ViewObject.ShapeColor = self.Object.MarkerColor
        else:
            # Aucune position sélectionnée, utiliser la couleur normale pour tout
            self.Object.ViewObject.ShapeColor = self.Object.MarkerColor

    def onChanged(self, vobj, prop):
        """Appelé quand une propriété du ViewProvider est modifiée"""
        pass

    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
        import BaptDrillTaskPanel
        panel = BaptDrillTaskPanel.DrillGeometryTaskPanel(vobj.Object)
        Gui.Control.showDialog(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Fermer l'éditeur"""
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        return True

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def claimChildren(self):
        """Retourne les enfants de cet objet"""
        #debug
        App.Console.PrintMessage(f"claimChildren de {self.Object.Name}\n")
        children = []
        # Récupérer tous les objets de contournage qui référencent cette géométrie par son nom
        if self.Object:
            doc = self.Object.Document
            if not doc:
                return children
                
            # Vérifier que l'objet a un nom valide
            if not hasattr(self.Object, "Name") or not self.Object.Name:
                return children
                
            for obj in doc.Objects:
                # Vérifier si l'objet est un cycle de contournage
                if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type") and obj.Proxy.Type == "DrillOperation":
                    # Vérifier si l'objet référence cette géométrie
                    if hasattr(obj, "DrillGeometryName") and obj.DrillGeometryName == self.Object.Name:
                        children.append(obj)
                        
            # Vérifier si l'objet a un groupe
            if hasattr(self.Object, "Group"):
                # Ajouter tous les objets du groupe qui ne sont pas déjà dans la liste
                for obj in self.Object.Group:
                    if obj not in children:
                        children.append(obj)
                        
        return children
    
    def onBeforeDelete(self, obj, subelements):
        """Supprime tous les enfants lors de la suppression du parent"""
        #debug
        App.Console.PrintMessage(f"onBeforeDelete de {obj.Name}\n")
        children = self.claimChildren()
        for child in children:
            try:
                if child and hasattr(child, "Document") and child.Document:
                    child.Document.removeObject(child.Name)
            except Exception as e:
                App.Console.PrintError(f"Erreur suppression enfant {child.Name}: {e}\n")

class ContourGeometry:
    """Classe pour gérer les contours d'usinage"""
    
    def __init__(self, obj):
        """Ajoute les propriétés"""
        
        self.Type = "ContourGeometry"
        
        # Transformer l'objet en groupe
        #obj.addExtension("App::GroupExtensionPython", None)
        # obj.addExtension("App::GroupExtensionPython")
        #DocumentObjectGroupPython
        
        # Permettre les références à des objets en dehors du groupe
        #obj.addExtension("App::LinkExtensionPython", None)
        #obj.addExtension("App::LinkExtensionPython")
        #obj.addProperty("App::PropertyLinkList", "Group", "Base", "Groupe d'objets géométriques")
        
        # Propriétés pour stocker les arêtes sélectionnées
        if not hasattr(obj, "Edges"):
            obj.addProperty("App::PropertyLinkSubList", "Edges", "Contour", "Arêtes sélectionnées pour le contour")
        
        if not hasattr(obj, "Zref"):
            obj.addProperty("App::PropertyFloat", "Zref", "Contour", "Hauteur de référence")
            obj.Zref = 0.0
        
        if not hasattr(obj, "depth"):
            obj.addProperty("App::PropertyFloat", "depth", "Contour", "Hauteur finale")
            obj.depth = 0.0
        
        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyEnumeration", "DepthMode", "Contour", "Mode de profondeur (Absolu ou Relatif)")
            obj.DepthMode = ["Absolu", "Relatif"]
            obj.DepthMode = "Absolu"
        
        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Contour", "Direction d'usinage")
            obj.Direction = ["Horaire", "Anti-horaire"]
            obj.Direction = "Horaire"

        #proprité read only pour savoir si un contour est fermé 
        if not hasattr(obj, "IsClosed"):
            obj.addProperty("App::PropertyBool", "IsClosed", "Contour", "Indique si le contour est fermé")
            obj.IsClosed = False
        
        # Créer une forme vide
        obj.Shape = Part.Shape()

        obj.Proxy = self

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        #return
        # App.Console.PrintMessage('Restoring ContourGeometry\n')
        # children = []
        # if hasattr(obj, "Group"):
        #     App.Console.PrintMessage(f"ContourGeometry {obj.Name} a un groupe\n")
        #     for child in obj.Group:
        #         App.Console.PrintMessage(f"Enfant: {child.Name}\n")
        #         children.append(child)
        self.__init__(obj)
        # obj.Group = children
        
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["DepthMode"]:
            App.Console.PrintMessage('changement \n')
            if obj.DepthMode == "Relatif":
                obj.depth = obj.depth - obj.Zref
            else:
                obj.depth = obj.Zref + obj.depth
            App.Console.PrintMessage(' fin changement \n')
            self.execute(obj)
        elif prop in ["Edges", "Zref", "Direction", "depth"]:
            self.execute(obj)
        elif prop == "SelectedEdgeIndex":
            # Mettre à jour les couleurs des arêtes lorsque la sélection change
            self.updateEdgeColors(obj)

    def execute(self, obj):
        """Mettre à jour la représentation visuelle du contour"""
        if App.ActiveDocument.Restoring:
            return
        try:
            if not hasattr(obj, "Edges") or not obj.Edges:
                App.Console.PrintMessage("Aucune arête sélectionnée pour le contour.\n")
                return
            
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
                            #App.Console.PrintMessage(f"Arête ajoutée: {sub_name} de {obj_ref.Name}\n")
                        except Exception as e:
                            App.Console.PrintError(f"Execute : Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
            
            if not edges:
                App.Console.PrintError("Aucune arête valide trouvée.\n")
                return
            
            #App.Console.PrintMessage(f"Nombre d'arêtes collectées: {len(edges)}\n")
            
            # Vérifier si une arête est sélectionnée
            selected_index = -1
            if hasattr(obj, "SelectedEdgeIndex"):
                selected_index = obj.SelectedEdgeIndex
            
            # Créer des arêtes ajustées à la hauteur Zref et à depth
            adjusted_edges_zref = []
            adjusted_edges_depth = []
            
            # Créer des flèches pour indiquer la direction
            direction_arrows = []
            
            for i, edge in enumerate(edges):
                # Créer des arêtes ajustées avec des couleurs différentes selon la sélection
                
                # Pour l'arête sélectionnée, utiliser une couleur différente et une largeur plus grande
                edge_zref = self._create_adjusted_edge(edge, obj.Zref, selected= (i == selected_index))

                if obj.DepthMode == "Relatif":
                    edge_zfinal = self._create_adjusted_edge(edge, obj.Zref + obj.depth, selected=(i == selected_index))
                else:
                    edge_zfinal = self._create_adjusted_edge(edge, obj.depth, selected=(i == selected_index))
                
                adjusted_edges_zref.append(edge_zref)
                adjusted_edges_depth.append(edge_zfinal)
                
                # Créer une flèche pour indiquer la direction de l'arête
                arrow = self._create_direction_arrow(edge, obj.Zref, size=2.0)
                if arrow:
                    direction_arrows.append(arrow)
            
            try:
                # Créer le fil à Zref
                wire_zref = Part.Wire(adjusted_edges_zref)
                
                # Créer le fil à depth
                wire_zfinal = Part.Wire(adjusted_edges_depth)
                
                # Créer un compound contenant les deux fils et les flèches
                shapes = [wire_zref, wire_zfinal]
                shapes.extend(direction_arrows)
                compound = Part.makeCompound(shapes)
                obj.Shape = compound
                
                # Vérifier si le fil est fermé (utiliser le fil à Zref pour cette vérification)
                if wire_zref.isClosed():
                    obj.IsClosed = True
                else:
                    obj.IsClosed = False
                
            except Exception as e:
                App.Console.PrintError(f"Impossible de créer un fil à partir des arêtes sélectionnées: {str(e)}\n")
                # Essayer de créer une forme composite si le fil échoue
                try:
                    all_edges = adjusted_edges_zref
                    all_edges.extend(adjusted_edges_depth)
                    compound = Part.makeCompound(all_edges)
                    obj.Shape = compound
                    App.Console.PrintMessage("Forme composite créée à la place du fil.\n")
                    return
                except Exception as e2:
                    App.Console.PrintError(f"Impossible de créer une forme composite: {str(e2)}\n")
                    return
            
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de l'exécution: {str(e)}\n")
    
    def _create_adjusted_edge(self, edge, z_value, selected=False):
        """Crée une arête ajustée à une hauteur Z spécifique avec une couleur optionnelle
        
        Args:
            edge: L'arête d'origine
            z_value: Valeur Z à appliquer
            selected: Si True, l'arête est sélectionnée et aura une apparence différente
            
        Returns:
            Nouvelle arête ajustée
        """
        new_edge = None
        
        if isinstance(edge.Curve, Part.Line):
            # Pour une ligne droite
            p1 = edge.Vertexes[0].Point
            p2 = edge.Vertexes[1].Point
            # Créer de nouveaux points avec Z = z_value
            new_p1 = App.Vector(p1.x, p1.y, z_value)
            new_p2 = App.Vector(p2.x, p2.y, z_value)
            # Créer une nouvelle ligne
            new_edge = Part.makeLine(new_p1, new_p2)
        elif isinstance(edge.Curve, Part.Circle):
            # Pour un arc ou un cercle
            circle = edge.Curve
            center = circle.Center
            new_center = App.Vector(center.x, center.y, z_value)
            # Créer un nouvel axe Z
            new_axis = App.Vector(0, 0, 1)
            radius = circle.Radius
            
            # Créer un nouveau cercle
            new_circle = Part.Circle(new_center, new_axis, radius)
            
            # Vérifier si c'est un arc (pas un cercle complet) en utilisant les paramètres
            # au lieu des attributs AngleXU et AngleXV qui peuvent ne pas exister
            try:
                if hasattr(edge, "FirstParameter") and hasattr(edge, "LastParameter"):
                    first_param = edge.FirstParameter
                    last_param = edge.LastParameter
                    
                    # Si les paramètres sont différents, c'est un arc
                    if abs(last_param - first_param) < 6.28:  # Moins que 2*pi
                        new_edge = Part.Edge(new_circle, first_param, last_param)
                    else:
                        # Cercle complet
                        new_edge = Part.Edge(new_circle)
                else:
                    # Cercle complet par défaut
                    new_edge = Part.Edge(new_circle)
            except Exception as e:
                App.Console.PrintWarning(f"Erreur lors de la création d'un arc: {str(e)}. Création d'un cercle complet.\n")
                new_edge = Part.Edge(new_circle)
        else:
            # Pour les autres types de courbes, utiliser une approximation par points
            points = []
            for i in range(10):  # Utiliser 10 points pour l'approximation
                param = edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * i / 9
                point = edge.valueAt(param)
                new_point = App.Vector(point.x, point.y, z_value)
                points.append(new_point)
            
            # Créer une BSpline à partir des points
            if len(points) >= 2:
                bspline = Part.BSplineCurve()
                bspline.interpolate(points)
                new_edge = Part.Edge(bspline)
        
        # Si l'arête est sélectionnée, stocker cette information dans la propriété Tag
        if new_edge and selected:
            new_edge.Tag = 1  # Utiliser Tag=1 pour indiquer que c'est une arête sélectionnée
        
        return new_edge
        
    def _create_direction_arrow(self, edge, z_value, size=2.0):
        """Crée une petite flèche au milieu de l'arête pour indiquer la direction
        
        Args:
            edge: L'arête d'origine
            z_value: Valeur Z à appliquer
            size: Taille de la flèche en mm
            
        Returns:
            Shape représentant la flèche
        """
        try:
            # Obtenir le point au milieu de l'arête
            mid_param = (edge.FirstParameter + edge.LastParameter) / 2
            mid_point = edge.valueAt(mid_param)
            mid_point_z = App.Vector(mid_point.x, mid_point.y, z_value)
            
            # Obtenir la tangente à ce point (normalisée)
            tangent = edge.tangentAt(mid_param).normalize()
            tangent_z = App.Vector(tangent.x, tangent.y, 0)  # Projeter sur le plan XY
            
            # Si la tangente est nulle (peut arriver avec certaines courbes), utiliser une direction par défaut
            if tangent_z.Length < 1e-6:
                if isinstance(edge.Curve, Part.Circle):
                    # Pour un cercle, calculer la tangente manuellement
                    center = edge.Curve.Center
                    center_z = App.Vector(center.x, center.y, z_value)
                    radius_vector = mid_point_z.sub(center_z)
                    # La tangente est perpendiculaire au rayon
                    tangent_z = App.Vector(-radius_vector.y, radius_vector.x, 0).normalize()
                else:
                    # Direction par défaut si on ne peut pas calculer la tangente
                    tangent_z = App.Vector(1, 0, 0)
            
            # Créer la flèche (une ligne avec deux lignes plus petites pour la pointe)
            # Point de départ de la flèche (légèrement en arrière du point milieu)
            start_point = mid_point_z.sub(tangent_z.multiply(size/2))
            
            # Point de fin de la flèche (légèrement en avant du point milieu)
            end_point = mid_point_z.add(tangent_z.multiply(size/2))
            
            # Créer la ligne principale de la flèche
            arrow_line = Part.makeLine(start_point, end_point)
            
            # Créer les deux lignes de la pointe de la flèche
            # Vecteur perpendiculaire à la tangente
            perp = App.Vector(-tangent_z.y, tangent_z.x, 0).normalize()
            
            # Points pour les deux lignes de la pointe
            arrow_p1 = end_point.sub(tangent_z.multiply(size/3)).add(perp.multiply(size/4))
            arrow_p2 = end_point.sub(tangent_z.multiply(size/3)).sub(perp.multiply(size/4))
            
            # Créer les deux lignes de la pointe
            arrow_line1 = Part.makeLine(end_point, arrow_p1)
            arrow_line2 = Part.makeLine(end_point, arrow_p2)
            
            # Combiner les trois lignes en une seule forme
            arrow_shape = Part.makeCompound([arrow_line, arrow_line1, arrow_line2])
            
            return arrow_shape
            
        except Exception as e:
            App.Console.PrintWarning(f"Erreur lors de la création de la flèche: {str(e)}\n")
            return None
    
    def getOutList(self, obj):
        """Retourne la liste des objets référencés par cet objet"""
        outlist = []
        if hasattr(obj, "Edges") and obj.Edges:
            for sub in obj.Edges:
                if sub[0] not in outlist:
                    outlist.append(sub[0])
        return outlist
    
    def __getstate__(self):
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def updateEdgeColors(self, obj):
        """Met à jour les couleurs des arêtes en fonction de l'index sélectionné"""
        if not hasattr(obj, "SelectedEdgeIndex") or not hasattr(obj, "Edges") or not obj.Edges:
            return
        
        selected_index = obj.SelectedEdgeIndex
        if selected_index < 0:
            # Aucune sélection, restaurer les couleurs normales
            self.execute(obj)
            return
        
        try:
            # Collecter toutes les arêtes
            all_edges = []
            for sub in obj.Edges:
                obj_ref = sub[0]
                sub_names = sub[1]
                
                for sub_name in sub_names:
                    if "Edge" in sub_name:
                        try:
                            edge = obj_ref.Shape.getElement(sub_name)
                            all_edges.append(edge)
                        except Exception as e:
                            App.Console.PrintError(f"Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
            
            if not all_edges or selected_index >= len(all_edges):
                return
            
            # Créer des arêtes ajustées à Zref et depth
            adjusted_edges_zref = []
            adjusted_edges_depth = []
            
            for i, edge in enumerate(all_edges):
                # Créer des arêtes ajustées avec des couleurs différentes selon la sélection
                if i == selected_index:
                    # Pour l'arête sélectionnée, utiliser une couleur différente et une largeur plus grande
                    edge_zref = self._create_adjusted_edge(edge, obj.Zref, selected=True)
                    edge_depth = self._create_adjusted_edge(edge, obj.depth, selected=True)
                else:
                    edge_zref = self._create_adjusted_edge(edge, obj.Zref, selected=False)
                    edge_depth = self._create_adjusted_edge(edge, obj.depth, selected=False)
                
                adjusted_edges_zref.append(edge_zref)
                adjusted_edges_depth.append(edge_depth)
            
            # Séparer les arêtes sélectionnées et non sélectionnées
            normal_edges_zref = []
            normal_edges_depth = []
            selected_edges_zref = []
            selected_edges_depth = []
            
            for i, edge in enumerate(adjusted_edges_zref):
                if i == selected_index:
                    selected_edges_zref.append(edge)
                else:
                    normal_edges_zref.append(edge)
            
            for i, edge in enumerate(adjusted_edges_depth):
                if i == selected_index:
                    selected_edges_depth.append(edge)
                else:
                    normal_edges_depth.append(edge)
            
            # Créer des compounds pour les arêtes normales et sélectionnées
            shapes = []
            
            # Ajouter les arêtes normales
            if normal_edges_zref:
                normal_compound_zref = Part.makeCompound(normal_edges_zref)
                shapes.append(normal_compound_zref)
            
            if normal_edges_depth:
                normal_compound_depth = Part.makeCompound(normal_edges_depth)
                shapes.append(normal_compound_depth)
            
            # Ajouter les arêtes sélectionnées
            if selected_edges_zref:
                selected_compound_zref = Part.makeCompound(selected_edges_zref)
                shapes.append(selected_compound_zref)
            
            if selected_edges_depth:
                selected_compound_depth = Part.makeCompound(selected_edges_depth)
                shapes.append(selected_compound_depth)
            
            # Créer un compound final
            if shapes:
                compound = Part.makeCompound(shapes)
                obj.Shape = compound
                
                # Stocker les informations pour le ViewProvider
                if not hasattr(obj, "NormalEdges"):
                    obj.addProperty("App::PropertyPythonObject", "NormalEdges", "Visualization", "Normal edges")
                if not hasattr(obj, "SelectedEdges"):
                    obj.addProperty("App::PropertyPythonObject", "SelectedEdges", "Visualization", "Selected edges")
                
                # Stocker les compounds pour que le ViewProvider puisse les colorier
                normal_edges = normal_edges_zref + normal_edges_depth
                selected_edges = selected_edges_zref + selected_edges_depth
                
                obj.NormalEdges = Part.makeCompound(normal_edges) if normal_edges else Part.Shape()
                obj.SelectedEdges = Part.makeCompound(selected_edges) if selected_edges else Part.Shape()
            
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la mise à jour des couleurs: {str(e)}\n")
            # En cas d'erreur, revenir à l'affichage normal
            self.execute(obj)


class ViewProviderContourGeometry:
    """Classe pour gérer l'affichage des contours"""
    
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
        # Définir la couleur rouge pour le contour
        vobj.LineColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.PointColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.LineWidth = 4.0  # Largeur de ligne plus grande
        vobj.PointSize = 6.0  # Taille des points plus grande
        
        # Ajouter une propriété pour la couleur des arêtes sélectionnées
        if not hasattr(vobj, "SelectedEdgeColor"):
            vobj.addProperty("App::PropertyColor", "SelectedEdgeColor", "Display", "Color of selected edges")
            vobj.SelectedEdgeColor = (0.0, 1.0, 1.0)  # Cyan par défaut
    
    def getIcon(self):
        """Retourne l'icône"""
        return BaptUtilities.getIconPath("Tree_Contour.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # # Définir la couleur rouge pour le contour
        # vobj.LineColor = (1.0, 0.0, 0.0)  # Rouge
        # vobj.PointColor = (1.0, 0.0, 0.0)  # Rouge
        # vobj.LineWidth = 4.0  # Largeur de ligne plus grande
        # vobj.PointSize = 6.0  # Taille des points plus grande
        
        # # Ajouter une propriété pour la couleur des arêtes sélectionnées
        # if not hasattr(vobj, "SelectedEdgeColor"):
        #     vobj.addProperty("App::PropertyColor", "SelectedEdgeColor", "Display", "Color of selected edges")
        #     vobj.SelectedEdgeColor = (0.0, 1.0, 1.0)  # Cyan par défaut
    
    def updateData(self, obj, prop):
        """Appelé lorsqu'une propriété de l'objet est modifiée"""
        # Mettre à jour l'affichage si une propriété pertinente change
        if prop == "SelectedEdgeIndex":
            # Forcer une recomputation pour mettre à jour l'affichage
            if obj.Document:
                obj.Document.recompute()
    
    def onChanged(self, vobj, prop):
        """Appelé lorsqu'une propriété du ViewProvider est modifiée"""
        pass
    
    def claimChildren(self):
        """Retourne les enfants de cet objet"""
        children = []
        # Récupérer tous les objets de contournage qui référencent cette géométrie par son nom
        if self.Object:
            doc = self.Object.Document
            if not doc:
                return children
                
            # Vérifier que l'objet a un nom valide
            if not hasattr(self.Object, "Name") or not self.Object.Name:
                return children
                
            for obj in doc.Objects:
                # Vérifier si l'objet est un cycle de contournage
                if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type") and obj.Proxy.Type == "ContournageCycle":
                    # Vérifier si l'objet référence cette géométrie
                    if hasattr(obj, "ContourGeometryName") and obj.ContourGeometryName == self.Object.Name:
                        children.append(obj)
                        
            # Vérifier si l'objet a un groupe
            if hasattr(self.Object, "Group"):
                # Ajouter tous les objets du groupe qui ne sont pas déjà dans la liste
                for obj in self.Object.Group:
                    if obj not in children:
                        children.append(obj)
                        
        return children
    
    def getDisplayModes(self, vobj):
        """Retourne les modes d'affichage disponibles"""
        return ["Flat Lines"]
    
    def getDefaultDisplayMode(self):
        """Retourne le mode d'affichage par défaut"""
        return "Flat Lines"
    
    def setDisplayMode(self, mode):
        """Définit le mode d'affichage"""
        return mode
    
    def onChanged(self, vobj, prop):
        """Appelé lorsqu'une propriété du ViewProvider est modifiée"""
        pass
    
    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))

        actionExport = menu.addAction("Export")
        actionExport.triggered.connect(lambda: self.export(vobj))
        return True
    
    def export(self, vobj, mode=0):
        """Exporte l'objet"""
        sheet = App.activeDocument().addObject('Spreadsheet::Sheet','Spreadsheet')
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(App.activeDocument().Name,'Spreadsheet')

        #recupere les edges de la géométrie
        edges = vobj.Object.Edges
        
        for i, edge in enumerate(edges):
            obj_ref = edge[0]
            sub_names = edge[1]
            sheet.set("A" + str(i+1), str(i))
            for j, sub_name in enumerate(sub_names):
                sheet.set("B" + str(i+j+1), str(sub_name))
                edge_ref = obj_ref.Shape.getElement(sub_name)
                start_point = edge_ref.Vertexes[0].Point
                end_point = edge_ref.Vertexes[-1].Point
                sheet.set("C" + str(i+j+1), str(start_point))
                sheet.set("D" + str(i+j+1), str(end_point))
                if isinstance(edge_ref.Curve, Part.Circle):
                    sheet.set("E" + str(i+j+1), "Cercle")
                elif isinstance(edge_ref.Curve, Part.Line):
                    sheet.set("E" + str(i+j+1), "Ligne")
                else:
                    sheet.set("E" + str(i+j+1), "Inconnu")
        pass
    
    def setEdit(self, vobj, mode=0):
        """Appelé lorsque l'objet est édité"""
        try:
            import importlib
            import BaptContourTaskPanel
            # Recharger le module pour prendre en compte les modifications
            importlib.reload(BaptContourTaskPanel)
            # Créer et afficher le panneau
            panel = BaptContourTaskPanel.ContourTaskPanel(vobj.Object)
            Gui.Control.showDialog(panel)
            return True
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de l'ouverture du panneau d'édition: {str(e)}\n")
            return False
    
    def unsetEdit(self, vobj, mode=0):
        """Appelé lorsque l'édition est terminée"""
        Gui.Control.closeDialog()
        return True
    
    def doubleClicked(self, vobj):
        """Appelé lors d'un double-clic sur l'objet"""
        self.setEdit(vobj)
        return True
    
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
