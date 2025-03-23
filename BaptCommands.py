# -*- coding: utf-8 -*-

"""
BaptCommands.py
Contient les commandes principales du workbench
"""

import FreeCAD as App
import FreeCADGui as Gui
import os
from PySide import QtCore, QtGui
import BaptCamProject
import BaptGeometry

class CreateDrillGeometryCommand:
    """Commande pour créer une géométrie de perçage"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Drilling.svg"),
                'MenuText': "Nouvelle géométrie de perçage",
                'ToolTip': "Créer une nouvelle géométrie de perçage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False
        return hasattr(sel[0], "Proxy") and sel[0].Proxy.Type == "CamProject"

    def Activated(self):
        """Créer une nouvelle géométrie de perçage"""
        # Obtenir le projet CAM sélectionné
        project = Gui.Selection.getSelection()[0]
        
        # Créer l'objet avec le bon type pour avoir une Shape
        obj = App.ActiveDocument.addObject("Part::FeaturePython", "DrillGeometry")
        
        # Ajouter la fonctionnalité
        drill = BaptGeometry.DrillGeometry(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptGeometry.ViewProviderDrillGeometry(obj.ViewObject)
            obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Rouge
        
        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)
        
        # Recomputer
        App.ActiveDocument.recompute()
        
        # Message de confirmation
        App.Console.PrintMessage("Géométrie de perçage créée. Sélectionnez les faces cylindriques.\n")

class CreateCamProjectCommand:
    """Commande pour créer un nouveau projet CAM"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg"),
                'MenuText': "Nouveau Projet CAM",
                'ToolTip': "Créer un nouveau projet d'usinage"}

    def IsActive(self):
        """La commande est active si un document est ouvert"""
        return App.ActiveDocument is not None

    def Activated(self):
        """Créer un nouveau projet CAM"""
        # Créer un nouveau document si aucun n'est ouvert
        if App.ActiveDocument is None:
            App.newDocument()
        
        # Créer l'objet projet CAM
        obj = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "CamProject")
        
        # Ajouter la fonctionnalité
        project = BaptCamProject.CamProject(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptCamProject.ViewProviderCamProject(obj.ViewObject)
        
        # Recomputer
        App.ActiveDocument.recompute()
        
        # Message de confirmation
        App.Console.PrintMessage("Projet CAM créé avec succès!\n")

class CreateHotReloadCommand:
    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg"),
                'MenuText': "Hot Reload",
                'ToolTip': "Recharge les modules Bapt"}
    def IsActive(self):
        return App.ActiveDocument is not None
    def Activated(self):
        """Recharge les modules Bapt"""
        try:    
            from importlib import reload
            reload(BaptCamProject)
            reload(BaptGeometry)
            reload(BaptDrillTaskPanel)  
            reload(BaptCommands)
            reload(BaptPreferences)
            reload(BaptWorkbench)   
        except:
            pass

        # Recomputer
        App.ActiveDocument.recompute()
        # Message de confirmation
        App.Console.PrintMessage("hot Reload avec Succes!\n")



class BaptCommand:
    """Ma première commande"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg"),
                'MenuText': "Ma Commande",
                'ToolTip': "Description de ma commande"}

    def IsActive(self):
        """Si cette fonction retourne False, la commande sera désactivée"""
        return True

    def Activated(self):
        """Cette fonction est exécutée quand la commande est activée"""
        App.Console.PrintMessage("Hello, FreeCAD!\n")

# Enregistrer les commandes
Gui.addCommand('Bapt_Command', BaptCommand())
Gui.addCommand('Bapt_CreateCamProject', CreateCamProjectCommand())
Gui.addCommand('Bapt_CreateDrillGeometry', CreateDrillGeometryCommand())
Gui.addCommand('Bapt_CreateHotReload', CreateHotReloadCommand())
