import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from FreeCAD import Base
import BaptTaskPanel  # Import direct du module

class CamProject:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "CamProject"
        
        if not hasattr(obj, "Origin"):
            # Origine du projet
            obj.addProperty("App::PropertyVector", "Origin", "Project Setup", "Project origin point")
            obj.Origin = App.Vector(0,0,0)
        
        if not hasattr(obj, "StockLength"):
            # Dimensions du brut
            obj.addProperty("App::PropertyLength", "StockLength", "Stock", "Length of stock material")
            obj.StockLength = 100.0
            
        if not hasattr(obj, "StockWidth"):
            obj.addProperty("App::PropertyLength", "StockWidth", "Stock", "Width of stock material")
            obj.StockWidth = 100.0
            
        if not hasattr(obj, "StockHeight"):
            obj.addProperty("App::PropertyLength", "StockHeight", "Stock", "Height of stock material")
            obj.StockHeight = 20.0
        
        if not hasattr(obj, "WorkPlane"):
            # Plan de travail
            obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Project Setup", "Working plane")
            obj.WorkPlane = ["XY", "XZ", "YZ"]
            obj.WorkPlane = "XY"  # Valeur par défaut

        # Propriétés pour la position d'origine du brut
        if not hasattr(obj, "StockOrigin"):
            obj.addProperty("App::PropertyVector", "StockOrigin", "Stock", "position of stock origin")
            obj.StockOrigin = App.Vector(0,0,0)
        
        # Créer le groupe Geometry
        self.getGeometryGroup(obj)

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def getGeometryGroup(self, obj):
        """Obtient ou crée le groupe Geometry"""
        # Chercher le groupe Geometry existant
        for item in obj.Group:
            if item.Name == "Geometry":
                return item
        
        # Créer un nouveau groupe Geometry si non trouvé
        geometry_group = App.ActiveDocument.addObject("App::DocumentObjectGroup", "Geometry")
        obj.addObject(geometry_group)
        return geometry_group

    def createStock(self, obj):
        """Crée l'objet stock"""
        
        stock = App.ActiveDocument.addObject("Part::Feature", "Stock")

        # stock = App.ActiveDocument.addObject("Part::FeaturePython", "Stock")
        # Ajouter le stock au groupe
        obj.addObject(stock)
        
        # Définir la couleur et la transparence du stock
        if hasattr(stock, "ViewObject"):
            stock.ViewObject.ShapeColor = (0.8, 0.8, 0.8)  # Gris clair
            stock.ViewObject.Transparency = 50  # Semi-transparent
        return stock

    def getStock(self, obj):
        """Obtient ou crée l'objet stock"""
        # App.Console.PrintMessage('getStock in camproject\n')
        stock = None
        if obj.Group:  # Chercher un stock existant dans le groupe
            for child in obj.Group:
                if child.Name.startswith("Stock"):
                    stock = child
                    break
        
        # App.Console.PrintMessage('getStock\n')
        if not stock:  # Créer un nouveau stock si nécessaire
            stock = self.createStock(obj)
        
        return stock

    def execute(self, obj):
        """Crée ou met à jour la représentation visuelle du brut"""
        # App.Console.PrintMessage('execute in camproject\n')
        try:
            # S'assurer que toutes les propriétés existent
            if not hasattr(obj, "WorkPlane") or not hasattr(obj, "StockLength") or not hasattr(obj, "StockWidth") or not hasattr(obj, "StockHeight") or not hasattr(obj, "StockOrigin"):
                return
                
            # Créer une boîte représentant le brut
            if obj.WorkPlane == "XY":
                box = Part.makeBox(obj.StockLength, obj.StockWidth, obj.StockHeight, obj.StockOrigin)
            elif obj.WorkPlane == "XZ":
                box = Part.makeBox(obj.StockLength, obj.StockHeight, obj.StockWidth, obj.StockOrigin)
            else:  # YZ
                box = Part.makeBox(obj.StockHeight, obj.StockLength, obj.StockWidth, obj.StockOrigin)
            
            # Obtenir ou créer le stock et mettre à jour sa forme
            stock = self.getStock(obj)
            stock.Shape = box
            
        except Exception as e:
            App.Console.PrintError(f"Error in execute: {str(e)}\n")

    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["StockLength", "StockWidth", "StockHeight", "Origin", "WorkPlane", "StockOrigin"]:
            App.Console.PrintMessage("Change property: " + str(obj.Name) + " " + str(prop) + "\n")
            self.execute(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

class ViewProviderCamProject:
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg")
        
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
        panel = BaptTaskPanel.CamProjectTaskPanel(vobj.Object)
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
