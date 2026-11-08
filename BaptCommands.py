# -*- coding: utf-8 -*-

"""
BaptCommands.py
Contient les commandes principales du workbench
"""

import FreeCAD as App
import FreeCADGui as Gui
import BaptCamProject
import ContourBaseGeom
import BaptContour25DGeom
import BaptContourEditableGeometry
import BaptContourGeometry
import BaptDrillGeometry
from BaptHighlight import CreateHighlightCommand
import BaptMpfReader
import BaptPath
import Op.AdaptativeOp as AdaptativeOp
import Op.PocketOp as PocketOp
from Op.PathOp import CreatePathCommand
from Op.ArrayOp import CreateArrayOpCommand

import BaptPostProcess
import BaptPreferences
import Tool.BaptTools as BaptTools
import BaptUtilities


from BaptOrigin import CreateOriginCommand

from Op import DrillOp, OpContournage, OpSurfacage, OpContournageTest, SpiraleOp, ChamferOp
from Probe import probeFace, probeReference
import Tool.ToolsGUI
import testFPO


class CreateCamProjectCommand:
    """Commande pour créer un nouveau projet CAM"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("BaptWorkbench.svg"),
                'MenuText': "Nouveau Projet CAM",
                'ToolTip': "Créer un nouveau projet d'usinage"}

    def IsActive(self):
        """La commande est active si un document est ouvert"""
        return App.ActiveDocument is not None

    def Activated(self):
        """Créer un nouveau projet CAM"""

        doc = App.ActiveDocument
        # Créer un nouveau document si aucun n'est ouvert
        if doc is None:
            doc = App.newDocument()

        doc.openTransaction('Create Cam Project')

        # Créer l'objet projet CAM
        obj = doc.addObject("App::DocumentObjectGroupPython", "CamProject")

        # Ajouter la fonctionnalité
        BaptCamProject.CamProject(obj)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            BaptCamProject.ViewProviderCamProject(obj.ViewObject)

            Gui.activeView().setActiveObject("camproject", obj)

        # Recomputer
        doc.recompute()
        doc.commitTransaction()

        # Ouvrir l'éditeur
        if obj.ViewObject and App.GuiUp:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)


# -------------Geometry Commands


class CreateContourGeometryCommand:
    """Commande pour créer une géométrie de contour"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Tree_Contour.svg"),
                'MenuText': "Nouvelle géométrie de contour",
                'ToolTip': "Créer une nouvelle géométrie de contour pour l'usinage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer une nouvelle géométrie de contour"""

        doc = App.ActiveDocument
        doc.openTransaction('Create Contour Geometry')

        # Obtenir le projet CAM sélectionné ou actif
        project = BaptUtilities.getActiveCamProject()

        obj = doc.addObject("Part::FeaturePython", "ContourGeometry")
        # obj = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "ContourGeometry")
        obj.addExtension("App::GroupExtensionPython")

        # Ajouter la fonctionnalité
        BaptContourGeometry.ContourGeometry(obj)

        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            BaptContourGeometry.ViewProviderContourGeometry(obj.ViewObject)

        # Message de confirmation
        App.Console.PrintMessage("Géométrie de contour créée.\n")

        doc.commitTransaction()
        doc.recompute()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)


class CreateDrillGeometryCommand:
    """Commande pour créer une géométrie de perçage"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Tree_Drilling.svg"),
                'MenuText': "Nouvelle géométrie de perçage",
                'ToolTip': "Créer une nouvelle géométrie de perçage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer une nouvelle géométrie de perçage"""

        doc = App.ActiveDocument
        # Obtenir le projet CAM sélectionné
        project = BaptUtilities.getActiveCamProject()

        doc.openTransaction('Create Drill Geometry')

        # Créer l'objet avec le type DocumentObjectGroupPython pour pouvoir contenir des enfants
        # obj = doc.addObject("App::DocumentObjectGroupPython", "DrillGeometry")
        obj = doc.addObject("Part::FeaturePython", "DrillGeometry")
        obj.addExtension("App::GroupExtensionPython")

        # Ajouter la fonctionnalité
        BaptDrillGeometry.DrillGeometry(obj)

        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            BaptDrillGeometry.ViewProviderDrillGeometry(obj.ViewObject)

        # Recomputer
        doc.recompute()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()


