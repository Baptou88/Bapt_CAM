import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from utils import PointSelectionObserver


class CamProjectTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        
        # Obtenir l'objet Stock
        self.stock = self.getStockObject(obj)
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Edit CAM Project")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe Project Setup
        setupGroup = QtGui.QGroupBox("Project Setup")
        setupLayout = QtGui.QFormLayout()
        
        # Work Plane
        self.workPlane = QtGui.QComboBox()
        self.workPlane.addItems(["XY", "XZ", "YZ"])
        setupLayout.addRow("Work Plane:", self.workPlane)
        
        setupGroup.setLayout(setupLayout)
        layout.addWidget(setupGroup)
        
        # Groupe Model
        modelGroup = QtGui.QGroupBox("Model")
        modelLayout = QtGui.QFormLayout()
        
        # Model
        self.model = QtGui.QComboBox()
        self.model.addItems( [obj.Name for obj in App.ActiveDocument.Objects if obj.isDerivedFrom("Part::Feature")])
        modelLayout.addRow("Model:", self.model)
        modelGroup.setLayout(modelLayout)
        layout.addWidget(modelGroup)

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
        
        # Stock Origin
        self.stockOriginX = QtGui.QDoubleSpinBox()
        self.stockOriginY = QtGui.QDoubleSpinBox()
        self.stockOriginZ = QtGui.QDoubleSpinBox()
        for spinBox in [self.stockOriginX, self.stockOriginY, self.stockOriginZ]:
            spinBox.setRange(-10000, 10000)
            spinBox.setDecimals(2)
        
        stockOriginLayout = QtGui.QHBoxLayout()
        stockOriginLayout.addWidget(self.stockOriginX)
        stockOriginLayout.addWidget(self.stockOriginY)
        stockOriginLayout.addWidget(self.stockOriginZ)
        stockLayout.addRow("Stock Origin (X,Y,Z):", stockOriginLayout)

        self.clickOnPartBtn = QtGui.QPushButton("Click on Part")
        self.clickOnPartBtn.clicked.connect(self.clickOnPart)
        stockLayout.addRow(self.clickOnPartBtn)
        
        stockGroup.setLayout(stockLayout)
        layout.addWidget(stockGroup)
        
        # Ajouter un espace extensible en bas
        layout.addStretch()
        
        # Initialiser les valeurs
        self.workPlane.setCurrentText(obj.WorkPlane)
        self.model.setCurrentText(obj.Model.Name)
        if self.stock:
            self.stockLength.setValue(self.stock.Length)
            self.stockWidth.setValue(self.stock.Width)
            self.stockHeight.setValue(self.stock.Height)
            self.stockOriginX.setValue(self.stock.Placement.Base.x)
            self.stockOriginY.setValue(self.stock.Placement.Base.y)
            self.stockOriginZ.setValue(self.stock.Placement.Base.z)
        
        # Connecter les signaux
        self.workPlane.currentIndexChanged.connect(lambda: self.updateVisual())
        self.model.currentIndexChanged.connect(lambda: self.updateVisual())
        self.stockOriginX.valueChanged.connect(lambda: self.updateVisual())
        self.stockOriginY.valueChanged.connect(lambda: self.updateVisual())
        self.stockOriginZ.valueChanged.connect(lambda: self.updateVisual())
        self.stockHeight.valueChanged.connect(lambda: self.updateVisual())
        self.stockWidth.valueChanged.connect(lambda: self.updateVisual())
        self.stockLength.valueChanged.connect(lambda: self.updateVisual())

    def getStockObject(self, obj):
        """Obtenir l'objet Stock à partir du projet CAM"""
        if hasattr(obj, "Group"):
            for child in obj.Group:
                if child.Name.startswith("Stock"):
                    return child
        return None

    def clickOnPart(self):
        """Appelé quand l'utilisateur clique sur le bouton Click on Part"""
        # Changer le texte du bouton pour indiquer que l'on attend un clic
        self.clickOnPartBtn.setText("Cliquez sur un point...")
        self.clickOnPartBtn.setEnabled(False)
        
        # Créer et activer l'observer
        self.observer = PointSelectionObserver.PointSelectionObserver(self.pointSelected)
        self.observer.enable()

    def pointSelected(self, point):
        """Appelé quand l'utilisateur a cliqué sur un point"""
        # Mettre à jour les coordonnées du stock origin
        self.stockOriginX.setValue(point.x)
        self.stockOriginY.setValue(point.y)
        self.stockOriginZ.setValue(point.z)
        
        # Mettre à jour la représentation visuelle
        self.updateVisual()
        
        # Remettre le bouton dans son état initial
        self.clickOnPartBtn.setText("Click on Part")
        self.clickOnPartBtn.setEnabled(True)

    def updateVisual(self):
        """Met à jour la représentation visuelle"""
        # Mettre à jour les propriétés du projet
        self.obj.WorkPlane = self.workPlane.currentText()
        # Mettre à jour les propriétés du model
        for obj in App.ActiveDocument.Objects:
            if obj.Name == self.model.currentText():
                self.obj.Model = obj
                break
        # Mettre à jour les propriétés du stock
        if self.stock:
            self.stock.Length = self.stockLength.value()
            self.stock.Width = self.stockWidth.value()
            self.stock.Height = self.stockHeight.value()
            self.stock.Placement = App.Placement(App.Vector(self.stockOriginX.value(), self.stockOriginY.value(), self.stockOriginZ.value()), App.Rotation(App.Vector(0,0,1),0))
            self.stock.WorkPlane = self.workPlane.currentText()
        
        # Recomputer
        self.obj.Document.recompute()

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        
        self.updateVisual()
        
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
