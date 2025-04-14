import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class PointSelectionObserver:
    def __init__(self, callback):
        self.callback = callback
        self.active = False
        
    def enable(self):
        """Activer l'observer"""
        self.active = True
        Gui.Selection.addObserver(self)
        App.Console.PrintMessage("Observer activé. Cliquez sur un point de la pièce.\n")
        
    def disable(self):
        """Désactiver l'observer"""
        self.active = False
        Gui.Selection.removeObserver(self)
        App.Console.PrintMessage("Observer désactivé.\n")
        
    def addSelection(self, document, object, element, position):
        """Appelé quand l'utilisateur sélectionne quelque chose"""
        if not self.active:
            return
            
        # Récupérer les coordonnées du point sélectionné
        point = App.Vector(position[0], position[1], position[2])
        App.Console.PrintMessage(f"Point sélectionné: {point.x}, {point.y}, {point.z}\n")
        
        # Appeler le callback avec le point
        self.callback(point)
        
        # Désactiver l'observer après la sélection
        self.disable()

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
        self.originX.setValue(obj.Origin.x)
        self.originY.setValue(obj.Origin.y)
        self.originZ.setValue(obj.Origin.z)
        self.workPlane.setCurrentText(obj.WorkPlane)
        
        if self.stock:
            self.stockLength.setValue(self.stock.Length)
            self.stockWidth.setValue(self.stock.Width)
            self.stockHeight.setValue(self.stock.Height)
            self.stockOriginX.setValue(self.stock.Origin.x)
            self.stockOriginY.setValue(self.stock.Origin.y)
            self.stockOriginZ.setValue(self.stock.Origin.z)
        
        # Connecter les signaux
        self.originX.valueChanged.connect(lambda: self.updateVisual())
        self.originY.valueChanged.connect(lambda: self.updateVisual())
        self.originZ.valueChanged.connect(lambda: self.updateVisual())
        self.workPlane.currentIndexChanged.connect(lambda: self.updateVisual())
        
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
        self.observer = PointSelectionObserver(self.pointSelected)
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
        self.obj.Origin = App.Vector(self.originX.value(), self.originY.value(), self.originZ.value())
        self.obj.WorkPlane = self.workPlane.currentText()
        
        # Mettre à jour les propriétés du stock
        if self.stock:
            self.stock.Length = self.stockLength.value()
            self.stock.Width = self.stockWidth.value()
            self.stock.Height = self.stockHeight.value()
            self.stock.Origin = App.Vector(self.stockOriginX.value(), self.stockOriginY.value(), self.stockOriginZ.value())
            self.stock.WorkPlane = self.workPlane.currentText()
        
        # Recomputer
        self.obj.Document.recompute()

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour l'origine et le plan de travail du projet
        self.obj.Origin = App.Vector(self.originX.value(), self.originY.value(), self.originZ.value())
        self.obj.WorkPlane = self.workPlane.currentText()
        
        # Mettre à jour les propriétés du stock
        if self.stock:
            self.stock.Length = self.stockLength.value()
            self.stock.Width = self.stockWidth.value()
            self.stock.Height = self.stockHeight.value()
            self.stock.Origin = App.Vector(self.stockOriginX.value(), self.stockOriginY.value(), self.stockOriginZ.value())
            self.stock.WorkPlane = self.workPlane.currentText()
        
        # Recomputer
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