class CreateContourCommand:
    """Commande pour créer un Contournage"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Contournage.svg"),
                'MenuText': "Nouveau Contournage",
                'ToolTip': "Créer un nouveau contournage pour l'usinage"}

    def IsActive(self):
        """La commande est active si une geometrie de contour est sélectionné"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False

        return hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, (
            BaptContourGeometry.ContourGeometry,
            BaptContourEditableGeometry.ContourEditableGeometry
        )
        )

    def Activated(self):
        """Créer un nouveau contournage"""
        doc = App.ActiveDocument
        doc.openTransaction('Create Contour')

        # Obtenir la géométrie de contour sélectionnée
        contour_geometry = Gui.Selection.getSelection()[0]

        # Créer l'objet de contournage
        obj = doc.addObject("Part::FeaturePython", "Contournage")

        # Ajouter la fonctionnalité
        OpContournage.ContournageCycle(obj)

        pref = BaptPreferences.BaptPreferences()
        modeAjout = pref.getModeAjout()

        # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
        # 1 = ajouter à la géométrie comme enfant (pas conseillé)
        # 2 = ajouter au groupe opérations du projet CAM

        if modeAjout == 1 or modeAjout == 0:

            # Ajouter le contournage comme enfant de la géométrie du contour
            contour_geometry.addObject(obj)
            contour_geometry.Group.append(obj)

        if modeAjout == 2 or modeAjout == 0:
            camProject = BaptUtilities.find_cam_project(contour_geometry)
            if camProject:
                operations_group = camProject.Proxy.getOperationsGroup(camProject)
                if modeAjout == 2:
                    operations_group.addObject(obj)
                    operations_group.Group.append(obj)
                elif modeAjout == 0:
                    link = doc.addObject('App::Link', f'Link_{obj.Label}')
                    link.setLink(obj)
                    operations_group.addObject(link)
                    operations_group.Group.append(link)

        # Lier à la géométrie du contour
        obj.ContourGeometry = contour_geometry

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            OpContournage.ViewProviderContournageCycle(obj.ViewObject)

        doc.recompute()

        # Ouvrir le panneau de tâches pour l'édition
        if App.GuiUp and obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()

        # Message de confirmation
        App.Console.PrintMessage(f"Contournage créé et lié à {contour_geometry.Label}.\n")


class CreateContourEditableGeometryCommand:
    """Commande pour créer une géométrie de contour editable via Sketcher"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("ContourEditable.svg"),
                'MenuText': "Nouvelle géométrie de contour editable",
                'ToolTip': "Créer une nouvelle géométrie de contour pour l'usinage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer une nouvelle géométrie de contour"""
        doc = App.ActiveDocument

        # Obtenir le projet CAM sélectionné
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")

            return

        doc.openTransaction('Create Contour Geometry')
        # Créer l'objet avec le bon type pour avoir une Shape
        obj = doc.addObject("Part::FeaturePython", "ContourEditableGeometry")
        # obj = App.ActiveDocument.addObject("App::DocumentObjectGroupPython", "ContourGeometry")
        obj.addExtension("App::GroupExtensionPython")

        # Ajouter la fonctionnalité
        BaptContourEditableGeometry.ContourEditableGeometry(obj)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            obj.ViewObject.addExtension("Gui::ViewProviderGroupExtensionPython")
            BaptContourEditableGeometry.ViewProviderContourEditableGeometry(obj.ViewObject)

        # Ajouter au groupe Geometry
        geometry_group = project.Proxy.getGeometryGroup(project)
        geometry_group.addObject(obj)

        # Message de confirmation
        App.Console.PrintMessage("Géométrie de contour editable créée.\n")

        App.ActiveDocument.recompute()

        doc.commitTransaction()


class CreateContour25DGeometryCommand:
    """Commande pour créer une géométrie de contour 2.5D via Sketcher"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("ContourEditable.svg"),
                'MenuText': "Nouvelle géométrie de contour editable",
                'ToolTip': "Créer une nouvelle géométrie de contour pour l'usinage"}

    def IsActive(self):
        """La commande est active si un projet CAM est sélectionné"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer une nouvelle géométrie de contour"""
        doc = App.ActiveDocument

        # Obtenir le projet CAM sélectionné
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")

            return

        doc.openTransaction('Create Contour Geometry')
        # Créer l'objet avec le bon type pour avoir une Shape
        BaptContour25DGeom.createContour25DGeom(project)

        # Message de confirmation
        App.Console.PrintMessage("Géométrie de contour 2.5D créée.\n")

        App.ActiveDocument.recompute()

        doc.commitTransaction()


