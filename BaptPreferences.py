import os
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

class BaptPreferences:
    def __init__(self):
        self.form = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(self.form)
        
        # Create widgets
        hlayout = QtGui.QHBoxLayout()
        label = QtGui.QLabel("Tools Database Path:", self.form)
        self.toolsDbPath = QtGui.QLineEdit(self.form)
        self.toolsDbPathButton = QtGui.QPushButton("Browse...", self.form)
        
        hlayout.addWidget(label)
        hlayout.addWidget(self.toolsDbPath)
        hlayout.addWidget(self.toolsDbPathButton)
        
        layout.addLayout(hlayout)
        layout.addStretch()
        
        # Connect signals
        self.toolsDbPathButton.clicked.connect(self.chooseFile)
        
        # Load settings
        self.preferences = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Bapt")
        self.loadSettings()
        
    def chooseFile(self):
        path = QtGui.QFileDialog.getOpenFileName(
            self.form,
            "Select tools database file",
            self.toolsDbPath.text(),
            "Database files (*.db);;All files (*.*)"
        )[0]
        if path:
            self.toolsDbPath.setText(path)
    
    def saveSettings(self):
        self.preferences.SetString("ToolsDbPath", self.toolsDbPath.text())
        
    def loadSettings(self):
        self.toolsDbPath.setText(self.preferences.GetString("ToolsDbPath", ""))
        
    def getToolsDbPath(self):
        return self.preferences.GetString("ToolsDbPath", "")

class BaptPreferencesPage(QtGui.QWidget):
    def __init__(self, parent=None):
        super(BaptPreferencesPage, self).__init__(parent)
        
        # Create layout
        layout = QtGui.QVBoxLayout(self)
        
        # Create BaptPreferences instance
        self.prefs = BaptPreferences()
        layout.addWidget(self.prefs.form)
        
        # Connect signals
        self.prefs.toolsDbPathButton.clicked.connect(self.saveSettings)
        
    def saveSettings(self):
        self.prefs.saveSettings()
        
    def loadSettings(self):
        self.prefs.loadSettings()




#exemple d'utilisation:
# from BaptPreferences import BaptPreferences

# prefs = BaptPreferences()
# db_path = prefs.getToolsDbPath()