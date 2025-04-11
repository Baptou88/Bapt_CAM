import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from PySide import QtCore, QtGui
import json
import sqlite3
from BaptPreferences import BaptPreferences

class Tool:
    """Classe représentant un outil d'usinage"""
    def __init__(self, id=None, name="", type="", diameter=0.0, length=0.0, flutes=0, material="", comment=""):
        self.id = id
        self.name = name
        self.type = type
        self.diameter = diameter
        self.length = length
        self.flutes = flutes
        self.material = material
        self.comment = comment
    
    def to_dict(self):
        """Convertit l'outil en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'diameter': self.diameter,
            'length': self.length,
            'flutes': self.flutes,
            'material': self.material,
            'comment': self.comment
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un outil à partir d'un dictionnaire"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ""),
            type=data.get('type', ""),
            diameter=data.get('diameter', 0.0),
            length=data.get('length', 0.0),
            flutes=data.get('flutes', 0),
            material=data.get('material', ""),
            comment=data.get('comment', "")
        )


class ToolDatabase:
    """Classe gérant la base de données d'outils"""
    def __init__(self):
        # Récupérer le chemin depuis les préférences
        prefs = BaptPreferences()
        custom_path = prefs.getToolsDbPath()
        
        # Utiliser le chemin personnalisé s'il est défini, sinon utiliser le chemin par défaut
        if custom_path and os.path.isdir(os.path.dirname(custom_path)):
            self.db_path = custom_path
        else:
            # Chemin par défaut vers le fichier de base de données
            self.db_path = os.path.join(App.getUserAppDataDir(), "Bapt", "tools.db")
            
            # Créer le dossier s'il n'existe pas
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialiser la base de données
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données si elle n'existe pas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Créer la table des outils si elle n'existe pas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            diameter REAL,
            length REAL,
            flutes INTEGER,
            material TEXT,
            comment TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_all_tools(self):
        """Récupère tous les outils de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, type, diameter, length, flutes, material, comment FROM tools")
        rows = cursor.fetchall()
        
        tools = []
        for row in rows:
            tool = Tool(
                id=row[0],
                name=row[1],
                type=row[2],
                diameter=row[3],
                length=row[4],
                flutes=row[5],
                material=row[6],
                comment=row[7]
            )
            tools.append(tool)
        
        conn.close()
        return tools
    
    def add_tool(self, tool):
        """Ajoute un outil à la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tools (name, type, diameter, length, flutes, material, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tool.name, tool.type, tool.diameter, tool.length, tool.flutes, tool.material, tool.comment))
        
        # Récupérer l'ID généré
        tool.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return tool
    
    def update_tool(self, tool):
        """Met à jour un outil dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE tools
        SET name=?, type=?, diameter=?, length=?, flutes=?, material=?, comment=?
        WHERE id=?
        ''', (tool.name, tool.type, tool.diameter, tool.length, tool.flutes, tool.material, tool.comment, tool.id))
        
        conn.commit()
        conn.close()
    
    def delete_tool(self, tool_id):
        """Supprime un outil de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tools WHERE id=?", (tool_id,))
        
        conn.commit()
        conn.close()