# ------------- Operation Command

class CreateDrillOperationCommand:
    """Commande pour créer une opération d'usinage de perçage"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Tree_Drilling.svg"),
                'MenuText': "Nouvelle opération de perçage",
                'ToolTip': "Créer une nouvelle opération d'usinage pour les géométries de perçage"}

    def IsActive(self):
        """La commande est active si une géométrie de perçage est sélectionnée"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False

        return hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, BaptDrillGeometry.DrillGeometry)

    def Activated(self):
        """Créer une nouvelle opération de perçage"""

        doc = App.ActiveDocument
        doc.openTransaction('Create Drill Operation')

        # Obtenir la géométrie de perçage sélectionnée
        drill_geometry = Gui.Selection.getSelection()[0]

        # Créer l'objet avec le bon type pour avoir une Shape
        obj = doc.addObject("Part::FeaturePython", "DrillOperation")

        # Ajouter la fonctionnalité
        DrillOp.DrillOperation(obj)

        # Définir le nom de la géométrie de perçage associée (au lieu d'un lien direct)
        obj.DrillGeometry = drill_geometry

        pref = BaptPreferences.BaptPreferences()
        modeAjout = pref.getModeAjout()

        # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
        # 1 = ajouter à la géométrie comme enfant (pas conseillé)
        # 2 = ajouter au groupe opérations du projet CAM

        if modeAjout == 1 or modeAjout == 0:

            # Ajouter le contournage comme enfant de la géométrie du contour
            drill_geometry.addObject(obj)
            drill_geometry.Group.append(obj)

        if modeAjout == 2 or modeAjout == 0:
            camProject = BaptUtilities.find_cam_project(drill_geometry)
            if camProject:
                operations_group = camProject.Proxy.getOperationsGroup(camProject)
                if modeAjout == 2:
                    operations_group.addObject(obj)
                    operations_group.Group.append(obj)
                elif modeAjout == 0:
                    link = doc.addObject('App::Link', f'Link_{obj.Label}')
                    link.setLink(obj)
                    operations_group.addObject(link)
                    operations_group.Group.append(link)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            DrillOp.ViewProviderDrillOperation(obj.ViewObject)

        # Recomputer
        doc.recompute()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        # Message de confirmation
        App.Console.PrintMessage("Opération de perçage créée et ajoutée comme enfant de la géométrie de perçage.\n")

        doc.commitTransaction()


class CreateSpiraleOpCommand:
    """Commande pour créer une opération d'usinage de spirale"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Tree_Drilling.svg"),
                'MenuText': "Nouvelle opération de spirale",
                'ToolTip': "Créer une nouvelle opération d'usinage pour les géométries de percage"}

    def IsActive(self):
        """La commande est active si une géométrie de perçage est sélectionnée"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False

        return hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, BaptDrillGeometry.DrillGeometry)

    def Activated(self):
        """Créer une nouvelle opération de perçage"""

        doc = App.ActiveDocument
        doc.openTransaction('Create Drill Operation')

        # Obtenir la géométrie de perçage sélectionnée
        drill_geometry = Gui.Selection.getSelection()[0]

        # Créer l'objet avec le bon type pour avoir une Shape
        obj = doc.addObject("Part::FeaturePython", "SpiraleOperation")

        camProject = BaptUtilities.find_cam_project(drill_geometry)

        # Ajouter la fonctionnalité
        SpiraleOp.SpiraleOp(obj, camProject)

        # Définir le nom de la géométrie de perçage associée (au lieu d'un lien direct)
        obj.DrillGeometry = drill_geometry

        pref = BaptPreferences.BaptPreferences()
        modeAjout = pref.getModeAjout()

        # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
        # 1 = ajouter à la géométrie comme enfant (pas conseillé)
        # 2 = ajouter au groupe opérations du projet CAM

        if modeAjout == 1 or modeAjout == 0:

            # Ajouter le contournage comme enfant de la géométrie du contour
            drill_geometry.addObject(obj)
            drill_geometry.Group.append(obj)

        if modeAjout == 2 or modeAjout == 0:

            if camProject:
                operations_group = camProject.Proxy.getOperationsGroup(camProject)
                if modeAjout == 2:
                    operations_group.addObject(obj)
                    operations_group.Group.append(obj)
                elif modeAjout == 0:
                    link = doc.addObject('App::Link', f'Link_{obj.Label}')
                    link.setLink(obj)
                    operations_group.addObject(link)
                    operations_group.Group.append(link)

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            SpiraleOp.ViewProviderSpiraleOp(obj.ViewObject)

        # Recomputer
        doc.recompute()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            pass
            # obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        # Message de confirmation
        App.Console.PrintMessage("Opération de spirale créée et ajoutée comme enfant de la géométrie de perçage.\n")

        doc.commitTransaction()


