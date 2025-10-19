import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
from pivy import coin
import Part 
import BaptUtilities
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
        #obj.addProperty("App::PropertyPythonObject", "Rapid", "Surfacage", "Movements rapide")
        #obj.addProperty("App::PropertyPythonObject", "Feed", "Surfacage", "Movements feed")
        obj.addProperty("App::PropertyPythonObject", "move", "Surfacage", "Movements")

    def execute(self, obj):
        if not hasattr(obj,"ToolDiameter"):
            return
        #obj.Shape = Part.Shape()
        if not obj.Stock:
            App.Console.PrintMessage("Aucun stock sélectionné\n")
            return
        App.Console.PrintMessage(f"Stock sélectionné : {obj.Stock.Name}\n")
        bb = obj.Stock.Shape.BoundBox
        App.Console.PrintMessage(f"Taille du stock : {bb.XLength}, {bb.YLength}, {bb.ZLength}\n")
        wires = []
        points = []

        Rapid = []
        Feed = []
        obj.move = []
        nbPasseLat = (bb.YLength / obj.Recouvrement) // 1 + 1
        passeLat = bb.YLength / nbPasseLat
        App.Console.PrintMessage(f'Nombre de passes latérales : {nbPasseLat}\n')
        App.Console.PrintMessage(f' passe latérale : {passeLat}\n')
        posX = bb.XMin - obj.ToolDiameter / 2
        posY = bb.YMin - (obj.ToolDiameter / 2) + passeLat
        posZ = obj.Depth
        
        points.append(App.Vector(posX, posY, posZ + 2 ))
        points.append(App.Vector(posX, posY, posZ))
        Rapid.append(Part.makeLine(points[0], points[1]))
        obj.move.append({"Type": "Rapid", "from": points[0], "to": points[1]})
        for i in range(int(nbPasseLat)):
            if i % 2 != 0:
                points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ))
                Feed.append(Part.makeLine(points[-2], points[-1]))
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:
                    points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ + 2 ))
                    Rapid.append(Part.makeLine(points[-2], points[-1]))
                    obj.move.append({"Type": "Rapid", "from": points[-2], "to": points[-1]})
                else:
                    posY += passeLat
                    points.append(App.Vector(bb.XMin - (obj.ToolDiameter / 2), posY, posZ))
                    Feed.append(Part.makeLine(points[-2], points[-1]))
                    obj.move.append({"Type": "Feed", "from": points[-2], "to": points[-1]})
            else:
                points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ))
                Feed.append(Part.makeLine(points[-2], points[-1]))
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:
                    points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ + 2 ))
                    Rapid.append(Part.makeLine(points[-2], points[-1]))
                    obj.move.append({"Type": "Rapid", "from": points[-2], "to": points[-1]})
                else:
                    posY += passeLat
                    points.append(App.Vector(bb.XMax + (obj.ToolDiameter / 2), posY, posZ))
                    Feed.append(Part.makeLine(points[-2], points[-1]))
                    obj.move.append({"Type": "Feed", "from": points[-2], "to": points[-1]})
        
        #debug
        App.Console.PrintMessage(f"Rapid : {len(Rapid)}\n")
        App.Console.PrintMessage(f"Feed : {len(Feed)}\n")
        App.Console.PrintMessage(f"Points : {len(points)}\n")
        #points.append(App.Vector(posX, posY, posZ +2))
        # if not hasattr(obj, "Rapid"):
        #     obj.addProperty("App::PropertyPythonObject", "Rapid", "Surfacage", "Movements rapide")
        # if not hasattr(obj, "Feed"):
        #     obj.addProperty("App::PropertyPythonObject", "Feed", "Surfacage", "Movements feed")
        # obj.Rapid = Rapid
        # obj.Feed = Feed

        allMovements = Rapid + Feed
        App.Console.PrintMessage(f"AllMovements : {len(allMovements)}\n")
