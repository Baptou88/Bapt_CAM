from BaptUtilities import find_cam_project, getIconPath
import FreeCAD as App

from PySide import QtGui
from Tool import ToolSelectorDialog, tool_utils

from utils import Log
import utils.BQuantitySpinBox as BQantitySpinBox


class ToolTaskPanel:
    def __init__(self, obj, parent=None):

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
        # champ pour afficher l'outil sélectionné
        self.selectedToolLabel = QtGui.QLabel("Aucun outil sélectionné")
        layout.addWidget(self.selectedToolLabel)

        # champ edit id
        self.idTool = QtGui.QSpinBox()
        self.idTool.setRange(0, 10000)
        self.toolLayout.addRow("ID Outil:", self.idTool)

        # champ edit name
        self.nameTool = QtGui.QLineEdit()
        self.toolLayout.addRow("Nom Outil:", self.nameTool)

        # champ d'edition diametre
        self.diameter = QtGui.QDoubleSpinBox()
        self.diameter.setRange(0, 100)
        self.toolLayout.addRow("Diamètre:", self.diameter)

        # Type d'outil
        self.toolTypeLabel = QtGui.QLabel("")
        self.toolLayout.addRow("Type:", self.toolTypeLabel)

        # Rayon de tore (visible seulement pour fraise torique)
        self.torusRadiusSpin = QtGui.QDoubleSpinBox()
        self.torusRadiusSpin.setRange(0.0, 50.0)
        self.torusRadiusSpin.setSingleStep(0.1)
        self.torusRadiusSpin.setSuffix(" mm")
        self.torusRadiusLabel = QtGui.QLabel("Rayon du tore:")
        self.toolLayout.addRow(self.torusRadiusLabel, self.torusRadiusSpin)
        self.torusRadiusLabel.setVisible(False)
        self.torusRadiusSpin.setVisible(False)

        # Angle de pointe (visible seulement pour foret)
        self.pointAngleSpin = QtGui.QDoubleSpinBox()
        self.pointAngleSpin.setRange(60.0, 180.0)
        self.pointAngleSpin.setSingleStep(1.0)
        self.pointAngleSpin.setSuffix(" °")
        self.pointAngleSpin.setValue(118.0)
        self.pointAngleLabel = QtGui.QLabel("Angle de pointe:")
        self.toolLayout.addRow(self.pointAngleLabel, self.pointAngleSpin)
        self.pointAngleLabel.setVisible(False)
        self.pointAngleSpin.setVisible(False)

        # champ d'edition Speed
        self.speed = QtGui.QDoubleSpinBox()
        self.speed = BQantitySpinBox.BQuantitySpinBox(self.obj, "Tool.Speed")
        # self.speed.setRange(0, 10000)
        self.toolLayout.addRow("Vitesse de coupe (RPM):", self.speed.getWidget())

        # champ d'edition Feed
        # self.feed = QtGui.QDoubleSpinBox()
        self.feed = BQantitySpinBox.BQuantitySpinBox(self.obj, "Tool.Feed")
        # self.feed.setRange(0, 10000)
        self.toolLayout.addRow("Vitesse d'avance:", self.feed.getWidget())

        layout.addLayout(self.toolLayout)

        self.initValues()

        self.initListeners()

    def _updateSpecificFieldsVisibility(self, tool_type):
        """Show/hide specific fields depending on tool type."""
        is_torus = (tool_type == "Fraise torique")
        self.torusRadiusLabel.setVisible(is_torus)
        self.torusRadiusSpin.setVisible(is_torus)
        is_drill = (tool_type == "Foret")
        self.pointAngleLabel.setVisible(is_drill)
        self.pointAngleSpin.setVisible(is_drill)

    def onToolComboBoxChanged(self):

        tool = self.toolComboBox.currentText()
        if not tool:
            return
        toolObj = App.ActiveDocument.getObject(tool)
        if toolObj is None:
            return
        self.obj.Tool = toolObj
        self.selectedToolLabel.setText(f"Outil sélectionné: {toolObj.Label} (ID: {toolObj.Id})")
        self.diameter.setValue(toolObj.Radius * 2.0)
        self.idTool.setValue(toolObj.Id)
        self.nameTool.setText(toolObj.Label)
        self.speed.updateWidget()
        self.feed.updateWidget()
        tool_type = getattr(toolObj, "ToolType", "Fraise")
        self.toolTypeLabel.setText(tool_type)
        self._updateSpecificFieldsVisibility(tool_type)
        if hasattr(toolObj, "TorusRadius"):
            self.torusRadiusSpin.setValue(toolObj.TorusRadius)
        if hasattr(toolObj, "PointAngle"):
            self.pointAngleSpin.setValue(toolObj.PointAngle)

    def selectTool(self):
        """Ouvre le dialogue de sélection d'outil"""

        current_tool = getattr(self.obj, "Tool", None)

        dialog = ToolSelectorDialog.ToolSelectorDialog(current_tool.Id if current_tool else -1, self.form)
        result = dialog.exec_()
        sel = dialog.selected_tool
        if result == QtGui.QDialog.Rejected and sel is None:
            return
        # Récupérer le projet CAM actif
        p = find_cam_project(self.obj)
        if not p:
            return

        groupTools = p.Proxy.getToolsGroup()

        if current_tool is None or current_tool.Id != sel.id:
            new_tool = tool_utils.create_tool_obj(
                sel.id, sel.name, sel.diameter, sel.speed, sel.feed,
                tool_type=sel.type, torus_radius=sel.torus_radius,
                length=sel.length, point_angle=sel.point_angle
            )
            groupTools.addObject(new_tool)
            self.obj.Tool = new_tool

            if current_tool is not None:
                # Supprimer l'ancien outil s'il n'est utilisé par aucun autre objet
                if len(current_tool.InList) <= 1:
                    App.Console.PrintMessage("L'outil n'est utilisé par aucun autre objet, il sera supprimé.\n")
                    groupTools.removeObject(current_tool)
                    App.ActiveDocument.removeObject(current_tool.Name)
        else:
            # Même ID : mettre à jour les propriétés de l'outil existant
            current_tool.Speed = f"{sel.speed} mm/min"
            current_tool.Feed = f"{sel.feed} mm/min"
            current_tool.Radius = sel.diameter / 2.0
            current_tool.Height = sel.length
            if hasattr(current_tool, "ToolType"):
                current_tool.ToolType = sel.type
            if hasattr(current_tool, "TorusRadius"):
                current_tool.TorusRadius = sel.torus_radius
            if hasattr(current_tool, "PointAngle"):
                current_tool.PointAngle = sel.point_angle

        # Mettre à jour l'UI avec les données sélectionnées
        self._updateToolUI(sel)
        self.obj.recompute()
        self.initToolComboBox()

    def _updateToolUI(self, sel):
        """Met à jour tous les champs UI à partir d'un objet Tool (DB)."""
        self.selectedToolLabel.setText(f"Outil sélectionné: {self.obj.Tool.Label} (ID: {self.obj.Tool.Id})")
        self.idTool.setValue(sel.id)
        self.nameTool.setText(sel.name)
        self.diameter.setValue(sel.diameter)
        self.speed.updateWidget()
        self.feed.updateWidget()
        self.toolTypeLabel.setText(sel.type)
        self._updateSpecificFieldsVisibility(sel.type)
        self.torusRadiusSpin.setValue(sel.torus_radius)
        self.pointAngleSpin.setValue(sel.point_angle)

    def initValues(self):

        self.initToolComboBox()

        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            tool = self.obj.Tool
            self.selectedToolLabel.setText(f"Outil sélectionné: {tool.Name} (ID: {tool.Id})")
            self.diameter.setValue(tool.Radius * 2.0)
            self.idTool.setValue(tool.Id)
            self.nameTool.setText(tool.Name)
            tool_type = getattr(tool, "ToolType", "Fraise")
            self.toolTypeLabel.setText(tool_type)
            self._updateSpecificFieldsVisibility(tool_type)
            if hasattr(tool, "TorusRadius"):
                self.torusRadiusSpin.setValue(tool.TorusRadius)
            if hasattr(tool, "PointAngle"):
                self.pointAngleSpin.setValue(tool.PointAngle)

    def initToolComboBox(self):
        '''populate tool combo box'''
        p = find_cam_project(self.obj)
        if not p:
            return

        groupTools = p.Proxy.getToolsGroup()

        # Bloquer les signaux pour éviter les appels en cascade à onToolComboBoxChanged
        self.toolComboBox.blockSignals(True)
        self.toolComboBox.clear()
        for t in groupTools.Group:
            self.toolComboBox.addItem(t.Name)
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            idx = self.toolComboBox.findText(self.obj.Tool.Name)
            Log.baptDebug(f'Finding tool {self.obj.Tool.Name} in tool group idx {idx}')
            if idx >= 0:
                self.toolComboBox.setCurrentIndex(idx)
        else:
            self.toolComboBox.setCurrentIndex(-1)
        self.toolComboBox.blockSignals(False)

    def initListeners(self):
        self.selectToolButton.clicked.connect(lambda: self.selectTool())
        self.idTool.valueChanged.connect(lambda: self.updateToolId())
        self.nameTool.textChanged.connect(lambda: self.updateToolName())
        self.diameter.valueChanged.connect(lambda: self.updateToolDiameter())
        self.torusRadiusSpin.valueChanged.connect(lambda: self.updateTorusRadius())
        self.pointAngleSpin.valueChanged.connect(lambda: self.updatePointAngle())
        self.toolComboBox.currentTextChanged.connect(lambda: self.onToolComboBoxChanged())

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
            tool.Label = self.nameTool.text()
            self.selectedToolLabel.setText(f"Outil sélectionné: {tool.Label} (ID: {tool.Id})")

    def updateTorusRadius(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            if hasattr(self.obj.Tool, "TorusRadius"):
                self.obj.Tool.TorusRadius = self.torusRadiusSpin.value()

    def updatePointAngle(self):
        if hasattr(self.obj, "Tool") and self.obj.Tool is not None:
            if hasattr(self.obj.Tool, "PointAngle"):
                self.obj.Tool.PointAngle = self.pointAngleSpin.value()

    def getForm(self):
        return self.form
