import re

import FreeCAD as App
import FreeCADGui as Gui
from Op.Gui.ArrayOpTaskPanel import ArrayOpTaskPanel
from PySide import QtGui, QtCore

import BaptUtilities
from Op.BaseOp import baseOp, baseOpViewProviderProxy

__doc__ = "Array operation for FreeCAD"


class ArrayOp(baseOp):
    def __init__(self, obj):
        super().__init__(obj)

        if not hasattr(obj, "baseOp"):
            obj.addProperty(
                "App::PropertyLink",
                "baseOp",
                "Base",
                "Base object for the array operation"
            )  # TODO: "App::PropertyLinkList"

        if not hasattr(obj, "Pattern"):
            obj.addProperty(
                "App::PropertyEnumeration",
                "Pattern",
                "Base",
                "Pattern objects for the array operation"
            ).Pattern = ("Linear1D", "Linear2D", "Polar")
            obj.Pattern = "Linear1D"

        if not hasattr(obj, "CopiesX"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "CopiesX",
                "Base",
                "Number of copies for the array operation"
            ).CopiesX = (1, 0, 9999, 1)  # (default, min, max, step)

        if not hasattr(obj, "CopiesY"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "CopiesY",
                "Base",
                "Number of copies for the array operation"
            ).CopiesY = (1, 0, 9999, 1)  # (default, min, max, step)

        if not hasattr(obj, "SpacingX"):
            obj.addProperty(
                "App::PropertyVectorDistance",
                "SpacingX",
                "Base",
                "Spacing X between copies for the array operation"
            )
        if not hasattr(obj, "SpacingY"):
            obj.addProperty(
                "App::PropertyVectorDistance",
                "SpacingY",
                "Base",
                "Spacing Y between copies for the array operation"
            )

        if not hasattr(obj, "angle"):
            obj.addProperty(
                "App::PropertyAngle",
                "angle",
                "Base",
                "Rotation angle for the array operation"
            )
        if not hasattr(self, "omitt"):
            self.omitt = []

        super().installToolProp(obj)
        self.updateVisibleProperties(obj)
        obj.Proxy = self

    def updateVisibleProperties(self, obj):
        if obj.Pattern == "Polar":
            obj.setEditorMode("angle", 0)  # 0 = visible
        else:
            obj.setEditorMode("angle", 2)  # 2 = hidden

        if obj.Pattern == "Linear2D":
            obj.setEditorMode("CopiesY", 0)  # 0 = visible
            obj.setEditorMode("SpacingY", 0)  # 0 = visible
        else:
            obj.setEditorMode("CopiesY", 2)  # 2 = hidden
            obj.setEditorMode("SpacingY", 2)  # 2 = hidden

    def onChanged(self, obj, prop):
        # super().onChanged(obj, prop)
        if prop == "Pattern":
            self.updateVisibleProperties(obj)
        if prop == "baseOp":
            obj.Tool = obj.baseOp.Tool
            App.Console.PrintMessage(f"{obj.Name}: Base operation changed\n")
        if prop in ["baseOp", "CopiesX", "CopiesY", "SpacingX", "SpacingY", "Pattern", "angle"]:
            self.execute(obj)

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return
        super().execute(obj)

        if hasattr(obj, "baseOp") and obj.baseOp is None:
            return

        if obj.Pattern == "Linear1D":
            self.generate_linear1D(obj)
        elif obj.Pattern == "Linear2D":
            self.generate_linear2D(obj)
        elif obj.Pattern == "Polar":
            App.Console.PrintWarning(f"{obj.Name}: Generating polar array not fully implemented\n")
            self.generate_polar(obj)
        else:
            raise NotImplementedError(f"{obj.Name} Pattern '{obj.Pattern}' not implemented")

    def dumps(self):

        return [getattr(self, "omitt", [])]

    def loads(self, state):
        App.Console.PrintMessage(f"Loading state: {state}\n")
        App.Console.PrintMessage(f"Loading state: {state[0]}\n")
        self.omitt = [(p[0], p[1]) for p in state[0]]
        App.Console.PrintMessage(f"Loaded omitt: {self.omitt}\n")

    def generate_linear1D(self, obj):
        if not hasattr(obj, "CopiesX") or not hasattr(obj, "SpacingX"):
            return
        copies = obj.CopiesX
        spacingX = obj.SpacingX
        gcode_source = obj.baseOp.Gcode
        gcode_transformed = ""
        distanceMode = "Absolute"
        for i in range(0, copies + 1):
            if i == 0:
                continue
            if (i,) in self.omitt:
                continue
            gcode_transformed += f"; Copy {i}\n"
            for line in gcode_source.splitlines():
                if 'G90' in line:
                    distanceMode = "Absolute"
                if 'G91' in line:
                    distanceMode = "Relative"
                if line.startswith(("G0", "G1", "G2", "G3")):
                    # Apply spacing offset for linear 1D array
                    # regex to match XYZIJK coordinate
                    if distanceMode == "Relative":
                        continue
                    import re
                    pattern = r"([XYZ])([-+]?\d*\.?\d+)"
                    matches = re.findall(pattern, line)
                    new_line = line
                    for axis, value in matches:
                        if axis == "X":
                            new_value = float(value) + spacingX.x * i
                        elif axis == "Y":
                            new_value = float(value) + spacingX.y * i
                        elif axis == "Z":
                            new_value = float(value) + spacingX.z * i
                        else:
                            new_value = float(value)
                        new_line = new_line.replace(f"{axis}{value}", f"{axis}{new_value}")
                    gcode_transformed += new_line + "\n"

                else:
                    gcode_transformed += line + "\n"
        obj.Gcode = gcode_transformed

    def generate_linear2D(self, obj):
        if not hasattr(obj, "CopiesX") or not hasattr(obj, "CopiesY") or not hasattr(obj, "SpacingX") or not hasattr(obj, "SpacingY"):
            return
        copiesX = obj.CopiesX
        copiesY = obj.CopiesY
        spacingX = obj.SpacingX
        spacingY = obj.SpacingY
        gcode_source = obj.baseOp.Gcode
        gcode_transformed = ""
        distanceMode = "Absolute"

        for i in range(0, copiesX + 1):
            for j in range(0, copiesY + 1):
                if i == 0 and j == 0:
                    continue
                if (i, j) in self.omitt:
                    continue
                gcode_transformed += f"; Copy {i},{j}\n"
                for line in gcode_source.splitlines():
                    if 'G90' in line:
                        distanceMode = "Absolute"
                    if 'G91' in line:
                        distanceMode = "Relative"
                    if line.startswith(("G0", "G1", "G2", "G3")):
                        if distanceMode == "Relative":
                            continue
                        # Apply spacing offset for linear 1D array
                        # regex to match XYZIJK coordinate
                        import re
                        pattern = r"([XYZ])([-+]?\d*\.?\d+)"
                        matches = re.findall(pattern, line)
                        new_line = line
                        for axis, value in matches:
                            if axis == "X":
                                new_value = float(value) + spacingX.x * i + spacingY.x * j
                            elif axis == "Y":
                                new_value = float(value) + spacingX.y * i + spacingY.y * j
                            elif axis == "Z":
                                new_value = float(value) + spacingX.z * i + spacingY.z * j
                            else:
                                new_value = float(value)
                            new_line = new_line.replace(f"{axis}{value}", f"{axis}{new_value}")
                        gcode_transformed += new_line + "\n"

                    else:
                        gcode_transformed += line + "\n"
        obj.Gcode = gcode_transformed

    def generate_polar(self, obj):
        angle = obj.angle
        axis = obj.SpacingX  # Assuming the rotation axis is defined by SpacingX for now
        import math

        def get_quaternion(axis, angle):
            import math
            half_angle = math.radians(angle) / 2
            sin_half_angle = math.sin(half_angle)
            return (
                axis.x * sin_half_angle,
                axis.y * sin_half_angle,
                axis.z * sin_half_angle,
                math.cos(half_angle)
            )
        quaternion = get_quaternion({'x': 0, 'y': 0, 'z': 1}, angle)
        rot = App.Rotation(quaternion[0], quaternion[1], quaternion[2], quaternion[3])
        centreRot = axis
        placement = App.Placement(App.Vector(0, 0, 0), rot, centreRot)
        gcode_transformed = ""
        current_position = {"X": None, "Y": None, "Z": None}
        gcode_source = obj.baseOp.Gcode
        for i in range(0, obj.CopiesX + 1):
            if i == 0:
                continue
            if (i, ) in self.omitt:
                continue
            gcode_transformed += f"; Copy {i},0\n"
            for line in gcode_source.splitlines():
                if line.startswith(("G0", "G1", "G2", "G3")):
                    # Apply polar transformation
                    pattern = r"([XYZIJK])([-+]?\d*\.?\d+)"
                    matches = re.findall(pattern, line)
                    new_line = line
                    for axis_char, value in matches:
                        if axis_char == "X":
                            new_value = (float(value) - axis.x) * math.cos(math.radians(angle * i))
                        elif axis_char == "Y":
                            new_value = (float(value) - axis.y) * math.sin(math.radians(angle * i))
                        elif axis_char == "I":
                            new_value = float(value) * math.cos(math.radians(angle * i))
                        elif axis_char == "J":
                            new_value = float(value) * math.sin(math.radians(angle * i))
                        else:
                            # TODO: Handle other axis characters if needed
                            new_value = float(value)
                        new_line = new_line.replace(f"{axis_char}{value}", f"{axis_char}{new_value}")
                    gcode_transformed += new_line + "\n"
                else:
                    gcode_transformed += line + "\n"
        obj.Gcode = gcode_transformed

    def onDocumentRestored(self, obj):
        self.__init__(obj)
        # return super().onDocumentRestored(obj)


