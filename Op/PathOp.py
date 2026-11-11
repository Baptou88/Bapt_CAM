import FreeCAD as App
import FreeCADGui as Gui

from BaptPath import GcodeAnimator
from Op.Gui.PathOpTaskPanel import PathOpTaskPanel
import BaptUtilities
from Op.BaseOp import baseOp, baseOpViewProviderProxy


class pathOp(baseOp):
    def __init__(self, obj):
        super().__init__(obj)
        self.Type = "Path"

        self.installToolProp(obj)
        if not hasattr(obj, "AttachmentSupport"):
            self.installAttachment(obj)
        obj.Proxy = self

    def installAttachment(self, obj):
        # obj.addExtension('App::GeoFeatureGroupExtensionPython')
        obj.addExtension('Part::AttachExtensionPython')
        obj.MapMode = 'ObjectXY'
        return

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return
        super().execute(obj)  # Appelle la logique de base (vérifications, etc.)

        if hasattr(obj, "AttachmentSupport"):
            obj.positionBySupport()
            pass

        return True

    def onChanged(self, fp, prop):
        return
        return super().onChanged(fp, prop)

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)


class pathOpViewProviderProxy(baseOpViewProviderProxy):
    def __init__(self, vobj):
        super().__init__(vobj)

        self.Object = vobj.Object
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object
        return super().attach(vobj)

    # def setupContextMenu(self, vobj, menu):
    #     return super().setupContextMenu(vobj, menu)

    def getDefaultDisplayMode(self):
        return super().getDefaultDisplayMode()

    def setDisplayMode(self, mode):
        return super().setDisplayMode(mode)

    def getDisplayModes(self, vobj):
        return super().getDisplayModes(vobj)

    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("PathOp.svg")

    def setEdit(self, vobj):
        # return super().setEdit(vobj)
        taskPanel = PathOpTaskPanel(vobj.Object)
        Gui.Control.showDialog(taskPanel)

        return True


class CreatePathCommand:
    """Commande pour créer une opération de chemin d'usinage"""

    def GetResources(self):
        return {'Pixmap': BaptUtilities.getIconPath("PathOp.svg"),
                'MenuText': "Créer une opération de chemin d'usinage",
                'ToolTip': "Créer une opération de chemin d'usinage"}

    def IsActive(self):
        doc = App.ActiveDocument
        if doc is None:
            return False
        cam_project = BaptUtilities.getActiveCamProject()

        return cam_project is not None

    def Activated(self):
        doc = App.ActiveDocument
        project = BaptUtilities.getActiveCamProject()
        if project is None:
            App.Console.PrintError("Aucun projet CAM actif. Veuillez sélectionner ou activer un projet CAM.\n")
            return
        doc.openTransaction('Créer une opération de chemin d\'usinage')

        obj = doc.addObject("Part::FeaturePython", "Path")

        pathOp(obj)

        # obj.Gcode ="G0 X0 Y-20 Z50\nG0 Z2\nG1 Z0 F500\nG1 Y-10\nG3 X-10 Y0 I-10 J0\nG1 X-48\nG2 X-50 Y2 I0 J2\nG1 Y20\nG91\nG1 X5\nG0 Z50\n"

        # obj.Gcode = "R1=10\nG0 X0 Y0 Z10\nG1 Z0 F500\nLABEL1:\nG91\nG1 Z-2\nG90\nG1 X16 Y0\nG3 X20 Y4 I0 J4 \nG1 X20 Y20\nG1 X0 Y20\nG1 X0 Y0\nREPEAT LABEL1 P=R1\nG0 Z10\n"
        obj.Gcode = "G0 X20 Y20 Z2\nG81 Z-20 R2\nG0 X30\nG80\nG0 X40\nG83 Z-30 R2 Q2"

        # Ajouter au groupe Operations
        operations_group = project.Proxy.getOperationsGroup(project)
        operations_group.addObject(obj)

        if App.GuiUp:
            pathOpViewProviderProxy(obj.ViewObject)
        doc.commitTransaction()

        doc.recompute()


def create():
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument()
    obj = doc.addObject("Part::FeaturePython", "Path")

    baseOp(obj)
    # obj.Gcode ="G0 X0 Y-20 Z50\nG0 Z2\nG1 Z0 F500\nG1 Y-10\nG3 X-10 Y0 I-10 J0\nG1 X-48\nG2 X-50 Y2 I0 J2\nG1 Y20\nG91\nG1 X5\nG0 Z50\nREPEAT LABEL1 P=2\n"

    obj.Gcode = "R1=10\nG0 X0 Y0 Z10\nG1 Z0 F500\nLABEL1:\nG91\nG1 Z-2\nG90\nG1 X10 Y0\nG1 X10 Y10\nG1 X0 Y10\nG1 X0 Y0\nREPEAT LABEL1 P=R1\nG0 Z10\n"
    baseOpViewProviderProxy(obj.ViewObject)

    vp = obj.ViewObject.Proxy
    vp.animator = GcodeAnimator(vp)
    vp.animator.load_paths(include_rapid=True)

    vp.animator.start(speed_mm_s=20.0)

    doc.recompute()
