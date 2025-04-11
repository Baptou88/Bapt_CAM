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
        
        self.confirmSelectionButton.setEnabled(False)  # Désactivé par défaut
        selectionLayout.addWidget(self.confirmSelectionButton)
        
        contourLayout.addRow("Arêtes:", selectionLayout)
        
        # Propriété IsClosed
        self.isClosedLabel = QtGui.QLabel("Contour fermé: ")
        contourLayout.addRow("", self.isClosedLabel)
        
        # Affichage des arêtes sélectionnées
        self.edgesLabel = QtGui.QLabel("Aucune arête sélectionnée")
        contourLayout.addRow("", self.edgesLabel)
        
        # Tableau des éléments du contour
        self.edgesTable = QtGui.QTableWidget()
        self.edgesTable.setColumnCount(3)
        self.edgesTable.setHorizontalHeaderLabels(["Objet", "Élément", "Type"])
        self.edgesTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.edgesTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.edgesTable.horizontalHeader().setStretchLastSection(True)
        self.edgesTable.verticalHeader().setVisible(False)
        self.edgesTable.setMinimumHeight(150)
        contourLayout.addRow("Éléments:", self.edgesTable)
    
        
        # Direction
        self.direction = QtGui.QComboBox()
        self.direction.addItems(["Horaire", "Anti-horaire"])
        self.direction.setCurrentText(obj.Direction)
        contourLayout.addRow("Direction:", self.direction)
        
        contourGroup.setLayout(contourLayout)
        layout.addWidget(contourGroup)
        
        
        # Groupe Coupe
        contourGroup = QtGui.QGroupBox("Paramètres du contour")
        contourLayout = QtGui.QFormLayout()
        
        # Hauteur de référence
        self.Zref = QtGui.QDoubleSpinBox()
        self.Zref.setRange(0.1, 100)
        self.Zref.setDecimals(2)
        self.Zref.setSuffix(" mm")
        self.Zref.setValue(obj.Zref)
        contourLayout.addRow("Zref:", self.Zref)
        
        # Mode de profondeur (absolu ou relatif)
        self.depthModeLayout = QtGui.QHBoxLayout()
        self.depthModeGroup = QtGui.QButtonGroup(self.form)
        
        self.absoluteDepthRadio = QtGui.QRadioButton("Absolu")
        self.relativeDepthRadio = QtGui.QRadioButton("Relatif")
        
        # Définir le mode actif en fonction de la propriété de l'objet
        if hasattr(obj, "DepthMode") and obj.DepthMode == "Relatif":
            self.relativeDepthRadio.setChecked(True)
        else:
            self.absoluteDepthRadio.setChecked(True)
        
        self.depthModeGroup.addButton(self.absoluteDepthRadio)
        self.depthModeGroup.addButton(self.relativeDepthRadio)
        
        self.depthModeLayout.addWidget(self.absoluteDepthRadio)
        self.depthModeLayout.addWidget(self.relativeDepthRadio)
        
        contourLayout.addRow("Mode de profondeur:", self.depthModeLayout)
        
        # Hauteur finale
        self.Zfinal = QtGui.QDoubleSpinBox()
        if self.relativeDepthRadio.isChecked():
            self.Zfinal.setRange(-100, 0)
            self.Zfinal.setValue(obj.Zfinal - obj.Zref if obj.Zfinal <= obj.Zref else -1.0)
            self.Zfinal.setSuffix(" mm (relatif)")
        else:
            self.Zfinal.setRange(0.1, 100)
            self.Zfinal.setValue(obj.Zfinal)
            self.Zfinal.setSuffix(" mm (absolu)")
        
        self.Zfinal.setDecimals(2)
        contourLayout.addRow("Zfinal:", self.Zfinal)
        
        contourGroup.setLayout(contourLayout)
        layout.addWidget(contourGroup)
        
        # Mettre à jour l'affichage des arêtes sélectionnées
        self.updateEdgesLabel()
        
        # Connecter les signaux pour l'actualisation en temps réel
        self.confirmSelectionButton.clicked.connect(self.confirmSelection)
        self.direction.currentTextChanged.connect(self.updateContour)
        self.Zref.valueChanged.connect(self.updateContour)
        self.Zfinal.valueChanged.connect(self.updateContour)
        
        # Connecter les signaux pour le changement de mode de profondeur
        self.absoluteDepthRadio.toggled.connect(self.depthModeChanged)
        self.relativeDepthRadio.toggled.connect(self.depthModeChanged)
        
        # Variable pour suivre l'état de sélection
        self.selectionMode = False
        
    def updateEdgesLabel(self):
        """Met à jour l'affichage des arêtes sélectionnées"""
        if not hasattr(self.obj, "Edges") or not self.obj.Edges:
            self.edgesLabel.setText("Aucune arête sélectionnée")
            # Vider le tableau
            self.edgesTable.setRowCount(0)
            return
        
        count = 0
        for sub in self.obj.Edges:
            count += len(sub[1])
        
        self.edgesLabel.setText(f"{count} arête(s) sélectionnée(s)")
        self.isClosedLabel.setText(f"Contour fermé: {self.obj.IsClosed}")
        
        # Mettre à jour le tableau
        self.edgesTable.setRowCount(0)  # Vider le tableau
        row = 0
        for edge in self.obj.Edges:
            obj = edge[0]
            for subElement in edge[1]:
                self.edgesTable.insertRow(row)
                self.edgesTable.setItem(row, 0, QtGui.QTableWidgetItem(obj.Label))
                self.edgesTable.setItem(row, 1, QtGui.QTableWidgetItem(subElement))
                
                # Déterminer le type d'élément (ligne droite, arc, etc.)
                try:
                    element = obj.Shape.getElement(subElement)
                    elementType = element.Curve.__class__.__name__
                    self.edgesTable.setItem(row, 2, QtGui.QTableWidgetItem(elementType))
                except:
                    self.edgesTable.setItem(row, 2, QtGui.QTableWidgetItem("Inconnu"))
                
                row += 1
        
        # Ajuster la taille des colonnes
        self.edgesTable.resizeColumnsToContents()
        
    def selectEdges(self):
        """Permet à l'utilisateur de sélectionner des arêtes"""
        # Activer le mode de sélection
        self.selectionMode = True
        self.confirmSelectionButton.setEnabled(True)
        
        # Récupérer la sélection actuelle
        current_selection = Gui.Selection.getSelectionEx()
        App.Console.PrintMessage(f"Sélection actuelle: {len(current_selection)} objets.\n")
        
        # Demander à l'utilisateur de sélectionner des arêtes
        App.Console.PrintMessage("Sélectionnez les arêtes pour le contour, puis cliquez sur 'Confirmer la sélection'.\n")
        
        # Définir le mode de sélection pour les arêtes uniquement
        Gui.Selection.clearSelection()
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Edge")
        
        # Restaurer la sélection actuelle
        for obj in current_selection:
            Gui.Selection.addSelection(obj.Object)
        
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
    
    def depthModeChanged(self):
        """Gère le changement de mode de profondeur (absolu/relatif)"""
        current_value = self.Zfinal.value()
        
        if self.relativeDepthRadio.isChecked():
            # Passage en mode relatif
            self.Zfinal.setRange(-100, 0)
            if self.absoluteDepthRadio.isChecked():
                # Si on vient du mode absolu, convertir la valeur
                self.Zfinal.setValue(current_value - self.Zref.value())
            self.Zfinal.setSuffix(" mm (relatif)")
        else:
            # Passage en mode absolu
            self.Zfinal.setRange(0.1, 100)
            if self.relativeDepthRadio.isChecked():
                # Si on vient du mode relatif, convertir la valeur
                self.Zfinal.setValue(self.Zref.value() + current_value)
            self.Zfinal.setSuffix(" mm (absolu)")
        
        # Mettre à jour le contour
        self.updateContour()

    def updateContour(self):
        """Met à jour le contour en fonction des paramètres"""
        self.obj.Direction = self.direction.currentText()
        
        # Mettre à jour Zref
        self.obj.Zref = self.Zref.value()
        
        # Mettre à jour Zfinal en fonction du mode
        if self.relativeDepthRadio.isChecked():
            # Mode relatif: Zfinal = Zref + valeur relative (négative)
            self.obj.Zfinal = self.Zref.value() + self.Zfinal.value()
            self.obj.DepthMode = "Relatif"
        else:
            # Mode absolu: Zfinal = valeur absolue
            self.obj.Zfinal = self.Zfinal.value()
            self.obj.DepthMode = "Absolu"
        
        self.obj.Document.recompute()
    
    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        #debug
        App.Console.PrintMessage("Accepté\n")
        # Mettre à jour toutes les propriétés
        self.obj.Direction = self.direction.currentText()
        
        # Calculer le point le plus haut du contour
        if hasattr(self.obj, "Edges") and self.obj.Edges:
            highest_z = float('-inf')
            for edge in self.obj.Edges:
                for sub in edge[1]:
                    face = edge[0].Shape.getElement(sub)
                    for vertex in face.Vertexes:
                        if vertex.Point.z > highest_z:
                            highest_z = vertex.Point.z
            #self.obj.Zref = highest_z
        else:
            App.Console.PrintWarning("Aucune arête sélectionnée, Zref non mis à jour.\n")
        #debug
        App.Console.PrintMessage(f"Zref mis à jour: {self.obj.Zref}\n")
        
        # Mettre à jour les autres propriétés
        self.obj.Zref = self.Zref.value()
        
        # Mettre à jour Zfinal en fonction du mode
        if self.relativeDepthRadio.isChecked():
            # Mode relatif: Zfinal = Zref + valeur relative (négative)
            self.obj.Zfinal = self.Zref.value() + self.Zfinal.value()
            self.obj.DepthMode = "Relatif"
        else:
            # Mode absolu: Zfinal = valeur absolue
            self.obj.Zfinal = self.Zfinal.value()
            self.obj.DepthMode = "Absolu"
        
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
