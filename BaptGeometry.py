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
        
        # Propriétés pour stocker les arêtes sélectionnées
        if not hasattr(obj, "Edges"):
            obj.addProperty("App::PropertyLinkSubList", "Edges", "Contour", "Arêtes sélectionnées pour le contour")
        
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
        
        if not hasattr(obj, "Offset"):
            obj.addProperty("App::PropertyLength", "Offset", "Contour", "Décalage du contour (positif = extérieur, négatif = intérieur)")
            obj.Offset = 0.0
        
        if not hasattr(obj, "Direction"):
            obj.addProperty("App::PropertyEnumeration", "Direction", "Contour", "Direction d'usinage")
            obj.Direction = ["Horaire", "Anti-horaire"]
            obj.Direction = "Horaire"
        
        # Créer une forme vide
        obj.Shape = Part.Shape()
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["Edges", "ToolDiameter", "Offset", "Direction"]:
            self.execute(obj)
    
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
            
            # Créer un fil à partir des arêtes
            try:
                # Trier les arêtes pour essayer de former un contour connecté
                sorted_edges = Part.sortEdges(edges)
                if sorted_edges:
                    wire = Part.Wire(sorted_edges[0])
                    App.Console.PrintMessage("Fil créé avec succès à partir des arêtes triées.\n")
                else:
                    wire = Part.Wire(edges)
                    App.Console.PrintMessage("Fil créé avec succès à partir des arêtes non triées.\n")
            except Exception as e:
                App.Console.PrintError(f"Impossible de créer un fil à partir des arêtes sélectionnées: {str(e)}\n")
                # Essayer de créer une forme composite si le fil échoue
                try:
                    compound = Part.makeCompound(edges)
                    obj.Shape = compound
                    App.Console.PrintMessage("Forme composite créée à la place du fil.\n")
                    return
                except Exception as e2:
                    App.Console.PrintError(f"Impossible de créer une forme composite: {str(e2)}\n")
                    return
            
            # Appliquer le décalage si nécessaire
            if hasattr(obj, "Offset") and obj.Offset != 0:
                try:
                    # Vérifier si le fil est fermé
                    if wire.isClosed():
                        # Créer une face à partir du fil
                        face = Part.Face(wire)
                        # Décaler la face
                        offset_face = face.makeOffset(obj.Offset)
                        # Extraire le contour externe de la face décalée
                        offset_wire = offset_face.OuterWire
                        wire = offset_wire
                        App.Console.PrintMessage(f"Décalage appliqué avec succès: {obj.Offset}.\n")
                    else:
                        App.Console.PrintWarning("Le fil n'est pas fermé, impossible d'appliquer un décalage.\n")
                except Exception as e:
                    App.Console.PrintError(f"Impossible d'appliquer le décalage au contour: {str(e)}\n")
            
            # Créer une forme pour la visualisation
            obj.Shape = wire
            App.Console.PrintMessage("Forme mise à jour avec succès.\n")
            
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de l'exécution: {str(e)}\n")
    
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
        vobj.LineWidth = 2.0  # Largeur de ligne plus grande
        vobj.PointSize = 4.0  # Taille des points plus grande
    
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Contour.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # Définir la couleur rouge pour le contour
        vobj.LineColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.PointColor = (1.0, 0.0, 0.0)  # Rouge
        vobj.LineWidth = 2.0  # Largeur de ligne plus grande
        vobj.PointSize = 4.0  # Taille des points plus grande
    
    def updateData(self, obj, prop):
        """Appelé lorsqu'une propriété de l'objet est modifiée"""
        pass
    
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
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None
