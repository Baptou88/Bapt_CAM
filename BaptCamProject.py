import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Base
import os
from PySide2 import QtWidgets

class Stock:
    """Classe pour gérer le brut d'usinage"""
    
    def __init__(self, obj, parent=None):
        """Initialise l'objet Stock
        
        Args:
            obj: L'objet FreeCAD
            parent: L'objet parent (CamProject)
        """
        
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
        
        # if not hasattr(obj, "Origin"):
        #     obj.addProperty("App::PropertyVector", "Origin", "Stock", "Origine du brut")
        #     obj.Origin = App.Vector(0, 0, 0)
        
        if not hasattr(obj, "WorkPlane"):
            obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Stock", "Plan de travail")
            obj.WorkPlane = ["XY", "XZ", "YZ"]
            obj.WorkPlane = "XY"
        
        # Créer une forme initiale
        self.updateShape(obj)

        obj.Proxy = self
    
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
        App.Console.PrintMessage(f'updateShape {obj.Placement.Base}\n')
        placement = obj.Placement
        obj.Shape = Part.Shape()
        
        
        # Créer la boîte en fonction du plan de travail
        if obj.WorkPlane == "XY":
            box = Part.makeBox(obj.Length, obj.Width, obj.Height)
        elif obj.WorkPlane == "XZ":
            box = Part.makeBox(obj.Length, obj.Height, obj.Width)
        else:  # YZ
            box = Part.makeBox(obj.Height, obj.Length, obj.Width)
        
        # Assigner la forme
        obj.Shape = box
        obj.Placement = placement
    
    def onChanged(self, obj, prop):
        """Gérer les changements de propriétés"""
        if prop in ["Length", "Width", "Height", "WorkPlane"]:
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