class CreateAdaptativeOperationCommand:
    """Commande pour créer une opération de fraisage adaptatif (trochoïdal)"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("AdaptativeOp.svg"),
                'MenuText': "Nouvelle opération adaptive",
                'ToolTip': "Créer une opération de fraisage adaptatif trochoïdal"}

    def IsActive(self):
        sel = Gui.Selection.getSelection()
        return sel and hasattr(sel[0], "Proxy") and \
            isinstance(sel[0].Proxy, BaptContourGeometry.ContourGeometry
                       )

    def Activated(self):
        doc = App.ActiveDocument
        doc.openTransaction('Create Adaptive Operation')
        contour_geometry = Gui.Selection.getSelection()[0]
        AdaptativeOp.createAdaptativeOperation(contour=contour_geometry)
        doc.recompute()
        doc.commitTransaction()
        App.Console.PrintMessage(
            f"Opération adaptive créée et liée à {contour_geometry.Label}.\n")


class CreateChamferOperationCommand:
    """Commande pour créer une opération de chamfrein sur profil"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Contournage.svg"),
                'MenuText': "Nouvelle opération de chamfrein",
                'ToolTip': "Créer une opération de chamfrein sur un profil de contour"}

    def IsActive(self):
        sel = Gui.Selection.getSelection()
        if not sel:
            return False

        return hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, ContourBaseGeom.ContourBaseGeom)

    def Activated(self):
        doc = App.ActiveDocument
        doc.openTransaction('Create Chamfer Operation')
        contour_geometry = Gui.Selection.getSelection()[0]
        ChamferOp.createChamferOperation(contour=contour_geometry)
        doc.recompute()
        doc.commitTransaction()
        App.Console.PrintMessage(f"Opération de chamfrein créée et liée à {contour_geometry.Label}.\n")


