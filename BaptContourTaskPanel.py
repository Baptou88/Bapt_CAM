from BaptCamProject import CamProject
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class ContourTaskPanel:
    def __init__(self, obj,deleteOnReject):
        # Garder une référence à l'objet
        self.obj = obj
        
        self.deleteOnReject = deleteOnReject

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
        
        # Connecter le signal de sélection du tableau
        self.edgesTable.itemSelectionChanged.connect(self.onTableSelectionChanged)
        
        # Direction
        self.direction = QtGui.QComboBox()
        self.direction.addItems(["Horaire", "Anti-horaire"])
        self.direction.setCurrentText(obj.Direction)
        contourLayout.addRow("Direction:", self.direction)
        
        contourGroup.setLayout(contourLayout)
        layout.addWidget(contourGroup)
        
        # ReverseOrder btn
        self.reverseOrderButton = QtGui.QPushButton("Inverser l'ordre des arêtes")
        self.reverseOrderButton.clicked.connect(self.reverseOrder)
        layout.addWidget(self.reverseOrderButton)
        
        # Groupe Coupe
        contourGroup = QtGui.QGroupBox("Paramètres du contour")
        contourLayout = QtGui.QFormLayout()
        
        # Hauteur de référence
        self.Zref = QtGui.QDoubleSpinBox()
        self.Zref.setRange(-1000, 1000)
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
        self.depth = QtGui.QDoubleSpinBox()
        self.depth.setRange(-1000, 1000)
        if self.relativeDepthRadio.isChecked():
            #self.depth.setRange(-1000, 1000)
            #self.depth.setValue(obj.depth - obj.Zref if obj.depth <= obj.Zref else -1.0)
            self.depth.setValue(obj.depth)
            self.depth.setSuffix(" mm (relatif)")
        else:
            #self.depth.setRange(0.1, 100)
            self.depth.setValue(obj.depth)
            self.depth.setSuffix(" mm (absolu)")
        
        self.depth.setDecimals(2)
        contourLayout.addRow("depth:", self.depth)
        
        contourGroup.setLayout(contourLayout)
        layout.addWidget(contourGroup)
        
        # Mettre à jour l'affichage des arêtes sélectionnées
        self.updateEdgesLabel()
        
        # Connecter les signaux pour l'actualisation en temps réel
        self.confirmSelectionButton.clicked.connect(self.confirmSelection)
        self.direction.currentTextChanged.connect(self.updateContour)
        self.Zref.valueChanged.connect(self.updateZref)
        self.depth.valueChanged.connect(self.updateDepth)
        
        # Connecter les signaux pour le changement de mode de profondeur
        if self.obj.DepthMode == "Relatif":
            self.absoluteDepthRadio.clicked.connect(self.depthModeChanged)
        else:
            self.relativeDepthRadio.clicked.connect(self.depthModeChanged)
        
        # Variable pour suivre l'état de sélection
        self.selectionMode = False
        self.viewModeToRestore = None
        
    
    def reverseOrder(self):
        """Inverser l'ordre des arêtes sélectionnées"""
        if not hasattr(self.obj, "Edges") or not self.obj.Edges:
            return
        
        a = []
        # Inverser l'ordre des arêtes
        for edge in self.obj.Edges:
            print(edge)
            for subElement in edge[1]:
                print(subElement)
                a.insert(0, (edge[0], [subElement]))
        self.obj.Edges = a
        print(f"new edges: {self.obj.Edges}")
        #print(f"new edges reverse: {self.obj.Edges.reverse()}")
        
        # Mettre à jour l'affichage
        self.updateEdgesLabel()
    
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


        # recupere l'objet CamProject Parent
        parent = self.obj.getParent()
        print(f"parent: {parent.Name}")
        while parent and not isinstance(parent, CamProject):
        #while parent and not parent.Type == "CamProject":
            parent = parent.getParent()
            #print(f"parent: {parent.Name}")
        parent = self.obj.getParent().getParent() #TODO fixme
        if parent:
            self.viewModeToRestore = parent.Model.ViewObject.DisplayMode
            print(f"viewModeToRestore: {self.viewModeToRestore}")
            print(f"viewModeToRestore: {parent.Model.Name}")
            parent.Model.ViewObject.DisplayMode = u"Wireframe"
        else:
            print("No parent found")
        self.selectable = self.obj.ViewObject.Selectable
        self.obj.ViewObject.Selectable = False
        
        # Récupérer la sélection actuelle
        #current_selection = Gui.Selection.getSelectionEx()
        #App.Console.PrintMessage(f"Sélection actuelle: {len(current_selection)} objets.\n")
        
        # Demander à l'utilisateur de sélectionner des arêtes
        App.Console.PrintMessage("Sélectionnez les arêtes pour le contour, puis cliquez sur 'Confirmer la sélection'.\n")
        
        # Définir le mode de sélection pour les arêtes uniquement
        Gui.Selection.clearSelection()
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Edge")
        
        # Restaurer la sélection actuelle
        for obj in self.obj.Edges:
            Gui.Selection.addSelection(obj[0], obj[1])
        #for obj in current_selection:
        #    Gui.Selection.addSelection(obj.Object)
        
        # Changer le texte du bouton
        self.selectEdgesButton.setText("Annuler la sélection")
        self.selectEdgesButton.clicked.disconnect()
        self.selectEdgesButton.clicked.connect(self.cancelSelection)
    
    def cancelSelection(self):
        """Annule le mode de sélection"""
        # Désactiver le mode de sélection
        self.selectionMode = False
        self.confirmSelectionButton.setEnabled(False)
        
        self.obj.ViewObject.Selectable = self.selectable

        # recupere l'objet CamProject Parent
        parent = self.obj.getParent()
        while parent and not isinstance(parent, CamProject):
            parent = parent.getParent()
        parent = self.obj.getParent().getParent() #TODO fixme
        if parent:
            parent.Model.ViewObject.DisplayMode = self.viewModeToRestore
        
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
        
        self.obj.ViewObject.Selectable = self.selectable
        
        # recupere l'objet CamProject Parent
        parent = self.obj.getParent()
        while parent and not isinstance(parent, CamProject):
            parent = parent.getParent()
        parent = self.obj.getParent().getParent() #TODO fixme
        if parent:
            parent.Model.ViewObject.DisplayMode = self.viewModeToRestore
        
        App.Console.PrintMessage(f"Confirmation de la sélection: {len(selection)} objets sélectionnés.\n")
        
        if not selection:
            #App.Console.PrintMessage("Aucune arête sélectionnée.\n")
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
        
        current_value = self.depth.value()
        
        
        if self.relativeDepthRadio.isChecked():
        #     App.Console.PrintMessage('passage en relatif\n')
            self.absoluteDepthRadio.clicked.connect(self.depthModeChanged)
            self.relativeDepthRadio.clicked.disconnect(self.depthModeChanged)
        #     # Passage en mode relatif
        #     #self.depth.setRange(-100, 0)
            #self.depth.setValue(current_value - self.Zref.value())
            
            self.depth.setSuffix(" mm (relatif)")
            self.obj.DepthMode = "Relatif"
        else:
        #     App.Console.PrintMessage('passage en absolu\n')
            self.absoluteDepthRadio.clicked.disconnect(self.depthModeChanged)
            self.relativeDepthRadio.clicked.connect(self.depthModeChanged)
        #     # Passage en mode absolu
        #     #self.depth.setRange(0.1, 100)
            #self.depth.setValue(self.Zref.value() + current_value)
            
            self.depth.setSuffix(" mm (absolu)")
            self.obj.DepthMode = "Absolu"
        App.Console.PrintMessage('fin calcul\n')
        # Mettre à jour le contour
        self.updateContour()

    def updateZref(self):
        """Met à jour Zref"""
        self.obj.Zref = self.Zref.value()

    def updateDepth(self):
        """Met à jour depth"""
        self.obj.depth = self.depth.value()

    def updateContour(self):
        """Met à jour le contour en fonction des paramètres"""
        # Mettre à jour la direction
        self.obj.Direction = self.direction.currentText()
        
        # Mettre à jour Zref
        # self.obj.Zref = self.Zref.value()
        
        # self.obj.depth = self.depth.value()
        self.Zref.setValue(self.obj.Zref)
        self.depth.setValue(self.obj.depth)
        
        # Mettre à jour le mode de profondeur
        #if self.relativeDepthRadio.isChecked():
            # Mode relatif: depth = Zref + valeur relative (négative)
            #self.obj.depth = self.Zref.value() + self.depth.value()
            #self.obj.DepthMode = "Relatif"
        #else:
            # Mode absolu: depth = valeur absolue
            #self.obj.depth = self.depth.value()
            #self.obj.DepthMode = "Absolu"
        
        self.obj.Document.recompute()
    
    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour toutes les propriétés
        self.obj.Direction = self.direction.currentText()
        
        # Désactiver le mode de sélection si actif
        if self.selectionMode:
            Gui.Selection.removeSelectionGate()
            
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
        # else:
        #     App.Console.PrintWarning("Aucune arête sélectionnée, Zref non mis à jour.\n")
        # #debug
        # App.Console.PrintMessage(f"Zref mis à jour: {self.obj.Zref}\n")
        
        # # Mettre à jour les autres propriétés
        # self.obj.Zref = self.Zref.value()
        
        # # Mettre à jour depth en fonction du mode
        # if self.relativeDepthRadio.isChecked():
        #     # Mode relatif: depth = Zref + valeur relative (négative)
        #     #self.obj.depth = self.Zref.value() + self.depth.value()
        #     self.obj.DepthMode = "Relatif"
        # else:
        #     # Mode absolu: depth = valeur absolue
        #     #self.obj.depth = self.depth.value()
        #     self.obj.DepthMode = "Absolu"
        
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
        if self.deleteOnReject:
            App.ActiveDocument.removeObject(self.obj.Name)
        Gui.Control.closeDialog()
        return False
    
    def getStandardButtons(self):
        """Définir les boutons standard"""
        return int(QtGui.QDialogButtonBox.Ok |
                  QtGui.QDialogButtonBox.Cancel)

    def updateEdgesTable(self):
        """Met à jour le tableau des arêtes"""
        self.edgesTable.clearContents()
        
        if not hasattr(self.obj, "Edges") or not self.obj.Edges:
            self.edgesTable.setRowCount(0)
            return
        
        # Compter le nombre total d'arêtes
        total_edges = sum(len(sub[1]) for sub in self.obj.Edges)
        self.edgesTable.setRowCount(total_edges)
        
        # Ajouter chaque arête au tableau
        row = 0
        for sub in self.obj.Edges:
            obj = sub[0]
            for subElement in sub[1]:
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
        
    def onTableSelectionChanged(self):
        """Gère la sélection d'une ligne dans le tableau"""
        selected_rows = self.edgesTable.selectedIndexes()
        if not selected_rows:
            # Aucune sélection, effacer la sélection dans FreeCAD
            Gui.Selection.clearSelection()
            return
        
        # Obtenir l'index de la ligne sélectionnée
        row = selected_rows[0].row()
        
        # Trouver l'arête correspondante dans la liste des arêtes
        current_row = 0
        for sub in self.obj.Edges:
            obj_ref = sub[0]  # L'objet référencé
            sub_names = sub[1]  # Les noms des sous-éléments (arêtes)
            
            for sub_name in sub_names:
                if current_row == row:
                    # Sélectionner cette arête dans FreeCAD
                    Gui.Selection.clearSelection()
                    Gui.Selection.addSelection(obj_ref, sub_name)
                    return
                current_row += 1
    
    def highlightEdge(self, index):
        """Met en surbrillance l'arête sélectionnée"""
        # Vérifier si l'objet a la propriété pour stocker l'index sélectionné
        if not hasattr(self.obj, "SelectedEdgeIndex"):
            self.obj.addProperty("App::PropertyInteger", "SelectedEdgeIndex", "Visualization", "Index of the selected edge")
            self.obj.SelectedEdgeIndex = -1  # -1 signifie aucune sélection
        
        # Mettre à jour l'index sélectionné
        self.obj.SelectedEdgeIndex = index
        
        # Mettre à jour la visualisation
        if hasattr(self.obj, "Proxy"):
            self.obj.Proxy.updateEdgeColors(self.obj)
        
        # Recomputer pour mettre à jour l'affichage
        self.obj.Document.recompute()
