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
        
        # Groupe pour la liste des perçages
        drillGroup = QtGui.QGroupBox("Drill Positions")
        drillLayout = QtGui.QVBoxLayout()
        
        # Table des positions
        self.drillTable = QtGui.QTableWidget()
        self.drillTable.setColumnCount(4)
        self.drillTable.setHorizontalHeaderLabels(["X", "Y", "Z", ""])
        self.drillTable.horizontalHeader().setStretchLastSection(True)
        
        # Remplir la table avec les positions existantes
        self.updateDrillTable()
        
        drillLayout.addWidget(self.drillTable)
        
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
            deleteButton.clicked.connect(lambda checked, r=row: self.deleteRow(r))
            self.drillTable.setCellWidget(row, 3, deleteButton)

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
        deleteButton.clicked.connect(lambda checked, r=row: self.deleteRow(r))
        self.drillTable.setCellWidget(row, 3, deleteButton)

    def deleteRow(self, row):
        """Supprimer une ligne spécifique"""
        self.drillTable.removeRow(row)

    def deleteSelected(self):
        """Supprimer les lignes sélectionnées"""
        rows = set(item.row() for item in self.drillTable.selectedItems())
        for row in sorted(rows, reverse=True):
            self.drillTable.removeRow(row)

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Collecter toutes les positions
        positions = []
        for row in range(self.drillTable.rowCount()):
            try:
                x = float(self.drillTable.item(row, 0).text())
                y = float(self.drillTable.item(row, 1).text())
                z = float(self.drillTable.item(row, 2).text())
                positions.append(App.Vector(x, y, z))
            except (ValueError, AttributeError):
                App.Console.PrintError(f"Invalid position at row {row+1}\n")
                return False
        
        # Mettre à jour les positions
        self.obj.DrillPositions = positions
        
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
