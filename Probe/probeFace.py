import FreeCAD as App
import FreeCADGui as Gui
from Op.BaseOp import baseOp, baseOpViewProviderProxy
from PySide import QtCore, QtGui
import BaptUtilities
import Part
from Tool import ToolSelectorDialog
from Tool.ToolsGUI import ToolTaskPanel
from utils import GcodeWriter
from utils.BQuantitySpinBox import BQuantitySpinBox


class ProbeFace(baseOp):
    def __init__(self, obj):
        super().__init__(obj)
        obj.addProperty("App::PropertyLinkSub", "Face", "Base", "Face à mesurer")
        obj.addProperty("App::PropertyVector", "Origin", "Base", "Point d'origine")
        obj.addProperty("App::PropertyVector", "Direction", "Base", "Direction de l'outil")
        obj.addProperty("App::PropertyVector", "UV", "Base", "UV")
        obj.addProperty("App::PropertyLength", "NormalLength", "Base", "Longueur de la normal")
        obj.NormalLength = 10

        self.installToolProp(obj)

        obj.Proxy = self

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return

        shape = Part.Shape()
        gcodeWriter = GcodeWriter.GcodeWriter()

        if not obj.Face or not obj.Origin or not obj.Direction:
            return

        if obj.Direction == App.Vector(0, 0, 0):
            return

        print(obj.Face)
        # surface = App.getDocument(obj.Face[0].Document).getObject(obj.Face[0].Object).Shape.getElement(obj.Face[1])
        # obj.Direction = surface.normalAt(0, 0)

        Sphere = Part.makeSphere(1, obj.Origin)
        print(f'obj.Origin: {obj.Origin}')
        print(f'obj.Direction: {obj.Direction}')
        ptApproche = obj.Origin + (obj.Direction * obj.NormalLength)
        print(f'obj.Direction * 10: {ptApproche}')
        gcodeWriter.linearMove({'X': ptApproche.x, 'Y': ptApproche.y}, rapid=True)
        gcodeWriter.linearMove({'Z': ptApproche.z + 10}, rapid=True)
        gcodeWriter.linearMove({'Z': ptApproche.z}, feed=100)

        gcodeWriter.lines.append(f"G38.2 X{obj.Origin.x:.3f} Y{obj.Origin.y:.3f} Z{obj.Origin.z:.3f} F100")
        # gcodeWriter.lines.append(f"G92.1 Z{obj.Origin.z:.3f}")

        # return to approach point
        gcodeWriter.linearMove({'X': ptApproche.x, 'Y': ptApproche.y, 'Z': ptApproche.z}, feed=500, force=True)

        gcodeWriter.lines.append("; #5070 set to 1 to indicate probe success")
        gcodeWriter.lines.append("; #5061 to #5069 can be used to store the measured position if needed")

        Normal = Part.makeLine(obj.Origin, obj.Origin + (obj.Direction * obj.NormalLength))
        normalWire = Part.Wire([Normal])
        compound = Part.makeCompound([Sphere, normalWire])
        obj.Shape = compound
        obj.Gcode = "\n".join(gcodeWriter.lines)
        obj.TimeEstimate = gcodeWriter.time_estimate
        obj.LastCoordinate = App.Vector(gcodeWriter.current_position['X'], gcodeWriter.current_position['Y'], gcodeWriter.current_position['Z'])

        pass

    def onChanged(self, obj, prop):
        if prop in ["Face", "Origin", "Direction", "NormalLength", "UV"]:
            self.execute(obj)
        pass

    def onDocumentRestored(self, obj):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        print(f"state: {state}")
        return None


class ViewProviderProbeFace(baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        if self.Object.Active:
            return BaptUtilities.getIconPath("ProbeSurface.svg")
        return BaptUtilities.getIconPath("operation_disabled.svg")

    def attach(self, vobj):
        super().attach(vobj)
        self.Object = vobj.Object

    def setupContextMenu(self, vobj, menu):
        super().setupContextMenu(vobj, menu)
        action_edit_gcode = QtGui.QAction(QtGui.QIcon(BaptUtilities.getIconPath("GcodeFile.svg")), "edit Gcode", menu)
        QtCore.QObject.connect(action_edit_gcode, QtCore.SIGNAL("triggered()"), lambda: self.viewGcode(vobj))
        menu.addAction(action_edit_gcode)
        return
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))

    def setEdit(self, vobj):
        """Démarrer l'édition"""
        Gui.Control.showDialog(ProbeFaceTaskPanel(vobj.Object))
        return True

    def unsetEdit(self, vobj):
        """Fermer l'édition"""
        Gui.Control.closeDialog()
        return True

    def doubleClicked(self, vobj):
        """Appelé lorsque l'objet est double-cliqué"""
        # Ouvrir le panneau de tâche pour l'édition
        self.setEdit(vobj)
        return True

    # def getDisplayModes(self, vobj):
    #     """Retourne les modes d'affichage disponibles"""
    #     return ["Flat Lines", "Shaded", "Wireframe"]

    # def getDefaultDisplayMode(self):
    #     """Retourne le mode d'affichage par défaut"""
    #     return "Flat Lines"

    # def setDisplayMode(self, mode):
    #     """Définit le mode d'affichage"""
    #     return mode


