from Gui import cuttingConditionTaskPanel as cc
from Op.BaseOp import baseOpViewProviderProxy
import FreeCAD as App
import FreeCADGui as Gui
from Op.BaseOp import baseOp
from PySide import QtGui, QtCore
from Tool.ToolTaskPannel import ToolTaskPanel
import BaptUtilities


from utils import Log, PointSelectionObserver
from utils import BQuantitySpinBox
import math

from utils.GcodeWriter import GcodeWriter


class Surfacage(baseOp):
    def __init__(self, obj, cam_proj=None):
        self.Type = "Surfacage"
        super().__init__(obj, cam_proj)

        self.initProperties(obj)
        self.installToolProp(obj)

        obj.Proxy = self

    def initProperties(self, obj):

        if not hasattr(obj, "Stock"):
            obj.addProperty("App::PropertyLink", "Stock", "Surfacage", "Stock")

        super().installToolProp(obj)

        if not hasattr(obj, "Depth"):
            obj.addProperty("App::PropertyFloat", "Depth", "Surfacage", "Profondeur finale")
        if not hasattr(obj, "safeZ"):
            obj.addProperty("App::PropertyFloat", "safeZ", "Surfacage", "Hauteur de sécurité pour les déplacements rapides")
            obj.safeZ = 2.0

        if not hasattr(obj, "Recouvrement"):
            obj.addProperty("App::PropertyFloat", "Recouvrement", "Surfacage", "Recouvrement").Recouvrement = 10.0

        # cherche l'objet Model dans le document actif

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return
        super().execute(obj)  # Appelle la logique de base (vérifications, etc.)

        if not hasattr(obj, "Tool") or obj.Tool is None:
            return
        if not obj.Stock:
            App.Console.PrintMessage("Aucun stock sélectionné\n")
            return

        gcodeWriter = GcodeWriter()

        App.Console.PrintMessage(f"Stock sélectionné : {obj.Stock.Name}\n")
        bb = obj.Stock.Shape.BoundBox
        App.Console.PrintMessage(f"Taille du stock : {bb.XLength}, {bb.YLength}, {bb.ZLength}\n")

        nbPasseLat = math.ceil(bb.YLength / obj.Recouvrement) + 1
        passeLat = bb.YLength / nbPasseLat
        App.Console.PrintMessage(f'Nombre de passes latérales : {nbPasseLat}\n')
        App.Console.PrintMessage(f' passe latérale : {passeLat}\n')

        posX = bb.XMin - obj.Tool.Radius.Value
        posY = bb.YMin - (obj.Tool.Radius.Value) + passeLat
        posZ = obj.Depth

        gcodeWriter.linearMove({'X': posX, 'Y': posY}, rapid=True)
        gcodeWriter.linearMove({'Z': posZ + obj.safeZ}, rapid=True)
        gcodeWriter.linearMove({'Z': posZ}, feed=float(obj.FeedRate.getValueAs('mm/min')))

        for i in range(int(nbPasseLat)):
            if i % 2 != 0:
                gcodeWriter.linearMove({'X': bb.XMin - (obj.Tool.Radius.Value), 'Y': posY})
                # points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:

                    gcodeWriter.linearMove({'X': bb.XMin - (obj.Tool.Radius.Value), 'Y': posY, 'Z': posZ + obj.safeZ})
                else:
                    posY += passeLat

                    gcodeWriter.linearMove({'X': bb.XMin - (obj.Tool.Radius.Value), 'Y': posY})
            else:

                gcodeWriter.linearMove({'X': bb.XMax + (obj.Tool.Radius.Value), 'Y': posY})
                # points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:

                    gcodeWriter.linearMove({'X': bb.XMax + (obj.Tool.Radius.Value), 'Y': posY, 'Z': posZ + obj.safeZ})

                else:
                    posY += passeLat

                    gcodeWriter.linearMove({'X': bb.XMax + (obj.Tool.Radius.Value), 'Y': posY})

        obj.Gcode = "\n".join(gcodeWriter.lines)
        obj.TimeEstimate = gcodeWriter.time_estimate
        obj.LastCoordinate = App.Vector(gcodeWriter.current_position['X'], gcodeWriter.current_position['Y'], gcodeWriter.current_position['Z'])

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        super().onDocumentRestored(obj)
        self.__init__(obj)

    def onChanged(self, obj, prop):
        # super().onChanged(obj, prop)
        if prop in ("Stock", "Depth", "Tool", "Recouvrement", "FeedRate", "safeZ"):
            self.execute(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderSurfacage(baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object
        self.icon = "Surfacage.svg"
        self.panel = None

    def attach(self, obj):
        self.Object = obj.Object
        self.panel = None
        return super().attach(obj)

    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Surfacage.svg")

        # return ":/icons/surfacage.svg"

    # def attach(self,vobj):
    #     #self.updateColors()
    #     #self.root = self.buildScene(vobj)
    #     vobj.addDisplayMode(self.root, "Lines")
    #     pass

    # def buildScene(self,vobj):
    #     App.Console.PrintMessage(f"Build scene\n")
    #     root = coin.SoGroup()
    #     for i in range(10):
    #         # line = coin.SoLineSet()
    #         # line.numVertices.setValue(2)
    #         # line.vertexProperty.setValue(coin.SoVertexProperty())
    #         # line.vertexProperty.vertex.setValues([
    #         #     [i, 0, 0],
    #         #     [i+1, 0, 0]])
    #         # line.vertexProperty.vertex.setBinding(coin.SoVertexProperty.PER_FACE)
    #         # line.vertexProperty.vertex.setNumValues(2)
    #         # line.materialBinding.setValue(coin.SoMaterialBinding.PER_PART)
    #         # material = coin.SoMaterial()
    #         # material.diffuseColor.setValue([i/10.0, 1-(i/10.0), 0.0])
    #         # root.addChild(material)
    #         # root.addChild(line)
    #         line = coin.SoSeparator()
    #         line_color = coin.SoBaseColor()
    #         line_color.rgb = (i/10.0, 1-(i/10.0), 0.0)
    #         line.addChild(line_color)
    #         line_coords = coin.SoCoordinate3()
    #         line_coords.point.setValues(0,2,[
    #             App.Vector(i *10, 5, 0),
    #             App.Vector((i+1) *10, 5, 0)])
    #         line.addChild(line_coords)
    #         line.addChild(coin.SoLineSet())
    #         root.addChild(line)
    #     # App.Console.PrintMessage(f"Move : {len(vobj.Object.move)}\n")
    #     #for i in range(len(vobj.Object.move)):
    #         # line = coin.SoSeparator()
    #         # line_color = coin.SoBaseColor()
    #         # if vobj.Object.move[i]["Type"] == "Rapid":
    #         #     line_color.rgb = (1.0, 0.0, 0.0)
    #         # else:
    #         #     line_color.rgb = (0.0, 1.0, 0.0)
    #         # line.addChild(line_color)
    #         # line_coords = coin.SoCoordinate3()
    #         # line_coords.point.setValues(0,2,[
    #         #     vobj.Object.move[i]["from"],
    #         #     vobj.Object.move[i]["to"]])
    #         # line.addChild(line_coords)
    #         # line.addChild(coin.SoLineSet())
    #         # root.addChild(line)

    #     return root

    # def getHighlightSegments(self, vobj, sub):
    #     # sub est une liste de sous-éléments survolés (ex : ["Edge1"])
    #     if not sub or not self.root:
    #         return
    #     App.Console.PrintMessage(f"Get highlight segments\n")

    def updateData(self, obj, prop):
        super().updateData(obj, prop)
        if self.panel is not None:
            self.panel.updateData(obj, prop)
        if prop in ("Depth", "Rapid", "Feed", "Recouvrement", "safeZ", "Label"):
            # self.updateVisual()
            pass

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)
        action_edit_gcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "edit Gcode", menu)
        QtCore.QObject.connect(action_edit_gcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(action_edit_gcode)

    def setEdit(self, vobj, mode=0):
        try:
            import importlib
            importlib.reload(SurfacageTaskPanel)
        except Exception:
            pass
        self.panel = SurfacageTaskPanel(vobj.Object, deleteOnReject=False)
        Gui.Control.showDialog(self.panel)

    # def doubleClicked(self, vobj):
    #     self.setEdit(vobj)
    #     return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def unsetEdit(self, vobj, mode=0):
        Log.baptDebug("unsetEdit called")
        if self.panel is not None:
            # self.panel.reject(resetEdit=True)
            self.panel = None

    # def getDisplayModes(self, vobj):
    #     return ["Lines"]
    # def getDefaultDisplayMode(self):
    #     return "Lines"
    # def setDisplayMode(self, vobj, mode=None):
    #     return self.getDefaultDisplayMode() if mode is None else mode

    def dumps(self):
        '''When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here -- the Coin stuff -- we must define this method\
                to return a tuple of all serializable objects or None.'''
        return None

    def loads(self, state):
        '''When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here.'''
        return None


class SurfacageTaskPanel:
    def __init__(self, obj, deleteOnReject):
        self.obj = obj
        self.deleteOnReject = deleteOnReject
        App.activeDocument().openTransaction("Edit Surfacage Operation")
        self.cuttingCondition = cc.cuttingConditionTaskPanel(obj)

        self.ui1 = QtGui.QWidget()
        ui2 = ToolTaskPanel(obj)
        self.form = [self.ui1, ui2.getForm(), self.cuttingCondition.getForm()]
        self.ui1.setWindowTitle("Édition de l'opérateur")
        self.ui1.setWindowIcon(QtGui.QIcon(BaptUtilities.getIconPath("Surfacage.svg")))

        layout = QtGui.QFormLayout(self.ui1)
        # Nom
        self.labelEdit = QtGui.QLineEdit(obj.Label)
        layout.addRow("Label", self.labelEdit)

        # Recouvrement
        self.recouvrement = BQuantitySpinBox.BQuantitySpinBox(obj, "Recouvrement")

        layout.addRow("Recouvrement", self.recouvrement.getWidget())

        # Profondeur finale
        self.depthEdit = BQuantitySpinBox.BQuantitySpinBox(obj, "Depth")
        layout.addRow("Profondeur finale", self.depthEdit.getWidget())
        self.depthBtn = QtGui.QPushButton("Click on Part")
        self.depthBtn.clicked.connect(self.setDepth)
        layout.addRow(self.depthBtn)

        if self.obj.Tool:
            self.obj.Tool.Visibility = True

    def updateData(self, obj, prop):
        if prop in ("Depth", "Recouvrement", "Label", "safeZ"):
            self.setFields()
        pass

    def updateValue(self):
        # self.obj.Depth = self.depthEdit.value()
        # self.obj.Depth = self.depthEdit.property('rawValue')
        # self.obj.Recouvrement = self.recouvrement.value()
        return

    def getFields(self):
        self.recouvrement.updateProperty()

    def setFields(self):
        self.labelEdit.setText(self.obj.Label)
        self.depthEdit.updateWidget()
        self.recouvrement.updateWidget()

    def setDepth(self):
        self.depthBtn.setEnabled(False)
        self.observer = PointSelectionObserver.PointSelectionObserver(self.pointSelected)
        self.observer.enable()
        # sel = Gui.Selection.getSelection()
        # if not sel:
        #     return
        # self.obj.Depth = sel[0].Proxy.getDepth(sel[0])

    def pointSelected(self, point):
        self.depthEdit.setValue(point.z)
        self.depthBtn.setEnabled(True)
        self.updateVisual()

    def updateVisual(self):
        self.obj.Depth = self.depthEdit.value()
        self.obj.Recouvrement = self.recouvrement.value()

    def accept(self):
        self.obj.ViewObject.Proxy.unsetEdit(self.obj.ViewObject)
        self.obj.Label = self.labelEdit.text()
        self.updateValue()
        if self.obj.Tool:
            self.obj.Tool.Visibility = False

        App.activeDocument().commitTransaction()
        App.ActiveDocument.recompute()
        Gui.Control.closeDialog()

    def reject(self, resetEdit=False):
        self.obj.ViewObject.Proxy.unsetEdit(self.obj.ViewObject)
        if self.obj.Tool:
            self.obj.Tool.Visibility = False
        App.activeDocument().abortTransaction()

        if self.deleteOnReject:
            App.ActiveDocument.removeObject(self.obj.Name)
        Gui.Control.closeDialog()
