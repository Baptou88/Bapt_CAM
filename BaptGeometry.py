import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from FreeCAD import Base
import BaptDrillTaskPanel

class DrillGeometry:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "DrillGeometry"
        
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

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "DrillFaces":
            self.updateDrillParameters(obj)
        elif prop in ["DrillPositions", "MarkerSize"]:
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
                    
                    # Calculer la profondeur en trouvant la face plane associée
                    # TODO: Implémenter la détection de profondeur
                    depths.add(10.0)  # valeur temporaire

        # Mettre à jour les propriétés
        obj.DrillPositions = positions
        
        # Si tous les perçages ont le même diamètre, le définir
        if len(diameters) == 1:
            obj.DrillDiameter = list(diameters)[0]
        
        # Si tous les perçages ont la même profondeur, la définir
        if len(depths) == 1:
            obj.DrillDepth = list(depths)[0]

    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        if not obj.DrillPositions:
            obj.Shape = Part.Shape()  # Shape vide
            return

        # Créer une sphère pour chaque position
        spheres = []
        radius = obj.MarkerSize / 2.0  # Rayon = moitié de la taille
        
        for pos in obj.DrillPositions:
            sphere = Part.makeSphere(radius, pos)
            spheres.append(sphere)
        
        # Fusionner toutes les sphères
        if spheres:
            compound = Part.makeCompound(spheres)
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


class ViewProviderDrillGeometry:
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Drilling.svg")
        
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True

    def updateData(self, obj, prop):
        """Appelé quand une propriété de l'objet est modifiée"""
        pass

    def onChanged(self, vobj, prop):
        """Appelé quand une propriété du ViewProvider est modifiée"""
        pass

    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
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


class ContourGeometry:
    """Classe pour gérer les contours d'usinage"""
    
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "ContourGeometry"
        
        # Transformer l'objet en groupe
        obj.addExtension("App::GroupExtensionPython", None)
        
        # Permettre les références à des objets en dehors du groupe
        obj.addExtension("App::LinkExtensionPython", None)
        
        # Propriétés pour stocker les arêtes sélectionnées
        if not hasattr(obj, "Edges"):
            obj.addProperty("App::PropertyLinkSubList", "Edges", "Contour", "Arêtes sélectionnées pour le contour")
        
        if not hasattr(obj, "Zref"):
            obj.addProperty("App::PropertyLength", "Zref", "Contour", "Hauteur de référence")
            obj.Zref = 0.0
        
        if not hasattr(obj, "Zfinal"):
            obj.addProperty("App::PropertyLength", "Zfinal", "Contour", "Hauteur finale")
            obj.Zfinal = 0.0
        
        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyString", "DepthMode", "Contour", "Mode de profondeur (Absolu ou Relatif)")
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
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        #if prop == "Zref":
            #App.Console.PrintMessage('Message\n')
            #App.Console.PrintMessage(f'{self.obj.Zref} {obj.Zref}\n')
            #if obj.DepthMode == "Relatif":
                # calcul la difference entre l'ancienne et la nouvelle valeur

        if prop in ["Edges", "Zref", "Zfinal", "Direction", "DepthMode"]:
            self.execute(obj)
    
    def _create_adjusted_edges(self, edges, z_value):
        """Crée des arêtes ajustées à une hauteur Z spécifique
        
        Args:
            edges: Liste des arêtes d'origine
            z_value: Valeur Z à appliquer
            
        Returns:
            Liste des nouvelles arêtes ajustées
        """
        adjusted_edges = []
        for edge in edges:
            #App.Console.PrintMessage(f"Traitement de l'arête pour Z={z_value}: {edge}\n")
            if isinstance(edge.Curve, Part.Line):
                # Pour une ligne droite
                p1 = edge.Vertexes[0].Point
                p2 = edge.Vertexes[1].Point
                # Créer de nouveaux points avec Z = z_value
                new_p1 = App.Vector(p1.x, p1.y, z_value)
                new_p2 = App.Vector(p2.x, p2.y, z_value)
                # Créer une nouvelle ligne
                new_edge = Part.makeLine(new_p1, new_p2)
                adjusted_edges.append(new_edge)
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
                
                # Si c'est un arc (pas un cercle complet)
                if edge.Curve.AngleXU != 0 or edge.Curve.AngleXV != 0:
                    # Récupérer les angles de début et de fin
                    first_param = edge.FirstParameter
                    last_param = edge.LastParameter
                    new_edge = Part.Edge(new_circle, first_param, last_param)
                else:
                    # Cercle complet
                    new_edge = Part.Edge(new_circle)
                
                adjusted_edges.append(new_edge)
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
                    new_edge = Part.BSplineCurve()
                    new_edge.interpolate(points)
                    adjusted_edges.append(Part.Edge(new_edge))
        
        return adjusted_edges
    
    def execute(self, obj):
        """Mettre à jour la représentation visuelle du contour"""
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
                            App.Console.PrintMessage(f"Arête ajoutée: {sub_name} de {obj_ref.Name}\n")
                        except Exception as e:
                            App.Console.PrintError(f"Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
            
            if not edges:
                App.Console.PrintError("Aucune arête valide trouvée.\n")
                return
            
            App.Console.PrintMessage(f"Nombre d'arêtes collectées: {len(edges)}\n")
            
            # Créer des arêtes ajustées à la hauteur Zref et à Zfinal
            adjusted_edges_zref = self._create_adjusted_edges(edges, obj.Zref)
            adjusted_edges_zfinal = self._create_adjusted_edges(edges, obj.Zfinal)
            
            try:
                # Créer le fil à Zref
                wire_zref = Part.Wire(adjusted_edges_zref)
                
                # Créer le fil à Zfinal
                wire_zfinal = Part.Wire(adjusted_edges_zfinal)
                
                # Créer un compound contenant les deux fils
                compound = Part.makeCompound([wire_zref, wire_zfinal])
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
                    all_edges.extend(adjusted_edges_zfinal)
                    compound = Part.makeCompound(all_edges)
                    obj.Shape = compound
                    App.Console.PrintMessage("Forme composite créée à la place du fil.\n")
                    return
                except Exception as e2:
                    App.Console.PrintError(f"Impossible de créer une forme composite: {str(e2)}\n")
                    return
            
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de l'exécution: {str(e)}\n")
    
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
    
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Contour.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # Définir la couleur rouge pour le contour
        vobj.LineColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.PointColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.LineWidth = 4.0  # Largeur de ligne plus grande
        vobj.PointSize = 6.0  # Taille des points plus grande
    
    def updateData(self, obj, prop):
        """Appelé lorsqu'une propriété de l'objet est modifiée"""
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
        return True
    
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
        return {"ObjectName": self.Object.Name if self.Object else None}
    
    def __setstate__(self, state):
        """Appelé lors du chargement"""
        if state and "ObjectName" in state and state["ObjectName"]:
            self.Object = App.ActiveDocument.getObject(state["ObjectName"])
        return None