class ProbeFaceTaskPanel:
    def __init__(self, obj):
        self.obj = obj

        ui2 = ToolTaskPanel(obj)

        # Créer l'interface utilisateur
        self.ui1 = QtGui.QWidget()
        self.ui1.setWindowTitle("Éditer le cycle")

        self.form = [self.ui1, ui2.getForm()]

        layout = QtGui.QVBoxLayout(self.ui1)

        # bouton pour la selection de la face
        self.selectFaceButton = QtGui.QPushButton("Sélectionner la face")
        self.selectFaceButton.clicked.connect(self.selectFace)
        layout.addWidget(self.selectFaceButton)

        # champ pour l'origine
        self.originLabel = QtGui.QLabel("Origine:")
        layout.addWidget(self.originLabel)
        self.originEdit = QtGui.QLineEdit()
        layout.addWidget(self.originEdit)

        # champ pour la direction
        self.directionLabel = QtGui.QLabel("Direction:")
        self.direction = QtGui.QLabel()
        layout.addWidget(self.directionLabel)
        self.direction = QtGui.QLabel()
        layout.addWidget(self.direction)

        # champ pour la longueur de la normal
        self.normalLengthLabel = QtGui.QLabel("Longueur de la normal:")
        self.normalLengthEdit = BQuantitySpinBox(obj, "NormalLength")
        layout.addWidget(self.normalLengthLabel)
        layout.addWidget(self.normalLengthEdit.getWidget())

        self.updateUI()

    def updateUI(self):
        """Mettre à jour l'interface utilisateur avec les valeurs de l'objet"""
        # if self.obj.Origin:
        #     self.originEdit.setText(f"{self.obj.Origin.x:.3f}, {self.obj.Origin.y:.3f}, {self.obj.Origin.z:.3f}")
        # else:
        #     self.originEdit.setText("")

        if self.obj.Direction:
            self.direction.setText(f"{self.obj.Direction.x:.3f}, {self.obj.Direction.y:.3f}, {self.obj.Direction.z:.3f}")
        else:
            self.direction.setText("")

    def selectFace(self):
        """Sélectionner la face"""
        Gui.Selection.clearSelection()

        self.surfaceSelectionObserver = SurfaceSelectionObserver(self.onSelection)
        self.surfaceSelectionObserver.enable()

    def onSelection(self, doc, obj, sub, pos):
        """Appelé quand l'utilisateur sélectionne quelque chose"""
        print(f"Selection: {obj} {sub}")
        # self.obj.Face = App.getDocument(doc).getObject(obj).Shape.getElement(sub)
        self.obj.Face = (App.getDocument(doc).getObject(obj), [sub])
        self.obj.Origin = pos

        # face2 = App.getDocument(doc).getObject(obj).Shape.getSubObject(sub)
        print(self.obj.Face)
        print(self.obj.Face[0])
        surface = App.getDocument(doc).getObject(obj).Shape.getElement(sub)
        print(f"surface: {surface}")
        u, v = surface.Surface.parameter(pos)
        print(f"u,v: {u},{v}")
        self.obj.UV = App.Vector(u, v, 0)
        # print(App.getDocument(doc).getObject(obj).Shape.getElement(sub))
        # self.obj.Face[0].CenterOfMass()

        # self.obj.Direction = obj.Shape.getElement(sub).NormalAt(0, 0)
        # self.obj.Direction = self.obj.Face[0].NormalAt(0, 0)
        # self.obj.Direction = self.obj.Face[0].Shape.getElement(sub).NormalAt(0, 0)
        self.obj.Direction = surface.normalAt(u, v)

        self.surfaceSelectionObserver.disable()

        self.updateUI()

    def confirmSelection(self):
        """Confirmer la sélection"""

    def reject(self):
        """Rejeter la sélection"""
        if hasattr(self, "surfaceSelectionObserver"):
            self.surfaceSelectionObserver.disable()
        Gui.Control.closeDialog()

    def accept(self):
        """Accepter la sélection"""
        if hasattr(self, "surfaceSelectionObserver"):
            self.surfaceSelectionObserver.disable()
        Gui.Control.closeDialog()


class SurfaceSelectionObserver:
    def __init__(self, callback):
        self.callback = callback
        self.active = False

    def enable(self):
        """Activer l'observer"""
        self.active = True
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Face")
        Gui.Selection.addObserver(self)
        App.Console.PrintMessage("Observer activé. Cliquez sur une face de la pièce.\n")

    def disable(self):
        """Désactiver l'observer"""
        self.active = False
        Gui.Selection.removeObserver(self)
        Gui.Selection.removeSelectionGate()
        App.Console.PrintMessage("Observer désactivé.\n")

    def addSelection(self, document, object, element, position):
        """Appelé quand l'utilisateur sélectionne quelque chose"""
        if not self.active:
            return

        # Récupérer les coordonnées du point sélectionné
        point = App.Vector(position[0], position[1], position[2])
        App.Console.PrintMessage(f"Point sélectionné: {point.x}, {point.y}, {point.z}\n")

        # Appeler le callback avec le point
        self.callback(document, object, element, point)

        # Désactiver l'observer après la sélection
        self.disable()
