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
    
    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["ToolDiameter", "CutDepth", "StepDown", "Direction", "ContourGeometryName"]:
            self.execute(obj)
    
    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        # Vérifier si l'objet a une géométrie de contour associée
        if not hasattr(obj, "ContourGeometryName") or not obj.ContourGeometryName:
            #App.Console.PrintError("Aucune géométrie de contour associée.\n")
            return
        
        # Récupérer la géométrie du contour
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
        
        # Créer une représentation visuelle de la trajectoire d'usinage
        try:
            # Récupérer la hauteur de référence depuis la géométrie du contour
            z_ref = 0.0
            if hasattr(contour, "Zref"):
                z_ref = contour.Zref
            
            # Calculer le décalage en fonction du rayon de l'outil
            offset = obj.ToolDiameter / 2.0
            
            # Déterminer la direction du décalage
            # Pour l'usinage en avalant (Climb), le décalage est vers l'intérieur pour un contour horaire
            # Pour l'usinage en opposition (Conventional), le décalage est vers l'extérieur pour un contour horaire
            direction_contour = "Horaire"  # Valeur par défaut
            if hasattr(contour, "Direction"):
                direction_contour = contour.Direction
                
            direction_usinage = obj.Direction
            
            # Déterminer si le décalage est vers l'intérieur ou l'extérieur
            decalage_interieur = False
            if (direction_contour == "Horaire" and direction_usinage == "Climb") or \
               (direction_contour == "Anti-horaire" and direction_usinage == "Conventional"):
                decalage_interieur = True
            
            # Calculer le signe du décalage
            offset_value = -offset if decalage_interieur else offset
            
            # Récupérer la forme du contour
            shape = contour.Shape
            
            # Vérifier si le contour est fermé
            is_closed = False
            if hasattr(contour, "IsClosed"):
                is_closed = contour.IsClosed
            
            # Créer le chemin d'outil avec makeOffset
            path_shape = None
            
            # Ajuster la forme à la hauteur de référence (Zref)
            # Créer une copie de la forme à la hauteur Zref
            if hasattr(shape, "Wires") and shape.Wires:
                # Prendre le premier wire si la forme en contient plusieurs
                wire = shape.Wires[0]
                
                # Créer un wire ajusté à la hauteur Zref
                adjusted_edges = []
                for edge in wire.Edges:
                    if isinstance(edge.Curve, Part.Line):
                        # Pour une ligne droite
                        p1 = edge.Vertexes[0].Point
                        p2 = edge.Vertexes[1].Point
                        p1_z = App.Vector(p1.x, p1.y, z_ref)
                        p2_z = App.Vector(p2.x, p2.y, z_ref)
                        adjusted_edges.append(Part.makeLine(p1_z, p2_z))
                    elif isinstance(edge.Curve, Part.Circle):
                        # Pour un arc ou un cercle
                        circle = edge.Curve
                        center = App.Vector(circle.Center.x, circle.Center.y, z_ref)
                        axis = App.Vector(0, 0, 1)
                        
                        # Créer un nouveau cercle
                        new_circle = Part.Circle(center, axis, circle.Radius)
                        
                        # Si c'est un arc (pas un cercle complet)
                        if hasattr(edge, "FirstParameter") and hasattr(edge, "LastParameter"):
                            first_param = edge.FirstParameter
                            last_param = edge.LastParameter
                            if first_param != last_param:
                                adjusted_edges.append(Part.Edge(new_circle, first_param, last_param))
                            else:
                                adjusted_edges.append(Part.Edge(new_circle))
                        else:
                            adjusted_edges.append(Part.Edge(new_circle))
                    else:
                        # Pour les autres types de courbes, utiliser une approximation par points
                        try:
                            points = []
                            for i in range(10):  # Utiliser 10 points pour l'approximation
                                param = edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * i / 9
                                point = edge.valueAt(param)
                                point_z = App.Vector(point.x, point.y, z_ref)
                                points.append(point_z)
                            
                            if len(points) >= 2:
                                bspline = Part.BSplineCurve()
                                bspline.interpolate(points)
                                adjusted_edges.append(Part.Edge(bspline))
                        except Exception as e:
                            App.Console.PrintWarning(f"Erreur lors de l'ajustement d'une courbe complexe: {str(e)}\n")
                
                # Créer un wire ajusté
                if adjusted_edges:
                    try:
                        # Trier les arêtes pour s'assurer qu'elles sont connectées
                        sorted_edges = Part.__sortEdges__(adjusted_edges)
                        adjusted_wire = Part.Wire(sorted_edges)
                        
                        # Vérifier si le wire est fermé
                        if adjusted_wire.isClosed():
                            # Pour un wire fermé, créer une face puis utiliser makeOffset
                            try:
                                face = Part.Face(adjusted_wire)
                                offset_shape = face.makeOffset(offset_value)
                                
                                # Extraire le wire du résultat du décalage
                                if isinstance(offset_shape, Part.Shape) and hasattr(offset_shape, "Wires") and offset_shape.Wires:
                                    path_shape = offset_shape.Wires[0]
                                else:
                                    path_shape = offset_shape
                                
                                App.Console.PrintMessage(f"Décalage créé avec makeOffset: {offset_value} mm\n")
                            except Exception as e:
                                App.Console.PrintError(f"Erreur lors de la création du décalage avec makeOffset: {str(e)}\n")
                                
                                # En cas d'échec, essayer avec makeOffset2D directement sur le wire
                                try:
                                    path_shape = adjusted_wire.makeOffset2D(offset_value, fill=False, join=2, openResult=True)
                                    App.Console.PrintMessage(f"Décalage créé avec makeOffset2D: {offset_value} mm\n")
                                except Exception as e2:
                                    App.Console.PrintError(f"Erreur lors de la création du décalage avec makeOffset2D: {str(e2)}\n")
                        else:
                            # Pour un wire ouvert, utiliser makeOffset2D
                            try:
                                path_shape = adjusted_wire.makeOffset2D(offset_value, fill=False, join=2, openResult=False)
                                App.Console.PrintMessage(f"Décalage créé avec makeOffset2D pour wire ouvert: {offset_value} mm\n")
                            except Exception as e:
                                App.Console.PrintError(f"Erreur lors de la création du décalage pour wire ouvert: {str(e)}\n")
                    except Exception as e:
                        App.Console.PrintError(f"Erreur lors de la création du wire ajusté: {str(e)}\n")
            
            # Assigner la forme au cycle de contournage
            if path_shape:
                obj.Shape = path_shape
                App.Console.PrintMessage("Chemin d'usinage créé avec succès.\n")
            else:
                App.Console.PrintError("Impossible de créer le chemin d'usinage.\n")
                
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la création du chemin d'usinage: {str(e)}\n")
    
    def __getstate__(self):
        """Appelé lors de la sauvegarde"""
        return None
        # return {
        #     "Type": self.Type,
        #     "ContourGeometryName": getattr(self.Object, "ContourGeometryName", "")
        # }
    
    def __setstate__(self, state):
        """Appelé lors du chargement"""
        return None
        # if state:
        #     self.Type = state.get("Type", "ContournageCycle")
        # return None


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
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Contournage.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        
        # Configuration de l'affichage
        vobj.LineColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.PointColor = (0.0, 0.0, 1.0)  # Bleu
        vobj.LineWidth = 2.0
        vobj.PointSize = 4.0
    
    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True
    
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
        return None
        return {"ObjectName": self.Object.Name if self.Object else None}
    
    def __setstate__(self, state):
        """Appelé lors du chargement"""
        return None
        if state and "ObjectName" in state and state["ObjectName"]:
            self.Object = App.ActiveDocument.getObject(state["ObjectName"])
        return None
