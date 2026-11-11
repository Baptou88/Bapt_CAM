
import BaptOrigin

from BaptPath import GcodeEditorTaskPanel
import FreeCAD as App
from PySide import QtGui

from Tool.ToolsGUI import ToolTaskPanel


class PathOpTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.ui1 = GcodeEditorTaskPanel(obj)

        ui2 = ToolTaskPanel(obj)

        ui3 = attachementSupportTaskPanel(obj)

        self.form = [self.ui1.getForm(), ui2.getForm(), ui3.getForm()]

    def accept(self):
        self.ui1.accept()
        # FreeCADGui.Control.closeDialog()

    def reject(self):
        self.ui1.reject()
        # self.obj.ViewObject.Cursor = -1
        # FreeCADGui.Control.closeDialog()

    def clicked(self, button):
        """clicked(button) ... callback invoked when the user presses any of the task panel buttons."""
        self.ui1.clicked(button)

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return (QtGui.QDialogButtonBox.Ok
                | QtGui.QDialogButtonBox.Apply
                | QtGui.QDialogButtonBox.Cancel)


class attachementSupportTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.ui = QtGui.QWidget()
        self.ui.setWindowTitle("Attachement Support")
        layout = QtGui.QVBoxLayout(self.ui)

        items = []
        for o in obj.Document.Objects:
            if hasattr(o, "Proxy") and isinstance(o.Proxy, BaptOrigin.Origin):
                items.append((o.Label, o))
        self.comboBox = QtGui.QComboBox()
        for label, obj in items:
            self.comboBox.addItem(label, obj)
        # init comboBox with current value
        if hasattr(obj, "AttachmentSupport") and obj.AttachmentSupport:
            index = self.comboBox.findData(obj.AttachmentSupport)
            if index >= 0:
                self.comboBox.setCurrentIndex(index)
        layout.addWidget(self.comboBox)
        self.form = self.ui

        # add listener for comboBox changes
        self.comboBox.currentIndexChanged.connect(lambda index: self.onComboBoxChanged(index))

    def onComboBoxChanged(self, index):
        App.Console.PrintMessage("ComboBox changed to index: {}\n".format(index))
        obj = self.comboBox.itemData(index)
        if obj:
            self.obj.AttachmentSupport = obj

    def getForm(self):
        return self.form
