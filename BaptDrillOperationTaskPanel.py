import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from BaptTools import ToolDatabase, Tool

class ToolSelectorDialog(QtGui.QDialog):
    """Dialogue pour sélectionner un outil"""
    def __init__(self, current_tool_id=-1, parent=None):
        super(ToolSelectorDialog, self).__init__(parent)
        self.current_tool_id = current_tool_id
        self.selected_tool_id = -1
        self.selected_tool_name = ""
        self.setup_ui()
        self.load_tools()
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        self.setWindowTitle("Sélectionner un outil")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QtGui.QVBoxLayout(self)
        
        # Filtre pour les outils
        filter_layout = QtGui.QHBoxLayout()
        
        # Filtre par texte
        filter_label = QtGui.QLabel("Filtre texte:")
        self.filter_edit = QtGui.QLineEdit()
        self.filter_edit.textChanged.connect(self.filter_tools)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        # Filtre par type d'outil
        type_label = QtGui.QLabel("Type d'outil:")
        self.type_combo = QtGui.QComboBox()
        self.type_combo.addItem("Tous", "")
        # Les types seront ajoutés dynamiquement lors du chargement des outils
        self.type_combo.currentIndexChanged.connect(self.filter_tools)
        filter_layout.addWidget(type_label)
        filter_layout.addWidget(self.type_combo)
        
        layout.addLayout(filter_layout)
        
        # Table des outils
        self.tool_table = QtGui.QTableWidget()
        self.tool_table.setColumnCount(5)
        self.tool_table.setHorizontalHeaderLabels(["ID", "Nom", "Type", "Diamètre", "Longueur"])
        self.tool_table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tool_table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tool_table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tool_table.horizontalHeader().setStretchLastSection(True)
        self.tool_table.doubleClicked.connect(self.accept)
        
        layout.addWidget(self.tool_table)
        
        # Boutons d'action
        button_layout = QtGui.QHBoxLayout()
        
        # Bouton pour ajouter un outil
        self.add_tool_button = QtGui.QPushButton("Ajouter un outil")
        self.add_tool_button.clicked.connect(self.add_tool)
        button_layout.addWidget(self.add_tool_button)
        
        # Spacer pour pousser les boutons OK/Annuler à droite
        button_layout.addStretch()
        
        # Boutons standard
        button_box = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
    
    def load_tools(self):
        """Charge les outils depuis la base de données"""
        try:
            # Récupérer les outils
            db = ToolDatabase()
            self.tools = db.get_all_tools()
            
            # Ajouter les types d'outils au combobox
            types = set(tool.type for tool in self.tools)
            for tool_type in types:
                self.type_combo.addItem(tool_type, tool_type)
            
            # Remplir la table
            self.update_tool_table(self.tools)
            
            # Sélectionner l'outil actuel si défini
            if self.current_tool_id >= 0:
                for row in range(self.tool_table.rowCount()):
                    if int(self.tool_table.item(row, 0).text()) == self.current_tool_id:
                        self.tool_table.selectRow(row)
                        break
        except Exception as e:
            App.Console.PrintError(f"Erreur lors du chargement des outils: {str(e)}\n")
    
    def update_tool_table(self, tools):
        """Met à jour la table des outils avec la liste fournie"""
        self.tool_table.setRowCount(0)
        
        for tool in tools:
            row = self.tool_table.rowCount()
            self.tool_table.insertRow(row)
            
            # Ajouter les données de l'outil
            self.tool_table.setItem(row, 0, QtGui.QTableWidgetItem(str(tool.id)))
            self.tool_table.setItem(row, 1, QtGui.QTableWidgetItem(tool.name))
            self.tool_table.setItem(row, 2, QtGui.QTableWidgetItem(tool.type))
            self.tool_table.setItem(row, 3, QtGui.QTableWidgetItem(f"{tool.diameter:.2f} mm"))
            self.tool_table.setItem(row, 4, QtGui.QTableWidgetItem(f"{tool.length:.2f} mm"))
        
        # Ajuster les colonnes
        self.tool_table.resizeColumnsToContents()
    
    def filter_tools(self):
        """Filtre les outils en fonction du texte saisi"""
        filter_text = self.filter_edit.text().lower()
        selected_type = self.type_combo.currentData()
        
        if not filter_text and selected_type == "":
            # Aucun filtre, afficher tous les outils
            self.update_tool_table(self.tools)
            return
        
        # Filtrer les outils
        filtered_tools = [tool for tool in self.tools if 
                        (filter_text in tool.name.lower() or 
                        filter_text in tool.type.lower() or 
                        filter_text in str(tool.diameter)) and 
                        (selected_type == "" or tool.type == selected_type)]
        
        # Mettre à jour la table
        self.update_tool_table(filtered_tools)
    
    def add_tool(self):
        """Ouvre le dialogue pour ajouter un nouvel outil"""
        from BaptTools import ToolDialog
        dialog = ToolDialog(parent=self)
        result = dialog.exec_()
        
        if result == QtGui.QDialog.Accepted:
            # Ajouter l'outil à la base de données
            try:
                db = ToolDatabase()
                db.add_tool(dialog.tool)
                
                # Recharger la liste des outils
                self.load_tools()
                
                # Sélectionner le nouvel outil
                for row in range(self.tool_table.rowCount()):
                    if self.tool_table.item(row, 1).text() == dialog.tool.name:
                        self.tool_table.selectRow(row)
                        break
                
                App.Console.PrintMessage(f"Outil '{dialog.tool.name}' ajouté avec succès\n")
            except Exception as e:
                App.Console.PrintError(f"Erreur lors de l'ajout de l'outil: {str(e)}\n")
    
    def accept(self):
        """Valider la sélection"""
        selected_items = self.tool_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.selected_tool_id = int(self.tool_table.item(row, 0).text())
            self.selected_tool_name = self.tool_table.item(row, 1).text()
            super(ToolSelectorDialog, self).accept()
        else:
            # Aucune sélection, ne rien faire
            pass


class DrillOperationTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        
        # Créer l'interface utilisateur
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Opération de perçage")
        layout = QtGui.QVBoxLayout(self.form)
        
        # Créer un widget avec onglets
        self.tabs = QtGui.QTabWidget()
        layout.addWidget(self.tabs)
        
        # Onglet Général
        generalTab = QtGui.QWidget()
        generalLayout = QtGui.QVBoxLayout(generalTab)
        
        # Groupe pour la géométrie
        geometryGroup = QtGui.QGroupBox("Géométrie")
        geometryLayout = QtGui.QFormLayout()
        
        # Sélection de la géométrie
        self.geometryCombo = QtGui.QComboBox()
        self.updateGeometryList()
        geometryLayout.addRow("Géométrie de perçage:", self.geometryCombo)
        
        geometryGroup.setLayout(geometryLayout)
        generalLayout.addWidget(geometryGroup)
        
        # Groupe pour l'outil
        toolGroup = QtGui.QGroupBox("Outil")
        toolLayout = QtGui.QVBoxLayout()
        
        # Informations sur l'outil sélectionné
        self.toolInfoLayout = QtGui.QFormLayout()
        self.toolIdLabel = QtGui.QLabel("Aucun outil sélectionné")
        self.toolNameLabel = QtGui.QLabel("")
        self.toolTypeLabel = QtGui.QLabel("")
        self.toolDiameterLabel = QtGui.QLabel("")
        
        self.toolInfoLayout.addRow("ID:", self.toolIdLabel)
        self.toolInfoLayout.addRow("Nom:", self.toolNameLabel)
        self.toolInfoLayout.addRow("Type:", self.toolTypeLabel)
        self.toolInfoLayout.addRow("Diamètre:", self.toolDiameterLabel)
        
        toolLayout.addLayout(self.toolInfoLayout)
        
        # Bouton pour sélectionner un outil
        self.selectToolButton = QtGui.QPushButton("Sélectionner un outil")
        self.selectToolButton.clicked.connect(self.selectTool)
        toolLayout.addWidget(self.selectToolButton)
        
        toolGroup.setLayout(toolLayout)
        generalLayout.addWidget(toolGroup)
        
        # Ajouter l'onglet général
        self.tabs.addTab(generalTab, "Général")
        
        # Onglet Cycle
        cycleTab = QtGui.QWidget()
        cycleLayout = QtGui.QVBoxLayout(cycleTab)
        
        # Groupe pour le type de cycle
        cycleTypeGroup = QtGui.QGroupBox("Type de cycle")
        cycleTypeLayout = QtGui.QVBoxLayout()
        
        # Sélection du type de cycle
        self.cycleTypeCombo = QtGui.QComboBox()
        self.cycleTypeCombo.addItems(["Simple", "Peck", "Tapping", "Boring", "Reaming"])
        self.cycleTypeCombo.currentIndexChanged.connect(self.cycleTypeChanged)
        cycleTypeLayout.addWidget(self.cycleTypeCombo)
        
        cycleTypeGroup.setLayout(cycleTypeLayout)
        cycleLayout.addWidget(cycleTypeGroup)
        
        # Groupe pour les paramètres communs
        commonGroup = QtGui.QGroupBox("Paramètres communs")
        commonLayout = QtGui.QFormLayout()
        
        # Vitesse de broche
        self.spindleSpeed = QtGui.QSpinBox()
        self.spindleSpeed.setRange(1, 100000)
        self.spindleSpeed.setSingleStep(100)
        self.spindleSpeed.setSuffix(" tr/min")
        commonLayout.addRow("Vitesse de broche:", self.spindleSpeed)
        
        # Vitesse d'avance
        self.feedRate = QtGui.QSpinBox()
        self.feedRate.setRange(1, 10000)
        self.feedRate.setSingleStep(10)
        self.feedRate.setSuffix(" mm/min")
        commonLayout.addRow("Vitesse d'avance:", self.feedRate)
        
        # Mode de refroidissement
        self.coolantMode = QtGui.QComboBox()
        self.coolantMode.addItems(["Off", "Flood", "Mist"])
        commonLayout.addRow("Refroidissement:", self.coolantMode)
        
        commonGroup.setLayout(commonLayout)
        cycleLayout.addWidget(commonGroup)
        
        # Groupe pour les paramètres spécifiques
        self.specificGroup = QtGui.QGroupBox("Paramètres spécifiques")
        self.specificLayout = QtGui.QStackedLayout()
        
        # Widget pour le perçage simple (vide)
        simpleWidget = QtGui.QWidget()
        self.specificLayout.addWidget(simpleWidget)
        
        # Widget pour le perçage profond (Peck)
        peckWidget = QtGui.QWidget()
        peckLayout = QtGui.QFormLayout(peckWidget)
        
        self.peckDepth = QtGui.QDoubleSpinBox()
        self.peckDepth.setRange(0.1, 100.0)
        self.peckDepth.setSingleStep(0.5)
        self.peckDepth.setSuffix(" mm")
        peckLayout.addRow("Profondeur de passe:", self.peckDepth)
        
        self.retract = QtGui.QDoubleSpinBox()
        self.retract.setRange(0.1, 100.0)
        self.retract.setSingleStep(0.5)
        self.retract.setSuffix(" mm")
        peckLayout.addRow("Retrait:", self.retract)
        
        self.specificLayout.addWidget(peckWidget)
        
        # Widget pour le taraudage
        tappingWidget = QtGui.QWidget()
        tappingLayout = QtGui.QFormLayout(tappingWidget)
        
        self.threadPitch = QtGui.QDoubleSpinBox()
        self.threadPitch.setRange(0.1, 10.0)
        self.threadPitch.setSingleStep(0.1)
        self.threadPitch.setSuffix(" mm")
        tappingLayout.addRow("Pas de filetage:", self.threadPitch)
        
        self.specificLayout.addWidget(tappingWidget)
        
        # Widget pour l'alésage
        boringWidget = QtGui.QWidget()
        boringLayout = QtGui.QFormLayout(boringWidget)
        
        self.dwellTime = QtGui.QDoubleSpinBox()
        self.dwellTime.setRange(0.0, 10.0)
        self.dwellTime.setSingleStep(0.1)
        self.dwellTime.setSuffix(" s")
        boringLayout.addRow("Temps de pause:", self.dwellTime)
        
        self.specificLayout.addWidget(boringWidget)
        
        # Widget pour l'alésage de précision
        reamingWidget = QtGui.QWidget()
        self.specificLayout.addWidget(reamingWidget)
        
        self.specificGroup.setLayout(self.specificLayout)
        cycleLayout.addWidget(self.specificGroup)
        
        # Ajouter l'onglet cycle
        self.tabs.addTab(cycleTab, "Cycle")
        
        # Onglet Profondeur
        depthTab = QtGui.QWidget()
        depthLayout = QtGui.QVBoxLayout(depthTab)
        
        # Groupe pour le mode de profondeur
        depthModeGroup = QtGui.QGroupBox("Mode de profondeur")
        depthModeLayout = QtGui.QVBoxLayout()
        
        # Boutons radio pour le mode de profondeur
        self.absoluteRadio = QtGui.QRadioButton("Absolu")
        self.relativeRadio = QtGui.QRadioButton("Relatif")
        
        # Connecter les boutons radio
        self.absoluteRadio.toggled.connect(self.depthModeChanged)
        
        depthModeLayout.addWidget(self.absoluteRadio)
        depthModeLayout.addWidget(self.relativeRadio)
        
        depthModeGroup.setLayout(depthModeLayout)
        depthLayout.addWidget(depthModeGroup)
        
        # Groupe pour les paramètres de profondeur
        depthParamsGroup = QtGui.QGroupBox("Paramètres de profondeur")
        depthParamsLayout = QtGui.QFormLayout()
        
        # Profondeur finale
        self.finalDepth = QtGui.QDoubleSpinBox()
        self.finalDepth.setRange(-1000.0, 1000.0)
        self.finalDepth.setSingleStep(1.0)
        self.finalDepth.setSuffix(" mm")
        depthParamsLayout.addRow("Profondeur finale:", self.finalDepth)
        
        # Référence Z (pour le mode relatif)
        self.zReference = QtGui.QDoubleSpinBox()
        self.zReference.setRange(-1000.0, 1000.0)
        self.zReference.setSingleStep(1.0)
        self.zReference.setSuffix(" mm")
        self.zRefLabel = QtGui.QLabel("Référence Z:")
        depthParamsLayout.addRow(self.zRefLabel, self.zReference)
        
        # Hauteur de sécurité
        self.safeHeight = QtGui.QDoubleSpinBox()
        self.safeHeight.setRange(0.0, 1000.0)
        self.safeHeight.setSingleStep(1.0)
        self.safeHeight.setSuffix(" mm")
        depthParamsLayout.addRow("Hauteur de sécurité:", self.safeHeight)
        
        depthParamsGroup.setLayout(depthParamsLayout)
        depthLayout.addWidget(depthParamsGroup)
        
        # Ajouter l'onglet profondeur
        self.tabs.addTab(depthTab, "Profondeur")
        
        # Onglet Affichage
        displayTab = QtGui.QWidget()
        displayLayout = QtGui.QVBoxLayout(displayTab)
        
        # Groupe pour les paramètres d'affichage du fil
        pathLineGroup = QtGui.QGroupBox("Fil de parcours")
        pathLineLayout = QtGui.QFormLayout()
        
        # Option pour afficher/masquer le fil
        self.showPathLine = QtGui.QCheckBox()
        pathLineLayout.addRow("Afficher le fil:", self.showPathLine)
        
        # Hauteur du fil au-dessus des trous
        self.pathLineHeight = QtGui.QDoubleSpinBox()
        self.pathLineHeight.setRange(0.0, 100.0)
        self.pathLineHeight.setSingleStep(1.0)
        self.pathLineHeight.setSuffix(" mm")
        pathLineLayout.addRow("Hauteur du fil:", self.pathLineHeight)
        
        # Couleur du fil
        self.pathLineColorButton = QtGui.QPushButton()
        self.pathLineColorButton.setFixedSize(25, 25)
        self.pathLineColorButton.clicked.connect(self.selectPathLineColor)
        pathLineLayout.addRow("Couleur du fil:", self.pathLineColorButton)
        
        pathLineGroup.setLayout(pathLineLayout)
        displayLayout.addWidget(pathLineGroup)
        
        # Ajouter un espace extensible
        displayLayout.addStretch()
        
        # Ajouter l'onglet affichage
        self.tabs.addTab(displayTab, "Affichage")
        
        # Initialiser les valeurs depuis l'objet
        self.initValues()
        
        # Connecter les signaux
        self.geometryCombo.currentIndexChanged.connect(self.geometryChanged)

        self.pathLineHeight.valueChanged.connect(lambda: self.updateVisual())

    def updateVisual(self):
        """Mise à jour visuelle des paramètres"""
        self.obj.PathLineHeight = self.pathLineHeight.value()
    
    def geometryChanged(self, index):
        """Appelé quand la géométrie sélectionnée change"""
        if index < 0:
            return
        
        # Récupérer le nom de l'objet sélectionné
        objName = self.geometryCombo.itemData(index)
        if not objName:
            return
        
        # Récupérer l'objet
        obj = App.ActiveDocument.getObject(objName)
        if not obj:
            return
        
        # Mettre à jour les valeurs depuis la géométrie
        if hasattr(obj, "DrillDiameter"):
            # Mettre à jour la profondeur
            if hasattr(obj, "DrillDepth"):
                self.finalDepth.setValue(obj.DrillDepth.Value)
            
            # Trouver un outil correspondant au diamètre
            diameter = obj.DrillDiameter.Value
            try:
                db = ToolDatabase()
                tools = db.get_all_tools()
                
                bestTool = None
                bestDiff = float('inf')
                
                for tool in tools:
                    diff = abs(tool.diameter - diameter)
                    if diff < bestDiff:
                        bestDiff = diff
                        bestTool = tool
                
                # Sélectionner l'outil si trouvé
                if bestTool:
                    self.obj.ToolId = bestTool.id
                    self.updateToolInfo()
            except Exception as e:
                App.Console.PrintError(f"Erreur lors de la recherche d'un outil adapté: {str(e)}\n")
    
    def updateGeometryList(self):
        """Met à jour la liste des géométries de perçage disponibles"""
        self.geometryCombo.clear()
        
        # Parcourir tous les objets du document
        for obj in App.ActiveDocument.Objects:
            if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "Type") and obj.Proxy.Type == "DrillGeometry":
                self.geometryCombo.addItem(obj.Label, obj.Name)
        
        # Sélectionner la géométrie actuelle si elle existe
        if hasattr(self.obj, "DrillGeometryName") and self.obj.DrillGeometryName:
            index = self.geometryCombo.findData(self.obj.DrillGeometryName)
            if index >= 0:
                self.geometryCombo.setCurrentIndex(index)

    def selectTool(self):
        """Ouvre le dialogue de sélection d'outil"""
        dialog = ToolSelectorDialog(self.obj.ToolId, self.form)
        result = dialog.exec_()
        
        if result == QtGui.QDialog.Accepted and dialog.selected_tool_id >= 0:
            # Mettre à jour l'outil sélectionné
            self.obj.ToolId = dialog.selected_tool_id
            self.updateToolInfo()
    
    def updateToolInfo(self):
        """Met à jour les informations de l'outil sélectionné"""
        if self.obj.ToolId < 0:
            self.toolIdLabel.setText("Aucun outil sélectionné")
            self.toolNameLabel.setText("")
            self.toolTypeLabel.setText("")
            self.toolDiameterLabel.setText("")
            return
        
        try:
            # Récupérer l'outil depuis la base de données
            db = ToolDatabase()
            tools = db.get_all_tools()
            
            for tool in tools:
                if tool.id == self.obj.ToolId:
                    self.toolIdLabel.setText(str(tool.id))
                    self.toolNameLabel.setText(tool.name)
                    self.toolTypeLabel.setText(tool.type)
                    self.toolDiameterLabel.setText(f"{tool.diameter:.2f} mm")
                    self.obj.ToolName = f"{tool.name} (Ø{tool.diameter}mm)"
                    
                    # Si c'est un taraud, mettre à jour le pas de filetage
                    if tool.type.lower() == "taraud" and self.obj.CycleType == "Tapping":
                        self.threadPitch.setValue(tool.thread_pitch)
                    break
        except Exception as e:
            App.Console.PrintError(f"Erreur lors de la mise à jour des informations de l'outil: {str(e)}\n")
    
    def initValues(self):
        """Initialise les valeurs des widgets depuis l'objet"""
        # Onglet Cycle
        if hasattr(self.obj, "CycleType"):
            index = self.cycleTypeCombo.findText(self.obj.CycleType)
            if index >= 0:
                self.cycleTypeCombo.setCurrentIndex(index)
        
        # Mettre à jour les informations de l'outil
        self.updateToolInfo()
        
        if hasattr(self.obj, "SpindleSpeed"):
            self.spindleSpeed.setValue(self.obj.SpindleSpeed.Value)
        
        if hasattr(self.obj, "FeedRate"):
            self.feedRate.setValue(self.obj.FeedRate.Value)
        
        if hasattr(self.obj, "CoolantMode"):
            index = self.coolantMode.findText(self.obj.CoolantMode)
            if index >= 0:
                self.coolantMode.setCurrentIndex(index)
        
        if hasattr(self.obj, "PeckDepth"):
            self.peckDepth.setValue(self.obj.PeckDepth.Value)
        
        if hasattr(self.obj, "Retract"):
            self.retract.setValue(self.obj.Retract.Value)
        
        if hasattr(self.obj, "ThreadPitch"):
            self.threadPitch.setValue(self.obj.ThreadPitch.Value)
        
        if hasattr(self.obj, "DwellTime"):
            self.dwellTime.setValue(self.obj.DwellTime)
        
        # Onglet Profondeur
        if hasattr(self.obj, "DepthMode"):
            if self.obj.DepthMode == "Absolute":
                self.absoluteRadio.setChecked(True)
            else:
                self.relativeRadio.setChecked(True)
        
        if hasattr(self.obj, "FinalDepth"):
            self.finalDepth.setValue(self.obj.FinalDepth.Value)
        
        if hasattr(self.obj, "ZReference"):
            self.zReference.setValue(self.obj.ZReference.Value)
        
        if hasattr(self.obj, "SafeHeight"):
            self.safeHeight.setValue(self.obj.SafeHeight.Value)
        
        # Onglet Affichage
        if hasattr(self.obj, "ShowPathLine"):
            self.showPathLine.setChecked(self.obj.ShowPathLine)
        
        if hasattr(self.obj, "PathLineHeight"):
            self.pathLineHeight.setValue(self.obj.PathLineHeight.Value)
        
        if hasattr(self.obj, "PathLineColor"):
            color = QtGui.QColor()
            color.setRgbF(*self.obj.PathLineColor)
            self.pathLineColorButton.setStyleSheet(f"background-color: {color.name()}")
            self.selectedPathLineColor = self.obj.PathLineColor
        else:
            self.selectedPathLineColor = (0.0, 0.5, 1.0)  # Bleu clair par défaut
        
        # Mettre à jour l'affichage du mode de profondeur
        self.depthModeChanged(self.absoluteRadio.isChecked())

    def selectPathLineColor(self):
        """Ouvre un sélecteur de couleur pour le fil"""
        color = QtGui.QColorDialog.getColor(QtGui.QColor(*[int(c*255) for c in self.obj.PathLineColor]))
        if color.isValid():
            # Mettre à jour la couleur du bouton
            self.pathLineColorButton.setStyleSheet(f"background-color: {color.name()}")
            # Stocker la couleur pour l'appliquer lors de l'acceptation
            self.selectedPathLineColor = (color.redF(), color.greenF(), color.blueF())

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour la géométrie
        if self.geometryCombo.currentIndex() >= 0:
            objName = self.geometryCombo.itemData(self.geometryCombo.currentIndex())
            self.obj.DrillGeometryName = objName
        
        # Mettre à jour le type de cycle
        self.obj.CycleType = self.cycleTypeCombo.currentText()
        
        # Mettre à jour les paramètres communs
        self.obj.SpindleSpeed = self.spindleSpeed.value()
        self.obj.FeedRate = self.feedRate.value()
        self.obj.CoolantMode = self.coolantMode.currentText()
        
        # Mettre à jour les paramètres spécifiques
        self.obj.PeckDepth = self.peckDepth.value()
        self.obj.Retract = self.retract.value()
        self.obj.ThreadPitch = self.threadPitch.value()
        self.obj.DwellTime = self.dwellTime.value()
        
        # Mettre à jour le mode de profondeur
        self.obj.DepthMode = "Absolute" if self.absoluteRadio.isChecked() else "Relative"
        
        # Mettre à jour les paramètres de profondeur
        self.obj.FinalDepth = self.finalDepth.value()
        self.obj.ZReference = self.zReference.value()
        self.obj.SafeHeight = self.safeHeight.value()
        
        # Mettre à jour les paramètres d'affichage
        self.obj.ShowPathLine = self.showPathLine.isChecked()
        self.obj.PathLineHeight = self.pathLineHeight.value()
        self.obj.PathLineColor = self.selectedPathLineColor
        
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

    def cycleTypeChanged(self, index):
        """Appelé quand le type de cycle change"""
        # Mettre à jour l'affichage des paramètres spécifiques
        self.specificLayout.setCurrentIndex(index)

    def depthModeChanged(self, checked):
        """Appelé quand le mode de profondeur change"""
        # Mettre à jour la visibilité de la référence Z
        self.zRefLabel.setVisible(not checked)
        self.zReference.setVisible(not checked)
