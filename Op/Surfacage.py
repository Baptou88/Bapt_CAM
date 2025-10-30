from BaptPath import baseOp, baseOpViewProviderProxy
from BaptTools import ToolDatabase
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
from pivy import coin
import Part 
import BaptUtilities
from Tool.ToolSelectorDialog import ToolSelectorDialog
from utils import PointSelectionObserver
import math
import os

class Surfacage(baseOp):
    def __init__(self, obj):
        self.Type = "Surfacage"
        super().__init__(obj)

        self.initProperties(obj)
        obj.Proxy = self
    
    def initProperties(self, obj):
        if not hasattr(obj,"Name"):
            obj.addProperty("App::PropertyString", "Name", "Surfacage", "Nom de l'opérateur").Name = "Surfacage"
        if not hasattr(obj,"Stock"):
            obj.addProperty("App::PropertyLink", "Stock", "Surfacage", "Stock")
        if not hasattr(obj,"Tool"):
            obj.addProperty("App::PropertyLink", "Tool", "Surfacage", "Tool")
        if not hasattr(obj,"Depth"):
            obj.addProperty("App::PropertyFloat", "Depth", "Surfacage", "Profondeur finale")
        # # Outil sélectionné
        # if not hasattr(obj, "ToolId"):
        #     obj.addProperty("App::PropertyInteger", "ToolId", "Tool", "Selected tool ID")
        #     obj.ToolId = -1  # Valeur par défaut (aucun outil sélectionné)
        
        # # Nom de l'outil (affiché en lecture seule)
        # if not hasattr(obj, "ToolName"):
        #     obj.addProperty("App::PropertyString", "ToolName", "Tool", "Selected tool name")
        #     obj.setEditorMode("ToolName", 1)  # en lecture seule
        
        # obj.addProperty("App::PropertyFloat", "ToolDiameter", "Tool", "Diamètre de la tool").ToolDiameter = 12.0
        if not hasattr(obj,"Recouvrement"):
            obj.addProperty("App::PropertyFloat", "Recouvrement", "Surfacage", "Recouvrement").Recouvrement = 10.0

        #cherche l'objet Model dans le document actif



    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return
        if not hasattr(obj,"Tool") or  obj.Tool is None:
            return
        #obj.Shape = Part.Shape()
        if not obj.Stock:
            App.Console.PrintMessage("Aucun stock sélectionné\n")
            return
        App.Console.PrintMessage(f"Stock sélectionné : {obj.Stock.Name}\n")
        bb = obj.Stock.Shape.BoundBox
        App.Console.PrintMessage(f"Taille du stock : {bb.XLength}, {bb.YLength}, {bb.ZLength}\n")

        nbPasseLat = math.ceil(bb.YLength / obj.Recouvrement)  + 1
        passeLat = bb.YLength / nbPasseLat
        App.Console.PrintMessage(f'Nombre de passes latérales : {nbPasseLat}\n')
        App.Console.PrintMessage(f' passe latérale : {passeLat}\n')

        posX = bb.XMin - obj.Tool.Radius.Value
        posY = bb.YMin - (obj.Tool.Radius.Value) + passeLat
        #posY = bb.YMin + (obj.Tool.Radius.Value) - passeLat
        posZ = obj.Depth

        obj.Gcode = ""
        obj.Gcode += f"G0 X{posX} Y{posY} Z{posZ+2}\n"
        obj.Gcode += f"G1 Z{posZ} F500\n"


        for i in range(int(nbPasseLat)):
            if i % 2 != 0:
                obj.Gcode += f"G1 X{bb.XMin - (obj.Tool.Radius.Value)} Y{posY}\n"
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:

                    obj.Gcode += f"G0 X{bb.XMin - (obj.Tool.Radius.Value)} Y{posY} Z{posZ + 2}\n"
                else:
                    posY += passeLat

                    obj.Gcode += f"G1 X{bb.XMin - (obj.Tool.Radius.Value)} Y{posY}\n"
            else:

                obj.Gcode += f"G1 X{bb.XMax + (obj.Tool.Radius.Value)} Y{posY}\n"
                #points.append(App.Vector(posX, posY, posZ))
                if i == nbPasseLat - 1:

                    obj.Gcode += f"G0 X{bb.XMax + (obj.Tool.Radius.Value)} Y{posY} Z{posZ + 2}\n"
                    
                else:
                    posY += passeLat

                    obj.Gcode += f"G1 X{bb.XMax + (obj.Tool.Radius.Value)} Y{posY}\n"
        

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def onChanged(self, obj, prop):
        if prop in ("Stock", "Depth", "Tool", "Recouvrement"):
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

    def attach(self, obj):
        self.Object = obj.Object
        return super().attach(obj)
    
    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Surfacage.svg")

        #return ":/icons/surfacage.svg"

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
    
    # def updateData(self, obj, prop):
    #     if prop in ("Depth","Rapid", "Feed"):
    #         #self.updateColors()
    #         pass
    #     if hasattr(self, "root"):
    #         #self.root.removeAllChildren()
    #         self.root = self.buildScene(obj.ViewObject)
    # def updateColors(self):
    #     App.Console.PrintMessage(f"Update colors\n")
    #     if not hasattr(self, "Object") or not self.Object:
    #         return
    #     #debug
    #     App.Console.PrintMessage(f"Update colors 1\n")
    #     if hasattr(self.Object, "Rapid") and hasattr(self.Object, "Feed"):
    #         App.Console.PrintMessage(f"Update colors 2\n")
    #         rapidcount = len(self.Object.Rapid)
    #         feedcount = len(self.Object.Feed)
    #         colors = []
    #         colors.extend([self.Object.ViewObject.Rapid] * rapidcount)
    #         colors.extend([self.Object.ViewObject.Feed] * feedcount)
    #         self.Object.ViewObject.DiffuseColor = colors
    #         # self.Object.ViewObject.LineColor = colors

    # def setupContextMenu(self, vobj, menu):
    #     action = menu.addAction("Edit")
    #     action.triggered.connect(lambda: self.setEdit(vobj))
    
    def setEdit(self, vobj, mode=0):
        try:
            import importlib
            importlib.reload(SurfacageTaskPanel)
        except Exception:
            pass
        Gui.Control.showDialog(SurfacageTaskPanel(vobj.Object,deleteOnReject=False))
    
    # def doubleClicked(self, vobj):
    #     self.setEdit(vobj)
    #     return True
    
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
    def __init__(self, obj,deleteOnReject):
        self.obj = obj
        self.deleteOnReject = deleteOnReject
        self.form = QtGui.QWidget()

        self.form.setWindowTitle("Édition de l'opérateur")
        layout = QtGui.QFormLayout(self.form)
        # Nom
        self.nameEdit = QtGui.QLineEdit(obj.Name)
        layout.addRow("Nom", self.nameEdit)

        # Tool
        self.toolDiameterEdit = QtGui.QDoubleSpinBox(); 
        self.toolDiameterEdit.setRange(0,1000); 
        
        layout.addRow("Diamètre de l'outil", self.toolDiameterEdit)

        # Recouvrement
        self.recouvrement = QtGui.QDoubleSpinBox(); 
        self.recouvrement.setRange(0,1000); 
        self.recouvrement.setValue(obj.Recouvrement)
        layout.addRow("Recouvrement", self.recouvrement)

        # Profondeur finale
        self.depthEdit = QtGui.QDoubleSpinBox(); 
        self.depthEdit.setRange(-10000,10000); 
        self.depthEdit.setValue(obj.Depth)
        layout.addRow("Profondeur finale", self.depthEdit)
        self.depthBtn = QtGui.QPushButton("Click on Part")
        self.depthBtn.clicked.connect(self.setDepth)
        layout.addRow(self.depthBtn)
        
        # Groupe pour l'outil
        toolGroup = QtGui.QGroupBox("Outil")
        toolLayout = QtGui.QVBoxLayout()
        
        # Informations sur l'outil sélectionné
        self.toolInfoLayout = QtGui.QFormLayout()
        if not obj.Tool:
            self.toolIdLabel = QtGui.QLabel("Aucun outil sélectionné")
            self.toolNameLabel = QtGui.QLabel("")
            self.toolTypeLabel = QtGui.QLabel("")
            self.toolDiameterLabel = QtGui.QLabel("")
            self.toolDiameterEdit.setValue(0.0)
        else:
            self.toolIdLabel = QtGui.QLabel(obj.Tool.Id)
            self.toolNameLabel = QtGui.QLabel(f"{obj.Tool.Name}")
            self.toolTypeLabel = QtGui.QLabel("")
            self.toolDiameterLabel = QtGui.QLabel(f"{obj.Tool.Radius.Value * 2:.3f} mm")
            self.toolDiameterEdit.setValue(obj.Tool.Radius * 2)
        
        self.toolInfoLayout.addRow("ID:", self.toolIdLabel)
        self.toolInfoLayout.addRow("Nom:", self.toolNameLabel)
        self.toolInfoLayout.addRow("Type:", self.toolTypeLabel)
        self.toolInfoLayout.addRow("Diamètre:", self.toolDiameterLabel)
        
        toolLayout.addLayout(self.toolInfoLayout)
        
        # Bouton pour sélectionner un outil
        self.selectToolButton = QtGui.QPushButton("Sélectionner un outil")
        self.selectToolButton.clicked.connect(self.selectTool)
        toolLayout.addWidget(self.selectToolButton)
        
        toolGroup.setLayout(toolLayout)
        layout.addWidget(toolGroup)
    
        self.toolDiameterEdit.valueChanged.connect(self.updateValue)
        self.depthEdit.valueChanged.connect(self.updateValue)
        self.recouvrement.valueChanged.connect(self.updateValue)

                
        if self.obj.Tool:
            self.obj.Tool.Visibility = True

    def updateValue(self):
        self.obj.Depth = self.depthEdit.value()
        self.obj.Tool.Radius = self.toolDiameterEdit.value() / 2
        self.obj.Recouvrement = self.recouvrement.value()

    def selectTool(self):
        """Ouvre le dialogue de sélection d'outil"""
        if not hasattr(self.obj, "Tool") or self.obj.Tool is None:
            current_tool_id = -1
        else:
            current_tool_id = self.obj.Tool.Id
        dialog = ToolSelectorDialog(current_tool_id, self.form)
        result = dialog.exec_()
        
        sel = dialog.selected_tool_id
        if result == QtGui.QDialog.Accepted and sel >= 0:
            # Mettre à jour l'outil sélectionné
            

            # ajoute un object Part::Cylinder pour visualiser l'outil
            p = Gui.activeView().getActiveObject("camproject")
            if p:
                groopTools = p.Proxy.getToolsGroup()
                tool = App.ActiveDocument.getObject("ToolVisual_"+str(sel))
                if tool is None:
                    tool = App.ActiveDocument.addObject("Part::Cylinder","ToolVisual_"+str(sel))
                    tool.addProperty("App::PropertyInteger","Id","Tool","Tool ID").Id = sel
                    tool.addProperty("App::PropertyString","Name","Tool","Tool Name").Name = dialog.selected_tool.name
                    groopTools.addObject(tool)
                    self.obj.Tool = tool
                tool.Id = sel
                tool.Label = "ToolVisual_"+str(sel)
                tool.Radius = dialog.selected_tool.diameter / 2
                tool.Height = 50
                


            self.updateToolInfo()

    def updateToolInfo(self):
        """Met à jour les informations de l'outil sélectionné"""
        if not hasattr(self.obj, "Tool") or self.obj.Tool is None:
            return
        if self.obj.Tool.Id < 0:
            self.toolIdLabel.setText("Aucun outil sélectionné")
            self.toolNameLabel.setText("")
            self.toolTypeLabel.setText("")
            self.toolDiameterLabel.setText("")
            return
        
        try:
            # Récupérer l'outil depuis la base de données
            db = ToolDatabase()
            tools = db.get_all_tools()
            
            for tool in tools:
                if tool.id == self.obj.Tool.Id:
                    self.toolIdLabel.setText(str(tool.id))
                    self.toolNameLabel.setText(tool.name)
                    self.toolTypeLabel.setText(tool.type)
                    self.toolDiameterLabel.setText(f"{tool.diameter:.2f} mm")
                    self.obj.Tool.Radius = tool.diameter / 2
                    self.toolDiameterEdit.setValue(tool.diameter)
                    # self.obj.ToolName = f"{tool.name} (Ø{tool.diameter}mm)"
                    
                    # Si c'est un taraud, mettre à jour le pas de filetage
                    if tool.type.lower() == "taraud" and self.obj.CycleType == "Tapping":
                        self.threadPitch.setValue(tool.thread_pitch)
                    break
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la récupération de l'outil: {e}\n")

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
        #self.obj.Name = self.nameEdit.text()
        self.updateValue()

        if self.obj.Tool:
            self.obj.Tool.Visibility = False

        App.ActiveDocument.recompute()
        Gui.Control.closeDialog()
    def reject(self):
                
        if self.obj.Tool:
            self.obj.Tool.Visibility = False

        if self.deleteOnReject :
            App.ActiveDocument.removeObject(self.obj.Name)
        Gui.Control.closeDialog()
