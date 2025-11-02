from BaptUtilities import getIconPath
import FreeCAD as App
import FreeCADGui as Gui

from PySide import QtCore, QtGui
from Tool import ToolSelectorDialog


class ToolTaskPanel:
    def __init__(self,obj,parent=None):

        self.obj = obj
        self.parent = parent

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Sélection d'outil")
        self.form.setWindowIcon(QtGui.QIcon(getIconPath("tool.svg")))

        layout = QtGui.QVBoxLayout(self.form)


        self.selectToolButton = QtGui.QPushButton("Sélectionner un outil")
        layout.addWidget(self.selectToolButton)


        self.toolLayout = QtGui.QFormLayout()
        #champ pour afficher l'outil sélectionné
        self.selectedToolLabel = QtGui.QLabel("Aucun outil sélectionné")
        layout.addWidget(self.selectedToolLabel)

        #champ edit id 
        self.idTool = QtGui.QSpinBox()
        self.idTool.setRange(0, 10000)
        self.toolLayout.addRow("ID Outil:", self.idTool)

        #champ edit name
        self.nameTool = QtGui.QLineEdit()
        self.toolLayout.addRow("Nom Outil:", self.nameTool)

        #champ d'edition diametre
        self.diameter = QtGui.QDoubleSpinBox()
        self.diameter.setRange(0, 100)
        self.toolLayout.addRow("Diamètre:", self.diameter)

        layout.addLayout(self.toolLayout)
    
        self.initValues()

    def selectTool(self):
        App.Console.PrintMessage(f'label\n')
        #QtGui.QMessageBox.information(self.form, "Info", "Bouton de sélection d'outil cliqué!")

        """Ouvre le dialogue de sélection d'outil"""
        if not hasattr(self.obj, "Tool") or self.obj.Tool is None:
            current_tool_id = -1
        else:
            current_tool_id = self.obj.Tool.Id
        dialog = ToolSelectorDialog.ToolSelectorDialog(current_tool_id, self.form)
        result = dialog.exec_()
        sel = dialog.selected_tool
        if result == QtGui.QDialog.Accepted and sel is not None:
            p = Gui.activeView().getActiveObject("camproject") #FIXME
            if p:
                groupTools = p.Proxy.getToolsGroup()
                tool = App.ActiveDocument.getObject(f"T{sel.id} ({sel.name})")
                if tool is None:
                    tool = App.ActiveDocument.addObject("Part::Cylinder",f"T{sel.id} ({sel.name})")
                    tool.addProperty("App::PropertyInteger","Id","Tool","Tool ID").Id = sel.id
                    tool.addProperty("App::PropertyString","Name","Tool","Tool Name").Name = sel.name
                    groupTools.addObject(tool)
                    self.obj.Tool = tool
                tool.Id = sel.id
                self.idTool.setValue(sel.id)
                tool.Label = f"T{sel.id} ({sel.name})"
                self.nameTool.setText(sel.name)
                tool.Radius = sel.diameter / 2.0
                self.diameter.setValue(sel.diameter)
                tool.Height = sel.length
    
    def initValues(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            tool = self.obj.Tool
            self.selectedToolLabel.setText(f"Outil sélectionné: {tool.Name} (ID: {tool.Id})")
            self.diameter.setValue(tool.Radius * 2.0)
            self.idTool.setValue(tool.Id)
            self.nameTool.setText(tool.Name)

    def initVListeners(self):
        self.selectToolButton.clicked.connect(lambda: self.selectTool())
        self.idTool.valueChanged.connect(lambda: self.updateToolId())
        self.nameTool.textChanged.connect(lambda: self.updateToolName())
        self.diameter.valueChanged.connect(lambda: self.updateToolDiameter())
    def updateToolDiameter(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            tool = self.obj.Tool
            tool.Radius = self.diameter.value() / 2.0
    def updateToolId(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            tool = self.obj.Tool
            tool.Id = self.idTool.value()
            self.selectedToolLabel.setText(f"Outil sélectionné: {tool.Name} (ID: {tool.Id})")
    def updateToolName(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            tool = self.obj.Tool
            tool.Name = self.nameTool.text()
            self.selectedToolLabel.setText(f"Outil sélectionné: {tool.Name} (ID: {tool.Id})")
    
    def getForm(self):
        return self.form
