# based on file "Path/Op/Gui/Base.py" and
# src/Mod/CAM/Path/Base/Gui/Util.py
import math

import FreeCAD as App
import FreeCADGui as Gui
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore
from utils import Log

DEBUG = False


class BQuantitySpinBox(QtCore.QObject):
    def __init__(self, obj, prop, widget=None):
        super().__init__()
        # try:
        self.obj = obj
        self.prop = prop
        if widget is not None:
            self.widget = widget
        else:
            self.widget = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
        self.attach(obj, prop)

    def attach(self, obj, prop):
        # App.Console.PrintMessage(f'Attach\n')
        # self.widget.setProperty("unit", "mm")
        attr = self.getProperty(obj, prop)  # getattr(obj, prop) semble etre equivalent
        if attr is not None:
            if hasattr(attr, "Value"):
                self.widget.setProperty("unit", attr.getUserPreferred()[2])

                self.widget.setProperty("rawValue", attr.Value)
            else:
                self.widget.setProperty("rawValue", attr)
        # self.widget.setProperty("Value", a)
            # if widget is  not None:
            if True:
                self.widget.setProperty("binding", "%s.%s" % (obj.Name, prop))
            else:
                Gui.ExpressionBinding(self.widget).bind(obj, prop)
        else:
            pass
            # self.widget.setProperty("exprSet", "true")
        # self.widget.style().unpolish(self.widget)
        # self.widget.ensurePolished()
        # Gui.ExpressionBinding(self.recouvrement).bind(self.obj,"Recouvrement")
        self.widget.installEventFilter(self)
        # self.widget.textChanged.connect(lambda: self.onWidgetValueChanged())
        self.widget.valueChanged.connect(lambda: self.updateValue())
        # except Exception as e:
        #     App.Console.PrintError("BQuantitySpinBox __init__ error: {}\n".format(e))

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.FocusIn:
            self.updateWidget()
        return False

    def getProperty(self, obj, prop):
        """getProperty(obj, prop) ... answer obj's property defined by its canonical name."""
        o, attr, name = self._getProperty(obj, prop)
        return attr

    def _getProperty(self, obj, prop):
        o = obj
        attr = obj
        name = None
        for name in prop.split("."):
            o = attr
            if not hasattr(o, name):
                break
            attr = getattr(o, name)

        if o == attr:
            # Path.Log.debug(translate("PathGui", "%s has no property %s (%s)") % (obj.Label, prop, name))
            return (None, None, None)

        # Path.Log.debug("found property %s of %s (%s: %s)" % (prop, obj.Label, name, attr))
        # App.Console.PrintMessage(f'found property {prop} of {obj.Label} ({name}: {attr})\n')
        return (o, attr, name)

    def updateWidget(self):
        expr = self._hasExpression()
        attr = self.getProperty(self.obj, self.prop)  # getattr(obj, prop) semble etre equivalent

        # self.widget.setProperty("rawValue", getattr(self.obj, self.prop))
        if attr is not None:
            if hasattr(attr, "Value"):
                self.widget.setProperty("unit", attr.getUserPreferred()[2])
                self.widget.setProperty("rawValue", attr.Value)
                # Log.baptDebug(f'update Widget {self.obj.Name}.{self.prop} Value={attr.Value} unit={attr.getUserPreferred()[2]}\n')
            else:
                self.widget.setProperty("rawValue", attr)
            self.widget.setProperty("binding", "%s.%s" % (self.obj.Name, self.prop))
            # Gui.ExpressionBinding(self.widget).bind(self.obj, self.prop)

        if expr:
            self.widget.setProperty("exprSet", "true")
            self.widget.style().unpolish(self.widget)
            self.widget.ensurePolished()
        else:
            self.widget.setProperty("exprSet", "false")
            self.widget.style().unpolish(self.widget)
            self.widget.ensurePolished()
        self.widget.update()

    def getWidget(self):
        return self.widget

    def updateValue(self):
        value = self.widget.property("rawValue")
        o, attr, name = self._getProperty(self.obj, self.prop)
        attrValue = attr.Value if hasattr(attr, "Value") else attr

        if DEBUG:
            Log.baptDebug(f'update Value current {attrValue} new {value}')
            Log.baptDebug(f'update Value o {o} attr {attr} name {name}')

        if attrValue != value:
            self.updateProperty()

            if o and name:
                if type(attr) == int:
                    value = int(value)
                setattr(o, name, value)
        # if hasattr(self.obj, self.prop):
        #     App.Console.PrintMessage(f'update Value hasattr\n')
        #     value = self.widget.property("rawValue")
        #     setattr(self.obj, self.prop, value)
        # # except Exception as e:
        # #     App.Console.PrintError("BQuantitySpinBox updateValue error: {}\n".format(e))

    def onWidgetValueChanged(self):
        App.Console.PrintMessage(f'Widget Value Changed\n')
        if hasattr(self.obj, self.prop):
            App.Console.PrintMessage(f'Widget Value Changed hasattr\n')
            value = self.widget.property("rawValue")
            setattr(self.obj, self.prop, value)
        # self.widget.editingFinished.emit()

    def updateProperty(self):
        return
        value = self.widget.property("rawValue")
        setattr(self.obj, self.prop, value)
        self.widget.update()
        pass

    def _hasExpression(self):
        for prop, exp in self.obj.ExpressionEngine:
            if prop == self.prop:
                return exp
        return None

    def setValue(self, value):
        attr = self.getProperty(self.obj, self.prop)
        if hasattr(self.obj, self.prop):
            setattr(self.obj, self.prop, value)
            self.updateWidget()
        # except Exception as e:
        #     App.Console.PrintError("BQuantitySpinBox setValue error: {}\n".format(e))


