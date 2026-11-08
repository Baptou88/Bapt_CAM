from PySide import QtGui

from Op.Gui.ContournageTaskPanel import ContournageTaskPanel
from utils import BQuantitySpinBox


class ChamferTaskPanel(ContournageTaskPanel):
    """TaskPanel de chamfrein, basé sur le panel de contournage."""

    def __init__(self, obj, deleteOnReject):
        super().__init__(obj, deleteOnReject)
        self.ui1.setWindowTitle("Paramètres de chamfrein")

        self.chamfer_group = QtGui.QGroupBox("Paramètres de chamfrein")
        chamfer_layout = QtGui.QFormLayout(self.chamfer_group)

        self.use_width_check = QtGui.QCheckBox()
        self.use_width_check.setChecked(bool(getattr(obj, "UseChamferWidth", True)))
        chamfer_layout.addRow("Piloter par largeur:", self.use_width_check)

        self.chamfer_width = BQuantitySpinBox.BQuantitySpinBox(obj, "ChamferWidth")
        chamfer_layout.addRow("Largeur du chamfrein:", self.chamfer_width.getWidget())

        self.chamfer_depth = BQuantitySpinBox.BQuantitySpinBox(obj, "ChamferDepth")
        chamfer_layout.addRow("Profondeur du chamfrein:", self.chamfer_depth.getWidget())

        self.tool_start_depth = BQuantitySpinBox.BQuantitySpinBox(obj, "ToolStartDepth")
        chamfer_layout.addRow("Position sous Zref:", self.tool_start_depth.getWidget())

        self.use_tool_geometry_check = QtGui.QCheckBox()
        self.use_tool_geometry_check.setChecked(bool(getattr(obj, "UseToolConicalGeometry", True)))
        chamfer_layout.addRow("Lire angle/pointe depuis l'outil:", self.use_tool_geometry_check)

        self.cone_angle = QtGui.QDoubleSpinBox()
        self.cone_angle.setRange(1.0, 179.0)
        self.cone_angle.setDecimals(2)
        self.cone_angle.setSuffix(" °")
        self.cone_angle.setValue(float(getattr(obj, "ConeAngle", 90.0)))
        chamfer_layout.addRow("Angle de cône:", self.cone_angle)

        self.tip_diameter = QtGui.QDoubleSpinBox()
        self.tip_diameter.setRange(0.0, 100.0)
        self.tip_diameter.setDecimals(3)
        self.tip_diameter.setSuffix(" mm")
        tip_val = getattr(obj, "TipDiameter", 0.0)
        if hasattr(tip_val, "Value"):
            tip_val = tip_val.Value
        self.tip_diameter.setValue(float(tip_val))
        chamfer_layout.addRow("Diamètre de pointe:", self.tip_diameter)

        self.computed_depth_label = QtGui.QLabel("")
        chamfer_layout.addRow("Profondeur calculée:", self.computed_depth_label)

        self.effective_diameter_label = QtGui.QLabel("")
        chamfer_layout.addRow("Diamètre effectif:", self.effective_diameter_label)

        self.final_z_label = QtGui.QLabel("")
        chamfer_layout.addRow("Z final du chanfrein:", self.final_z_label)

        base_layout = self.ui1.layout()
        base_layout.addWidget(self.chamfer_group)

        self.use_width_check.stateChanged.connect(self.updateChamfer)
        self.use_tool_geometry_check.stateChanged.connect(self.updateChamfer)
        self.cone_angle.valueChanged.connect(self.updateChamfer)
        self.tip_diameter.valueChanged.connect(self.updateChamfer)

        self.refreshComputedLabels()
        self.updateChamferFieldState()

    def updateChamferFieldState(self):
        by_width = self.use_width_check.isChecked()
        self.chamfer_width.getWidget().setEnabled(by_width)
        self.chamfer_depth.getWidget().setEnabled(not by_width)

        use_tool_geom = self.use_tool_geometry_check.isChecked()
        self.cone_angle.setEnabled(not use_tool_geom)
        self.tip_diameter.setEnabled(not use_tool_geom)

    def refreshComputedLabels(self):
        depth = getattr(self.obj, "ComputedChamferDepth", 0.0)
        diameter = getattr(self.obj, "EffectiveToolDiameter", 0.0)
        if hasattr(depth, "Value"):
            depth = depth.Value
        if hasattr(diameter, "Value"):
            diameter = diameter.Value
        self.computed_depth_label.setText(f"{float(depth):.3f} mm")
        self.effective_diameter_label.setText(f"{float(diameter):.3f} mm")

        start_z = 0.0
        if getattr(self.obj, "ContourGeometry", None) is not None:
            zref = float(self.obj.ContourGeometry.Proxy.getDepths()[0])
            start_depth = float(getattr(self.obj.ToolStartDepth, "Value", self.obj.ToolStartDepth))
            start_z = zref - start_depth

        self.final_z_label.setText(f"{start_z:.3f} mm")

    def updateChamfer(self):
        self.obj.UseChamferWidth = self.use_width_check.isChecked()
        self.obj.UseToolConicalGeometry = self.use_tool_geometry_check.isChecked()
        self.obj.ConeAngle = self.cone_angle.value()
        self.obj.TipDiameter = self.tip_diameter.value()

        self.updateChamferFieldState()
        self.updateContournage()
        self.refreshComputedLabels()

    def updateData(self, obj, prop):
        super().updateData(obj, prop)
        if prop in ["ComputedChamferDepth", "EffectiveToolDiameter", "Tool", "UseChamferWidth", "UseToolConicalGeometry", "ToolStartDepth", "ContourGeometry"]:
            self.refreshComputedLabels()
            self.updateChamferFieldState()
