import FreeCAD as App
import FreeCADGui as Gui
import BaptUtilities

try:
    from pivy import coin  # type: ignore
except ImportError:
    coin = None


class DrillGeometry:
    def __init__(self, obj):
        """Ajoute les propriétés"""

        self.Type = "DrillGeometry"

        # obj.addExtension("App::GroupExtensionPython")
        # obj.addExtension("App::DocumentObjectGroupPython")
        # obj.addExtension("App::LinkExtensionPython")

        # Référence aux faces sélectionnées
        if not hasattr(obj, "DrillFaces"):
            obj.addProperty("App::PropertyLinkSubList", "DrillFaces", "Drill", "Selected drill faces")

        # Liste des positions de perçage
        if not hasattr(obj, "DrillPositions"):  # TODO Renamer en HolePositions
            obj.addProperty("App::PropertyVectorList", "DrillPositions", "Drill", "Drill positions")

        # Diamètre des perçages (détecté automatiquement)
        if not hasattr(obj, "DrillDiameter"):
            obj.addProperty("App::PropertyLength", "DrillDiameter", "Drill", "Detected drill diameter")
            obj.setEditorMode("DrillDiameter", 1)  # en lecture seule

        # Profondeur des perçages (détectée automatiquement)
        if not hasattr(obj, "DrillDepth"):
            obj.addProperty("App::PropertyLength", "DrillDepth", "Drill", "Detected drill depth")
            obj.setEditorMode("DrillDepth", 1)  # en lecture seule

        # Index de la position sélectionnée (-1 si aucune)
        if not hasattr(obj, "SelectedPosition"):
            obj.addProperty("App::PropertyInteger", "SelectedPosition", "Display", "Index of the selected position")
            obj.SelectedPosition = -1

        obj.Proxy = self

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "DrillFaces":
            self.updateDrillParameters(obj)
        elif prop == "DrillPositions":
            self.execute(obj)

    def updateDrillParameters(self, obj):
        """Met à jour les paramètres de perçage en fonction des faces sélectionnées"""
        if not obj.DrillFaces:
            return

        positions = []
        diameters = set()
        depths = set()

        for link, subs in obj.DrillFaces:
            # Pour chaque sous-élément dans la liste
            for subname in subs:
                # Obtenir la face
                face = getattr(link.Shape, subname)

                if face.Surface.TypeId == 'Part::GeomCylinder':
                    # Récupérer le centre de la face cylindrique
                    center = face.Surface.Center
                    # axis = face.Surface.Axis

                    # Trouver le point le plus haut de la face
                    z_max = float('-inf')
                    for vertex in face.Vertexes:
                        if vertex.Point.z > z_max:
                            z_max = vertex.Point.z

                    # Créer le point au sommet en gardant X,Y du centre
                    pos = App.Vector(center.x, center.y, z_max)
                    positions.append(pos)

                    # Récupérer le diamètre
                    diameters.add(face.Surface.Radius * 2)
                    # App.Console.PrintMessage(f'diam detected {face.Surface.Radius * 2}\n')
                    # Calculer la profondeur en trouvant la face plane associée
                    # TODO: Implémenter la détection de profondeur
                    depths.add(10.0)  # valeur temporaire

        # Mettre à jour les propriétés
        obj.DrillPositions = positions

        # Si tous les perçages ont le même diamètre, le définir
        if len(diameters) == 1:
            obj.DrillDiameter = list(diameters)[0]
        elif len(diameters) > 1:
            # sinon prendre le plus petit
            obj.DrillDiameter = min(diameters)

        # Si tous les perçages ont la même profondeur, la définir
        if len(depths) == 1:
            obj.DrillDepth = list(depths)[0]

    def execute(self, obj):
        """Mettre à jour la shape (vide, la visualisation est dans le ViewProvider)"""
        pass
        # obj.Shape = Part.Shape()

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None

    def onBeforeDelete(self, obj, subelements):
        # Custom logic before deletion
        App.Console.PrintMessage("Object is about to be deleted: " + obj.Name + "\n")


