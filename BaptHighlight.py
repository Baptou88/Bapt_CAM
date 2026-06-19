import BaptUtilities
import FreeCAD as App
import FreeCADGui as Gui
import Part

# source: https://github.com/FreeCAD/FreeCAD-macros/blob/master/Utility/HighlightCommon.FCMacro


class BaptHighlight:
    def __init__(self, obj):
        self.obj = obj

        if not hasattr(obj, "ObjectsToEnumerate"):
            obj.addProperty("App::PropertyLinkList", "ObjectsToEnumerate", "Highlight", "List of objects to highlight")

        obj.Proxy = self

    def onChanged(self, fp, prop):
        pass

    def execute(self, obj):

        # Ensure list of unique objects.
        object_list = []

        colli_count = 0  # Number of collisions found.
        colli_max = 0.0  # Maximum collision volume.
        obj.Shape = Part.Shape()  # Clear shape of the feature.
        collisions = []

        for item in obj.ObjectsToEnumerate:
            if ((item not in object_list)
                    and hasattr(item, 'Shape')
                    and hasattr(item, 'getGlobalPlacement')
                    and hasattr(item, 'Label')):
                object_list.append(item)

        if len(object_list) < 2:
            App.Console.PrintWarning('No suitable objects selected, select at least two objects\n')
            return

        # Going through selected objects (object A).
        for i, object_a in enumerate(object_list):
            shape_a = object_a.Shape.copy()
            shape_a.Placement = object_a.getGlobalPlacement()
            label_a = object_a.Label

            # Comparing object A with all
            # following ones in the list (object B).
            for object_b in object_list[(i + 1):]:

                shape_b = object_b.Shape.copy()
                shape_b.Placement = object_b.getGlobalPlacement()
                label_b = object_b.Label
                common = shape_a.common(shape_b)

                # If object A & object B have a collision
                # display a message with collision volume and
                # add a new representative shape in the group.
                if common.Volume > 1e-6:
                    App.Console.PrintMessage(
                        'Volume of the intersection between {} and {}: {:.3f} mm³\n'.format(
                            label_a,
                            label_b,
                            common.Volume))
                    colli_count += 1
                    colli_max = max(colli_max, common.Volume)
                    collisions.append(common)
                else:
                    App.Console.PrintMessage(
                        'No intersection between {} and {}\n'.format(
                            label_a,
                            label_b))

        # Build compound shape from all collision volumes.
        if collisions:
            obj.Shape = Part.makeCompound(collisions)
            App.Console.PrintMessage(
                '{} collision(s) found between selected objects\n'
                'Maximum collision volume: {:.3f} mm³\n'.format(
                    colli_count, colli_max))
        else:
            obj.Shape = Part.Shape()
            if len(object_list) >= 2:
                App.Console.PrintWarning('No collision found between selected objects\n')

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderBaptHighlight:
    def __init__(self, obj):
        self.obj = obj.Object
        obj.Proxy = self

    def attach(self, obj):
        self.obj = obj.Object
        obj.ShapeColor = (1.0, 0.0, 0.0, 1.0)

    def updateData(self, fp, prop):
        pass

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        return "Shaded"

    def setDisplayMode(self, mode):
        return mode

    def getIcon(self):
        """Retourne l'icône"""
        return BaptUtilities.getIconPath("HighlightCommon.svg")

    def dumps(self):
        return None

    def loads(self, state):
        return None


class CreateHighlightCommand:
    """Create Highlight object"""

    def GetResources(self):
        return {
            'MenuText': 'Highlight Collisions',
            'ToolTip': 'Create a Highlight object to detect and highlight collisions between selected objects',
            'Pixmap': BaptUtilities.getIconPath('BaptWorkbench.svg')
        }

    def IsActive(self):
        obj = Gui.activeView().getActiveObject("camproject")
        return obj is not None

    def Activated(self):
        doc = App.ActiveDocument

        sel = Gui.Selection.getSelection()

        obj = doc.addObject("Part::FeaturePython", "Highlight_Collisions")
        BaptHighlight(obj)
        if obj.ViewObject:
            ViewProviderBaptHighlight(obj.ViewObject)
        obj.ObjectsToEnumerate = sel
        doc.recompute()