class ToolsTableModel(QtCore.QAbstractTableModel):
    """Modèle de tableau pour afficher les outils"""
    def __init__(self, tools=None):
        super(ToolsTableModel, self).__init__()
        self.tools = tools or []
        self.filtered_tools = list(self.tools)  # Liste filtrée des outils
        self.headers = ["ID", "Nom", "Type", "Diamètre (mm)", "Longueur (mm)", "Nb dents", "Matériau", "Commentaire"]
        self.filter_text = ""  # Texte de filtrage
        self.filter_column = -1  # Colonne de filtrage (-1 = toutes les colonnes)
    
    def rowCount(self, parent=None):
        return len(self.filtered_tools)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.filtered_tools)):
            return None
        
        tool = self.filtered_tools[index.row()]
        col = index.column()
        
        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return str(tool.id)
            elif col == 1:
                return tool.name
            elif col == 2:
                return tool.type
            elif col == 3:
                return str(tool.diameter)
            elif col == 4:
                return str(tool.length)
            elif col == 5:
                return str(tool.flutes)
            elif col == 6:
                return tool.material
            elif col == 7:
                return tool.comment
        
        return None
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None
    
    def setTools(self, tools):
        """Met à jour la liste des outils"""
        self.beginResetModel()
        self.tools = tools
        self.applyFilter()
        self.endResetModel()
    
    def setFilter(self, text, column=-1):
        """Définit le filtre à appliquer"""
        self.filter_text = text.lower()
        self.filter_column = column
        self.applyFilter()
    
    def applyFilter(self):
        """Applique le filtre actuel à la liste des outils"""
        self.beginResetModel()
        
        if not self.filter_text:
            # Pas de filtre, afficher tous les outils
            self.filtered_tools = list(self.tools)
        else:
            # Appliquer le filtre
            self.filtered_tools = []
            
            for tool in self.tools:
                # Si une colonne spécifique est sélectionnée
                if self.filter_column >= 0:
                    value = ""
                    if self.filter_column == 0:
                        value = str(tool.id)
                    elif self.filter_column == 1:
                        value = tool.name
                    elif self.filter_column == 2:
                        value = tool.type
                    elif self.filter_column == 3:
                        value = str(tool.diameter)
                    elif self.filter_column == 4:
                        value = str(tool.length)
                    elif self.filter_column == 5:
                        value = str(tool.flutes)
                    elif self.filter_column == 6:
                        value = tool.material
                    elif self.filter_column == 7:
                        value = tool.comment
                    
                    if self.filter_text in value.lower():
                        self.filtered_tools.append(tool)
                else:
                    # Rechercher dans toutes les colonnes
                    values = [
                        str(tool.id),
                        tool.name,
                        tool.type,
                        str(tool.diameter),
                        str(tool.length),
                        str(tool.flutes),
                        tool.material,
                        tool.comment
                    ]
                    
                    # Si le texte de filtre est trouvé dans l'une des valeurs
                    if any(self.filter_text in value.lower() for value in values):
                        self.filtered_tools.append(tool)
        
        self.endResetModel()
    
    def sort(self, column, order):
        """Trie les outils selon la colonne et l'ordre spécifiés"""
        self.beginResetModel()
        
        # Définir la clé de tri en fonction de la colonne
        if column == 0:  # ID
            key = lambda tool: tool.id if tool.id is not None else 0
        elif column == 1:  # Nom
            key = lambda tool: tool.name.lower()
        elif column == 2:  # Type
            key = lambda tool: tool.type.lower()
        elif column == 3:  # Diamètre
            key = lambda tool: float(tool.diameter)
        elif column == 4:  # Longueur
            key = lambda tool: float(tool.length)
        elif column == 5:  # Nb dents
            key = lambda tool: int(tool.flutes)
        elif column == 6:  # Matériau
            key = lambda tool: tool.material.lower()
        elif column == 7:  # Commentaire
            key = lambda tool: tool.comment.lower()
        else:
            return
        
        # Trier la liste filtrée
        reverse = (order == QtCore.Qt.DescendingOrder)
        self.filtered_tools.sort(key=key, reverse=reverse)
        
        self.endResetModel()


class ToolDialog(QtGui.QDialog):
    """Dialogue pour ajouter ou modifier un outil"""
    def __init__(self, tool=None, parent=None):
        super(ToolDialog, self).__init__(parent)
        self.tool = tool or Tool()
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        self.setWindowTitle("Éditer un outil" if self.tool.id else "Ajouter un outil")
        self.setMinimumWidth(400)
        
        layout = QtGui.QVBoxLayout(self)
        
        # Formulaire
        form_layout = QtGui.QFormLayout()
        
        # Nom
        self.name_edit = QtGui.QLineEdit(self.tool.name)
        form_layout.addRow("Nom:", self.name_edit)
        
        # Type (combobox)
        self.type_combo = QtGui.QComboBox()
        self.type_combo.addItems(["Fraise", "Foret", "Taraud", "Autre"])
        if self.tool.type:
            self.type_combo.setCurrentText(self.tool.type)
        form_layout.addRow("Type:", self.type_combo)
        
        # Diamètre
        self.diameter_spin = QtGui.QDoubleSpinBox()
        self.diameter_spin.setRange(0.1, 100.0)
        self.diameter_spin.setSingleStep(0.1)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.setValue(self.tool.diameter)
        form_layout.addRow("Diamètre:", self.diameter_spin)
        
        # Longueur
        self.length_spin = QtGui.QDoubleSpinBox()
        self.length_spin.setRange(1.0, 300.0)
        self.length_spin.setSingleStep(1.0)
        self.length_spin.setSuffix(" mm")
        self.length_spin.setValue(self.tool.length)
        form_layout.addRow("Longueur:", self.length_spin)
        
        # Nombre de dents
        self.flutes_spin = QtGui.QSpinBox()
        self.flutes_spin.setRange(0, 20)
        self.flutes_spin.setValue(self.tool.flutes)
        form_layout.addRow("Nombre de dents:", self.flutes_spin)
        
        # Matériau
        self.material_edit = QtGui.QLineEdit(self.tool.material)
        form_layout.addRow("Matériau:", self.material_edit)
        
        # Commentaire
        self.comment_edit = QtGui.QTextEdit()
        self.comment_edit.setPlainText(self.tool.comment)
        self.comment_edit.setMaximumHeight(100)
        form_layout.addRow("Commentaire:", self.comment_edit)
        
        layout.addLayout(form_layout)
        
        # Boutons
        button_box = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept(self):
        """Valide les modifications"""
        self.tool.name = self.name_edit.text()
        self.tool.type = self.type_combo.currentText()
        self.tool.diameter = self.diameter_spin.value()
        self.tool.length = self.length_spin.value()
        self.tool.flutes = self.flutes_spin.value()
        self.tool.material = self.material_edit.text()
        self.tool.comment = self.comment_edit.toPlainText()
        
        super(ToolDialog, self).accept()


