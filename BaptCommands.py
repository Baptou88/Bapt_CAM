# -*- coding: utf-8 -*-

"""
BaptCommands.py
Contient les commandes principales du workbench
"""

import os

import BaptCamProject
import BaptDrillOperation
import BaptGeometry
import BaptMachiningCycle
import BaptTools
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class CreateContourCommand:
    """Commande pour créer un Contournage"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Contour.svg"),
                'MenuText': "Nouveau Contournage",
                'ToolTip': "Créer un nouveau contournage pour l'usinage"}

    def IsActive(self):
        """La commande est active si une geometrie de contour est sélectionné"""
        sel = Gui.Selection.getSelection()
        #debug
        #if sel:
            #App.Console.PrintMessage(f"Sélection: {sel[0].Name}\n")
            #if hasattr(sel[0], "Proxy"):
                #App.Console.PrintMessage(f"Type de Proxy: {sel[0].Proxy.Type}\n")
        if not sel:
            return False
        #return hasattr(sel[0], "Proxy") and sel[0].Proxy.Type == "ContourGeometry"
        return hasattr(sel[0], "Proxy") and sel[0].Proxy.Type == "ContourGeometry"

    def Activated(self):
        """Créer un nouveau contournage"""
        # Obtenir la géométrie de contour sélectionnée
        contour_geometry = Gui.Selection.getSelection()[0]
        
        # Créer l'objet de contournage
        obj = App.ActiveDocument.addObject("Part::FeaturePython", "Contournage")
        
        # Ajouter la fonctionnalité
        contour = BaptMachiningCycle.ContournageCycle(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptMachiningCycle.ViewProviderContournageCycle(obj.ViewObject)
            obj.ViewObject.LineColor = (0.0, 0.0, 1.0)  # Bleu
            obj.ViewObject.PointColor = (0.0, 0.0, 1.0)  # Bleu
            obj.ViewObject.LineWidth = 2.0
            obj.ViewObject.PointSize = 4.0
        
        # Lier à la géométrie du contour par son nom
        obj.ContourGeometryName = contour_geometry.Name
        
        # Ajouter le contournage comme enfant de la géométrie du contour
        # Vérifier si la géométrie du contour est un groupe (a l'extension Group)
        if hasattr(contour_geometry, "Group") and hasattr(contour_geometry, "addObject"):
            # Ajouter directement à la géométrie du contour
            contour_geometry.addObject(obj)
            App.Console.PrintMessage(f"Contournage ajouté comme enfant de {contour_geometry.Label}\n")
        else:
            # Si la géométrie n'est pas un groupe, essayer de l'ajouter au document
            App.Console.PrintWarning(f"La géométrie {contour_geometry.Label} n'est pas un groupe, impossible d'ajouter le contournage comme enfant\n")
            
            # Trouver le groupe parent de la géométrie du contour
            for parent in App.ActiveDocument.Objects:
                if hasattr(parent, "Group") and contour_geometry in parent.Group:
                    parent.addObject(obj)
                    App.Console.PrintMessage(f"Contournage ajouté comme enfant de {parent.Label}\n")
                    break
        
        # Recomputer
        App.ActiveDocument.recompute()
        
        # Message de confirmation
        App.Console.PrintMessage(f"Contournage créé et lié à {contour_geometry.Label}.\n")

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
        
        # Créer l'objet avec le type DocumentObjectGroupPython pour pouvoir contenir des enfants
        obj = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "DrillGeometry")
        
        # Ajouter la fonctionnalité
        drill = BaptGeometry.DrillGeometry(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptGeometry.ViewProviderDrillGeometry(obj.ViewObject)
        
        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)
        
        # Recomputer
        App.ActiveDocument.recompute()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)


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
        
        App.Console.PrintMessage("par ici\n")

        # Ajouter la fonctionnalité
        project = BaptCamProject.CamProject(obj)

        App.Console.PrintMessage("par là\n")
        
        App.Console.PrintMessage('vreation view provider\n')
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptCamProject.ViewProviderCamProject(obj.ViewObject)
        
        # Recomputer
        App.ActiveDocument.recompute()
        
        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)
            
        # Message de confirmation
        App.Console.PrintMessage("Projet CAM créé avec succès!\n")

class CreateContourGeometryCommand:
    """Commande pour créer une géométrie de contour"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Contour.svg"),
                'MenuText': "Nouvelle géométrie de contour",
                'ToolTip': "Créer une nouvelle géométrie de contour pour l'usinage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False
        return hasattr(sel[0], "Proxy") and sel[0].Proxy.Type == "CamProject"

    def Activated(self):
        """Créer une nouvelle géométrie de contour"""
        # Obtenir le projet CAM sélectionné
        project = Gui.Selection.getSelection()[0]
        
        # Créer l'objet avec le bon type pour avoir une Shape
        obj = App.ActiveDocument.addObject("Part::FeaturePython", "ContourGeometry")
        #obj = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "ContourGeometry")
        
        # Ajouter la fonctionnalité
        contour = BaptGeometry.ContourGeometry(obj)
        
        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptGeometry.ViewProviderContourGeometry(obj.ViewObject)
            obj.ViewObject.LineColor = (1.0, 0.0, 0.0)  # Rouge
            obj.ViewObject.PointColor = (1.0, 0.0, 0.0)  # Rouge
            obj.ViewObject.LineWidth = 4.0  # Largeur de ligne plus grande
            obj.ViewObject.PointSize = 6.0  # Taille des points plus grande
        
        # Message de confirmation
        App.Console.PrintMessage("Géométrie de contour créée. Sélectionnez les arêtes pour le contour.\n")
        
        # Ouvrir le panneau de tâches pour l'édition
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)
        Gui.ActiveDocument.setEdit(obj.Name)

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
            reload(BaptDrillOperation) 
            reload(BaptTools)  # Ajouter le module BaptTools
            reload(BaptMachiningCycle)
            import BaptContournageTaskPanel
            reload(BaptContournageTaskPanel)
            import BaptDrillTaskPanel
            reload(BaptDrillTaskPanel)
            import BaptToolsTaskPanel
            reload(BaptToolsTaskPanel)
            import BaptPreferences
            reload(BaptPreferences)
            # Message de confirmation
            App.Console.PrintMessage("hot Reload avec Succes!\n")

        except Exception as e:
            App.Console.PrintError(f"Erreur lors du rechargement des modules: {str(e)}\n")
            pass

        # Recomputer
        App.ActiveDocument.recompute()
        

