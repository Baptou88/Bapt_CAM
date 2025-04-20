# -*- coding: utf-8 -*-

"""
InitGui.py for Bapt Workbench
This file is executed when FreeCAD starts up and loads your workbench
"""

import FreeCAD as App
import FreeCADGui as Gui
from FreeCADGui import Workbench
import os

class BaptWorkbench (Workbench):
    def __init__(self):
        self.__class__.MenuText = "Bapt"
        self.__class__.ToolTip = "Bapt Workbench"
        self.__class__.Icon = os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "BaptWorkbench.svg")

    def Initialize(self):
        """This function is executed when the workbench is first activated.
        It is executed once in a FreeCAD session."""
        import BaptCommands
        import BaptTools
        self.list = ["Bapt_CreateCamProject", "Bapt_Command", "Bapt_CreateDrillGeometry", "Bapt_CreateDrillOperation", "Bapt_ToolsManager", "Bapt_CreateContourGeometry", "Bapt_CreateMachiningCycle", "Bapt_CreateHotReload", "ImportMpf"]  # Ajout de la commande d'opération de perçage
        self.appendToolbar("Bapt Tools", self.list)
        self.appendMenu("Bapt", self.list)

    def Activated(self):
        """This function is executed whenever the workbench is activated"""
        return

    def Deactivated(self):
        """This function is executed whenever the workbench is deactivated"""
        return

    def GetClassName(self):
        """This function is mandatory if this is a full Python workbench"""
        return "Gui::PythonWorkbench"

Gui.addWorkbench(BaptWorkbench())

# Register preferences
from BaptPreferences import BaptPreferencesPage
Gui.addPreferencePage(BaptPreferencesPage, "Bapt")