class BQuantitySpinBox2(QtCore.QObject):
    """Wrapper around Gui::QuantitySpinBox that binds to a FreeCAD property.

    Supports simple properties (e.g. "Length") and nested properties
    (e.g. "Placement.Base.x").  Handles expressions via the native
    binding mechanism of Gui::QuantitySpinBox.

    Public API
    ----------
    - updateWidget()   : sync Model -> UI   (call from setFields / updateData)
    - updateProperty() : sync UI -> Model   (call from getFields / accept)
    - attach(obj, prop): rebind to a (possibly new) object / property
    - getWidget()      : return the underlying Qt widget
    - setValue(value)   : programmatically set the property AND refresh the widget
    """

    def __init__(self, obj, prop, widget=None):
        super().__init__()
        self.obj = obj
        self.prop = prop
        self._updating = False  # guard against signal loops

        if widget is not None:
            self.widget = widget
        else:
            self.widget = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")

        self.widget.installEventFilter(self)

        try:
            self.widget.showFormulaDialog.connect(self._onFormulaDialogClosed)
        except AttributeError:
            pass  # signal may not exist on older FreeCAD builds

        self._bind()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def attach(self, obj, prop):
        """Re-bind this spin box to a (possibly new) object/property."""
        self.obj = obj
        self.prop = prop
        self._bind()

    def getWidget(self):
        """Return the underlying Gui::QuantitySpinBox widget."""
        return self.widget

    def updateWidget(self):
        """Sync Model -> UI.  Safe to call at any time (no signal loops)."""
        self._updating = True
        try:
            attr = self._getAttr()
            if attr is None:
                return
            expr = self._hasExpression()
            if expr:
                quantity = App.Units.Quantity(self.obj.evalExpression(expr))
            else:
                quantity = attr
            if hasattr(quantity, "Value"):
                self.widget.setProperty("unit", quantity.getUserPreferred()[2])
                self.widget.setProperty("rawValue", quantity.Value)
            else:
                self.widget.setProperty("rawValue", quantity)

            self._applyExpressionStyle()
        finally:
            self._updating = False

    def updateProperty(self):
        """Sync UI -> Model.  Skips write when the property is driven by
        an expression or when the value hasn't changed."""
        if self._hasExpression():
            # The expression owns the value; just refresh the style.
            self._applyExpressionStyle()
            return

        value = self.widget.property("rawValue")
        attr = self._getAttr()
        if attr is None:
            Log.baptError(f"updateProperty: could not resolve {self.obj.Name}.{self.prop}\n")
            return

        current = attr.Value if hasattr(attr, "Value") else attr
        if math.fabs(current - value) < 1e-6:
            Log.baptDebug(f"updateProperty: {self.prop} unchanged ({current})")
            return

        Log.baptDebug(f"updateProperty: {self.prop} {current} -> {value}")
        self._setAttr(value)

    def setValue(self, value):
        """Programmatically set the property value and refresh the widget."""
        self._setAttr(value)
        self.updateWidget()

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _bind(self):
        """Set up the native Gui::QuantitySpinBox binding and sync the widget."""
        attr = self._getAttr()
        if attr is not None:
            if hasattr(attr, "Value"):
                self.widget.setProperty("unit", attr.getUserPreferred()[2])
            self.widget.setProperty("binding", "%s.%s" % (self.obj.Name, self.prop))
        self.updateWidget()
        self.widget.textChanged.connect(self._textChanged)
        self.widget.valueChanged.connect(self._valueChanged)

    def eventFilter(self, obj, event):
        """Refresh the widget when it receives focus so the displayed value
        is always up-to-date (e.g. after an expression re-evaluation)."""
        if event.type() == QtCore.QEvent.Type.FocusIn:
            if not self._updating:
                self.updateWidget()
        return False

    def _onFormulaDialogClosed(self, isOpen):
        """Called when the formula dialog opens/closes.  On close we
        recompute the object so that the expression result is written
        to the property, then refresh the widget display."""
        if not isOpen:
            Log.baptDebug(f"Formula dialog closed for {self.obj.Name}.{self.prop}")
            # self.obj.touch()
            # self.obj.Document.recompute()
            # self.updateProperty()  # write the value from the widget to the property (handles unit conversions)
            self.updateWidget()

    # -- Property resolution (supports dotted paths) -------------------

    def _resolve(self):
        """Walk the dotted property path and return
        `(parent_obj, leaf_name, leaf_value)`
        or `(None, None, None)` when the path is invalid."""
        parent = self.obj
        attr = self.obj
        name = None
        for name in self.prop.split("."):
            parent = attr
            if not hasattr(parent, name):
                return (None, None, None)
            attr = getattr(parent, name)
        if parent is attr:
            return (None, None, None)
        return (parent, name, attr)

    def _getAttr(self):
        """Return the current value of the bound property (or None)."""
        _, _, attr = self._resolve()
        return attr

    def _setAttr(self, value):
        """Write *value* into the bound property, handling dotted paths."""
        parent, name, _ = self._resolve()
        if parent is not None and name is not None:
            setattr(parent, name, value)

    # -- Expression helpers --------------------------------------------

    def _hasExpression(self):
        """Return the expression string if the property is expression-driven,
        else `None`."""
        ee = getattr(self.obj, "ExpressionEngine", None)
        if ee is None:
            return None
        for prop, exp in ee:
            if prop == self.prop:
                return exp
        return None

    def _applyExpressionStyle(self):
        """Toggle the read-only / green-border style when an expression
        is active."""
        has_expr = self._hasExpression() is not None
        self.widget.setReadOnly(has_expr)
        self.widget.setProperty("exprSet", "true" if has_expr else "false")
        self.widget.style().unpolish(self.widget)
        self.widget.ensurePolished()

    def _textChanged(self):
        """Handle the textChanged signal from the widget by syncing the
        value back to the property."""
        Log.baptDebug(f"textChanged: {self.prop}")

    def _valueChanged(self):
        """Handle the valueChanged signal from the widget by syncing the
        value back to the property."""
        Log.baptDebug(f"valueChanged: {self.prop}")