class ToolsManagerCommand:
    """Commande pour ouvrir le gestionnaire d'outils"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg"),
                'MenuText': "Gestionnaire d'outils",
                'ToolTip': "Ouvrir le gestionnaire d'outils pour créer et éditer des outils"}

    def IsActive(self):
        """La commande est toujours active"""
        return True

    def Activated(self):
        """Ouvrir le gestionnaire d'outils"""
        panel = BaptTools.ToolsManagerPanel()
        Gui.Control.showDialog(panel)
        App.Console.PrintMessage("Gestionnaire d'outils ouvert.\n")

class CreateDrillOperationCommand:
    """Commande pour créer une opération d'usinage de perçage"""

    def GetResources(self):
        return {'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Drilling.svg"),
                'MenuText': "Nouvelle opération de perçage",
                'ToolTip': "Créer une nouvelle opération d'usinage pour les géométries de perçage"}

    def IsActive(self):
        """La commande est active si une géométrie de perçage est sélectionnée"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False
        
        # Vérifier si l'objet sélectionné est une géométrie de perçage
        # en vérifiant directement le type de Proxy.Type
        return hasattr(sel[0], "Proxy") and hasattr(sel[0].Proxy, "Type") and sel[0].Proxy.Type == "DrillGeometry"

    def Activated(self):
        """Créer une nouvelle opération de perçage"""
        # Obtenir la géométrie de perçage sélectionnée
        drill_geometry = Gui.Selection.getSelection()[0]
        
        # Créer l'objet avec le bon type pour avoir une Shape
        obj = App.ActiveDocument.addObject("Part::FeaturePython", "DrillOperation")
        
        # Ajouter la fonctionnalité
        operation = BaptDrillOperation.DrillOperation(obj)
        
        # Ajouter le ViewProvider
        if obj.ViewObject:
            BaptDrillOperation.ViewProviderDrillOperation(obj.ViewObject)
            obj.ViewObject.ShapeColor = (0.0, 0.0, 1.0)  # Bleu
        
        # Définir le nom de la géométrie de perçage associée (au lieu d'un lien direct)
        obj.DrillGeometryName = drill_geometry.Name
        
        # Ajouter l'opération comme enfant direct de la géométrie de perçage
        # Maintenant que DrillGeometry est un DocumentObjectGroupPython, on peut utiliser addObject
        drill_geometry.addObject(obj)
        
        # Recomputer
        App.ActiveDocument.recompute()
        
        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)
        
        # Message de confirmation
        App.Console.PrintMessage("Opération de perçage créée et ajoutée comme enfant de la géométrie de perçage.\n")

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
Gui.addCommand('Bapt_CreateContourGeometry', CreateContourGeometryCommand())
Gui.addCommand('Bapt_CreateMachiningCycle', CreateContourCommand())
Gui.addCommand('Bapt_CreateHotReload', CreateHotReloadCommand())
Gui.addCommand('Bapt_ToolsManager', ToolsManagerCommand())
Gui.addCommand('Bapt_CreateDrillOperation', CreateDrillOperationCommand())  # Ajouter la nouvelle commande
