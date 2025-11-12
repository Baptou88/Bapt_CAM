# based on file "Path/Op/Gui/Base.py" and
# src/Mod/CAM/Path/Base/Gui/Util.py
import FreeCAD as App
import FreeCADGui as Gui
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

class BQuantitySpinBox(QtCore.QObject):
    def __init__(self,obj,prop):
        super().__init__()
        try:
            self.obj = obj
            self.prop = prop

            self.widget = Gui.UiLoader().createWidget("Gui::QuantitySpinBox")
            
            self.widget.setProperty("unit", "mm")
            self.widget.setProperty("rawValue", getattr(obj, prop))
            #self.widget.setProperty("binding","%s.%s" % (obj.Name, prop))
            Gui.ExpressionBinding(self.widget).bind(obj, prop)
            # self.widget.setProperty("exprSet", "true")
            # self.widget.style().unpolish(self.widget)
            # self.widget.ensurePolished()
            #Gui.ExpressionBinding(self.recouvrement).bind(self.obj,"Recouvrement")
            # self.widget.installEventFilter(self)
            self.widget.textChanged.connect(lambda: self.onWidgetValueChanged())
            self.widget.valueChanged.connect(lambda: self.updateValue())
        except Exception as e:
            App.Console.PrintError("BQuantitySpinBox __init__ error: {}\n".format(e))

    # def eventFilter(self, obj, event):
    #     if event.type() == QtCore.QEvent.Type.FocusIn:
    #         self.updateWidget()
    #     return False
    
    def updateWidget(self):
        expr = self._hasExpression()
        self.widget.setProperty("rawValue", getattr(self.obj, self.prop))
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
        try:
            value = self.widget.property("rawValue")
            setattr(self.obj, self.prop, value)
        except Exception as e:
            App.Console.PrintError("BQuantitySpinBox updateValue error: {}\n".format(e))

    def onWidgetValueChanged(self):
        App.Console.PrintMessage(f'Widget Value Changed\n')
        
        value = self.widget.property("rawValue")
        setattr(self.obj, self.prop, value)
        #self.widget.editingFinished.emit()

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