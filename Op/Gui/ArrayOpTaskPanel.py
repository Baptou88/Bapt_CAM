import FreeCAD as App
import FreeCADGui as Gui
from BaptUtilities import getIconPath
from Op.BaseOp import baseOp
from PySide import QtGui
from utils import BQuantitySpinBox, PointSelectionObserver


class ArrayOpTaskPanel:
    def __init__(self, obj):
        self.Object = obj
        self.pt = None
        App.activeDocument().openTransaction("Edit ArrayOp")
        self.setupUi()

    def setupUi(self):
        self.ui1 = QtGui.QWidget()
        self.ui1.setWindowTitle("Array Operation")
        self.ui1.setWindowIcon(QtGui.QIcon(getIconPath("Tree_ArrayOp.svg")))

        ui2 = QtGui.QWidget()
        ui2.setWindowTitle("Omitt")
        ui2.setWindowIcon(QtGui.QIcon(getIconPath("desactiveOp.png")))

        self.form = [self.ui1, ui2]
        layout = QtGui.QFormLayout(self.ui1)
        layoutOmitt = QtGui.QFormLayout(ui2)

        # Combobox for selecting the base operation
        self.baseOpCombo = QtGui.QComboBox()
        self.baseOpComboLayout = QtGui.QHBoxLayout()
        baseOpGroup = QtGui.QGroupBox("Base Operation")
        baseOpGroup.setLayout(self.baseOpComboLayout)
        self.baseOpComboLayout.addWidget(self.baseOpCombo)
        layout.addWidget(baseOpGroup)

        patternGroup = QtGui.QGroupBox("Pattern")
        patternLayout = QtGui.QFormLayout()
        patternGroup.setLayout(patternLayout)
        layout.addWidget(patternGroup)
        self.Pattern = QtGui.QComboBox()
        self.Pattern.addItems(["Linear1D", "Linear2D", "Polar"])
        patternLayout.addRow("Pattern:", self.Pattern)

        XGroup = QtGui.QGroupBox("Spacing X")
        XLayout = QtGui.QFormLayout()
        XGroup.setLayout(XLayout)
        layout.addWidget(XGroup)
        self.CopiesX = BQuantitySpinBox.BQuantitySpinBox(self.Object, "CopiesX")
        XLayout.addRow("Copies X:", self.CopiesX.getWidget())
        self.SpacingX_x = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingX.x")
        XLayout.addRow("Spacing X:", self.SpacingX_x.getWidget())
        self.SpacingX_y = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingX.y")
        XLayout.addRow("Spacing Y:", self.SpacingX_y.getWidget())
        self.SpacingX_z = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingX.z")
        XLayout.addRow("Spacing Z:", self.SpacingX_z.getWidget())

        self.SpacingX_button = QtGui.QPushButton("Update SpacingX")
        XLayout.addRow("", self.SpacingX_button)

        self.YGroup = QtGui.QGroupBox("Spacing Y")
        self.YLayout = QtGui.QFormLayout()
        self.YGroup.setLayout(self.YLayout)
        layout.addWidget(self.YGroup)
        self.CopiesY = BQuantitySpinBox.BQuantitySpinBox(self.Object, "CopiesY")
        self.YLayout.addRow("Copies Y:", self.CopiesY.getWidget())

        self.SpacingY_x = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingY.x")
        self.YLayout.addRow("Spacing X:", self.SpacingY_x.getWidget())
        self.SpacingY_y = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingY.y")
        self.YLayout.addRow("Spacing Y:", self.SpacingY_y.getWidget())
        self.SpacingY_z = BQuantitySpinBox.BQuantitySpinBox(self.Object, "SpacingY.z")
        self.YLayout.addRow("Spacing Z:", self.SpacingY_z.getWidget())

        if self.Object.Pattern == "Linear2D":
            self.YGroup.setVisible(True)
        else:
            self.YGroup.setVisible(False)

        # tableau for omitt
        self.omittTable = QtGui.QTableWidget()
        self.omittTable.setColumnCount(3)
        self.omittTable.setHorizontalHeaderLabels(["i", "j", "Remove"])
        layoutOmitt.addRow("Omitt:", self.omittTable)
        # Populate the omitt table with existing values
        if hasattr(self.Object.Proxy, "omitt"):
            for i, (row, col) in enumerate(self.Object.Proxy.omitt):
                self.omittTable.insertRow(i)
                self.omittTable.setItem(i, 0, QtGui.QTableWidgetItem(str(row)))
                self.omittTable.setItem(i, 1, QtGui.QTableWidgetItem(str(col)))
                removeButton = QtGui.QPushButton("Remove")
                removeButton.clicked.connect(lambda _, r=i: self.removeOmittRow(r))
                self.omittTable.setCellWidget(i, 2, removeButton)
        # Add button to add new omitt row
        self.addOmittButton = QtGui.QPushButton("Add")
        self.addOmittButton.clicked.connect(self.addOmittRow)
        layoutOmitt.addRow("", self.addOmittButton)

        # Populate the combobox with available operations
        for obj in App.activeDocument().Objects:
            if hasattr(obj, "Proxy") and isinstance(obj.Proxy, baseOp):
                if obj.Proxy == self.Object.Proxy:
                    continue
                self.baseOpCombo.addItem(obj.Label, obj.Name)
        if self.Object.baseOp:
            index = self.baseOpCombo.findData(self.Object.baseOp.Name)
            if index >= 0:
                self.baseOpCombo.setCurrentIndex(index)

        if self.Object.Pattern:
            index = self.Pattern.findText(self.Object.Pattern)
            if index >= 0:
                self.Pattern.setCurrentIndex(index)
        self.Pattern.currentTextChanged.connect(self.onPatternChanged)
        self.baseOpCombo.currentTextChanged.connect(self.onBaseOpChanged)
        self.SpacingX_button.clicked.connect(self.onSpacingXClicked)

    def removeOmittRow(self, row):
        self.omittTable.removeRow(row)
        if hasattr(self.Object.Proxy, "omitt"):
            self.Object.Proxy.omitt.pop(row)

    def addOmittRow(self):
        row = self.omittTable.rowCount()
        self.omittTable.insertRow(row)
        self.omittTable.setItem(row, 0, QtGui.QTableWidgetItem("0"))
        self.omittTable.setItem(row, 1, QtGui.QTableWidgetItem("0"))
        removeButton = QtGui.QPushButton("Remove")
        removeButton.clicked.connect(lambda _, r=row: self.removeOmittRow(r))
        self.omittTable.setCellWidget(row, 2, removeButton)
        if hasattr(self.Object.Proxy, "omitt"):
            self.Object.Proxy.omitt.append((0, 0))
        self.omittTable.scrollToBottom()

    def onBaseOpChanged(self, index):
        if self.baseOpCombo.currentIndex() >= 0:
            self.Object.baseOp = self.baseOpCombo.currentData()
            objName = self.baseOpCombo.itemData(self.baseOpCombo.currentIndex())
            base = App.activeDocument().getObject(objName)
            if base:
                self.Object.baseOp = base

    def onPatternChanged(self, text):
        self.Object.Pattern = text
        if text == "Linear2D":
            self.YGroup.setVisible(True)
        else:
            self.YGroup.setVisible(False)

    def onSpacingXClicked(self):
        self.SpacingX_button.clicked.disconnect(self.onSpacingXClicked)
        self.SpacingX_button.setText("click on first point")
        self.observer = PointSelectionObserver.PointSelectionObserver(lambda point, doc, object, element: self.onPointClicked(point))
        self.observer.enable()

    def onPointClicked(self, point):
        if self.pt is None:
            self.SpacingX_button.setText("click on second point")
            self.pt = point
            # self.observer.enable()
        else:
            self.SpacingX_button.setText("Update SpacingX")
            self.observer.disable()
            self.observer = None

            # if hasattr(self.Object.Proxy, "SpacingX"):
            App.Console.PrintMessage(f"Updating SpacingX with delta: {point - self.pt}\n")
            try:
                self.Object.SpacingX = point - self.pt
                App.Console.PrintMessage(f"SpacingX updated to: {self.Object.SpacingX}\n")
            except Exception as e:
                App.Console.PrintMessage(f"Error updating SpacingX: {e}\n")
            self.pt = None
        self.SpacingX_button.clicked.connect(self.onSpacingXClicked)

    def updateData(self, fp_object, prop):
        self.CopiesX.updateWidget()
        self.CopiesY.updateWidget()

        self.SpacingX_x.updateWidget()
        self.SpacingX_y.updateWidget()
        self.SpacingX_z.updateWidget()
        self.SpacingY_x.updateWidget()
        self.SpacingY_y.updateWidget()
        self.SpacingY_z.updateWidget()

    def getStandardButtons(self):
        return (
            QtGui.QDialogButtonBox.Ok |
            QtGui.QDialogButtonBox.Apply |
            QtGui.QDialogButtonBox.Cancel
        )

    def clicked(self, button):
        if button == QtGui.QDialogButtonBox.Apply:
            self.Object.recompute()

    def preCleanup(self):
        if hasattr(self, "observer") and self.observer:
            self.observer.disable()
            self.observer = None
        self.Object.ViewObject.Proxy.closeTaskPanel()
        Gui.Control.closeDialog()

    def accept(self):
        self.preCleanup()
        self.Object.Proxy.omitt = [(int(self.omittTable.item(row, 0).text()), int(self.omittTable.item(row, 1).text())) for row in range(self.omittTable.rowCount())]

        self.Object.recompute()
        App.activeDocument().commitTransaction()
        return True

    def reject(self):
        self.preCleanup()
        App.activeDocument().abortTransaction()
        return True
