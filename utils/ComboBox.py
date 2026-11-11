import FreeCAD as App  # type: ignore
from PySide import QtCore  # type: ignore


class ComboBox(QtCore.QObject):
    def __init__(self, obj, prop, widget, items):
        super().__init__()
        self.obj = obj
        self.prop = prop
        self.items = items
        self.widget = widget

        self.attach()

    def attach(self):
        self.widget.clear()
        self.widget.addItems(self.items)
        self.setCurrentIndexFromProperty()
        self.widget.currentIndexChanged.connect(self.on_index_changed)

    def updateWidget(self):
        self.setCurrentIndexFromProperty()

    def setCurrentIndexFromProperty(self):
        value = getattr(self.obj, self.prop, None)
        if value in self.items:
            self.widget.setCurrentIndex(self.items.index(value))

    def getWidget(self):
        return self.widget

    def on_index_changed(self, index):
        App.Console.PrintMessage(f"ComboBox: on_index_changed called for index {index}\n")
        index = self.widget.currentIndex()
        if index < 0 or index >= len(self.items):
            return
        setattr(self.obj, self.prop, self.items[index])
        self.setCurrentIndexFromProperty()
