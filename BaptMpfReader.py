import os
import re
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
import MPFParser

class MpfReader:
    """Classe pour lire et analyser les fichiers MPF (programmes d'usinage)"""
    
    def __init__(self, obj):
        self.Type = "MPFReader"

        obj.addProperty("App::PropertyFile", "FilePath", "File", "Path to MPF file")
        #obj.addProperty("App::PropertyString", "Content", "File", "Content of MPF file")
        #obj.addProperty("App::PropertyMap", "Tools", "File", "Liste des outils avec leur diamètre et leur position")
        obj.addProperty("App::PropertyMap", "Origins", "File", "Liste des origines de programme avec leur emplacement")
        obj.Origins = { "54": "App.Vector(0, 0, 0)"}

        obj.Proxy = self
        pass
    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        pass
    
    def execute(self,obj):
        App.Console.PrintMessage('Execute\n')

        self.load_file(obj.FilePath)
        pass
    def load_file(self, file_path):
        if not file_path:
            return False
        
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                self.content = content
                return True
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la lecture du fichier: {str(e)}\n")
            return False
        
class MpfReaderTaskPanel:
    """Panneau de tâches pour l'importation de fichiers MPF"""
    
    def __init__(self, obj):
        self.obj = obj
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Importer un fichier MPF")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Champ pour le chemin du fichier
        file_layout = QtGui.QHBoxLayout()
        self.file_path = QtGui.QLineEdit()
        self.file_path.setText("D:\Program Files\FreeCAD 1.0\Mod\Bapt\FAO\\test.MPF")
        self.file_path.setReadOnly(True)
        file_layout.addWidget(self.file_path)
        
        # Bouton pour sélectionner le fichier
        self.browse_button = QtGui.QPushButton("Parcourir...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        
        layout.addLayout(file_layout)
        
        # Zone de texte pour afficher le contenu du fichier
        self.content_preview = QtGui.QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setMinimumHeight(200)
        layout.addWidget(QtGui.QLabel("Aperçu du contenu:"))
        layout.addWidget(self.content_preview)
        
        # Zone de texte pour afficher le résumé des opérations
        self.operations_summary = QtGui.QTextEdit()
        self.operations_summary.setReadOnly(True)
        self.operations_summary.setMinimumHeight(100)
        layout.addWidget(QtGui.QLabel("Résumé des opérations:"))
        layout.addWidget(self.operations_summary)
        
        # Options d'importation
        options_group = QtGui.QGroupBox("Options d'importation")
        options_layout = QtGui.QVBoxLayout()
        
        # Option pour créer des objets FreeCAD
        self.create_objects_checkbox = QtGui.QCheckBox("Créer des objets FreeCAD")
        self.create_objects_checkbox.setChecked(False)
        options_layout.addWidget(self.create_objects_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # tableau des origines
        self.origins_table = QtGui.QTableWidget()
        self.origins_table.setRowCount(0)
        self.origins_table.setColumnCount(4)
        self.origins_table.setHorizontalHeaderLabels(["Nom", "X", "Y", "Z"])
        self.updateOriginTable()
        
        layout.addWidget(self.origins_table)
        
        # Bouton pour ajouter une origine
        addOriginButton = QtGui.QPushButton("Ajouter une origine")
        addOriginButton.clicked.connect(self.addOrigin)
        layout.addWidget(addOriginButton)
        
        # Bouton pour supprimer une origine
        removeOriginButton = QtGui.QPushButton("Supprimer une origine")
        removeOriginButton.clicked.connect(self.removeOrigin)
        layout.addWidget(removeOriginButton)

    def addOrigin(self):
        name, ok = QtGui.QInputDialog.getText(self.form, "Ajouter une origine", "Nom:")
        if ok:
            position = App.Vector(0, 0, 0)
            self.obj.Origins[name] = position
            self.updateOriginTable()

    def removeOrigin(self):
        name, ok = QtGui.QInputDialog.getText(self.form, "Supprimer une origine", "Nom:")
        if ok:
            if name in self.obj.Origins:
                del self.obj.Origins[name]
                self.updateOriginTable()

    def updateOriginTable(self):
        self.origins_table.setRowCount(0)
        for i, (name, position) in enumerate(self.obj.Origins.items()):
            self.origins_table.insertRow(i)
            self.origins_table.setItem(i, 0, QtGui.QTableWidgetItem(name))
            self.origins_table.setItem(i, 1, QtGui.QTableWidgetItem(position))

            
    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True

    def setEdit(self,vobj, mode=0):
        """Ouvre le panneau de tâche pour l'édition"""
        import BaptMpfReaderTaskPanel
        taskd = BaptMpfReaderTaskPanel.MpfReaderTaskPanel(self.Object)
        Gui.Control.showDialog(taskd)
        return True

    def browse_file(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier MPF"""
        file_path, _ = QtGui.QFileDialog.getOpenFileName(
            self.form,
            "Sélectionner un fichier MPF",
            self.file_path.text(),
            "Fichiers MPF (*.mpf);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.file_path.setText(file_path)
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Charge un fichier MPF
        
        Args:
            file_path: Chemin vers le fichier MPF
        """
           
    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        file_path = self.file_path.text()
        
        if not file_path:
            QtGui.QMessageBox.warning(
                self.form,
                "Aucun fichier sélectionné",
                "Veuillez sélectionner un fichier MPF à importer."
            )
            return False
        self.obj.FilePath = file_path
        # Créer des objets FreeCAD si l'option est cochée
        if self.create_objects_checkbox.isChecked():
            pass
            created_objects = self.mpf_reader.create_freecad_objects()
            if created_objects:
                App.Console.PrintMessage(f"{len(created_objects)} objets créés.\n")
            else:
                App.Console.PrintWarning("Aucun objet créé.\n")
        
        # Fermer le panneau de tâches
        Gui.Control.closeDialog()
        return True
    
    def reject(self):
        """Appelé quand l'utilisateur clique sur Annuler"""
        Gui.Control.closeDialog()
        return True


class ImportMpfCommand:
    """Commande pour importer un fichier MPF"""
    
    def GetResources(self):
        return {
            'Pixmap': os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "ImportMpf.svg"),
            'MenuText': "Importer un fichier MPF",
            'ToolTip': "Importer un programme d'usinage au format MPF"
        }
    
    def IsActive(self):
        return True
        return App.ActiveDocument is not None
    
    def Activated(self):
        
        doc = App.ActiveDocument
        
        if not doc:
            doc = App.newDocument()
        doc.openTransaction('Create MPFReader Operation')
        
        obj = doc.addObject("App::DocumentObjectGroupPython", "MpfReader")
        
        mpfReader = MpfReader(obj)
        
        if obj.ViewObject:
            ViewProviderMpfReader(obj.ViewObject)
        
        doc.recompute()

        if obj.ViewObject:
            obj.ViewObject.Proxy.setEdit(obj.ViewObject)
        
        
        
        #panel = MpfReaderTaskPanel()
        #Gui.Control.showDialog(panel)

        App.ActiveDocument.commitTransaction()

class ViewProviderMpfReader:
    """
    ViewProvider pour le MpfReader
    """
    
    def __init__(self, vobj):
        """
        Initialisation du ViewProvider
        """
        self.Object = vobj.Object
        vobj.Proxy = self
    
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "ImportMpf.svg")
    
    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True
    
    def setEdit(self,vobj, mode=0):
        """Ouvre le panneau de tâche pour l'édition"""
        taskd = MpfReaderTaskPanel(self.Object)
        Gui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Ferme l'éditeur"""
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        return True

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def getIcon(self):
        """
        Retourne l'icône associée à l'objet
        """
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "ImportMpf.svg")
    
    def attach(self, vobj):
        """
        Appelé lors de l'attachement du ViewProvider
        """
        self.Object = vobj.Object
        #self.onChanged(vobj, "Visibility")
    
    def doubleClicked(self,vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True
    
    def onChanged(self, obj, prop):
        """
        Appelé lorsqu'une propriété de l'objet est modifiée
        """
        if prop == "Visibility":
            if obj.Visibility:
                self.show()
            else:
                self.hide()
    
    def show(self):
        """
        Affiche le ViewProvider
        """
        pass
    
    def hide(self):
        """
        Cache le ViewProvider
        """
        pass


# Ajouter la commande à FreeCAD
#Gui.addCommand('ImportMpf', ImportMpfCommand())
