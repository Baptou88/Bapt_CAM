import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
import Part 
from utils import PointSelectionObserver
import math
import os

class Surfacage:
    def __init__(self, obj):
        self.Type = "Surfacage"
        self.initProperties(obj)
        obj.Proxy = self
    
    def initProperties(self, obj):
        obj.addProperty("App::PropertyString", "Name", "Surfacage", "Nom de l'opérateur").Name = "Surfacage"
        obj.addProperty("App::PropertyLink", "Stock", "Surfacage", "Stock")
        obj.addProperty("App::PropertyFloat", "Depth", "Surfacage", "Profondeur finale")
        obj.addProperty("App::PropertyFloat", "ToolDiameter", "Surfacage", "Diamètre de la tool").ToolDiameter = 12.0
        obj.addProperty("App::PropertyFloat", "Recouvrement", "Surfacage", "Recouvrement").Recouvrement = 10.0
        
    def execute(self, obj):
        if not hasattr(obj,"ToolDiameter"):
            return
        obj.Shape = Part.Shape()
        if not obj.Stock:
            App.Console.PrintMessage("Aucun stock sélectionné\n")
            return
        App.Console.PrintMessage(f"Stock sélectionné : {obj.Stock.Name}\n")
        bb = obj.Stock.Shape.BoundBox
        App.Console.PrintMessage(f"Taille du stock : {bb.XLength}, {bb.YLength}, {bb.ZLength}\n")
        wires = []
        points = []
        nbPasseLat = (bb.YLength / obj.Recouvrement) // 1 + 1
        passeLat = bb.YLength / nbPasseLat
        App.Console.PrintMessage(f'Nombre de passes latérales : {nbPasseLat}\n')
        App.Console.PrintMessage(f' passe latérale : {passeLat}\n')
        posX = bb.XMin - obj.ToolDiameter / 2
        posY = bb.YMin + (obj.ToolDiameter / 2) - passeLat
        posZ = obj.Depth
        
        points.append(App.Vector(posX, posY, posZ + 2 ))
        points.append(App.Vector(posX, posY, posZ))
        for i in range(int(nbPasseLat)):
            if i % 2 != 0:
                points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ))
                
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:
                    points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ + 2 ))
                else:
                    posY += passeLat
                    points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ))
            else:
                points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ))
                
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:
                    points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ + 2 ))
                else:
                    posY += passeLat
                    points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ))
        
        #points.append(App.Vector(posX, posY, posZ +2))
        
        polyline = Part.makePolygon(points)
        wires.append(polyline)
        

        obj.Shape = Part.makeCompound(wires)

    def onChanged(self, obj, prop):
        if prop in ("Stock", "Depth", "ToolDiameter", "Recouvrement"):
            self.execute(obj)

class ViewProviderSurfacage:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Surfacage.svg")

        return ":/icons/surfacage.svg"

    def attach(self,vobj):
        pass

    def setupContextMenu(self, vobj, menu):
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
    
    def setEdit(self, vobj, mode=0):
        try:
            import importlib
            importlib.reload(SurfacageTaskPanel)
        except Exception:
            pass
        Gui.Control.showDialog(SurfacageTaskPanel(vobj.Object))
    
    def doubleClicked(self, vobj):
        self.setEdit(vobj)
        return True
    
    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class SurfacageTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Édition de l'opérateur")
        layout = QtGui.QFormLayout(self.form)
        # Nom
        self.nameEdit = QtGui.QLineEdit(obj.Name)
        layout.addRow("Nom", self.nameEdit)
        # Tool
        self.toolDiameterEdit = QtGui.QDoubleSpinBox(); self.toolDiameterEdit.setRange(0,1000); self.toolDiameterEdit.setValue(obj.ToolDiameter)
        layout.addRow("Diamètre de l'outil", self.toolDiameterEdit)
        # Recouvrement
        self.recouvrement = QtGui.QDoubleSpinBox(); self.recouvrement.setRange(0,1000); self.recouvrement.setValue(obj.Recouvrement)
        layout.addRow("Recouvrement", self.recouvrement)
        # Profondeur finale
        self.depthEdit = QtGui.QDoubleSpinBox(); self.depthEdit.setRange(-10000,10000); self.depthEdit.setValue(obj.Depth)
        layout.addRow("Profondeur finale", self.depthEdit)
        self.depthBtn = QtGui.QPushButton("Click on Part")
        self.depthBtn.clicked.connect(self.setDepth)
        layout.addRow(self.depthBtn)
        # Boutons
        btnLayout = QtGui.QHBoxLayout()
        self.okBtn = QtGui.QPushButton("OK"); self.cancelBtn = QtGui.QPushButton("Annuler")
        btnLayout.addWidget(self.okBtn); btnLayout.addWidget(self.cancelBtn)
        layout.addRow(btnLayout)
        self.okBtn.clicked.connect(self.accept)
        self.cancelBtn.clicked.connect(self.reject)

    def setDepth(self):
        self.depthBtn.setEnabled(False)
        self.observer = PointSelectionObserver.PointSelectionObserver(self.pointSelected)
        self.observer.enable()
        #sel = Gui.Selection.getSelection()
        # if not sel:
        #     return
        # self.obj.Depth = sel[0].Proxy.getDepth(sel[0])
    def pointSelected(self, point):
        self.depthEdit.setValue(point.z)
        self.depthBtn.setEnabled(True)
        self.updateVisual()

    def updateVisual(self):
        self.obj.Depth = self.depthEdit.value()
        self.obj.ToolDiameter = self.toolDiameterEdit.value()
        self.obj.Recouvrement = self.recouvrement.value()

    def accept(self):
        self.obj.Name = self.nameEdit.text()
        App.ActiveDocument.recompute()
        Gui.Control.closeDialog()
    def reject(self):
        Gui.Control.closeDialog()