class CreateContourTestCommand:
    """Commande pour créer un Contournage test"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Contournage.svg"),
                'MenuText': "Nouveau Contournage Test",
                'ToolTip': "Créer un nouveau contournage test pour l'usinage"}

    def IsActive(self):
        """La commande est active si une geometrie de contour est sélectionné"""
        sel = Gui.Selection.getSelection()
        if not sel:
            return False

        return hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, (
            BaptContourGeometry.ContourGeometry,
            BaptContourEditableGeometry.ContourEditableGeometry
        )
        )

    def Activated(self):
        """Créer un nouveau contournage test"""
        doc = App.ActiveDocument
        doc.openTransaction('Create Contour Test')

        # Obtenir la géométrie de contour sélectionnée
        contour_geometry = Gui.Selection.getSelection()[0]

        # Créer l'objet de contournage
        obj = doc.addObject("Part::FeaturePython", "ContournageTest")

        # Ajouter la fonctionnalité
        OpContournageTest.opContournageTest(obj)

        pref = BaptPreferences.BaptPreferences()
        modeAjout = pref.getModeAjout()

        # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
        # 1 = ajouter à la géométrie comme enfant (pas conseillé)
        # 2 = ajouter au groupe opérations du projet CAM

        if modeAjout == 1 or modeAjout == 0:

            # Ajouter le contournage comme enfant de la géométrie du contour
            contour_geometry.addObject(obj)
            contour_geometry.Group.append(obj)

        if modeAjout == 2 or modeAjout == 0:
            camProject = BaptUtilities.find_cam_project(contour_geometry)
            if camProject:
                operations_group = camProject.Proxy.getOperationsGroup(camProject)
                if modeAjout == 2:
                    operations_group.addObject(obj)
                    operations_group.Group.append(obj)
                elif modeAjout == 0:
                    link = doc.addObject('App::Link', f'Link_{obj.Label}')
                    link.setLink(obj)
                    operations_group.addObject(link)
                    operations_group.Group.append(link)

        # Lier à la géométrie du contour
        obj.ContourGeometry = contour_geometry

        # Ajouter le ViewProvider
        if App.GuiUp and obj.ViewObject:
            OpContournageTest.opContournageTestViewProvider(obj.ViewObject)

        doc.recompute()

        # Ouvrir le panneau de tâches pour l'édition
        # if App.GuiUp and obj.ViewObject:
        #     obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()

        # Message de confirmation
        App.Console.PrintMessage(f"Contournage créé et lié à {contour_geometry.Label}.\n")


class CreateSurfacageCommand:
    """Commande pour créer un nouveau surfacage"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Surfacage.svg"),
                'MenuText': "Nouveau Surfacage",
                'ToolTip': "Créer un nouveau surfacage"}

    def IsActive(self):
        """La commande est active si un document est ouvert"""

        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer un nouveau surfacage"""

        doc = App.ActiveDocument
        # Créer un nouveau document si aucun n'est ouvert
        if doc is None:
            doc = App.newDocument()

        project = BaptUtilities.getActiveCamProject()

        doc.openTransaction('Create Surfacage')

        # Créer l'objet surfacage
        obj = doc.addObject("Part::FeaturePython", "Surfacage")

        # Ajouter la fonctionnalité
        OpSurfacage.Surfacage(obj, project)
        model = project.Proxy.getModel(project)
        if model is not None:
            obj.Depth = model.Shape.BoundBox.ZMax

        expr = project.Proxy.getExprSet()
        if expr is not None:
            obj.setExpression("safeZ", f"{expr.Name}.safeZ")

        # Ajouter au groupe Operations
        operations_group = project.Proxy.getOperationsGroup(project)
        operations_group.addObject(obj)

        # Ajouter le ViewProvider
        if obj.ViewObject:
            OpSurfacage.ViewProviderSurfacage(obj.ViewObject)

        obj.Stock = project.Proxy.getStock(project)

        # Recomputer
        doc.recompute()
        doc.commitTransaction()

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)


class CreatePocketOperationCommand:
    """Commande pour créer une opération de poche basée sur ContourGeometry"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("Pocket.svg"),
                'MenuText': "Nouvelle opération de poche",
                'ToolTip': "Créer une nouvelle opération de poche pour l'usinage"}

    def IsActive(self):
        sel = Gui.Selection.getSelection()
        return sel and hasattr(sel[0], "Proxy") and \
            isinstance(sel[0].Proxy, ContourBaseGeom.ContourBaseGeom
                       )

    def Activated(self):
        doc = App.ActiveDocument
        doc.openTransaction('Create Pocket Operation')
        contour_geometry = Gui.Selection.getSelection()[0]
        PocketOp.createPocketOperation(contour=contour_geometry)
        # if obj.ViewObject:
        #     BaptPocketOperation.ViewProviderPocketOperation(obj.ViewObject)
        #     obj.ViewObject.Proxy.setEdit(obj.ViewObject)
        doc.recompute()
        doc.commitTransaction()
        App.Console.PrintMessage(f"Opération de poche créée et liée à {contour_geometry.Label}.\n")

# ------------- Probe Commands


class ProbeFaceCommand:
    """Commande pour générer un Probing sur une face"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("ProbeSurface.svg"),
                'MenuText': "Probing sur une face",
                'ToolTip': "Générer un Probing sur une face"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        # import probe.ProbeFace

        doc = App.ActiveDocument
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return

        doc.openTransaction('Create Probe Face')

        obj = doc.addObject("Part::FeaturePython", "ProbeFace")

        # Ajouter au groupe Operations
        operations_group = project.Proxy.getOperationsGroup(project)
        operations_group.addObject(obj)

        probeFace.ProbeFace(obj)

        if obj.ViewObject:
            probeFace.ViewProviderProbeFace(obj.ViewObject)

        # Ouvrir l'éditeur
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()


class ProbeReferenceCommand:
    """Commande pour créer une feature complémentaire de palpage multi-points."""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("ProbeSurface.svg"),
                'MenuText': "Palpage multipoints",
                'ToolTip': "Créer une feature complémentaire de palpage multi-points"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        doc = App.ActiveDocument
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return

        doc.openTransaction('Create Probe Reference')
        obj = doc.addObject("Part::FeaturePython", "ProbeReference")

        operations_group = project.Proxy.getOperationsGroup(project)
        operations_group.addObject(obj)

        probeReference.ProbeReference(obj)

        if obj.ViewObject:
            probeReference.ViewProviderProbeReference(obj.ViewObject)
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()
        doc.recompute()
        App.Console.PrintMessage("Objet de palpage multi-points créé.\n")

# ------------- Utilities


class rapportProgrammationCommand:
    def GetResources(self):
        return {
            'Pixmap': BaptUtilities.getIconPath("BaptWorkbench.svg"),
            'MenuText': "Rapport de programmation",
            'ToolTip': "Générer un rapport de programmation pour le projet CAM actif"
        }

    def IsActive(self):
        """La commande est active si un projet CAM est actif"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Générer le rapport de programmation"""
        import RapportProgrammation
        doc = App.ActiveDocument
        cam_project = BaptUtilities.getActiveCamProject()
        if cam_project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return

        doc.openTransaction('Générer Rapport de Programmation')
        RapportProgrammation.generate_report(cam_project)
        doc.recompute()
        doc.commitTransaction()
        App.Console.PrintMessage("Rapport de programmation généré.\n")


