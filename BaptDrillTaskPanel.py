import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class DrillGeometryTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Edit Drill Geometry")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe pour les paramètres automatiques
        autoGroup = QtGui.QGroupBox("Detected Parameters")
        autoLayout = QtGui.QFormLayout()
        
        # Diamètre détecté
        self.drillDiameter = QtGui.QLabel(f"{obj.DrillDiameter.Value:.2f} mm")
        autoLayout.addRow("Drill Diameter:", self.drillDiameter)
        
        # Profondeur détectée
        self.drillDepth = QtGui.QLabel(f"{obj.DrillDepth.Value:.2f} mm")
        autoLayout.addRow("Drill Depth:", self.drillDepth)
        
        autoGroup.setLayout(autoLayout)
        layout.addWidget(autoGroup)
        
        # Groupe pour la sélection
        selectionGroup = QtGui.QGroupBox("Selection")
        selectionLayout = QtGui.QVBoxLayout()
        
        # Bouton pour ajouter la sélection
        addSelectionButton = QtGui.QPushButton("Add Selected Face")
        addSelectionButton.clicked.connect(self.addSelectedFace)
        selectionLayout.addWidget(addSelectionButton)
        
        selectionGroup.setLayout(selectionLayout)
        layout.addWidget(selectionGroup)
        
        # Groupe pour la liste des perçages
        drillGroup = QtGui.QGroupBox("Drill Positions")
        drillLayout = QtGui.QVBoxLayout()
        
        # Disposition horizontale pour la table et les boutons de réorganisation
        tableLayout = QtGui.QHBoxLayout()
        
        # Table des positions
        self.drillTable = QtGui.QTableWidget()
        self.drillTable.setColumnCount(4)
        self.drillTable.setHorizontalHeaderLabels(["X", "Y", "Z", ""])
        self.drillTable.horizontalHeader().setStretchLastSection(True)
        self.drillTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.drillTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        # Connecter le signal de changement de sélection
        self.drillTable.itemSelectionChanged.connect(self.selectionChanged)
        self.drillTable.itemChanged.connect(self.itemChanged)
        
        # Remplir la table avec les positions existantes
        self.updateDrillTable()
        
        tableLayout.addWidget(self.drillTable, 1)  # La table prend la majorité de l'espace
        
        # Boutons de réorganisation (Up/Down)
        orderButtonLayout = QtGui.QVBoxLayout()
        
        # Bouton Up
        self.upButton = QtGui.QPushButton("▲")
        self.upButton.setToolTip("Déplacer la position vers le haut")
        self.upButton.clicked.connect(self.moveUp)
        orderButtonLayout.addWidget(self.upButton)
        
        # Bouton Down
        self.downButton = QtGui.QPushButton("▼")
        self.downButton.setToolTip("Déplacer la position vers le bas")
        self.downButton.clicked.connect(self.moveDown)
        orderButtonLayout.addWidget(self.downButton)
        
        # Ajouter un espace extensible en bas
        orderButtonLayout.addStretch()
        
        tableLayout.addLayout(orderButtonLayout)
        drillLayout.addLayout(tableLayout)
        
        # Boutons pour ajouter/supprimer des positions
        buttonLayout = QtGui.QHBoxLayout()
        
        # Bouton pour ajouter une position
        addButton = QtGui.QPushButton("Add Position")
        addButton.clicked.connect(self.addPosition)
        buttonLayout.addWidget(addButton)
        
        # Bouton pour supprimer la sélection
        deleteButton = QtGui.QPushButton("Delete Selected")
        deleteButton.clicked.connect(self.deleteSelected)
        buttonLayout.addWidget(deleteButton)
        
        drillLayout.addLayout(buttonLayout)
        drillGroup.setLayout(drillLayout)
        layout.addWidget(drillGroup)

    def itemChanged(self, item):
        """Mise à jour des positions lorsqu'un élément de la table est modifié"""
        print(f"Item at ({item.row()}, {item.column()}) changed to: {item.text()}")
        #self.updateDrillPositions()

    def addSelectedFace(self):
        """Ajouter la face sélectionnée"""
        self.drillTable.itemChanged.disconnect(self.itemChanged)
        
        sel = Gui.Selection.getSelectionEx()
        new_faces = []
        
        # Collecter toutes les faces sélectionnées
        for selObj in sel:
            for subname in selObj.SubElementNames:
                if "Face" in subname:
                    face = getattr(selObj.Object.Shape, subname)
                    if face.Surface.TypeId == 'Part::GeomCylinder':
                        # Créer un tuple (object, [subname]) pour PropertyLinkSubList
                        new_faces.append((selObj.Object, [subname]))
        
        # Mettre à jour les faces
        if new_faces:
            current_faces = [(link, [sub]) for link, subs in (self.obj.DrillFaces or []) for sub in subs]
            self.obj.DrillFaces = current_faces + new_faces
            
            # Mettre à jour la table
            self.updateDrillTable()
            
            # Recompute
            self.obj.Document.recompute()
        
        self.drillTable.itemChanged.connect(self.itemChanged)

    def updateDrillTable(self):
        """Mettre à jour la table des positions"""
        self.drillTable.setRowCount(0)
        for pos in self.obj.DrillPositions:
            row = self.drillTable.rowCount()
            self.drillTable.insertRow(row)
            
            # Ajouter les coordonnées
            for col, val in enumerate([pos.x, pos.y, pos.z]):
                item = QtGui.QTableWidgetItem(f"{val:.2f}")
                self.drillTable.setItem(row, col, item)
            
            # Ajouter un bouton de suppression
            deleteButton = QtGui.QPushButton("X")
            deleteButton.clicked.connect(lambda checked=False, r=row: self.deleteRow(r))
            self.drillTable.setCellWidget(row, 3, deleteButton)
        
        # Mettre à jour les labels des paramètres
        if hasattr(self.obj, "DrillDiameter"):
            self.drillDiameter.setText(f"{self.obj.DrillDiameter.Value:.2f} mm")
        if hasattr(self.obj, "DrillDepth"):
            self.drillDepth.setText(f"{self.obj.DrillDepth.Value:.2f} mm")

    def addPosition(self):
        """Ajouter une nouvelle position"""
        row = self.drillTable.rowCount()
        self.drillTable.insertRow(row)
        
        # Ajouter des valeurs par défaut
        for col in range(3):
            item = QtGui.QTableWidgetItem("0.00")
            self.drillTable.setItem(row, col, item)
        
        # Ajouter un bouton de suppression
        deleteButton = QtGui.QPushButton("X")
        deleteButton.clicked.connect(lambda checked=False, r=row: self.deleteRow(r))
        self.drillTable.setCellWidget(row, 3, deleteButton)

    def deleteRow(self, row):
        """Supprimer une ligne spécifique"""
        self.drillTable.removeRow(row)
        # Mettre à jour les positions après suppression
        self.updateDrillPositions()

    def deleteSelected(self):
        """Supprimer les lignes sélectionnées"""
        rows = set(item.row() for item in self.drillTable.selectedItems())
        for row in sorted(rows, reverse=True):
            self.drillTable.removeRow(row)
        # Mettre à jour les positions après suppression
        self.updateDrillPositions()

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour les positions
        if not self.updateDrillPositions():
            return False
        
        self.obj.SelectedPosition = -1

        # Fermer la tâche
        Gui.Control.closeDialog()
        return True

    def reject(self):
        """Appelé quand l'utilisateur clique sur Cancel"""

        self.obj.SelectedPosition = -1
        
        Gui.Control.closeDialog()
        return False

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return int(QtGui.QDialogButtonBox.Ok |
                  QtGui.QDialogButtonBox.Cancel)

    def moveUp(self):
        """Déplacer la position sélectionnée vers le haut"""
        selected = self.drillTable.selectedIndexes()
        if not selected:
            return
        
        row = selected[0].row()
        if row <= 0:
            return  # Déjà en haut
        
        # Échanger les positions dans la table
        self.swapRows(row, row - 1)
        
        # Mettre à jour les positions dans l'objet DrillGeometry
        self.updateDrillPositions()
        
        # Sélectionner la nouvelle position
        self.drillTable.selectRow(row - 1)
    
    def moveDown(self):
        """Déplacer la position sélectionnée vers le bas"""
        selected = self.drillTable.selectedIndexes()
        if not selected:
            return
        
        row = selected[0].row()
        if row >= self.drillTable.rowCount() - 1:
            return  # Déjà en bas
        
        # Échanger les positions dans la table
        self.swapRows(row, row + 1)
        
        # Mettre à jour les positions dans l'objet DrillGeometry
        self.updateDrillPositions()
        
        # Sélectionner la nouvelle position
        self.drillTable.selectRow(row + 1)
    
    def swapRows(self, row1, row2):
        """Échanger deux lignes dans la table"""
        # Sauvegarder les valeurs de la première ligne
        values1 = []
        for col in range(3):  # X, Y, Z
            item = self.drillTable.item(row1, col)
            if item:
                values1.append(item.text())
            else:
                values1.append("")
        
        # Sauvegarder les valeurs de la deuxième ligne
        values2 = []
        for col in range(3):  # X, Y, Z
            item = self.drillTable.item(row2, col)
            if item:
                values2.append(item.text())
            else:
                values2.append("")
        
        # Copier les valeurs de la deuxième ligne vers la première
        for col, value in enumerate(values2):
            self.drillTable.setItem(row1, col, QtGui.QTableWidgetItem(value))
        
        # Copier les valeurs de la première ligne vers la deuxième
        for col, value in enumerate(values1):
            self.drillTable.setItem(row2, col, QtGui.QTableWidgetItem(value))
        
        # Recréer les boutons de suppression
        deleteButton1 = QtGui.QPushButton("X")
        deleteButton1.clicked.connect(lambda checked=False, r=row1: self.deleteRow(r))
        self.drillTable.setCellWidget(row1, 3, deleteButton1)
        
        deleteButton2 = QtGui.QPushButton("X")
        deleteButton2.clicked.connect(lambda checked=False, r=row2: self.deleteRow(r))
        self.drillTable.setCellWidget(row2, 3, deleteButton2)

    def updateDrillPositions(self):
        """Mettre à jour les positions de perçage dans l'objet DrillGeometry"""
        # Collecter toutes les positions depuis la table
        positions = []
        for row in range(self.drillTable.rowCount()):
            try:
                # Vérifier que les éléments existent et ont un attribut text
                item_x = self.drillTable.item(row, 0)
                item_y = self.drillTable.item(row, 1)
                item_z = self.drillTable.item(row, 2)
                
                if not item_x or not item_y or not item_z:
                    App.Console.PrintError(f"Élément manquant à la ligne {row+1}\n")
                    return False
                
                x = float(item_x.text())
                y = float(item_y.text())
                z = float(item_z.text())
                positions.append(App.Vector(x, y, z))
            except (ValueError, AttributeError) as e:
                App.Console.PrintError(f"Position invalide à la ligne {row+1}: {str(e)}\n")
                return False
        
        # Mettre à jour les positions dans l'objet
        self.obj.DrillPositions = positions
        
        # Mettre à jour les opérations enfants
        self.updateChildOperations()
        
        # Recomputer pour mettre à jour la visualisation
        self.obj.Document.recompute()
        return True
    
    def updateChildOperations(self):
        """Mettre à jour les opérations de perçage enfants"""
        # Parcourir tous les objets enfants de type DrillOperation
        for child in self.obj.Group:
            if hasattr(child, "Proxy") and hasattr(child.Proxy, "Type") and child.Proxy.Type == "DrillOperation":
                # Forcer la mise à jour de l'opération
                if hasattr(child, "touch"):
                    child.touch()
                # Ou utiliser execute si disponible
                elif hasattr(child.Proxy, "execute"):
                    child.Proxy.execute(child)
        
        # Message de confirmation
        App.Console.PrintMessage("Opérations de perçage mises à jour avec le nouvel ordre.\n")

    def selectionChanged(self):
        """Appelé quand la sélection dans le tableau change"""
        selected = self.drillTable.selectedIndexes()
        if not selected:
            # Aucune sélection, désélectionner dans l'objet
            self.obj.SelectedPosition = -1
        else:
            # Mettre à jour la position sélectionnée dans l'objet
            row = selected[0].row()
            self.obj.SelectedPosition = row
            App.Console.PrintMessage(f"Position sélectionnée: {row}\n")
        
        # Recomputer pour mettre à jour la visualisation
        self.obj.Document.recompute()