#        polyline = Part.makePolygon(allMovements)
#        wires.append(polyline)
        

        obj.Shape = Part.makeCompound(allMovements)

    def onChanged(self, obj, prop):
        if prop in ("Stock", "Depth", "ToolDiameter", "Recouvrement"):
            self.execute(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

class ViewProviderSurfacage:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object

        vobj.addProperty("App::PropertyColor", "Rapid", "Display", "Color of the path").Rapid = (1.0, 0.0, 0.0)
        vobj.addProperty("App::PropertyColor", "Feed", "Display", "Color of the path").Feed = (0.0, 1.0, 0.0)

    def getIcon(self):
        return BaptUtilities.getIconPath("Surfacage.svg")

        #return ":/icons/surfacage.svg"

    def attach(self,vobj):
        #self.updateColors()
        #self.root = self.buildScene(vobj)
        vobj.addDisplayMode(self.root, "Lines")
        pass

    def buildScene(self,vobj):
        App.Console.PrintMessage(f"Build scene\n")
        root = coin.SoGroup()
        for i in range(10):
            # line = coin.SoLineSet()
            # line.numVertices.setValue(2)
            # line.vertexProperty.setValue(coin.SoVertexProperty())
            # line.vertexProperty.vertex.setValues([
            #     [i, 0, 0],
            #     [i+1, 0, 0]])
            # line.vertexProperty.vertex.setBinding(coin.SoVertexProperty.PER_FACE)
            # line.vertexProperty.vertex.setNumValues(2)
            # line.materialBinding.setValue(coin.SoMaterialBinding.PER_PART)
            # material = coin.SoMaterial()
            # material.diffuseColor.setValue([i/10.0, 1-(i/10.0), 0.0])
            # root.addChild(material)
            # root.addChild(line)
            line = coin.SoSeparator()
            line_color = coin.SoBaseColor()
            line_color.rgb = (i/10.0, 1-(i/10.0), 0.0)
            line.addChild(line_color)
            line_coords = coin.SoCoordinate3()
            line_coords.point.setValues(0,2,[
                App.Vector(i *10, 5, 0),
                App.Vector((i+1) *10, 5, 0)])
            line.addChild(line_coords)
            line.addChild(coin.SoLineSet())
            root.addChild(line)
        # App.Console.PrintMessage(f"Move : {len(vobj.Object.move)}\n")
        #for i in range(len(vobj.Object.move)):
            # line = coin.SoSeparator()
            # line_color = coin.SoBaseColor()
            # if vobj.Object.move[i]["Type"] == "Rapid":
            #     line_color.rgb = (1.0, 0.0, 0.0)
            # else:
            #     line_color.rgb = (0.0, 1.0, 0.0)
            # line.addChild(line_color)
            # line_coords = coin.SoCoordinate3()
            # line_coords.point.setValues(0,2,[
            #     vobj.Object.move[i]["from"],
            #     vobj.Object.move[i]["to"]])
            # line.addChild(line_coords)
            # line.addChild(coin.SoLineSet())
            # root.addChild(line)

        return root
    
    def getHighlightSegments(self, vobj, sub):
        # sub est une liste de sous-éléments survolés (ex : ["Edge1"])
        if not sub or not self.root:
            return
        App.Console.PrintMessage(f"Get highlight segments\n")
    def updateData(self, obj, prop):
        if prop in ("Depth","Rapid", "Feed"):
            #self.updateColors()
            pass
        if hasattr(self, "root"):
            #self.root.removeAllChildren()
            self.root = self.buildScene(obj.ViewObject)
    def updateColors(self):
        App.Console.PrintMessage(f"Update colors\n")
        if not hasattr(self, "Object") or not self.Object:
            return
        #debug
        App.Console.PrintMessage(f"Update colors 1\n")
        if hasattr(self.Object, "Rapid") and hasattr(self.Object, "Feed"):
            App.Console.PrintMessage(f"Update colors 2\n")
            rapidcount = len(self.Object.Rapid)
            feedcount = len(self.Object.Feed)
            colors = []
            colors.extend([self.Object.ViewObject.Rapid] * rapidcount)
            colors.extend([self.Object.ViewObject.Feed] * feedcount)
            self.Object.ViewObject.DiffuseColor = colors
            # self.Object.ViewObject.LineColor = colors

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

    def loads(self,state):
        '''When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here.'''
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
