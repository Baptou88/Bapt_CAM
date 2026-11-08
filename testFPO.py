import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
import Path.Base.Gui.Util as PathGuiUtil
import Path.Op.Gui.Base as PathGuiBase
from utils import Log
from utils.BQuantitySpinBox import BQuantitySpinBox2


class MyObjectProxy:
    """Manages the properties and behavior of our custom object."""

    def __init__(self, obj):
        obj.Proxy = self
        self.Object = obj
        obj.addProperty("App::PropertyLength", "Length", "Data", "A length value synchronized across two views.")

    def opFeatures(self, obj):
        """
        Returns 0 to disable the default Path Workbench pages, giving us a clean slate.
        """
        return 0

    def onChanged(self, obj, prop):
        """Called by FreeCAD when a property changes. We use this to trigger recomputation."""
        if prop in ["Length", "Placement"]:
            App.Console.PrintMessage(f"Property '{prop}' changed to {obj.Length}\n")
            # obj.recompute()

    def sanitizeBase(self, obj):
        """
        This is a required method for the PathGuiBase.TaskPanel framework.
        It's called to clean up base geometry, which we aren't using.
        """
        pass

    def execute(self, obj):
        """Called by FreeCAD when the object needs to be recomputed."""
        App.Console.PrintMessage(f"Recomputing '{obj.Label}': Length is now {obj.Length.Value}\n")

    def dumps(self):
        return None

    def loads(self, state):
        return None


class MySinglePageTaskPanel(object):
    """
    The single, custom page for our TaskPanel. It creates the UI with two widgets
    and manages their synchronization with the 'Length' property.
    """

    def __init__(self, obj):
        self.obj = obj

        self.form = QtGui.QWidget()
        layout = QtGui.QFormLayout(self.form)
        self.length_widget1 = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
        self.length_widget2 = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
        self.length_widget3 = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
        self.length_sb1 = PathGuiUtil.QuantitySpinBox(self.length_widget1, self.obj, "Length")
        self.length_sb2 = PathGuiUtil.QuantitySpinBox(self.length_widget2, self.obj, "Placement.Base.x")
        self.length_sb3 = BQuantitySpinBox2(self.obj, "Length", self.length_widget3)
        layout.addRow("Length (CAM):", self.length_widget1)
        layout.addRow("Placement.Base.x (CAM):", self.length_widget2)
        layout.addRow("Length (View 3):", self.length_widget3)
        if obj.isDerivedFrom("Part::FeaturePython"):
            self.length_widget4 = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
            self.length_sb4 = BQuantitySpinBox2(self.obj, "Placement.Base.x", self.length_widget4)
            layout.addRow("Placement.Base.x:", self.length_widget4)
        self.signal()

    def getSignalsForUpdate(self, obj):
        signals = [self.length_widget1.editingFinished, self.length_widget2.editingFinished, self.length_widget3.editingFinished]
        if hasattr(self, "length_widget4"):
            signals.append(self.length_widget4.editingFinished)
        return signals

    def signal(self):
        for sig in self.getSignalsForUpdate(self.obj):
            sig.connect(lambda: self.editFinished(self.obj))

    def editFinished(self, obj):
        Log.baptDebug("editFinished called")
        self.getFields(obj)

    def setFields(self, obj):
        Log.baptDebug("setFields: Syncing Model -> UI")
        self.length_sb1.updateWidget()
        self.length_sb2.updateWidget()
        self.length_sb3.updateWidget()
        if hasattr(self, "length_sb4"):
            self.length_sb4.updateWidget()

    def getFields(self, obj):
        Log.baptDebug("getFields: Syncing UI -> Model")
        self.length_sb1.updateProperty()
        self.length_sb2.updateProperty()
        self.length_sb3.updateProperty()
        if hasattr(self, "length_sb4"):
            self.length_sb4.updateProperty()

    def updateData(self, obj, prop):
        if prop in ["Length", "Placement"]:
            Log.baptDebug(f"updateData called for prop: {prop}")
            self.setFields(obj)

    def reject(self, resetEdit=False):
        return True


class MyViewProvider:
    """Manages the GUI representation and editing task panel for our object."""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.vobj = vobj
        self.panel = None

    def attach(self, vobj):
        """Called when the view provider is attached to a view object."""
        self.vobj = vobj

        # Ensure 'panel' attribute exists for early updates. This prevents an
        # error if updateData is called before setEdit.
        self.panel = None

    def setEdit(self, vobj, mode=0):
        if mode == 0:
            self.panel = MySinglePageTaskPanel(vobj.Object)

            Gui.Control.showDialog(self.panel)
            return True
        return False

    def unsetEdit(self, vobj, mode=0):
        Log.baptDebug("unsetEdit called")
        if self.panel is not None:
            self.panel.reject(resetEdit=True)
            self.panel = None

    def updateData(self, fp_object, prop):
        """Forwards property changes from the object to the active TaskPanel."""
        if self.panel is not None:
            self.panel.updateData(fp_object, prop)

    def doubleClicked(self, vobj):
        """Handle double-click events on the object."""
        return self.setEdit(vobj, mode=0)

    def __getstate__(self): return None
    def __setstate__(self, state): return None

    def clearTaskPanel(self):
        ''' to satisfy API '''
        pass


def create():
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("SyncDemo")

    obj_name = "SyncDemo"
    obj = doc.getObject(obj_name)

    if not obj:
        obj = doc.addObject("Part::FeaturePython", obj_name)
        MyObjectProxy(obj)
        MyViewProvider(obj.ViewObject)
        obj.setExpression("Length", "10mm * 2")
        doc.recompute()
    else:
        if not hasattr(obj, "Proxy") or obj.Proxy is None:
            MyObjectProxy(obj)
        if not hasattr(obj.ViewObject, "Proxy") or obj.ViewObject.Proxy is None:
            MyViewProvider(obj.ViewObject)

    Gui.ActiveDocument.setEdit(obj.Name, 0)
