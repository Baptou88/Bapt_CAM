import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class CamProjectTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Edit CAM Project")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe Project Setup
        setupGroup = QtGui.QGroupBox("Project Setup")
        setupLayout = QtGui.QFormLayout()
        
        # Origin
        self.originX = QtGui.QDoubleSpinBox()
        self.originY = QtGui.QDoubleSpinBox()
        self.originZ = QtGui.QDoubleSpinBox()
        for spinBox in [self.originX, self.originY, self.originZ]:
            spinBox.setRange(-10000, 10000)
            spinBox.setDecimals(2)
        originLayout = QtGui.QHBoxLayout()
        originLayout.addWidget(self.originX)
        originLayout.addWidget(self.originY)
        originLayout.addWidget(self.originZ)
        setupLayout.addRow("Origin (X,Y,Z):", originLayout)
        
        # Work Plane
        self.workPlane = QtGui.QComboBox()
        self.workPlane.addItems(["XY", "XZ", "YZ"])
        setupLayout.addRow("Work Plane:", self.workPlane)
        
        setupGroup.setLayout(setupLayout)
        layout.addWidget(setupGroup)
        
        # Groupe Stock
        stockGroup = QtGui.QGroupBox("Stock Dimensions")
        stockLayout = QtGui.QFormLayout()
        
        # Length
        self.stockLength = QtGui.QDoubleSpinBox()
        self.stockLength.setRange(0, 10000)
        self.stockLength.setDecimals(2)
        self.stockLength.setSuffix(" mm")
        stockLayout.addRow("Length:", self.stockLength)
        
        # Width
        self.stockWidth = QtGui.QDoubleSpinBox()
        self.stockWidth.setRange(0, 10000)
        self.stockWidth.setDecimals(2)
        self.stockWidth.setSuffix(" mm")
        stockLayout.addRow("Width:", self.stockWidth)
        
        # Height
        self.stockHeight = QtGui.QDoubleSpinBox()
        self.stockHeight.setRange(0, 10000)
        self.stockHeight.setDecimals(2)
        self.stockHeight.setSuffix(" mm")
        stockLayout.addRow("Height:", self.stockHeight)
        
        stockGroup.setLayout(stockLayout)
        layout.addWidget(stockGroup)
        
        # Ajouter un espace extensible en bas
        layout.addStretch()
        
        # Initialiser les valeurs
        self.originX.setValue(obj.Origin.x)
        self.originY.setValue(obj.Origin.y)
        self.originZ.setValue(obj.Origin.z)
        self.workPlane.setCurrentText(obj.WorkPlane)
        self.stockLength.setValue(obj.StockLength)
        self.stockWidth.setValue(obj.StockWidth)
        self.stockHeight.setValue(obj.StockHeight)

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour l'origine
        self.obj.Origin = App.Vector(self.originX.value(),
                                   self.originY.value(),
                                   self.originZ.value())
        
        # Mettre à jour le plan de travail
        self.obj.WorkPlane = self.workPlane.currentText()
        
        # Mettre à jour les dimensions du stock
        self.obj.StockLength = self.stockLength.value()
        self.obj.StockWidth = self.stockWidth.value()
        self.obj.StockHeight = self.stockHeight.value()
        
        # Recompute
        self.obj.Document.recompute()
        
        # Fermer la tâche
        Gui.Control.closeDialog()
        return True
    
    def reject(self):
        """Appelé quand l'utilisateur clique sur Cancel"""
        Gui.Control.closeDialog()
        return False

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return int(QtGui.QDialogButtonBox.Ok |
                  QtGui.QDialogButtonBox.Cancel)