class ToolsManagerPanel:
    """Panneau de gestion des outils"""
    def __init__(self):
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Gestionnaire d'outils")
        self.setup_ui()
        
        # Base de données d'outils
        self.db = ToolDatabase()
        
        # Charger les outils
        self.load_tools()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        layout = QtGui.QVBoxLayout(self.form)
        
        # Zone de filtrage
        filter_layout = QtGui.QHBoxLayout()
        
        # Libellé
        filter_label = QtGui.QLabel("Filtrer:")
        filter_layout.addWidget(filter_label)
        
        # Champ de recherche
        self.filter_edit = QtGui.QLineEdit()
        self.filter_edit.setPlaceholderText("Entrez un texte pour filtrer...")
        self.filter_edit.textChanged.connect(self.filter_changed)
        filter_layout.addWidget(self.filter_edit)
        
        # Sélection de colonne
        self.column_combo = QtGui.QComboBox()
        self.column_combo.addItem("Toutes les colonnes", -1)
        self.column_combo.addItem("ID", 0)
        self.column_combo.addItem("Nom", 1)
        self.column_combo.addItem("Type", 2)
        self.column_combo.addItem("Diamètre", 3)
        self.column_combo.addItem("Longueur", 4)
        self.column_combo.addItem("Nb dents", 5)
        self.column_combo.addItem("Matériau", 6)
        self.column_combo.addItem("Commentaire", 7)
        self.column_combo.currentIndexChanged.connect(self.column_changed)
        filter_layout.addWidget(self.column_combo)
        
        # Bouton pour effacer le filtre
        clear_button = QtGui.QPushButton("Effacer")
        clear_button.clicked.connect(self.clear_filter)
        filter_layout.addWidget(clear_button)
        
        layout.addLayout(filter_layout)
        
        # Tableau des outils
        self.table_view = QtGui.QTableView()
        self.table_view.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)  # Activer le tri
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        # Configurer le tri par défaut sur le diamètre (colonne 3)
        self.table_view.horizontalHeader().setSortIndicator(3, QtCore.Qt.AscendingOrder)
        
        layout.addWidget(self.table_view)
        
        # Boutons d'action
        button_layout = QtGui.QHBoxLayout()
        
        self.add_button = QtGui.QPushButton("Ajouter")
        self.add_button.clicked.connect(self.add_tool)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = QtGui.QPushButton("Éditer")
        self.edit_button.clicked.connect(self.edit_tool)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = QtGui.QPushButton("Supprimer")
        self.delete_button.clicked.connect(self.delete_tool)
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)
    
    def filter_changed(self):
        """Appelé quand le texte du filtre change"""
        if hasattr(self, 'model'):
            self.model.setFilter(
                self.filter_edit.text(),
                self.column_combo.itemData(self.column_combo.currentIndex())
            )
    
    def column_changed(self):
        """Appelé quand la colonne de filtrage change"""
        if hasattr(self, 'model'):
            self.model.setFilter(
                self.filter_edit.text(),
                self.column_combo.itemData(self.column_combo.currentIndex())
            )
    
    def clear_filter(self):
        """Efface le filtre"""
        self.filter_edit.clear()
        self.column_combo.setCurrentIndex(0)  # "Toutes les colonnes"
    
    def load_tools(self):
        """Charge les outils depuis la base de données"""
        tools = self.db.get_all_tools()
        self.model = ToolsTableModel(tools)
        self.table_view.setModel(self.model)
        
        # Connecter le signal de tri du tableau au modèle
        self.table_view.horizontalHeader().sortIndicatorChanged.connect(self.model.sort)
        
        # Ajuster les colonnes
        self.table_view.resizeColumnsToContents()
        
        # Trier initialement par diamètre (colonne 3) en ordre croissant
        self.model.sort(3, QtCore.Qt.AscendingOrder)
    
    def add_tool(self):
        """Ajoute un nouvel outil"""
        dialog = ToolDialog(parent=self.form)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            # Ajouter l'outil à la base de données
            tool = self.db.add_tool(dialog.tool)
            
            # Mettre à jour le modèle
            tools = self.db.get_all_tools()
            self.model.setTools(tools)
    
    def edit_tool(self):
        """Modifie l'outil sélectionné"""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
        
        row = selected[0].row()
        tool = self.model.tools[row]
        
        dialog = ToolDialog(tool, parent=self.form)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            # Mettre à jour l'outil dans la base de données
            self.db.update_tool(tool)
            
            # Mettre à jour le modèle
            tools = self.db.get_all_tools()
            self.model.setTools(tools)
    
    def delete_tool(self):
        """Supprime l'outil sélectionné"""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
        
        row = selected[0].row()
        tool = self.model.tools[row]
        
        # Demander confirmation
        reply = QtGui.QMessageBox.question(
            self.form,
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer l'outil '{tool.name}' ?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No
        )
        
        if reply == QtGui.QMessageBox.Yes:
            # Supprimer l'outil de la base de données
            self.db.delete_tool(tool.id)
            
            # Mettre à jour le modèle
            tools = self.db.get_all_tools()
            self.model.setTools(tools)
