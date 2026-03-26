import os
import FreeCAD as App
from PySide import QtCore, QtGui  # type: ignore
import BaptUtilities

translate = App.Qt.translate


class BaptPreferences:
    ''' Exemple d'utilisation:
     from BaptPreferences import BaptPreferences
     prefs = BaptPreferences()
     db_path = prefs.getToolsDbPath()
     dossier_gcode = prefs.getGCodeFolderPath()
     '''

    def __init__(self):

        self.ToolsDbList: str = ""   # Liste de chemins séparés par ;;
        self.selectedToolDb: int = 0
        self.GCodeFolderPath: str = None
        self.AutoChildUpdate: bool = None
        self.ModeAjout: int = None
        self.DefaultRapidColor = (1.0, 0.0, 0.0)
        self.DefaultFeedColor = (0.0, 1.0, 0.0)
        self.debugGcode: bool = False

        # Load settings
        self.preferences = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Bapt")
        self.loadSettings()

        self.Dirty = False

    def getAutoChildUpdate(self) -> bool:
        """Obtenir l'état de la mise à jour automatique des enfants"""
        return self.AutoChildUpdate

    def saveSettings(self) -> bool:
        """Enregistrer les paramètres"""

        self.preferences.SetString("ToolsDbList", self.ToolsDbList)
        self.preferences.SetInt("SelectedToolDb", self.selectedToolDb)
        self.preferences.SetString("GCodeFolderPath", self.GCodeFolderPath)
        self.preferences.SetBool("AutoChildUpdate", self.AutoChildUpdate)
        self.preferences.SetInt("ModeAjout", self.ModeAjout)
        # tuple to unsigned int
        r = int(self.DefaultRapidColor[0] * 255) & 0xFF
        g = int(self.DefaultRapidColor[1] * 255) & 0xFF
        b = int(self.DefaultRapidColor[2] * 255) & 0xFF
        rapid_color_unsigned = (r << 16) | (g << 8) | b
        self.preferences.SetUnsigned("DefaultRapidColor", rapid_color_unsigned)
        # tuple to unsigned int
        r = int(self.DefaultFeedColor[0] * 255) & 0xFF
        g = int(self.DefaultFeedColor[1] * 255) & 0xFF
        b = int(self.DefaultFeedColor[2] * 255) & 0xFF
        feed_color_unsigned = (r << 16) | (g << 8) | b
        self.preferences.SetUnsigned("DefaultFeedColor", feed_color_unsigned)

        self.preferences.SetBool("DebugGcode", self.debugGcode)

        self.Dirty = False

        return True

    def loadSettings(self) -> bool:
        """Charger les paramètres"""
        self.ToolsDbList = self.preferences.GetString("ToolsDbList", "")
        # Migration: si l'ancien paramètre existe encore, l'importer
        if not self.ToolsDbList:
            old = self.preferences.GetString("ToolsDbPath", "")
            if old:
                self.ToolsDbList = old
        self.selectedToolDb = self.preferences.GetInt("SelectedToolDb", 0)
        self.GCodeFolderPath = self.preferences.GetString("GCodeFolderPath", "")
        self.AutoChildUpdate = self.preferences.GetBool("AutoChildUpdate", False)
        self.ModeAjout = self.preferences.GetInt("ModeAjout", 0)
        DefaultRapidColor = self.preferences.GetUnsigned("DefaultRapidColor", 16711680)  # Default to red
        self.debugGcode = self.preferences.GetBool("DebugGcode", False)

        # unsigned int to tuple
        r = (DefaultRapidColor >> 16) & 0xFF
        g = (DefaultRapidColor >> 8) & 0xFF
        b = DefaultRapidColor & 0xFF
        self.DefaultRapidColor = (r / 255.0, g / 255.0, b / 255.0)

        DefaultFeedColor = self.preferences.GetUnsigned("DefaultFeedColor", 65280)  # Default to green

        # unsigned int to tuple
        r = (DefaultFeedColor >> 16) & 0xFF
        g = (DefaultFeedColor >> 8) & 0xFF
        b = DefaultFeedColor & 0xFF
        self.DefaultFeedColor = (r / 255.0, g / 255.0, b / 255.0)
        return True

    def getToolsDbPaths(self) -> list:
        """Retourne la liste des chemins de bases de données"""
        if not self.ToolsDbList:
            return []
        return [p for p in self.ToolsDbList.split(';;') if p]

    def setToolsDbPaths(self, paths):
        """Enregistre la liste des chemins de bases de données"""
        self.ToolsDbList = ';;'.join(paths)

    def getToolsDbPath(self) -> str:
        """Obtenir le chemin de la base de données d'outils sélectionnée"""
        paths = self.getToolsDbPaths()
        idx = self.selectedToolDb
        if paths and 0 <= idx < len(paths):
            return paths[idx]
        # Aucun chemin configuré -> base par défaut SQLite
        path = BaptUtilities.getDefaultToolsDbPath()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def getGCodeFolderPath(self) -> str:
        """Obtenir le dossier par défaut des programmes G-code"""
        return self.GCodeFolderPath

    def getModeAjout(self) -> int:
        """Obtenir le mode d'ajout des opérations"""
        # preferences = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Bapt")
        # return preferences.GetInt("ModeAjout", 0)  # Valeur par défaut 0
        return self.ModeAjout