class ViewProviderArrayOp(baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object
        self.panel = None

    def attach(self, vobj):
        self.Object = vobj.Object
        self.panel = None
        return super().attach(vobj)

    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Tree_ArrayOp.svg")

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)
        viewGcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "View G-code", menu)
        QtCore.QObject.connect(viewGcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(viewGcode)
        return True

    def onChanged(self, vp, prop):
        super().onChanged(vp, prop)

    def updateData(self, fp_object, prop):
        super().updateData(fp_object, prop)
        if self.panel:
            self.panel.updateData(fp_object, prop)

    def closeTaskPanel(self):
        App.Console.PrintMessage("Closing task panel\n")
        if self.panel:
            self.panel = None

    def setEdit(self, vobj, mode=0):
        if mode == 0:
            self.panel = ArrayOpTaskPanel(vobj.Object)
            Gui.Control.showDialog(self.panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        App.Console.PrintMessage("Unsetting edit mode\n")
        if self.panel:
            Gui.Control.closeDialog()
            self.panel = None
        return True

    def __setstate__(self, state):
        return None

    def __getstate__(self):
        return None


class CreateArrayOpCommand:

    def GetResources(self):
        return {
            'Pixmap': BaptUtilities.getIconPath("Tree_ArrayOp.svg"),
            'MenuText': "Créer une opération de Reseau",
            'ToolTip': "Créer une opération de Reseau"
        }

    def IsActive(self):
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        doc = App.ActiveDocument
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return
        doc.openTransaction('Create Array Operation')

        obj = doc.addObject("App::FeaturePython", "ArrayOp")

        ArrayOp(obj)

        operations_group = project.Proxy.getOperationsGroup(project)
        operations_group.addObject(obj)

        if App.GuiUp:

            ViewProviderArrayOp(obj.ViewObject)
            sel = Gui.Selection.getSelection()
            if sel and hasattr(sel[0], "Proxy") and isinstance(sel[0].Proxy, baseOp):
                obj.baseOp = sel[0]
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)
        doc.commitTransaction()

        doc.recompute()
