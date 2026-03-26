import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui  # type: ignore

import BaptDrillGeometry
from BaptUtilities import find_cam_project
from Gui.cuttingConditionTaskPanel import cuttingConditionTaskPanel
from Op import DrillOp

from Tool.ToolsGUI import ToolTaskPanel
from utils import BQuantitySpinBox, PointSelectionObserver


class DrillOperationTaskPanel:
    def __init__(self, obj):
        # Garder une référence à l'objet
        self.obj = obj
        self._click_observer = None

        App.activeDocument().openTransaction("Edit Drill Operation Parameters")
        self.cuttingCondition = cuttingConditionTaskPanel(obj)

        ui1 = QtGui.QWidget()
        ui1.setWindowTitle("Opération de perçage")
        ui2 = ToolTaskPanel(obj, self)
        # Créer l'interface utilisateur
        # self.form = QtGui.QWidget()
        # self.form.setWindowTitle("Opération de perçage")
        self.form = [ui1, ui2.getForm()]
        layout = QtGui.QVBoxLayout(self.form[0])

        # Créer un widget avec onglets
        self.tabs = QtGui.QTabWidget()
        layout.addWidget(self.tabs)

        # Onglet Général
        generalTab = QtGui.QWidget()
        generalLayout = QtGui.QVBoxLayout(generalTab)

        # Groupe pour la Nom de l'opération
        nameGroup = QtGui.QGroupBox("Nom de l'opération")
        nameLayout = QtGui.QHBoxLayout()
        self.nameEdit = QtGui.QLineEdit()
        nameLayout.addWidget(self.nameEdit)
        nameGroup.setLayout(nameLayout)
        generalLayout.addWidget(nameGroup)
        self.nameEdit.setText(self.obj.Label)
        self.nameEdit.textChanged.connect(lambda text: setattr(self.obj, "Label", text))

        # Groupe pour la géométrie
        geometryGroup = QtGui.QGroupBox("Géométrie")
        geometryLayout = QtGui.QFormLayout()

        # Sélection de la géométrie
        self.geometryCombo = QtGui.QComboBox()
        self.updateGeometryList()
        geometryLayout.addRow("Géométrie de perçage:", self.geometryCombo)

        geometryGroup.setLayout(geometryLayout)
        generalLayout.addWidget(geometryGroup)

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
        self.cycleTypeCombo.addItems(DrillOp.cycleType)
        self.cycleTypeCombo.currentIndexChanged.connect(self.cycleTypeChanged)
        cycleTypeLayout.addWidget(self.cycleTypeCombo)

        cycleTypeGroup.setLayout(cycleTypeLayout)
        cycleLayout.addWidget(cycleTypeGroup)

        # Groupe pour les paramètres communs
        commonGroup = QtGui.QGroupBox("Paramètres communs")
        # commonLayout = QtGui.QFormLayout()
        commonLayout = self.cuttingCondition.getLayout()

        # # Vitesse de broche
        # self.spindleSpeed = BQuantitySpinBox.BQuantitySpinBox(obj,"SpindleSpeed")
        # # self.spindleSpeed = QtGui.QSpinBox()
        # # self.spindleSpeed.setRange(1, 100000)
        # # self.spindleSpeed.setSingleStep(100)
        # # self.spindleSpeed.setSuffix(" tr/min")
        # commonLayout.addRow("Vitesse de broche:", self.spindleSpeed.getWidget())

        # # Vitesse d'avance
        # self.feedRate = BQuantitySpinBox.BQuantitySpinBox(obj,"FeedRate")
        # # self.feedRate.setRange(1, 10000)
        # # self.feedRate.setSingleStep(10)
        # # self.feedRate.setSuffix(" mm/min")
        # commonLayout.addRow("Vitesse d'avance:", self.feedRate.getWidget())
        # commonLayout.addRow(self.cuttingCondition.getLayout())

        # # Mode de refroidissement
        # self.coolantMode = QtGui.QComboBox()
        # self.coolantMode.addItems(CoolantMode)
        # commonLayout.addRow("Refroidissement:", self.coolantMode)

        commonGroup.setLayout(commonLayout)
        cycleLayout.addWidget(commonGroup)

        # Groupe pour les paramètres spécifiques
        self.specificGroup = QtGui.QGroupBox("Paramètres spécifiques")
        self.specificLayout = QtGui.QStackedLayout()

        def createDwellTimeSpinBox():
            spinbox = QtGui.QDoubleSpinBox()
            spinbox.setRange(0.0, 10.0)
            spinbox.setSingleStep(0.1)
            spinbox.setSuffix(" s")
            spinbox.valueChanged.connect(self.syncDwellTimes)
            return spinbox

        # Widget pour le perçage simple (vide)
        simpleWidget = QtGui.QWidget()
        simpleLayout = QtGui.QFormLayout(simpleWidget)
        self.dwellTimeSimple = createDwellTimeSpinBox()
        simpleLayout.addRow("Temps de pause:", self.dwellTimeSimple)

        self.specificLayout.addWidget(simpleWidget)

        # Widget pour le perçage profond (Peck)
        peckWidget = QtGui.QWidget()
        peckLayout = QtGui.QFormLayout(peckWidget)

        # self.peckDepth = QtGui.QDoubleSpinBox()
        # self.peckDepth.setRange(0.1, 100.0)
        # self.peckDepth.setSingleStep(0.5)
        # self.peckDepth.setSuffix(" mm")
        self.peckDepth = BQuantitySpinBox.BQuantitySpinBox(obj, "PeckDepth")
        peckLayout.addRow("Profondeur de passe:", self.peckDepth.getWidget())

        # self.retract = QtGui.QDoubleSpinBox()
        # self.retract.setRange(0.1, 100.0)
        # self.retract.setSingleStep(0.5)
        # self.retract.setSuffix(" mm")
        self.retract = BQuantitySpinBox.BQuantitySpinBox(obj, "Retract")
        peckLayout.addRow("Retrait:", self.retract.getWidget())

        self.dwellTimePeck = createDwellTimeSpinBox()
        peckLayout.addRow("Temps de pause:", self.dwellTimePeck)
        self.specificLayout.addWidget(peckWidget)

        # Widget pour le taraudage
        tappingWidget = QtGui.QWidget()
        tappingLayout = QtGui.QFormLayout(tappingWidget)

        # self.threadPitch = QtGui.QDoubleSpinBox()
        # self.threadPitch.setRange(0.1, 10.0)
        # self.threadPitch.setSingleStep(0.1)
        # self.threadPitch.setSuffix(" mm")
        self.threadPitch = BQuantitySpinBox.BQuantitySpinBox(obj, "ThreadPitch")
        tappingLayout.addRow("Pas de filetage:", self.threadPitch.getWidget())

        self.specificLayout.addWidget(tappingWidget)

        # Widget pour l'alésage
        boringWidget = QtGui.QWidget()
        boringLayout = QtGui.QFormLayout(boringWidget)

        self.dwellTimeBoring = createDwellTimeSpinBox()
        boringLayout.addRow("Temps de pause:", self.dwellTimeBoring)

        self.specificLayout.addWidget(boringWidget)

        # Widget pour l'alésage de précision
        reamingWidget = QtGui.QWidget()
        self.specificLayout.addWidget(reamingWidget)

        # Widget pour le contournage
        contouringWidget = QtGui.QWidget()
        contouringLayout = QtGui.QFormLayout(contouringWidget)

        self.Ap = BQuantitySpinBox.BQuantitySpinBox(obj, "Ap")
        contouringLayout.addRow("Profondeur de passe (ap):", self.Ap.getWidget())
        self.Diam = BQuantitySpinBox.BQuantitySpinBox(obj, "Diam")
        contouringLayout.addRow("Diam:", self.Diam.getWidget())

        # btn pour recuperer le diametre
        self.selectDiamButton = QtGui.QPushButton("Sélectionner le diamètre")
        contouringLayout.addRow(self.selectDiamButton)

        self.specificLayout.addWidget(contouringWidget)

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
        self.finalDepth = BQuantitySpinBox.BQuantitySpinBox(obj, "FinalDepth")
        depthParamsLayout.addRow("Profondeur finale:", self.finalDepth.getWidget())

        # btn pour selectionner la profondeur finale Z
        self.selectFinalDepthButton = QtGui.QPushButton("Sélectionner la profondeur finale")
        depthParamsLayout.addRow(self.selectFinalDepthButton)

        # Référence Z (pour le mode relatif)
        self.zReference = BQuantitySpinBox.BQuantitySpinBox(obj, "ZReference")
        self.zRefLabel = QtGui.QLabel("Référence Z:")
        depthParamsLayout.addRow(self.zRefLabel, self.zReference.getWidget())

        # Hauteur de sécurité
        self.safeHeight = BQuantitySpinBox.BQuantitySpinBox(obj, "SafeHeight")
        depthParamsLayout.addRow("Hauteur de sécurité:", self.safeHeight.getWidget())

        depthParamsGroup.setLayout(depthParamsLayout)
        depthLayout.addWidget(depthParamsGroup)

        # Ajouter l'onglet profondeur
        self.tabs.addTab(depthTab, "Profondeur")

        # Initialiser les valeurs depuis l'objet
        self.initValues()

        # Connecter les signaux
        self.geometryCombo.currentIndexChanged.connect(self.geometryChanged)

        self.selectFinalDepthButton.clicked.connect(self.selectFinalDepth)
        self.selectDiamButton.clicked.connect(self.selectDiam)

        # u2.testButton.clicked.connect(lambda: u2.onTestButtonClicked())
        if self.obj.Tool:
            self.obj.Tool.Visibility = True

    def updateVisual(self):
        """Mise à jour visuelle des paramètres"""
        self.obj.SafeHeight = self.safeHeight.value()
        self.obj.FinalDepth = self.finalDepth.value()

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

    def updateGeometryList(self):
        """Met à jour la liste des géométries de perçage disponibles"""
        self.geometryCombo.clear()

        project = find_cam_project(self.obj)
        if project is not None:
            objList = project.Proxy.getGeometryGroup(project).Group
        else:
            objList = App.ActiveDocument.Objects
        # Parcourir tous les objets du document
        for obj in objList:
            if hasattr(obj, "Proxy") and isinstance(obj.Proxy, BaptDrillGeometry.DrillGeometry):
                self.geometryCombo.addItem(obj.Label, obj.Name)

        # Sélectionner la géométrie actuelle si elle existe
        drill_geom = getattr(self.obj, "DrillGeometry", None)
        geom_name = getattr(drill_geom, "Name", None) if drill_geom is not None else None
        if geom_name:
            index = self.geometryCombo.findData(geom_name)
            if index >= 0:
                self.geometryCombo.setCurrentIndex(index)

    def syncDwellTimes(self, value):
        """Synchronise toutes les valeurs dwellTime quand l'une change"""
        # Créer une liste de tous les widgets dwellTime
        dwellWidgets = [self.dwellTimeSimple, self.dwellTimePeck, self.dwellTimeBoring]

        # Trouver quel widget a la valeur actuelle (celui qui a changé)
        senderWidget = None
        for widget in dwellWidgets:
            if widget.value() == value and widget.hasFocus():
                senderWidget = widget
                break

        # Si on ne trouve pas via hasFocus(), on utilise une autre approche
        if senderWidget is None:
            # On met à jour tous les widgets qui n'ont pas déjà cette valeur
            for widget in dwellWidgets:
                if abs(widget.value() - value) > 0.001:  # Tolérance pour les flottants
                    widget.blockSignals(True)
                    widget.setValue(value)
                    widget.blockSignals(False)
        else:
            # Mettre à jour tous les autres widgets
            for widget in dwellWidgets:
                if widget != senderWidget:
                    widget.blockSignals(True)
                    widget.setValue(value)
                    widget.blockSignals(False)

    def initValues(self):
        """Initialise les valeurs des widgets depuis l'objet"""
        # Onglet Cycle
        if hasattr(self.obj, "CycleType"):
            index = self.cycleTypeCombo.findText(self.obj.CycleType)
            if index >= 0:
                self.cycleTypeCombo.setCurrentIndex(index)

        # if hasattr(self.obj, "SpindleSpeed"):
        #     self.spindleSpeed.setValue(self.obj.SpindleSpeed.Value)

        # if hasattr(self.obj, "FeedRate"):
        #     self.feedRate.setValue(self.obj.FeedRate.Value)

        # if hasattr(self.obj, "CoolantMode"):
        #     index = self.coolantMode.findText(self.obj.CoolantMode)
        #     if index >= 0:
        #         self.coolantMode.setCurrentIndex(index)

        # if hasattr(self.obj, "PeckDepth"):
        #     self.peckDepth.setValue(self.obj.PeckDepth.Value)

        # if hasattr(self.obj, "Retract"):
        #     self.retract.setValue(self.obj.Retract.Value)

        # if hasattr(self.obj, "ThreadPitch"):
        #     self.threadPitch.setValue(self.obj.ThreadPitch.Value)

        if hasattr(self.obj, "DwellTime"):
            # self.dwellTime.setValue(self.obj.DwellTime)
            for widget in [self.dwellTimeSimple, self.dwellTimePeck, self.dwellTimeBoring]:
                widget.blockSignals(True)
                widget.setValue(self.obj.DwellTime)
                widget.blockSignals(False)

        # Onglet Profondeur
        if hasattr(self.obj, "DepthMode"):
            if self.obj.DepthMode == "Absolute":
                self.absoluteRadio.setChecked(True)
            else:
                self.relativeRadio.setChecked(True)

        # if hasattr(self.obj, "FinalDepth"):
        #     self.finalDepth.setValue(self.obj.FinalDepth.Value)

        # if hasattr(self.obj, "ZReference"):
        #     self.zReference.setValue(self.obj.ZReference.Value)

        # if hasattr(self.obj, "SafeHeight"):
        #     App.Console.PrintMessage(f'safe height: {self.obj.SafeHeight}\n')
        #     self.safeHeight.setValue(self.obj.SafeHeight.Value)

        # Mettre à jour l'affichage du mode de profondeur
        self.depthModeChanged(self.absoluteRadio.isChecked())

    # def selectPathLineColor(self):
    #     """Ouvre un sélecteur de couleur pour le fil"""
    #     color = QtGui.QColorDialog.getColor(QtGui.QColor(*[int(c*255) for c in self.obj.PathLineColor]))
    #     if color.isValid():
    #         # Mettre à jour la couleur du bouton
    #         self.pathLineColorButton.setStyleSheet(f"background-color: {color.name()}")
    #         # Stocker la couleur pour l'appliquer lors de l'acceptation
    #         self.selectedPathLineColor = (color.redF(), color.greenF(), color.blueF())

    def accept(self):
        """Appelé quand l'utilisateur clique sur OK"""
        # Mettre à jour la géométrie (seulement si elle a changé, sinon
        # updateFromGeometry écraserait les valeurs de profondeur)
        if self.geometryCombo.currentIndex() >= 0:
            objName = self.geometryCombo.itemData(self.geometryCombo.currentIndex())
            geom = App.ActiveDocument.getObject(objName)
            if geom and geom != self.obj.DrillGeometry:
                self.obj.DrillGeometry = geom

        if self._click_observer is not None:
            self._click_observer.disable()
            self._click_observer = None

        # Mettre à jour le type de cycle
        self.obj.CycleType = self.cycleTypeCombo.currentText()

        # Mettre à jour les paramètres communs

        # Mettre à jour les paramètres spécifiques
        # self.obj.PeckDepth = self.peckDepth.value()
        # self.obj.Retract = self.retract.value()
        # self.obj.ThreadPitch = self.threadPitch.value()

        # Prendre la valeur du widget dwellTime visible actuellement
        if self.specificLayout.currentIndex() == 0:  # Simple
            self.obj.DwellTime = self.dwellTimeSimple.value()
        elif self.specificLayout.currentIndex() == 1:  # Peck
            self.obj.DwellTime = self.dwellTimePeck.value()
        elif self.specificLayout.currentIndex() == 3:  # Boring
            self.obj.DwellTime = self.dwellTimeBoring.value()
        else:
            # Fallback sur la première valeur
            self.obj.DwellTime = self.dwellTimeSimple.value()

        # Mettre à jour le mode de profondeur
        self.obj.DepthMode = "Absolute" if self.absoluteRadio.isChecked() else "Relative"

        # Mettre à jour les paramètres de profondeur

        # Mettre à jour les paramètres d'affichage
        # self.obj.ShowPathLine = self.showPathLine.isChecked()
        # self.obj.PathLineColor = self.selectedPathLineColor

        if self.obj.Tool:
            self.obj.Tool.Visibility = False

        # Recompute
        self.obj.Document.recompute()

        # Fermer la tâche
        Gui.Control.closeDialog()
        App.activeDocument().commitTransaction()
        return True

    def reject(self):
        """Appelé quand l'utilisateur clique sur Cancel"""
        if self._click_observer is not None:
            self._click_observer.disable()
            self._click_observer = None

        App.activeDocument().abortTransaction()
        if self.obj.Tool:
            self.obj.Tool.Visibility = False

        Gui.Control.closeDialog()
        return False

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return (QtGui.QDialogButtonBox.Ok |
                QtGui.QDialogButtonBox.Apply |
                QtGui.QDialogButtonBox.Cancel)

    def clicked(self, button):
        """clicked(button) ... callback invoked when the user presses any of the task panel buttons."""
        if button == QtGui.QDialogButtonBox.Apply:
            self.obj.recompute()

    def cycleTypeChanged(self, index):
        """Appelé quand le type de cycle change"""
        # Mettre à jour l'affichage des paramètres spécifiques
        self.specificLayout.setCurrentIndex(index)

    def depthModeChanged(self, checked):
        """Appelé quand le mode de profondeur change"""
        # Mettre à jour la visibilité de la référence Z
        self.zRefLabel.setVisible(not checked)
        self.zReference.widget.setVisible(not checked)
        pass

    def selectFinalDepth(self):
        """Permet à l'utilisateur de sélectionner la profondeur finale en cliquant sur une face ou un point dans la vue 3D"""
        # utilise un listener
        self._start_observer("FinaleDepth")
        self.selectFinalDepthButton.setEnabled(False)
        pass

    def selectDiam(self):
        """Permet à l'utilisateur de sélectionner le diamètre en cliquant sur une face ou un point dans la vue 3D"""
        # utilise un listener
        self._start_observer("Diam")
        self.selectDiamButton.setEnabled(False)
        pass

    def _start_observer(self, target):
        """Démarre un observer pour écouter les clics dans la vue 3D"""
        # Créer un observer qui écoute les clics dans la vue 3D
        if self._click_observer is not None:
            self._click_observer.disable()
            self._click_observer = None
        self._click_observer = PointSelectionObserver.PointSelectionObserver(
            callback=lambda point, document, obj, element, t=target: self._on_point_selected(document, obj, element, point, t)
        )
        self._click_observer.enable()

    def _on_point_selected(self, doc, obj, element, point, target):
        """Callback appelé quand un point est sélectionné dans la vue 3D"""
        App.Console.PrintMessage(f"Point sélectionné pour {target}: {point}\n")
        if target == "FinaleDepth":
            self.finalDepth.setValue(point.z)
        elif target == "Diam":
            App.Console.PrintMessage(f'{doc}-{obj}-{element}\n')
            sub = App.getDocument(doc).getObject(obj).getSubObject(element)
            # sub = obj.getSubObject(element)
            if sub.Surface.TypeId == 'Part::GeomCylinder':
                self.Diam.setValue(sub.Surface.Radius * 2)
        self._click_observer = None
        self.selectFinalDepthButton.setEnabled(True)
        self.selectDiamButton.setEnabled(True)
