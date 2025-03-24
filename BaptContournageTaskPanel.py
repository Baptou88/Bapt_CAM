import os
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class ContournageTaskPanel:
    """Panneau de tâche pour éditer les paramètres de contournage"""
    
    def __init__(self, obj):
        """Initialise le panneau avec l'objet de contournage"""
        self.obj = obj
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Paramètres de contournage")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe Outil
        toolGroup = QtGui.QGroupBox("Paramètres d'outil")
        toolLayout = QtGui.QFormLayout()
        
        # Diamètre de l'outil
        self.toolDiameter = QtGui.QDoubleSpinBox()
        self.toolDiameter.setRange(0.1, 100)
        self.toolDiameter.setDecimals(2)
        self.toolDiameter.setSuffix(" mm")
        self.toolDiameter.setValue(obj.ToolDiameter)
        toolLayout.addRow("Diamètre de l'outil:", self.toolDiameter)
        
        toolGroup.setLayout(toolLayout)
        layout.addWidget(toolGroup)
        
        # Groupe Coupe
        cutGroup = QtGui.QGroupBox("Paramètres de coupe")
        cutLayout = QtGui.QFormLayout()
        
        # Profondeur de coupe
        self.cutDepth = QtGui.QDoubleSpinBox()
        self.cutDepth.setRange(0.1, 100)
        self.cutDepth.setDecimals(2)
        self.cutDepth.setSuffix(" mm")
        self.cutDepth.setValue(obj.CutDepth)
        cutLayout.addRow("Profondeur de coupe:", self.cutDepth)
        
        # Profondeur par passe
        self.stepDown = QtGui.QDoubleSpinBox()
        self.stepDown.setRange(0.1, 100)
        self.stepDown.setDecimals(2)
        self.stepDown.setSuffix(" mm")
        self.stepDown.setValue(obj.StepDown)
        cutLayout.addRow("Profondeur par passe:", self.stepDown)
        
        cutGroup.setLayout(cutLayout)
        layout.addWidget(cutGroup)
        
        # Groupe Direction
        directionGroup = QtGui.QGroupBox("Direction d'usinage")
        directionLayout = QtGui.QFormLayout()
        
        # Direction
        self.direction = QtGui.QComboBox()
        self.direction.addItems(["Climb", "Conventional"])
        self.direction.setCurrentText(obj.Direction)
        directionLayout.addRow("Direction:", self.direction)
        
        directionGroup.setLayout(directionLayout)
        layout.addWidget(directionGroup)
        
        # Groupe Affichage
        displayGroup = QtGui.QGroupBox("Affichage")
        displayLayout = QtGui.QFormLayout()
        
        # Afficher la trajectoire
        self.showToolPath = QtGui.QCheckBox()
        self.showToolPath.setChecked(obj.ViewObject.ShowToolPath)
        displayLayout.addRow("Afficher la trajectoire:", self.showToolPath)
        
        # Couleur de la trajectoire
        self.pathColor = QtGui.QPushButton()
        self.pathColor.setAutoFillBackground(True)
        color = obj.ViewObject.PathColor
        self.pathColor.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)})")
        self.pathColor.clicked.connect(self.chooseColor)
        displayLayout.addRow("Couleur de la trajectoire:", self.pathColor)
        
        # Épaisseur de la trajectoire
        self.pathWidth = QtGui.QDoubleSpinBox()
        self.pathWidth.setRange(0.1, 10)
        self.pathWidth.setDecimals(1)
        self.pathWidth.setValue(obj.ViewObject.PathWidth)
        displayLayout.addRow("Épaisseur de la trajectoire:", self.pathWidth)
        
        displayGroup.setLayout(displayLayout)
        layout.addWidget(displayGroup)
        
        # Informations sur le contour
        infoGroup = QtGui.QGroupBox("Informations sur le contour")
        infoLayout = QtGui.QFormLayout()
        
        # Récupérer la géométrie du contour
        contour_name = obj.ContourGeometryName
        contour = None
        for o in App.ActiveDocument.Objects:
            if o.Name == contour_name:
                contour = o
                break
        
        # Afficher si le contour est fermé
        is_closed_text = "Oui" if (contour and hasattr(contour, "IsClosed") and contour.IsClosed) else "Non"
        self.isClosedLabel = QtGui.QLabel(is_closed_text)
        infoLayout.addRow("Contour fermé:", self.isClosedLabel)
        
        # Afficher la direction du contour
        direction_text = contour.Direction if (contour and hasattr(contour, "Direction")) else "Inconnue"
        self.contourDirectionLabel = QtGui.QLabel(direction_text)
        infoLayout.addRow("Direction du contour:", self.contourDirectionLabel)
        
        infoGroup.setLayout(infoLayout)
        layout.addWidget(infoGroup)
        
        # Connecter les signaux
        self.toolDiameter.valueChanged.connect(self.updateContournage)
        self.cutDepth.valueChanged.connect(self.updateContournage)
        self.stepDown.valueChanged.connect(self.updateContournage)
        self.direction.currentTextChanged.connect(self.updateContournage)
        self.showToolPath.stateChanged.connect(self.updateDisplay)
        self.pathWidth.valueChanged.connect(self.updateDisplay)
    
    def chooseColor(self):
        """Ouvre un sélecteur de couleur"""
        color = QtGui.QColorDialog.getColor()
        if color.isValid():
            self.pathColor.setStyleSheet(f"background-color: {color.name()}")
            # Convertir la couleur en tuple (r, g, b) avec des valeurs entre 0 et 1
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
            self.obj.ViewObject.PathColor = (r, g, b)
            self.updateDisplay()
    
    def updateContournage(self):
        """Met à jour les paramètres de contournage"""
        self.obj.ToolDiameter = self.toolDiameter.value()
        self.obj.CutDepth = self.cutDepth.value()
        self.obj.StepDown = self.stepDown.value()
        self.obj.Direction = self.direction.currentText()
        
        # Recalculer la trajectoire
        self.obj.Proxy.execute(self.obj)
        
        # Mettre à jour la vue
        Gui.ActiveDocument.update()
    
    def updateDisplay(self):
        """Met à jour les paramètres d'affichage"""
        self.obj.ViewObject.ShowToolPath = self.showToolPath.isChecked()
        self.obj.ViewObject.PathWidth = self.pathWidth.value()
        
        # Mettre à jour la vue
        Gui.ActiveDocument.update()
    
    def accept(self):
        """Appelé lorsque l'utilisateur clique sur OK"""
        self.updateContournage()
        self.updateDisplay()
        Gui.Control.closeDialog()
        return True
    
    def reject(self):
        """Appelé lorsque l'utilisateur clique sur Annuler"""
        Gui.Control.closeDialog()
        return True
