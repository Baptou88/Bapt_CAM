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
