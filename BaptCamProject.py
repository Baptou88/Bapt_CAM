import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Base
import os

class Stock:
    """Classe pour gérer le brut d'usinage"""
    
    def __init__(self, obj, parent=None):
        """Initialise l'objet Stock
        
        Args:
            obj: L'objet FreeCAD
            parent: L'objet parent (CamProject)
        """
        obj.Proxy = self
        self.Type = "Stock"
        self.parent = parent
        
        # Ajouter les propriétés si elles n'existent pas déjà
        if not hasattr(obj, "Length"):
            obj.addProperty("App::PropertyLength", "Length", "Stock", "Longueur du brut")
            obj.Length = 100.0
        
        if not hasattr(obj, "Width"):
            obj.addProperty("App::PropertyLength", "Width", "Stock", "Largeur du brut")
            obj.Width = 100.0
        
        if not hasattr(obj, "Height"):
            obj.addProperty("App::PropertyLength", "Height", "Stock", "Hauteur du brut")
            obj.Height = 50.0
        
        if not hasattr(obj, "Origin"):
            obj.addProperty("App::PropertyVector", "Origin", "Stock", "Origine du brut")
            obj.Origin = App.Vector(0, 0, 0)
        
        if not hasattr(obj, "WorkPlane"):
            obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Stock", "Plan de travail")
            obj.WorkPlane = ["XY", "XZ", "YZ"]
            obj.WorkPlane = "XY"
        
        # Créer une forme initiale
        self.updateShape(obj)
    
    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)
    
    def execute(self, obj):
        """Mettre à jour la forme du brut"""
        
        self.updateShape(obj)
    
    def updateShape(self, obj):
        """Mettre à jour la forme du brut en fonction des propriétés"""
        if not hasattr(obj,"WorkPlane"):
            return
        try:
            # Créer la boîte en fonction du plan de travail
            if obj.WorkPlane == "XY":
                box = Part.makeBox(obj.Length, obj.Width, obj.Height, obj.Origin)
            elif obj.WorkPlane == "XZ":
                box = Part.makeBox(obj.Length, obj.Height, obj.Width, obj.Origin)
            else:  # YZ
                box = Part.makeBox(obj.Height, obj.Length, obj.Width, obj.Origin)
            
            # Assigner la forme
            obj.Shape = box
            
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la mise à jour du brut: {str(e)}\n")
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["Length", "Width", "Height", "Origin", "WorkPlane"]:
            self.updateShape(obj)
    
    def __getstate__(self):
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderStock:
    """Classe pour gérer l'affichage du brut"""
    
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
        # Définir la couleur et la transparence du stock
        vobj.ShapeColor = (0.8, 0.8, 0.8)  # Gris clair
        vobj.Transparency = 80  # 80% de transparence
    
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Stock.svg")
    
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
    
    def updateData(self, obj, prop):
        """Appelé lorsqu'une propriété de l'objet est modifiée"""
        pass
    
    def onChanged(self, vobj, prop):
        """Appelé lorsqu'une propriété du ViewProvider est modifiée"""
        pass
    
    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        return False
    
    def __getstate__(self):
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None


class CamProject:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        self.Type = "CamProject"
        
        # Transformer l'objet en groupe
        #obj.addExtension("App::GroupExtensionPython")
        
        # Propriétés du projet
        if not hasattr(obj, "Origin"):
            obj.addProperty("App::PropertyVector", "Origin", "Project", "Origine du projet")
            obj.Origin = App.Vector(0, 0, 0)
        
        if not hasattr(obj, "WorkPlane"):
            obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Project", "Plan de travail")
            obj.WorkPlane = ["XY", "XZ", "YZ"]
            obj.WorkPlane = "XY"
        
        # Créer le groupe Operations
        self.getOperationsGroup(obj)
        
        # Créer le groupe Geometry
        self.getGeometryGroup(obj)
        
        # Créer ou obtenir l'objet Stock
        self.getStock(obj)
        
        # Assigner le proxy à la fin pour éviter les problèmes de récursion
        obj.Proxy = self

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)
    
    def getOperationsGroup(self, obj):
        """Obtenir ou créer le groupe Operations"""
        operations_group = None
        
        # Vérifier si le groupe existe déjà
        for child in obj.Group:
            if child.Name.startswith("Operations"):
                operations_group = child
                break
        
        # Créer le groupe s'il n'existe pas
        if not operations_group:
            operations_group = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "Operations")
            operations_group.Label = "Operations"
            obj.Group.append(operations_group)
            obj.addObject(operations_group)
        
        return operations_group
    
    def getGeometryGroup(self, obj):
        """Obtenir ou créer le groupe Geometry"""
        geometry_group = None
        
        # Vérifier si le groupe existe déjà
        for child in obj.Group:
            if child.Name.startswith("Geometry"):
                geometry_group = child
                break
        
        # Créer le groupe s'il n'existe pas
        if not geometry_group:
            geometry_group = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "Geometry")
            geometry_group.Label = "Geometry"
            obj.addObject(geometry_group)
        
        return geometry_group
    
    def getStock(self, obj):
        """Obtenir ou créer l'objet Stock"""
        stock = None
        
        # Vérifier si le stock existe déjà
        if hasattr(obj, "Group"):
            for child in obj.Group:
                if child.Name.startswith("Stock"):
                    stock = child
                    break
        
        # Créer le stock s'il n'existe pas
        if not stock:
            stock = App.ActiveDocument.addObject("Part::FeaturePython", "Stock")
            stock_obj = Stock(stock, obj)
            
            # Ajouter le ViewProvider
            if stock.ViewObject:
                ViewProviderStock(stock.ViewObject)
            
            # Initialiser les propriétés du stock
            stock.Length = 100.0
            stock.Width = 100.0
            stock.Height = 50.0
            stock.Origin = App.Vector(0, 0, 0)
            stock.WorkPlane = obj.WorkPlane
            
            # Ajouter le stock au groupe
            obj.addObject(stock)
        
        return stock
    
    def execute(self, obj):
        """Mettre à jour le projet"""
        # Rien à faire ici, le stock gère sa propre mise à jour
        pass
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop == "WorkPlane":
            # Synchroniser le plan de travail avec le stock
            stock = self.getStock(obj)
            if stock:
                stock.WorkPlane = obj.WorkPlane
    
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
        """Appelé lorsque l'objet est édité"""
        import BaptTaskPanel
        taskd = BaptTaskPanel.CamProjectTaskPanel(vobj.Object)
        Gui.Control.showDialog(taskd)
        return True
    
    def unsetEdit(self, vobj, mode=0):
        """Appelé lorsque l'édition est terminée"""
        Gui.Control.closeDialog()
        return True
    
    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True
    
    def __getstate__(self):
        """Sérialisation"""
        return None
    
    def __setstate__(self, state):
        """Désérialisation"""
        return None