class ViewProviderDrillGeometry:
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        self._addProperties(vobj)

    def _addProperties(self, vobj):
        """Ajoute les propriétés d'affichage si elles n'existent pas encore"""
        if not hasattr(vobj, "MarkerSize"):
            vobj.addProperty("App::PropertyLength", "MarkerSize", "Display", "Size of position markers")
            vobj.MarkerSize = 2.0

        if not hasattr(vobj, "MarkerColor"):
            vobj.addProperty("App::PropertyColor", "MarkerColor", "Display", "Color of position markers")
            vobj.MarkerColor = (1.0, 0.0, 0.0)

        if not hasattr(vobj, "HighlightColor"):
            vobj.addProperty("App::PropertyColor", "HighlightColor", "Display", "Color of the highlighted position")
            vobj.HighlightColor = (1.0, 1.0, 0.0)

    def getIcon(self):
        """Retourne l'icône"""
        return BaptUtilities.getIconPath("Tree_Drilling.svg")

    def attach(self, vobj):
        """Crée le scene graph coin3d pour les sphères"""
        self.Object = vobj.Object
        self._addProperties(vobj)
        self.markers = coin.SoSeparator()
        vobj.addDisplayMode(self.markers, "Markers")
        if self.Object:
            self._buildMarkers(vobj)

    def _buildMarkers(self, vobj):
        """Reconstruit les sphères coin3d à partir de DrillPositions"""
        if not hasattr(self, 'markers') or not coin:
            return
        self.markers.removeAllChildren()

        obj = getattr(self, 'Object', None)
        if not obj or not hasattr(obj, 'DrillPositions') or not obj.DrillPositions:
            return

        radius = float(vobj.MarkerSize) / 2.0
        if radius <= 0:
            return

        nc = vobj.MarkerColor
        hc = vobj.HighlightColor
        # App::PropertyColor peut retourner (r,g,b) ou (r,g,b,a)
        normal_rgb = (float(nc[0]), float(nc[1]), float(nc[2]))
        highlight_rgb = (float(hc[0]), float(hc[1]), float(hc[2]))
        selected = obj.SelectedPosition if hasattr(obj, 'SelectedPosition') else -1

        for i, pos in enumerate(obj.DrillPositions):
            sep = coin.SoSeparator()

            # Matériau (couleur)
            mat = coin.SoMaterial()
            if i == selected:
                mat.diffuseColor.setValue(*highlight_rgb)
                r = radius * 1.5
            else:
                mat.diffuseColor.setValue(*normal_rgb)
                r = radius
            sep.addChild(mat)

            # Position
            trans = coin.SoTranslation()
            trans.translation.setValue(float(pos.x), float(pos.y), float(pos.z))
            sep.addChild(trans)

            # Sphère
            sphere = coin.SoSphere()
            sphere.radius.setValue(float(r))
            sep.addChild(sphere)

            self.markers.addChild(sep)

        # Forcer le rafraîchissement de la scène 3D
        self.markers.touch()

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True

    def updateData(self, obj, prop):
        """Appelé quand une propriété de l'objet data est modifiée"""
        if prop in ["DrillPositions", "SelectedPosition"]:
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                self._buildMarkers(obj.ViewObject)

    def onChanged(self, vobj, prop):
        """Appelé quand une propriété du ViewProvider est modifiée"""
        if prop in ["MarkerSize", "MarkerColor", "HighlightColor"]:
            self._buildMarkers(vobj)

    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
        import Gui.DrillGeomTaskPanel as DrillGeomTaskPanel
        panel = DrillGeomTaskPanel.DrillGeometryTaskPanel(vobj.Object)
        Gui.Control.showDialog(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Fermer l'éditeur"""
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        return True

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        self.Object = None
        return None

    def claimChildren(self):
        """Retourne les enfants de cet objet"""
        if self.Object and hasattr(self.Object, "Group"):
            return list(self.Object.Group)
        return []

    def onDelete(self, feature, subelements):
        App.Console.PrintMessage(f"onDelete de {feature.Object.Name}\n")
        for child in feature.Object.Group:
            App.ActiveDocument.removeObject(child.Name)
        return True

    def onBeforeDelete(self, obj, subelements):
        """Supprime tous les enfants lors de la suppression du parent"""
        App.Console.PrintMessage(f"onBeforeDelete de {obj.Name}\n")
        children = self.claimChildren()
        for child in children:
            try:
                if child and hasattr(child, "Document") and child.Document:
                    child.Document.removeObject(child.Name)
            except Exception as e:
                App.Console.PrintError(f"Erreur suppression enfant {child.Name}: {e}\n")

    def getDisplayModes(self, obj):
        """Return a list of display modes."""
        return ["Markers"]

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode."""
        return "Markers"

    def setDisplayMode(self, mode):
        return mode