class ObjSelector(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélection d'objet")
        self.resize(350, 200)
        layout = QtWidgets.QVBoxLayout(self)
        
        # Liste des objets du document actif
        self.listWidget = QtWidgets.QListWidget()
        self.objects = []
        doc = App.ActiveDocument
        if doc:
            for obj in doc.Objects:
                if hasattr(obj, "Shape"):
                    self.objects.append(obj)
                    self.listWidget.addItem(f"{obj.Label} ({obj.Name})")
        layout.addWidget(self.listWidget)
        
        # Bouton OK
        self.okBtn = QtWidgets.QPushButton("OK")
        self.okBtn.clicked.connect(self.accept)
        layout.addWidget(self.okBtn)
        
        # Label pour afficher la bounding box
        self.resultLabel = QtWidgets.QLabel("")
        layout.addWidget(self.resultLabel)
        
        # Action lors de la sélection
        self.listWidget.currentRowChanged.connect(self.showObj)
    
    def showObj(self, row):
        if row < 0 or row >= len(self.objects):
            self.resultLabel.setText("")
            return
        obj = self.objects[row]
        self.resultLabel.setText(obj.Label)
    
    def getSelectedObject(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= len(self.objects):
            return None
        return self.objects[row]

class BoundingBoxSelector(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélection d'objet")
        self.resize(350, 200)
        layout = QtWidgets.QVBoxLayout(self)
        
        # Liste des objets du document actif
        self.listWidget = QtWidgets.QListWidget()
        self.objects = []
        doc = App.ActiveDocument
        if doc:
            for obj in doc.Objects:
                if hasattr(obj, "Shape"):
                    self.objects.append(obj)
                    self.listWidget.addItem(f"{obj.Label} ({obj.Name})")
        layout.addWidget(self.listWidget)
        
        # Bouton OK
        self.okBtn = QtWidgets.QPushButton("OK")
        self.okBtn.clicked.connect(self.accept)
        layout.addWidget(self.okBtn)
        
        # Label pour afficher la bounding box
        self.resultLabel = QtWidgets.QLabel("")
        layout.addWidget(self.resultLabel)
        
        # Action lors de la sélection
        self.listWidget.currentRowChanged.connect(self.showBoundingBox)
    
    def showBoundingBox(self, row):
        if row < 0 or row >= len(self.objects):
            self.resultLabel.setText("")
            return
        obj = self.objects[row]
        bbox = obj.Shape.BoundBox
        dims = f"X: {bbox.XLength:.2f} mm\nY: {bbox.YLength:.2f} mm\nZ: {bbox.ZLength:.2f} mm"
        self.resultLabel.setText(dims)
    
    def getSelectedBoundingBox(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= len(self.objects):
            return None
        obj = self.objects[row]
        return obj.Shape.BoundBox

class CamProject:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        self.Type = "CamProject"
        
        # Transformer l'objet en groupe
        #obj.addExtension("App::GroupExtensionPython")
        
        # Propriétés du projet
        # if not hasattr(obj, "Origin"):
        #     obj.addProperty("App::PropertyVector", "Origin", "Project", "Origine du projet")
        #     obj.Origin = App.Vector(0, 0, 0)
        
        if not hasattr(obj, "WorkPlane"):
            obj.addProperty("App::PropertyEnumeration", "WorkPlane", "Project", "Plan de travail")
            obj.WorkPlane = ["XY", "XZ", "YZ"]
            obj.WorkPlane = "XY"
        
        if not hasattr(obj, "Model"):
            obj.addProperty("App::PropertyLink", "Model", "Base", "The base objects for all operations")

        # Créer le groupe Operations
        self.getOperationsGroup(obj)
        
        # Créer le groupe Geometry
        self.getGeometryGroup(obj)
        
        # Créer ou obtenir l'objet Stock
        self.getStock(obj)
        
        # Obtenir l'objet Origin
        self.origin = self.getOrigin(obj)
        
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
    
    def getOrigin(self, obj):
        """Obtenir ou créer l'objet Origin pour le projet"""
        # if hasattr(obj, "Origin") and obj.Origin:
        #     return obj.Origin
        #App.Console.PrintMessage("Origin not found in project. Creating new origin.\n")
        # Chercher un objet Origin dans le groupe du projet
        if hasattr(obj, "Group"):
            for child in obj.Group:
                if hasattr(child, "Proxy") and getattr(child.Proxy, "Type", "") == "Origin":
                    #obj.Origin = child
                    return child
        # Sinon, créer un nouvel objet Origin

        import BaptOrigin

        origin = BaptOrigin.createOrigin()
        origin.Label = "Default Origin"
        obj.addObject(origin)
        #obj.Origin = origin
        App.Console.PrintMessage("Origin created: " + origin.Name + "\n")
        return origin

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
            Stock(stock, obj)
            
            # Ajouter le ViewProvider
            if stock.ViewObject:
                ViewProviderStock(stock.ViewObject)
            
            dlg = BoundingBoxSelector()
            if dlg.exec_():
                bbox = dlg.getSelectedBoundingBox()
                if bbox:
                    # App.Console.PrintMessage(f"Dimensions: X={bbox.XLength} Y={bbox.YLength} Z={bbox.ZLength}\n")
                    # print(f"X Range: {bbox.XMin} to {bbox.XMax}")
                    # print(f"Y Range: {bbox.YMin} to {bbox.YMax}")
                    # print(f"Z Range: {bbox.ZMin} to {bbox.ZMax}")
                    stock.Length = bbox.XLength
                    stock.Width = bbox.YLength
                    stock.Height = bbox.ZLength
                    stock.Placement = App.Placement(App.Vector(bbox.XMin, bbox.YMin, bbox.ZMin), App.Rotation(App.Vector(0,0,1),0))
                    App.Console.PrintMessage(f"Stock created: {stock.Name}\n")
                    App.Console.PrintMessage(f"Stock origin: {stock.Placement.Base}\n")
                    #stock.Origin = App.Vector(bbox.XMin, bbox.YMin, bbox.ZMin)
                else:
                    App.Console.PrintMessage("Aucun objet sélectionné.\n")
                    # Initialiser les propriétés du stock
                    stock.Length = 100.0
                    stock.Width = 100.0
                    stock.Height = 50.0
                    stock.Placement.Base = App.Vector(0, 0, 0)
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
        if hasattr(obj,"WorkPlane") and prop == "WorkPlane":
            # Synchroniser le plan de travail avec le stock
            stock = self.getStock(obj)
            if stock and hasattr(stock, "WorkPlane"):
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