class PostProcessGCodeCommand:
    """Commande pour générer un programme G-code à partir du projet CAM"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("PostProcess.svg"),
                'MenuText': "Post-process G-code",
                'ToolTip': "Générer un programme G-code à partir des opérations d'usinage"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        BaptPostProcess.postprocess_gcode()


class ToolsManagerCommand:
    """Commande pour ouvrir le gestionnaire d'outils"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("BaptWorkbench.svg"),
                'MenuText': "Gestionnaire d'outils",
                'ToolTip': "Ouvrir le gestionnaire d'outils pour créer et éditer des outils"}

    def IsActive(self):
        """La commande est toujours active"""
        return True

    def Activated(self):
        """Ouvrir le gestionnaire d'outils"""
        panel = Tool.ToolsGUI.ToolsManagerPanel()
        Gui.Control.showDialog(panel)
        App.Console.PrintMessage("Gestionnaire d'outils ouvert.\n")


class HoleRecognitionCommand:
    """Commande pour la reconnaissance automatique de trous"""

    def GetResources(self):
        return {
            'Pixmap': BaptUtilities.getIconPath("Tree_HoleRecognition.svg"),
            'MenuText': "Reconnaissance de trous",
            'ToolTip': "Détecter automatiquement les trous cylindriques perpendiculaires au plan de travail"
        }

    def IsActive(self):
        """La commande est active si un document est ouvert"""
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        """Créer un nouvel objet de reconnaissance de trous"""
        import BaptHoleRecognition

        doc = App.ActiveDocument

        cam_project = BaptUtilities.getActiveCamProject()
        if cam_project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return

        doc.openTransaction('Create Hole Recognition')
        obj = BaptHoleRecognition.createHoleRecognition()
        cam_project.Proxy.getGeometryGroup(cam_project).addObject(obj)
        # Ouvrir le TaskPanel
        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)

        doc.commitTransaction()
        App.Console.PrintMessage("Objet de reconnaissance de trous créé.\n")

# ------------- Debug Commands


class CreateHotReloadCommand:
    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("hotreload.svg"),
                'MenuText': "Hot Reload",
                'ToolTip': "Recharge les modules Bapt",
                'Accel': "Ctrl+R"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        """Recharge les modules Bapt"""
        try:
            from importlib import reload
            reload(BaptCamProject)
            import BaptContourGeometry
            reload(BaptContourGeometry)
            import Op.Gui.ContournageTaskPanel as ContournageTaskPanel
            reload(ContournageTaskPanel)
            import Gui.ContourTaskPanel as ContourTaskPanel
            reload(ContourTaskPanel)
            reload(DrillOp)
            reload(BaptTools)  # Ajouter le module BaptTools
            reload(OpContournage)
            reload(BaptPath)
            import Gui.DrillGeomTaskPanel as DrillGeomTaskPanel
            reload(DrillGeomTaskPanel)
            import BaptPreferences
            reload(BaptPreferences)
            from Op import OpSurfacage
            reload(OpSurfacage)
            import BaptPostProcess
            reload(BaptPostProcess)
            from Probe import probeFace
            reload(probeFace)
            import Op.Gui.DrillOpTaskPanel as DrillOpTaskPanel
            reload(DrillOpTaskPanel)
            import utils.BQuantitySpinBox as BQuantitySpinBox
            reload(BQuantitySpinBox)

            import BaptHoleRecognition
            reload(BaptHoleRecognition)
            import Gui.HoleRecognitionTaskPanel as HoleRecognitionTaskPanel
            reload(HoleRecognitionTaskPanel)
            import Op.PocketOp as PocketOp
            reload(PocketOp)
            import Op.OpContournageTest as OpContournageTest
            reload(OpContournageTest)
            import Op.ChamferOp as ChamferOp
            reload(ChamferOp)
            import Op.Gui.ChamferTaskPanel as ChamferTaskPanel
            reload(ChamferTaskPanel)

            import Op.SpiraleOp as SpiraleOp
            reload(SpiraleOp)
            import Op
            reload(Op)
            # dossier = BaptUtilities.get_module_path()

            # modules = [
            #     f[:-3] for f in os.listdir(dossier)
            #     if f.endswith(".py") and f != "__init__.py"
            # ]

            # print(modules)
            # for module_name in modules:
            #     reload(__import__(module_name))
            # Message de confirmation
            App.Console.PrintMessage("hot Reload avec Succes!\n")

        except Exception as e:
            App.Console.PrintError(f"Erreur lors du rechargement des modules: {str(e)}\n")
            pass

        # Recomputer
        App.ActiveDocument.recompute()


