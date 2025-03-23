import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class ContourTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Éditer le contour")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe Contour
        contourGroup = QtGui.QGroupBox("Contour")
        contourLayout = QtGui.QFormLayout()
        
        # Boutons pour la sélection des arêtes
        selectionLayout = QtGui.QHBoxLayout()
        
        self.selectEdgesButton = QtGui.QPushButton("Sélectionner les arêtes")
        self.selectEdgesButton.clicked.connect(self.selectEdges)
        selectionLayout.addWidget(self.selectEdgesButton)
        
        self.confirmSelectionButton = QtGui.QPushButton("Confirmer la sélection")
        self.confirmSelectionButton.clicked.connect(self.confirmSelection)
        self.confirmSelectionButton.setEnabled(False)  # Désactivé par défaut
        selectionLayout.addWidget(self.confirmSelectionButton)
        
        contourLayout.addRow("Arêtes:", selectionLayout)
        
        # Affichage des arêtes sélectionnées
        self.edgesLabel = QtGui.QLabel("Aucune arête sélectionnée")
        contourLayout.addRow("", self.edgesLabel)
        
        # Offset
        self.offset = QtGui.QDoubleSpinBox()
        self.offset.setRange(-100, 100)
        self.offset.setDecimals(2)
        self.offset.setSuffix(" mm")
        self.offset.setValue(obj.Offset)
        contourLayout.addRow("Décalage:", self.offset)
        
        # Direction
        self.direction = QtGui.QComboBox()
        self.direction.addItems(["Horaire", "Anti-horaire"])
        self.direction.setCurrentText(obj.Direction)
        contourLayout.addRow("Direction:", self.direction)
        
        contourGroup.setLayout(contourLayout)
        layout.addWidget(contourGroup)
        
        # Groupe Outil
        toolGroup = QtGui.QGroupBox("Outil")
        toolLayout = QtGui.QFormLayout()
        
        # Diamètre de l'outil
        self.toolDiameter = QtGui.QDoubleSpinBox()
        self.toolDiameter.setRange(0.1, 100)
        self.toolDiameter.setDecimals(2)
        self.toolDiameter.setSuffix(" mm")
        self.toolDiameter.setValue(obj.ToolDiameter)
        toolLayout.addRow("Diamètre:", self.toolDiameter)
        
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
        cutLayout.addRow("Profondeur:", self.cutDepth)
        
        # Profondeur par passe
        self.stepDown = QtGui.QDoubleSpinBox()
        self.stepDown.setRange(0.1, 100)
        self.stepDown.setDecimals(2)
        self.stepDown.setSuffix(" mm")
        self.stepDown.setValue(obj.StepDown)
        cutLayout.addRow("Passe:", self.stepDown)
        
        cutGroup.setLayout(cutLayout)
        layout.addWidget(cutGroup)
        
        # Mettre à jour l'affichage des arêtes sélectionnées
        self.updateEdgesLabel()
        
        # Connecter les signaux pour l'actualisation en temps réel
        self.offset.valueChanged.connect(self.updateContour)
        self.direction.currentTextChanged.connect(self.updateContour)
        self.toolDiameter.valueChanged.connect(self.updateContour)
        
        # Variable pour suivre l'état de sélection
        self.selectionMode = False
        
    def updateEdgesLabel(self):
        """Met à jour l'affichage des arêtes sélectionnées"""
        if not hasattr(self.obj, "Edges") or not self.obj.Edges:
            self.edgesLabel.setText("Aucune arête sélectionnée")
            return
        
        count = 0
        for sub in self.obj.Edges:
            count += len(sub[1])
        
        self.edgesLabel.setText(f"{count} arête(s) sélectionnée(s)")
    
    def selectEdges(self):
        """Permet à l'utilisateur de sélectionner des arêtes"""
        # Activer le mode de sélection
        self.selectionMode = True
        self.confirmSelectionButton.setEnabled(True)
        
        # Demander à l'utilisateur de sélectionner des arêtes
        App.Console.PrintMessage("Sélectionnez les arêtes pour le contour, puis cliquez sur 'Confirmer la sélection'.\n")
        
        # Définir le mode de sélection pour les arêtes uniquement
        Gui.Selection.clearSelection()
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Edge")
        
        # Changer le texte du bouton
        self.selectEdgesButton.setText("Annuler la sélection")
        self.selectEdgesButton.clicked.disconnect()
        self.selectEdgesButton.clicked.connect(self.cancelSelection)
    
    def cancelSelection(self):
        """Annule le mode de sélection"""
        # Désactiver le mode de sélection
        self.selectionMode = False
        self.confirmSelectionButton.setEnabled(False)
        
        # Désactiver le mode de sélection
        Gui.Selection.removeSelectionGate()
        
        # Restaurer le bouton
        self.selectEdgesButton.setText("Sélectionner les arêtes")
        self.selectEdgesButton.clicked.disconnect()
        self.selectEdgesButton.clicked.connect(self.selectEdges)
        
        App.Console.PrintMessage("Sélection annulée.\n")
    
    def confirmSelection(self):
        """Confirme la sélection actuelle"""
        # Récupérer la sélection
        selection = Gui.Selection.getSelectionEx()
        
        App.Console.PrintMessage(f"Confirmation de la sélection: {len(selection)} objets sélectionnés.\n")
        
        if not selection:
            App.Console.PrintMessage("Aucune arête sélectionnée.\n")
            return
        
        # Mettre à jour les arêtes sélectionnées
        edges = []
        for sel in selection:
            if sel.SubElementNames:
                App.Console.PrintMessage(f"Objet: {sel.ObjectName}, Sous-éléments: {sel.SubElementNames}\n")
                edges.append((sel.Object, sel.SubElementNames))
        
        # Mettre à jour l'objet
        self.obj.Edges = edges
        
        # Mettre à jour l'affichage
        self.updateEdgesLabel()
        
        # Désactiver le mode de sélection
        self.selectionMode = False
        self.confirmSelectionButton.setEnabled(False)
        Gui.Selection.removeSelectionGate()
        
        # Restaurer le bouton
        self.selectEdgesButton.setText("Sélectionner les arêtes")
        self.selectEdgesButton.clicked.disconnect()
        self.selectEdgesButton.clicked.connect(self.selectEdges)
        
        # Mettre à jour la forme
        self.obj.Document.recompute()
        
        App.Console.PrintMessage("Sélection confirmée.\n")
    
    def updateContour(self):
        """Met à jour le contour en fonction des paramètres"""
        self.obj.Offset = self.offset.value()
        self.obj.Direction = self.direction.currentText()
        self.obj.ToolDiameter = self.toolDiameter.value()
        self.obj.Document.recompute()
    
    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour toutes les propriétés
        self.obj.Offset = self.offset.value()
        self.obj.Direction = self.direction.currentText()
        self.obj.ToolDiameter = self.toolDiameter.value()
        self.obj.CutDepth = self.cutDepth.value()
        self.obj.StepDown = self.stepDown.value()
        
        # Recomputer
        self.obj.Document.recompute()
        
        # Fermer la tâche
        Gui.Control.closeDialog()
        return True
    
    def reject(self):
        """Appelé quand l'utilisateur clique sur Cancel"""
        # Désactiver le mode de sélection si actif
        if self.selectionMode:
            Gui.Selection.removeSelectionGate()
        
        Gui.Control.closeDialog()
        return False
    
    def getStandardButtons(self):
        """Définir les boutons standard"""
        return int(QtGui.QDialogButtonBox.Ok |
                  QtGui.QDialogButtonBox.Cancel)
