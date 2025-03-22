import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Base

class CamProject:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "CamProject"
        
        # Origine du projet
        obj.addProperty("App::PropertyVector", "Origin", "Project Setup", "Project origin point")
        
        # Dimensions du brut
        obj.addProperty("App::PropertyLength", "StockLength", "Stock", "Length of stock material")
        obj.addProperty("App::PropertyLength", "StockWidth", "Stock", "Width of stock material")
        obj.addProperty("App::PropertyLength", "StockHeight", "Stock", "Height of stock material")
        
        # Plan de travail
        obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Project Setup", "Working plane")
        obj.WorkPlane = ["XY", "XZ", "YZ"]
        
        # Définir les valeurs par défaut
        obj.Origin = App.Vector(0,0,0)
        obj.StockLength = 100.0
        obj.StockWidth = 100.0
        obj.StockHeight = 20.0
        obj.WorkPlane = "XY"

    def createStock(self, obj):
        """Crée l'objet stock"""
        stock = App.ActiveDocument.addObject("Part::Feature", "Stock")
        # Ajouter le stock au groupe
        obj.addObject(stock)
        
        # Définir la couleur et la transparence du stock
        if hasattr(stock, "ViewObject"):
            stock.ViewObject.ShapeColor = (0.8, 0.8, 0.8)  # Gris clair
            stock.ViewObject.Transparency = 50  # Semi-transparent
        return stock

    def getStock(self, obj):
        """Obtient ou crée l'objet stock"""
        stock = None
        if obj.Group:  # Chercher un stock existant dans le groupe
            for child in obj.Group:
                if child.Name.startswith("Stock"):
                    stock = child
                    break
        
        if not stock:  # Créer un nouveau stock si nécessaire
            stock = self.createStock(obj)
        
        return stock

    def execute(self, obj):
        """Crée ou met à jour la représentation visuelle du brut"""
        try:
            # Créer une boîte représentant le brut
            if obj.WorkPlane == "XY":
                box = Part.makeBox(obj.StockLength, obj.StockWidth, obj.StockHeight, obj.Origin)
            elif obj.WorkPlane == "XZ":
                box = Part.makeBox(obj.StockLength, obj.StockHeight, obj.StockWidth, obj.Origin)
            else:  # YZ
                box = Part.makeBox(obj.StockHeight, obj.StockLength, obj.StockWidth, obj.Origin)
            
            # Obtenir ou créer le stock et mettre à jour sa forme
            stock = self.getStock(obj)
            stock.Shape = box
            
        except Exception as e:
            App.Console.PrintError(f"Error in execute: {str(e)}\n")

    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["StockLength", "StockWidth", "StockHeight", "Origin", "WorkPlane"]:
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
        """Retourne l'icône du projet CAM"""
        return ":/icons/Tree_Part.svg"
        
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object

    def updateData(self, obj, prop):
        """Appelé quand une propriété de l'objet est modifiée"""
        return

    def onChanged(self, vobj, prop):
        """Appelé quand une propriété du ViewProvider est modifiée"""
        return

    def doubleClicked(self, vobj):
        """Gérer le double-clic sur l'objet"""
        return True

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None
