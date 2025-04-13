import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from FreeCAD import Base
from PySide import QtCore, QtGui

class DrillOperation:
    """Classe représentant une opération d'usinage de perçage"""
    
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "DrillOperation"
        
        # Référence à la géométrie de perçage (utiliser le nom au lieu d'un lien direct)
        if not hasattr(obj, "DrillGeometryName"):
            obj.addProperty("App::PropertyString", "DrillGeometryName", "Base", "Name of drill geometry to machine")
        
        # Outil sélectionné
        if not hasattr(obj, "ToolId"):
            obj.addProperty("App::PropertyInteger", "ToolId", "Tool", "Selected tool ID")
            obj.ToolId = -1  # Valeur par défaut (aucun outil sélectionné)
        
        # Nom de l'outil (affiché en lecture seule)
        if not hasattr(obj, "ToolName"):
            obj.addProperty("App::PropertyString", "ToolName", "Tool", "Selected tool name")
            obj.setEditorMode("ToolName", 1)  # en lecture seule
        
        # Type de cycle
        if not hasattr(obj, "CycleType"):
            obj.addProperty("App::PropertyEnumeration", "CycleType", "Cycle", "Type of drilling cycle")
            obj.CycleType = ["Simple", "Peck", "Tapping", "Boring", "Reaming"]
            obj.CycleType = "Simple"  # Valeur par défaut
        
        # Paramètres communs à tous les cycles
        if not hasattr(obj, "FeedRate"):
            obj.addProperty("App::PropertySpeed", "FeedRate", "Feeds", "Feed rate for drilling")
            obj.FeedRate = 100.0  # mm/min par défaut
        
        if not hasattr(obj, "SpindleSpeed"):
            obj.addProperty("App::PropertySpeed", "SpindleSpeed", "Feeds", "Spindle speed")
            obj.SpindleSpeed = 1000.0  # tr/min par défaut
        
        if not hasattr(obj, "CoolantMode"):
            obj.addProperty("App::PropertyEnumeration", "CoolantMode", "Coolant", "Coolant mode")
            obj.CoolantMode = ["Off", "Flood", "Mist"]
            obj.CoolantMode = "Flood"  # Valeur par défaut
            
        # Paramètres de visualisation du fil
        if not hasattr(obj, "ShowPathLine"):
            obj.addProperty("App::PropertyBool", "ShowPathLine", "Display", "Show path line between holes")
            obj.ShowPathLine = True  # Activé par défaut
            
        if not hasattr(obj, "PathLineHeight"):
            obj.addProperty("App::PropertyLength", "PathLineHeight", "Display", "Additional height of path line above holes")
            obj.PathLineHeight = 10.0  # 10mm par défaut
            
        if not hasattr(obj, "PathLineColor"):
            obj.addProperty("App::PropertyColor", "PathLineColor", "Display", "Color of path line")
            obj.PathLineColor = (0.0, 0.5, 1.0)  # Bleu clair par défaut
        
        # Paramètres spécifiques au cycle de perçage profond (Peck)
        if not hasattr(obj, "PeckDepth"):
            obj.addProperty("App::PropertyLength", "PeckDepth", "Peck", "Depth of each peck")
            obj.PeckDepth = 2.0  # 2mm par défaut
        
        if not hasattr(obj, "Retract"):
            obj.addProperty("App::PropertyLength", "Retract", "Peck", "Retract distance after each peck")
            obj.Retract = 1.0  # 1mm par défaut
        
        # Paramètres spécifiques au cycle de taraudage
        if not hasattr(obj, "ThreadPitch"):
            obj.addProperty("App::PropertyLength", "ThreadPitch", "Tapping", "Thread pitch")
            obj.ThreadPitch = 1.0  # 1mm par défaut
        
        # Paramètres spécifiques au cycle d'alésage
        if not hasattr(obj, "DwellTime"):
            obj.addProperty("App::PropertyFloat", "DwellTime", "Boring", "Dwell time at bottom in seconds")
            obj.DwellTime = 0.5  # 0.5s par défaut
        
        # Paramètres de sécurité
        if not hasattr(obj, "SafeHeight"):
            obj.addProperty("App::PropertyLength", "SafeHeight", "Safety", "Safe height for rapid moves")
            obj.SafeHeight = 10.0  # 10mm par défaut
        
        # Paramètres de profondeur
        if not hasattr(obj, "FinalDepth"):
            obj.addProperty("App::PropertyLength", "FinalDepth", "Depth", "Final depth of drilling")
            obj.FinalDepth = 10.0  # 10mm par défaut
        
        # Mode de profondeur (absolu ou relatif)
        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyString", "DepthMode", "Depth", "Depth mode (Absolute or Relative)")
            obj.DepthMode = "Absolute"  # Valeur par défaut
        
        # Référence Z pour le mode relatif
        if not hasattr(obj, "ZReference"):
            obj.addProperty("App::PropertyLength", "ZReference", "Depth", "Z reference for relative depth mode")
            obj.ZReference = 0.0  # 0mm par défaut

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "ToolId" and obj.ToolId >= 0:
            self.updateToolInfo(obj)
        elif prop == "CycleType":
            self.updateVisibleProperties(obj)
        elif prop == "DrillGeometryName" and obj.DrillGeometryName:
            self.updateFromGeometry(obj)

    def updateToolInfo(self, obj):
        """Met à jour les informations de l'outil sélectionné"""
        from BaptTools import ToolDatabase
        
        try:
            # Récupérer l'outil depuis la base de données
            db = ToolDatabase()
            tools = db.get_all_tools()
            
            for tool in tools:
                if tool.id == obj.ToolId:
                    obj.ToolName = f"{tool.name} (Ø{tool.diameter}mm)"
                    break
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la mise à jour des informations de l'outil: {str(e)}\n")

    def updateVisibleProperties(self, obj):
        """Met à jour la visibilité des propriétés en fonction du type de cycle"""
        # Cacher toutes les propriétés spécifiques
        obj.setEditorMode("PeckDepth", 2)  # caché
        obj.setEditorMode("Retract", 2)  # caché
        obj.setEditorMode("ThreadPitch", 2)  # caché
        obj.setEditorMode("DwellTime", 2)  # caché
        
        # Afficher les propriétés spécifiques au cycle sélectionné
        if obj.CycleType == "Peck":
            obj.setEditorMode("PeckDepth", 0)  # visible
            obj.setEditorMode("Retract", 0)  # visible
        elif obj.CycleType == "Tapping":
            obj.setEditorMode("ThreadPitch", 0)  # visible
        elif obj.CycleType == "Boring":
            obj.setEditorMode("DwellTime", 0)  # visible

    def updateFromGeometry(self, obj):
        """Met à jour les paramètres en fonction de la géométrie sélectionnée"""
        if not obj.DrillGeometryName:
            return
        
        # Récupérer le diamètre et la profondeur depuis la géométrie
        for geom in App.ActiveDocument.Objects:
            if geom.Name == obj.DrillGeometryName:
                if hasattr(geom, "DrillDiameter"):
                    # Mettre à jour le message dans la console
                    App.Console.PrintMessage(f"Diamètre détecté: {geom.DrillDiameter.Value}mm\n")
        
                if hasattr(geom, "DrillDepth"):
                    # Utiliser la profondeur détectée comme profondeur finale
                    obj.FinalDepth = geom.DrillDepth.Value
                    App.Console.PrintMessage(f"Profondeur détectée: {obj.FinalDepth}mm\n")

    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        if not obj.DrillGeometryName or not hasattr(App.ActiveDocument.getObject(obj.DrillGeometryName), "DrillPositions"):
            obj.Shape = Part.Shape()  # Shape vide
            return
        
        # Obtenir les positions de perçage
        drill_geometry = App.ActiveDocument.getObject(obj.DrillGeometryName)
        positions = drill_geometry.DrillPositions
        
        if not positions:
            obj.Shape = Part.Shape()  # Shape vide
            return
        
        # Créer une sphère pour chaque position
        spheres = []
        radius = 2.0  # Rayon fixe pour la visualisation
        
        for pos in positions:
            sphere = Part.makeSphere(radius, pos)
            spheres.append(sphere)
        
        # Créer un fil qui relie tous les trous
        wires = []
        if obj.ShowPathLine and len(positions) > 1:
            points = []
            for pos in positions:
                # Ajouter un point au-dessus de chaque trou avec la hauteur supplémentaire
                elevated_pos = App.Vector(pos.x, pos.y, pos.z + obj.PathLineHeight.Value)
                points.append(elevated_pos)
            
            # Créer une polyligne avec tous les points
            polyline = Part.makePolygon(points)
            wires.append(polyline)
        
        # Fusionner les sphères et le fil
        shapes = spheres + wires
        if shapes:
            compound = Part.makeCompound(shapes)
            obj.Shape = compound

    def onChanged(self, obj, prop):
        """Appelé quand une propriété change"""
        if prop == "DrillGeometryName":
            self.updateFromGeometry(obj)
        elif prop in ["ShowPathLine", "PathLineHeight"]:
            self.execute(obj)

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)
        self.updateVisibleProperties(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderDrillOperation:
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
        from BaptDrillOperationTaskPanel import DrillOperationTaskPanel
        panel = DrillOperationTaskPanel(vobj.Object)
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