class BaptPreferencesPage(QtGui.QWidget):
    name = translate("Preferences", "Bapt CAM Pref")

    def __init__(self, parent=None):
        # super(BaptPreferencesPage, self).__init__(parent)
        super().__init__(parent)
        self.form = QtGui.QWidget()
        self.form.setWindowTitle(self.name)

        # Create layout
        layout = QtGui.QVBoxLayout(self.form)

        # Groupe pour les paramètres de la base de données d'outils
        tools_db_group = QtGui.QGroupBox(translate("Preferences", "Tools Database"))
        tools_db_layout = QtGui.QVBoxLayout()

        from PySide.QtCore import QT_TRANSLATE_NOOP  # type: ignore

        # Explication
        info_label = QtGui.QLabel(QT_TRANSLATE_NOOP("Preferences",
                                                    "Gérez vos bases de données d'outils. La ligne sélectionnée (en gras) est la base active. "
                                                    "Si la liste est vide, une base SQLite par défaut sera utilisée."))
        info_label.setWordWrap(True)
        tools_db_layout.addWidget(info_label)

        # Tableau des bases de données
        self.dbTable = QtGui.QTableWidget()
        self.dbTable.setColumnCount(2)
        self.dbTable.setHorizontalHeaderLabels(["Chemin", "Type"])
        self.dbTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.dbTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.dbTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.dbTable.horizontalHeader().setStretchLastSection(False)
        self.dbTable.horizontalHeader().setSectionResizeMode(0, QtGui.QHeaderView.Stretch)
        self.dbTable.horizontalHeader().setSectionResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.dbTable.setMinimumHeight(120)
        tools_db_layout.addWidget(self.dbTable)

        # Boutons
        buttons_layout = QtGui.QHBoxLayout()

        self.addDbButton = QtGui.QPushButton("Ajouter...")
        self.createNewDbButton = QtGui.QPushButton("Créer nouvelle...")
        self.removeDbButton = QtGui.QPushButton("Supprimer")
        self.setActiveDbButton = QtGui.QPushButton("Définir comme active")

        buttons_layout.addWidget(self.addDbButton)
        buttons_layout.addWidget(self.createNewDbButton)
        buttons_layout.addWidget(self.removeDbButton)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.setActiveDbButton)
        tools_db_layout.addLayout(buttons_layout)

        tools_db_group.setLayout(tools_db_layout)

        # toggle auto child update
        self.auto_child_update_checkbox = QtGui.QCheckBox("Mise à jour automatique des enfants")
        self.auto_child_update_checkbox.setToolTip("Si activé, les objets enfants seront mis à jour automatiquement lorsque l'objet parent est modifié.")
        layout.addWidget(self.auto_child_update_checkbox)
        # self.auto_child_update_checkbox.setChecked(BaptUtilities.getAutoChildUpdate())
        # self.auto_child_update_checkbox.stateChanged.connect(self.onAutoChildUpdateChanged)

        # Checkbox pour activer le debug du G-code
        self.debug_gcode_checkbox = QtGui.QCheckBox("Activer le debug du G-code")
        self.debug_gcode_checkbox.setToolTip("Si activé, des commentaires seront ajoutés dans le G-code pour faciliter le debug.")
        layout.addWidget(self.debug_gcode_checkbox)

        mode_ajout_label = QtGui.QLabel("Mode d'ajout des opérations:")
        mode_ajout_label.setToolTip("Sélectionnez comment les opérations doivent être ajoutées aux projets CAM.")
        layout.addWidget(mode_ajout_label)

        self.mode_ajout_combo = QtGui.QComboBox()
        self.mode_ajout_combo.addItem("Ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien (default)")
        self.mode_ajout_combo.addItem("Ajouter à la géométrie comme enfant (pas conseillé)")
        self.mode_ajout_combo.addItem("Ajouter uniquement au groupe opérations du projet CAM")

        # Chemin du dossier G-code
        gcode_group = QtGui.QGroupBox("Dossier G-code par défaut")
        gcode_folder_layout = QtGui.QHBoxLayout()
        gcode_folder_label = QtGui.QLabel("Dossier par défaut des programmes G-code:")
        self.gcodeFolderPath = QtGui.QLineEdit()
        self.gcodeFolderPath.setReadOnly(True)  # Rendre le champ en lecture seule pour éviter les erreurs
        self.gcodeFolderPathButton = QtGui.QPushButton("Parcourir...")

        gcode_folder_layout.addWidget(gcode_folder_label)
        gcode_folder_layout.addWidget(self.gcodeFolderPath)
        gcode_folder_layout.addWidget(self.gcodeFolderPathButton)
        gcode_group.setLayout(gcode_folder_layout)

        layout.addWidget(self.mode_ajout_combo)

        layout.addWidget(tools_db_group)

        layout.addWidget(gcode_group)

        color_group = QtGui.QGroupBox("Couleurs par défaut des mouvements G-code")
        color_layout = QtGui.QVBoxLayout()
        # Couleur des mouvements rapides
        rapid_color_layout = QtGui.QHBoxLayout()
        rapid_color_label = QtGui.QLabel("Couleur des mouvements rapides:")
        self.rapidColorButton = QtGui.QPushButton()
        self.rapidColorButton.setAutoFillBackground(True)
        self.rapidColorButton.clicked.connect(self.chooseRapidColor)
        rapid_color_layout.addWidget(rapid_color_label)
        rapid_color_layout.addWidget(self.rapidColorButton)
        color_layout.addLayout(rapid_color_layout)

        # Couleur des mouvements d'avance
        feed_color_layout = QtGui.QHBoxLayout()
        feed_color_label = QtGui.QLabel("Couleur des mouvements d'avance:")
        self.feedColorButton = QtGui.QPushButton()
        self.feedColorButton.setAutoFillBackground(True)
        self.feedColorButton.clicked.connect(self.chooseFeedColor)
        feed_color_layout.addWidget(feed_color_label)
        feed_color_layout.addWidget(self.feedColorButton)
        color_layout.addLayout(feed_color_layout)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Ajouter un espace extensible en bas
        layout.addStretch()

        # Connect signals
        self.addDbButton.clicked.connect(self.addDb)
        self.createNewDbButton.clicked.connect(self.createNewDb)
        self.removeDbButton.clicked.connect(self.removeDb)
        self.setActiveDbButton.clicked.connect(self.setActiveDb)
        self.gcodeFolderPathButton.clicked.connect(self.chooseGCodeFolder)
        self.mode_ajout_combo.currentIndexChanged.connect(self.onModeAjoutChanged)

        # Create BaptPreferences instance
        self.prefs = BaptPreferences()
        self.loadSettings()

    def chooseRapidColor(self):
        color = QtGui.QColorDialog.getColor()
        if color.isValid():
            self.rapidColorButton.setStyleSheet(f"background-color: {color.name()}")
            # Convertir la couleur en tuple (r, g, b) avec des valeurs entre 0 et 1
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
            self.rapidColor = (r, g, b)

    def chooseFeedColor(self):
        color = QtGui.QColorDialog.getColor()
        if color.isValid():
            self.feedColorButton.setStyleSheet(f"background-color: {color.name()}")
            # Convertir la couleur en tuple (r, g, b) avec des valeurs entre 0 et 1
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
            self.feedColor = (r, g, b)

    def saveSettings(self):
        """Enregistrer les paramètres"""
        self.prefs.GCodeFolderPath = self.gcodeFolderPath.text()
        self.prefs.AutoChildUpdate = self.auto_child_update_checkbox.isChecked()
        self.prefs.ModeAjout = self.mode_ajout_combo.currentIndex()
        self.prefs.DefaultRapidColor = self.rapidColor
        self.prefs.DefaultFeedColor = self.feedColor
        self.prefs.debugGcode = self.debug_gcode_checkbox.isChecked()

        self.prefs.saveSettings()

    def loadSettings(self):
        """Charger les paramètres"""
        self._refreshDbTable()
        self.gcodeFolderPath.setText(self.prefs.GCodeFolderPath)
        self.auto_child_update_checkbox.setChecked(self.prefs.AutoChildUpdate)
        self.mode_ajout_combo.setCurrentIndex(self.prefs.getModeAjout())

        self.rapidColor = self.prefs.DefaultRapidColor
        self.feedColor = self.prefs.DefaultFeedColor

        self.debug_gcode_checkbox.setChecked(self.prefs.debugGcode)

        self.rapidColorButton.setStyleSheet(f"background-color: rgb({int(self.rapidColor[0] * 255)}, {int(self.rapidColor[1] * 255)}, {int(self.rapidColor[2] * 255)})")
        self.feedColorButton.setStyleSheet(f"background-color: rgb({int(self.feedColor[0] * 255)}, {int(self.feedColor[1] * 255)}, {int(self.feedColor[2] * 255)})")

    def _refreshDbTable(self):
        """Rafraîchit le tableau des bases de données depuis les préférences"""
        paths = self.prefs.getToolsDbPaths()
        active = self.prefs.selectedToolDb
        self.dbTable.setRowCount(0)
        bold_font = QtGui.QFont()
        bold_font.setBold(True)
        for i, path in enumerate(paths):
            row = self.dbTable.rowCount()
            self.dbTable.insertRow(row)
            ext = os.path.splitext(path)[1].lower()
            db_type = "e-NC (.tls)" if ext == '.tls' else "SQLite (.db)"
            path_item = QtGui.QTableWidgetItem(path)
            type_item = QtGui.QTableWidgetItem(db_type)
            if i == active:
                path_item.setFont(bold_font)
                type_item.setFont(bold_font)
            self.dbTable.setItem(row, 0, path_item)
            self.dbTable.setItem(row, 1, type_item)
        # Sélectionner la ligne active
        if paths and 0 <= active < len(paths):
            self.dbTable.selectRow(active)

    def addDb(self):
        """Ajouter une base de données existante à la liste"""
        path = QtGui.QFileDialog.getOpenFileName(
            self.form,
            "Sélectionner un fichier de base de données",
            App.getUserAppDataDir(),
            "Fichiers supportés (*.db *.tls);;Fichiers SQLite (*.db);;Fichiers e-NC (*.tls);;Tous les fichiers (*.*)"
        )[0]
        if not path:
            return
        # Éviter les doublons
        paths = self.prefs.getToolsDbPaths()
        if path in paths:
            QtGui.QMessageBox.warning(self.form, "Doublon",
                                      "Cette base de données est déjà dans la liste.")
            return
        paths.append(path)
        self.prefs.setToolsDbPaths(paths)
        # Activer automatiquement la nouvelle entrée
        self.prefs.selectedToolDb = len(paths) - 1
        self.saveSettings()
        self._refreshDbTable()

    def createNewDb(self):
        """Créer une nouvelle base de données SQLite et l'ajouter à la liste"""
        path = QtGui.QFileDialog.getSaveFileName(
            self.form,
            "Créer une nouvelle base de données",
            App.getUserAppDataDir(),
            "Fichiers SQLite (*.db)"
        )[0]
        if not path:
            return
        if not path.lower().endswith('.db'):
            path += '.db'
        paths = self.prefs.getToolsDbPaths()
        if path in paths:
            QtGui.QMessageBox.warning(self.form, "Doublon",
                                      "Cette base de données est déjà dans la liste.")
            return
        paths.append(path)
        self.prefs.setToolsDbPaths(paths)
        self.prefs.selectedToolDb = len(paths) - 1
        self.saveSettings()
        self._refreshDbTable()

    def removeDb(self):
        """Supprimer la base de données sélectionnée de la liste"""
        selected = self.dbTable.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        paths = self.prefs.getToolsDbPaths()
        if 0 <= row < len(paths):
            paths.pop(row)
            self.prefs.setToolsDbPaths(paths)
            # Ajuster l'index actif
            if not paths:
                self.prefs.selectedToolDb = 0
            elif self.prefs.selectedToolDb >= len(paths):
                self.prefs.selectedToolDb = len(paths) - 1
            elif row < self.prefs.selectedToolDb:
                self.prefs.selectedToolDb -= 1
            self.saveSettings()
            self._refreshDbTable()

    def setActiveDb(self):
        """Définir la base de données sélectionnée comme active"""
        selected = self.dbTable.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        paths = self.prefs.getToolsDbPaths()
        if 0 <= row < len(paths):
            self.prefs.selectedToolDb = row
            self.saveSettings()
            self._refreshDbTable()

    def chooseGCodeFolder(self):
        """Sélectionner le dossier par défaut des programmes G-code"""
        folder = QtGui.QFileDialog.getExistingDirectory(self.form, "Sélectionner le dossier G-code")
        if folder:
            self.gcodeFolderPath.setText(folder)
            self.saveSettings()

            # Afficher un message de confirmation
            QtGui.QMessageBox.information(
                self.form,
                "Dossier G-code sélectionné",
                f"Le dossier G-code à l'emplacement suivant sera utilisé:\n{folder}"
            )

    def onModeAjoutChanged(self, index):
        """Gérer le changement du mode d'ajout des opérations"""
        pass

    def onAutoChildUpdateChanged(self, state):
        """Gérer le changement de l'option de mise à jour automatique des enfants"""
        is_checked = state == QtCore.Qt.Checked