class testFPOCommand:
    def GetResources(self):
        return {
            'Pixmap': BaptUtilities.getIconPath("Tree_HoleRecognition.svg"),
            'MenuText': "test FPO",
            'ToolTip': "Détecter automatiquement les trous cylindriques perpendiculaires au plan de travail"
        }

    def IsActive(self):
        """La commande est active si un document est ouvert"""
        doc = App.ActiveDocument
        if doc is None:
            return False

        return True

    def Activated(self):
        """Créer un nouvel objet de reconnaissance de trous"""

        doc = App.ActiveDocument

        doc.openTransaction('testFPO')
        testFPO.create()

        doc.commitTransaction()


# Enregistrer les commandes
if App.GuiUp:
    Gui.addCommand('Bapt_CreateOrigin', CreateOriginCommand())
    Gui.addCommand('Bapt_CreateCamProject', CreateCamProjectCommand())
    Gui.addCommand('Bapt_CreateDrillGeometry', CreateDrillGeometryCommand())
    Gui.addCommand('Bapt_CreateContourGeometry', CreateContourGeometryCommand())
    Gui.addCommand('Bapt_CreateContourEditableGeometry', CreateContourEditableGeometryCommand())
    Gui.addCommand('Bapt_CreateContour25DGeometry', CreateContour25DGeometryCommand())
    Gui.addCommand('Bapt_CreateMachiningCycle', CreateContourCommand())
    Gui.addCommand('Bapt_CreateChamferOperation', CreateChamferOperationCommand())
    Gui.addCommand('Bapt_CreatePocketOperation', CreatePocketOperationCommand())
    Gui.addCommand('Bapt_CreateHotReload', CreateHotReloadCommand())
    Gui.addCommand('Bapt_ToolsManager', ToolsManagerCommand())
    Gui.addCommand('Bapt_CreateDrillOperation', CreateDrillOperationCommand())  # Ajouter la nouvelle commande
    Gui.addCommand('Bapt_CreateSpiraleOp', CreateSpiraleOpCommand())  # Ajouter la nouvelle commande
    Gui.addCommand('ImportMpf', BaptMpfReader.ImportMpfCommand())  # Ajouter la commande d'importation MPF
    Gui.addCommand('Bapt_PostProcessGCode', PostProcessGCodeCommand())
    Gui.addCommand('Bapt_CreateSurfacage', CreateSurfacageCommand())
    Gui.addCommand('Bapt_CreateProbeFace', ProbeFaceCommand())
    Gui.addCommand('Bapt_CreateProbeReference', ProbeReferenceCommand())
    Gui.addCommand('Bapt_TestPath', CreatePathCommand())
    Gui.addCommand('Bapt_HighlightCollisions', CreateHighlightCommand())
    Gui.addCommand('Bapt_HoleRecognition', HoleRecognitionCommand())
    Gui.addCommand('Bapt_CreateAdaptativeOperation', CreateAdaptativeOperationCommand())
    Gui.addCommand('Bapt_createTestFPO', testFPOCommand())
    Gui.addCommand('Bapt_RapportProgrammation', rapportProgrammationCommand())
    Gui.addCommand('Bapt_CreateContournageTest', CreateContourTestCommand())
    Gui.addCommand('Bapt_CreateArrayOp', CreateArrayOpCommand())
