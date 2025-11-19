import sys
from BaptUtilities import find_cam_project, getIconPath
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

        self.toolComboBox = QtGui.QComboBox()
        layout.addWidget(self.toolComboBox)
        

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
        self.toolComboBox.currentTextChanged.connect(lambda: self.onToolComboBoxChanged())

    def onToolComboBoxChanged(self):
        App.Console.PrintMessage(f'par là\n')
        try:
            tool = self.toolComboBox.currentText()
            if tool:
                self.obj.Tool = App.ActiveDocument.getObject(tool)
                self.selectedToolLabel.setText(f"Outil sélectionné: {self.obj.Tool.Name} (ID: {self.obj.Tool.Id})")
                self.diameter.setValue(self.obj.Tool.Radius * 2.0)
                self.idTool.setValue(self.obj.Tool.Id)
                self.nameTool.setText(self.obj.Tool.Name)
        except Exception as e:
            
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            App.Console.PrintError(f"Erreur lors du changement d'outil: {e}\n")

    def selectTool(self):
        App.Console.PrintMessage(f'label\n')
        #QtGui.QMessageBox.information(self.form, "Info", "Bouton de sélection d'outil cliqué!")

        """Ouvre le dialogue de sélection d'outil"""
        if not hasattr(self.obj, "Tool") or self.obj.Tool is None:
            current_tool = None
        else:
            current_tool = self.obj.Tool


        dialog = ToolSelectorDialog.ToolSelectorDialog(current_tool.Id if current_tool else -1, self.form)
        result = dialog.exec_()
        sel = dialog.selected_tool
        if result == QtGui.QDialog.Accepted and sel is not None:
            # Récupérer le projet CAM actif
            p = find_cam_project(self.obj)
            # p = Gui.activeView().getActiveObject("camproject")  # FIXME
            if p:
                groupTools = p.Proxy.getToolsGroup()
                #tool = App.ActiveDocument.getObject(f"T{sel.id} ({sel.name})")
                if current_tool is None or current_tool.Id != sel.id:
                    new_tool = App.ActiveDocument.addObject("Part::Cylinder",f"T{sel.id} ({sel.name})")
                    new_tool.addProperty("App::PropertyInteger","Id","Tool","Tool ID").Id = sel.id
                    new_tool.addProperty("App::PropertyString","Name","Tool","Tool Name").Name = sel.name
                    groupTools.addObject(new_tool)
                    self.obj.Tool = new_tool
                    new_tool.Radius = sel.diameter / 2.0
                    if current_tool is not None:
                        # Supprimer l'ancien outil
                        groupTools.removeObject(current_tool)
                        App.ActiveDocument.removeObject(current_tool.Label)

                    #TODO Verifier si l'outil n'est pas déja utilisé par un autre objet avant de le supprimer
                new_tool.Height = sel.length
                self.idTool.setValue(sel.id)
                self.nameTool.setText(sel.name)
                self.diameter.setValue(sel.diameter)

    def initValues(self):
        #populate tool combo box
        p = find_cam_project(self.obj)
        if p:
            groupTools = p.Proxy.getToolsGroup()
            self.toolComboBox.clear()
            for t in groupTools.Group:
                self.toolComboBox.addItem(t.Label)
            if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
                idx = self.toolComboBox.findText(self.obj.Tool.Label)
                if idx >= 0:
                    self.toolComboBox.setCurrentIndex(idx)

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
