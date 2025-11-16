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
        
        ui1 = QtGui.QWidget()
        ui1.setWindowTitle("Edit CAM Project")
        # Créer l'interface utilisateur
        ui2 = PostProcessorTaskPanel(obj)

        self.form = [ui1, ui2.getForm()]

        layout = QtGui.QVBoxLayout(self.form[0])
        
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
        
        # Stock mode : choix entre "box" et "Extend Bounding Box"
        self.stockMode = QtGui.QComboBox()
        self.stockMode.addItems(["box", "Extend Bounding Box"])
        stockLayout.addRow("Stock Mode:", self.stockMode)

        if hasattr(self.stock, "Length"):
            self.stockMode.setCurrentText("box")
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

        elif hasattr(self.stock, "XNeg"):
            self.stockMode.setCurrentText("Extend Bounding Box")

            # Ici, on pourrait ajouter des champs pour XNeg, YNeg, ZNeg, XPos, YPos, ZPos si nécessaire
            self.stockXNeg = QtGui.QDoubleSpinBox()
            self.stockXNeg.setDecimals(3)
            self.stockXNeg.setSuffix(" mm")
            stockLayout.addRow("X Negative Extension:", self.stockXNeg)

            self.stockXPos = QtGui.QDoubleSpinBox()
            self.stockXPos.setDecimals(3)
            self.stockXPos.setSuffix(" mm")
            stockLayout.addRow("X Positive Extension:", self.stockXPos)

            self.stockYNeg = QtGui.QDoubleSpinBox()
            self.stockYNeg.setDecimals(3)
            self.stockYNeg.setSuffix(" mm")
            stockLayout.addRow("Y Negative Extension:", self.stockYNeg)

            self.stockYPos = QtGui.QDoubleSpinBox()
            self.stockYPos.setDecimals(3)
            self.stockYPos.setSuffix(" mm")
            stockLayout.addRow("Y Positive Extension:", self.stockYPos)

            self.stockZNeg = QtGui.QDoubleSpinBox()
            self.stockZNeg.setDecimals(3)
            self.stockZNeg.setSuffix(" mm")
            stockLayout.addRow("Z Negative Extension:", self.stockZNeg)

            self.stockZPos = QtGui.QDoubleSpinBox()
            self.stockZPos.setDecimals(3)
            self.stockZPos.setSuffix(" mm") 
            stockLayout.addRow("Z Positive Extension:", self.stockZPos)

            stockGroup.setLayout(stockLayout)
            layout.addWidget(stockGroup)
        
        
        # Ajouter un espace extensible en bas
        layout.addStretch()
        
        # Initialiser les valeurs
        self.workPlane.setCurrentText(obj.WorkPlane)
        if obj.Model:
            self.model.setCurrentText(obj.Model.Name)

        if self.stock:
            if hasattr(self.stock, "Length"):
                self.stockLength.setValue(self.stock.Length)
                self.stockWidth.setValue(self.stock.Width)
                self.stockHeight.setValue(self.stock.Height)
                self.stockOriginX.setValue(self.stock.Placement.Base.x)
                self.stockOriginY.setValue(self.stock.Placement.Base.y)
                self.stockOriginZ.setValue(self.stock.Placement.Base.z)
            elif hasattr(self.stock, "XNeg"):
                self.stockXNeg.setValue(self.stock.XNeg)
                self.stockXPos.setValue(self.stock.XPos)
                self.stockYNeg.setValue(self.stock.YNeg)
                self.stockYPos.setValue(self.stock.YPos)
                self.stockZNeg.setValue(self.stock.ZNeg)
                self.stockZPos.setValue(self.stock.ZPos)
        
        # Connecter les signaux
        self.workPlane.currentIndexChanged.connect(lambda: self.updateVisual())
        self.model.currentIndexChanged.connect(lambda: self.updateVisual())
        self.stockMode.currentIndexChanged.connect(lambda: self.stockModeChanged())
        if hasattr(self.stock, "Length"):
            self.stockOriginX.valueChanged.connect(lambda: self.updateVisual())
            self.stockOriginY.valueChanged.connect(lambda: self.updateVisual())
            self.stockOriginZ.valueChanged.connect(lambda: self.updateVisual())
            self.stockHeight.valueChanged.connect(lambda: self.updateVisual())
            self.stockWidth.valueChanged.connect(lambda: self.updateVisual())
            self.stockLength.valueChanged.connect(lambda: self.updateVisual())
        elif hasattr(self.stock, "XNeg"):
            self.stockXNeg.valueChanged.connect(lambda: self.updateVisual())
            self.stockXPos.valueChanged.connect(lambda: self.updateVisual())
            self.stockYNeg.valueChanged.connect(lambda: self.updateVisual())
            self.stockYPos.valueChanged.connect(lambda: self.updateVisual())
            self.stockZNeg.valueChanged.connect(lambda: self.updateVisual())
            self.stockZPos.valueChanged.connect(lambda: self.updateVisual())

    def stockModeChanged(self):
        """Gérer le changement de mode de stock"""
        mode = self.stockMode.currentText()
        if mode == "box":
            # supprimer les propriétés Xneg... de l'objet stock et ajouter Length, Width, Height
            if self.obj.Stock.hasProperty("XNeg"):
                for prop in ["XNeg", "YNeg", "ZNeg", "XPos", "YPos", "ZPos"]:
                    self.obj.Stock.removeProperty(prop)
            if not self.obj.Stock.hasProperty("Length"):
                self.obj.Stock.addProperty("App::PropertyLength", "Length", "Stock", "Length of the stock").Length = self.obj.Stock.boundBox.XLength
                self.obj.Stock.addProperty("App::PropertyLength", "Width", "Stock", "Width of the stock").Width = self.obj.Stock.boundBox.YLength
                self.obj.Stock.addProperty("App::PropertyLength", "Height", "Stock", "Height of the stock").Height = self.obj.Stock.boundBox.ZLength
                self.obj.Stock.Placement = App.Placement(App.Vector(self.obj.Stock.boundBox.XMin, self.obj.Stock.boundBox.YMin, self.obj.Stock.boundBox.ZMin), App.Rotation(App.Vector(0,0,1),0))
        elif mode == "Extend Bounding Box":
            # supprimer les propriétés Length, Width, Height de l'objet stock et ajouter Xneg...
            if self.obj.Stock.hasProperty("Length"):
                for prop in ["Length", "Width", "Height"]:
                    self.obj.Stock.removeProperty(prop)
            if not self.obj.Stock.hasProperty("XNeg"):
                self.obj.Stock.addProperty("App::PropertyLength", "XNeg", "Stock", "Negative X extension").XNeg = 1
                self.obj.Stock.addProperty("App::PropertyLength", "YNeg", "Stock", "Negative Y extension").YNeg = 1
                self.obj.Stock.addProperty("App::PropertyLength", "ZNeg", "Stock", "Negative Z extension").ZNeg = 1
                self.obj.Stock.addProperty("App::PropertyLength", "XPos", "Stock", "Positive X extension").XPos = 1
                self.obj.Stock.addProperty("App::PropertyLength", "YPos", "Stock", "Positive Y extension").YPos = 1
                self.obj.Stock.addProperty("App::PropertyLength", "ZPos", "Stock", "Positive Z extension").ZPos = 1
        self.updateVisual()

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
            if hasattr(self.stock, "XNeg"):
                self.stock.XNeg = self.stockXNeg.value()
                self.stock.XPos = self.stockXPos.value()
                self.stock.YNeg = self.stockYNeg.value()
                self.stock.YPos = self.stockYPos.value()
                self.stock.ZNeg = self.stockZNeg.value()
                self.stock.ZPos = self.stockZPos.value()
            elif hasattr(self.stock, "Length"):
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
        return (QtGui.QDialogButtonBox.Ok |
                  QtGui.QDialogButtonBox.Cancel)


class PostProcessorTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Edit Post Processor Settings")
        layout = QtGui.QVBoxLayout(self.form)
        
        label = QtGui.QLabel("Post Processor specific settings can be configured here.")
        layout.addWidget(label)
                # Liste des PostProcessors disponibles
        self.postProcessors = ["Siemens828", "ITnc530", "Fanuc"] #TODO : récupérer dynamiquement la liste des postprocessors disponibles

        
        # Groupe PostProcessors
        postProcGroup = QtGui.QGroupBox("PostProcessors")
        postProcLayout = QtGui.QVBoxLayout()
        
        # Table des postprocessors
        self.postProcTable = QtGui.QTableWidget()
        self.postProcTable.setColumnCount(2)
        self.postProcTable.setHorizontalHeaderLabels(["Sélectionné", "PostProcessor"])
        self.postProcTable.horizontalHeader().setStretchLastSection(True)
        self.postProcTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.postProcTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        
        # Remplir le tableau avec les postprocessors
        self.postProcTable.setRowCount(len(self.postProcessors))
        for i, postProc in enumerate(self.postProcessors):
            # Checkbox dans la première colonne
            checkBox = QtGui.QCheckBox()
            # Stocker le nom du postprocessor comme propriété
            checkBox.setProperty("postProcessorName", postProc)
            checkBox.setChecked(postProc in self.obj.PostProcessor)
            checkBox.stateChanged.connect(lambda state, name=postProc: self.postProcessorSelectionChanged(state, name))
            
            # Widget container pour centrer la checkbox
            checkWidget = QtGui.QWidget()
            checkLayout = QtGui.QHBoxLayout(checkWidget)
            checkLayout.addWidget(checkBox)
            checkLayout.setAlignment(QtCore.Qt.AlignCenter)
            checkLayout.setContentsMargins(0, 0, 0, 0)
            
            self.postProcTable.setCellWidget(i, 0, checkWidget)
            
            # Nom du postprocessor dans la deuxième colonne
            nameItem = QtGui.QTableWidgetItem(postProc)
            nameItem.setFlags(nameItem.flags() & ~QtCore.Qt.ItemIsEditable)
            self.postProcTable.setItem(i, 1, nameItem)
        
        # Ajuster la largeur des colonnes
        self.postProcTable.setColumnWidth(0, 80)
        
        postProcLayout.addWidget(self.postProcTable)
        postProcGroup.setLayout(postProcLayout)
        layout.addWidget(postProcGroup)
        
        # Ajouter un espace extensible en bas
        layout.addStretch()

        layout.addStretch()
    
    def getForm(self):
        return self.form
    
    def postProcessorSelectionChanged(self, state, PostProcessorName):
        """Appelé quand une checkbox de postprocessor est modifiée"""
        isChecked = (state == QtCore.Qt.Checked)

        App.Console.PrintMessage(f"PostProcessor '{PostProcessorName}' {'sélectionné' if isChecked else 'désélectionné'}\n")

        # Mettre à jour la propriété du projet CAM si elle existe
        if hasattr(self.obj, "PostProcessor"):
            selected = list(self.obj.PostProcessor)
            if isChecked and PostProcessorName not in selected:
                selected.append(PostProcessorName)
            elif not isChecked and PostProcessorName in selected:
                selected.remove(PostProcessorName)
            self.obj.PostProcessor = list(selected)
        
