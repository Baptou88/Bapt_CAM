import os
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
import BaptUtilities

class BaptPreferences:
    def __init__(self):
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Édition de l'opérateur")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Groupe pour les paramètres de la base de données d'outils
        tools_db_group = QtGui.QGroupBox("Base de données d'outils")
        tools_db_layout = QtGui.QVBoxLayout()
        
        # Explication
        info_label = QtGui.QLabel("Configurez l'emplacement de la base de données d'outils. Si aucun chemin n'est spécifié, "
                                  "une base de données par défaut sera créée dans le dossier utilisateur de FreeCAD.")
        info_label.setWordWrap(True)
        tools_db_layout.addWidget(info_label)
        
        # Chemin de la base de données
        path_layout = QtGui.QHBoxLayout()
        path_label = QtGui.QLabel("Chemin de la base de données:")
        self.toolsDbPath = QtGui.QLineEdit()
        self.toolsDbPath.setReadOnly(True)  # Rendre le champ en lecture seule pour éviter les erreurs
        self.toolsDbPathButton = QtGui.QPushButton("Parcourir...")
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.toolsDbPath)
        path_layout.addWidget(self.toolsDbPathButton)
        tools_db_layout.addLayout(path_layout)
        
        # Chemin du dossier G-code
        gcode_folder_layout = QtGui.QHBoxLayout()
        gcode_folder_label = QtGui.QLabel("Dossier par défaut des programmes G-code:")
        self.gcodeFolderPath = QtGui.QLineEdit()
        self.gcodeFolderPath.setReadOnly(True)  # Rendre le champ en lecture seule pour éviter les erreurs
        self.gcodeFolderPathButton = QtGui.QPushButton("Parcourir...")
        
        gcode_folder_layout.addWidget(gcode_folder_label)
        gcode_folder_layout.addWidget(self.gcodeFolderPath)
        gcode_folder_layout.addWidget(self.gcodeFolderPathButton)
        tools_db_layout.addLayout(gcode_folder_layout)
        
        # Boutons pour créer une nouvelle base de données ou utiliser celle par défaut
        buttons_layout = QtGui.QHBoxLayout()
        
        self.createNewDbButton = QtGui.QPushButton("Créer une nouvelle base de données...")
        self.useDefaultDbButton = QtGui.QPushButton("Utiliser la base de données par défaut")
        
        buttons_layout.addWidget(self.createNewDbButton)
        buttons_layout.addWidget(self.useDefaultDbButton)
        tools_db_layout.addLayout(buttons_layout)
        
        tools_db_group.setLayout(tools_db_layout)

        #toggle auto child update
        self.auto_child_update_checkbox = QtGui.QCheckBox("Mise à jour automatique des enfants")
        self.auto_child_update_checkbox.setToolTip("Si activé, les objets enfants seront mis à jour automatiquement lorsque l'objet parent est modifié.")
        layout.addWidget(self.auto_child_update_checkbox)
        #self.auto_child_update_checkbox.setChecked(BaptUtilities.getAutoChildUpdate())
        #self.auto_child_update_checkbox.stateChanged.connect(self.onAutoChildUpdateChanged)

        mode_ajout_label = QtGui.QLabel("Mode d'ajout des opérations:")
        mode_ajout_label.setToolTip("Sélectionnez comment les opérations doivent être ajoutées aux projets CAM.")
        layout.addWidget(mode_ajout_label)
        
        self.mode_ajout_combo = QtGui.QComboBox()
        self.mode_ajout_combo.addItem("Ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien (default)")
        self.mode_ajout_combo.addItem("Ajouter à la géométrie comme enfant (pas conseillé)")
        self.mode_ajout_combo.addItem("Ajouter uniquement au groupe opérations du projet CAM comme lien")
        
        self.mode_ajout_combo.currentIndexChanged.connect(self.onModeAjoutChanged)

        layout.addWidget(self.mode_ajout_combo)

        layout.addWidget(tools_db_group)
        
        # Ajouter un espace extensible en bas
        layout.addStretch()
        
        # Connect signals
        self.toolsDbPathButton.clicked.connect(self.chooseExistingDb)
        self.createNewDbButton.clicked.connect(self.createNewDb)
        self.useDefaultDbButton.clicked.connect(self.useDefaultDb)
        self.gcodeFolderPathButton.clicked.connect(self.chooseGCodeFolder)
        
        # Load settings
        self.preferences = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Bapt")
        self.loadSettings()
    
    def onAutoChildUpdateChanged(self, state):
        """Gérer le changement de l'option de mise à jour automatique des enfants"""
        is_checked = state == QtCore.Qt.Checked

    def getAutoChildUpdate(self):
        """Obtenir l'état de la mise à jour automatique des enfants"""
        return self.preferences.GetBool("AutoChildUpdate", True)    

    def chooseExistingDb(self):
        """Sélectionner une base de données existante"""
        path = QtGui.QFileDialog.getOpenFileName(
            self.form,
            "Sélectionner un fichier de base de données",
            os.path.dirname(self.toolsDbPath.text()) if self.toolsDbPath.text() else App.getUserAppDataDir(),
            "Fichiers SQLite (*.db);;Tous les fichiers (*.*)"
        )[0]
        
        if path:
            self.toolsDbPath.setText(path)
            self.saveSettings()
            
            # Afficher un message de confirmation
            QtGui.QMessageBox.information(
                self.form,
                "Base de données sélectionnée",
                f"La base de données à l'emplacement suivant sera utilisée:\n{path}"
            )
    
    def createNewDb(self):
        """Créer une nouvelle base de données"""
        path = QtGui.QFileDialog.getSaveFileName(
            self.form,
            "Créer une nouvelle base de données",
            os.path.dirname(self.toolsDbPath.text()) if self.toolsDbPath.text() else App.getUserAppDataDir(),
            "Fichiers SQLite (*.db)"
        )[0]
        
        if path:
            # S'assurer que le fichier a l'extension .db
            if not path.lower().endswith('.db'):
                path += '.db'
            
            self.toolsDbPath.setText(path)
            self.saveSettings()
            
            # Afficher un message de confirmation
            QtGui.QMessageBox.information(
                self.form,
                "Nouvelle base de données",
                f"Une nouvelle base de données sera créée à l'emplacement suivant:\n{path}\n\n"
                "La base de données sera initialisée lors de la prochaine utilisation du gestionnaire d'outils."
            )
    
    def useDefaultDb(self):
        """Utiliser la base de données par défaut"""
        self.toolsDbPath.clear()
        self.saveSettings()
        
        default_path = BaptUtilities.getToolsDbPath()
        
        # Afficher un message de confirmation
        QtGui.QMessageBox.information(
            self.form,
            "Base de données par défaut",
            f"La base de données par défaut sera utilisée à l'emplacement suivant:\n{default_path}"
        )
    
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
    
    def saveSettings(self):
        """Enregistrer les paramètres"""
        self.preferences.SetString("ToolsDbPath", self.toolsDbPath.text())
        self.preferences.SetString("GCodeFolderPath", self.gcodeFolderPath.text())
        self.preferences.SetBool("AutoChildUpdate", self.auto_child_update_checkbox.isChecked())
        self.preferences.SetInt("ModeAjout", self.mode_ajout_combo.currentIndex())
        
    def loadSettings(self):
        """Charger les paramètres"""
        self.toolsDbPath.setText(self.preferences.GetString("ToolsDbPath", ""))
        self.gcodeFolderPath.setText(self.preferences.GetString("GCodeFolderPath", ""))
        self.auto_child_update_checkbox.setChecked(self.preferences.GetBool("AutoChildUpdate", True))
        self.mode_ajout_combo.setCurrentIndex(self.getModeAjout())
        
    def getToolsDbPath(self):
        """Obtenir le chemin de la base de données d'outils"""
        path = self.preferences.GetString("ToolsDbPath", "")
        if not path or not os.path.isdir(os.path.dirname(path)):
            path = os.path.join(App.getUserAppDataDir(), "Bapt", "tools.db")
            # Créer le dossier s'il n'existe pas
            os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def getGCodeFolderPath(self):
        """Obtenir le dossier par défaut des programmes G-code"""
        return self.preferences.GetString("GCodeFolderPath", "")

    def onModeAjoutChanged(self, index):
        """Gérer le changement du mode d'ajout des opérations"""
        pass  

    def getModeAjout(self):
        """Obtenir le mode d'ajout des opérations"""
        # preferences = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Bapt")
        # return preferences.GetInt("ModeAjout", 0)  # Valeur par défaut 0
        return self.preferences.GetInt("ModeAjout", 0)
    
class BaptPreferencesPage(QtGui.QWidget):
    name = "Bapt CAM Pref"
    def __init__(self, parent=None):
        #super(BaptPreferencesPage, self).__init__(parent)
        super().__init__(parent)
        self.form = QtGui.QWidget()
        self.form.setWindowTitle(self.name)
        # Create layout
        layout = QtGui.QVBoxLayout(self.form)
        
        # Create BaptPreferences instance
        self.prefs = BaptPreferences()
        layout.addWidget(self.prefs.form)
        
    def saveSettings(self):
        """Enregistrer les paramètres"""
        self.prefs.saveSettings()
        
    def loadSettings(self):
        """Charger les paramètres"""
        self.prefs.loadSettings()


# Exemple d'utilisation:
# from BaptPreferences import BaptPreferences
# prefs = BaptPreferences()
# db_path = prefs.getToolsDbPath()
# dossier_gcode = prefs.getGCodeFolderPath()