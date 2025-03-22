import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
from FreeCAD import Base
import BaptDrillTaskPanel

class DrillGeometry:
    def __init__(self, obj):
        """Ajoute les propriétés"""
        obj.Proxy = self
        self.Type = "DrillGeometry"
        
        # Référence aux faces sélectionnées
        obj.addProperty("App::PropertyLinkSubList", "DrillFaces", "Drill", "Selected drill faces")
        
        # Liste des positions de perçage (en lecture seule)
        obj.addProperty("App::PropertyVectorList", "DrillPositions", "Drill", "Drill positions")
        obj.setEditorMode("DrillPositions", 1)  # en lecture seule
        
        # Diamètre des perçages (détecté automatiquement)
        obj.addProperty("App::PropertyLength", "DrillDiameter", "Drill", "Detected drill diameter")
        obj.setEditorMode("DrillDiameter", 1)  # en lecture seule
        
        # Profondeur des perçages (détectée automatiquement)
        obj.addProperty("App::PropertyLength", "DrillDepth", "Drill", "Detected drill depth")
        obj.setEditorMode("DrillDepth", 1)  # en lecture seule

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "DrillFaces":
            self.updateDrillParameters(obj)

    def updateDrillParameters(self, obj):
        """Met à jour les paramètres de perçage en fonction des faces sélectionnées"""
        if not obj.DrillFaces:
            return

        positions = []
        diameters = set()
        depths = set()

        for sub in obj.DrillFaces:
            # sub[0] est l'objet parent, sub[1] est le nom de la face
            face = getattr(sub[0].Shape, sub[1])
            
            if face.Surface.TypeId == 'Part::GeomCylinder':
                # Récupérer le centre de la face cylindrique
                pos = face.Surface.Center
                positions.append(pos)
                
                # Récupérer le diamètre
                diameters.add(face.Surface.Radius * 2)
                
                # Calculer la profondeur en trouvant la face plane associée
                # TODO: Implémenter la détection de profondeur
                depths.add(10.0)  # valeur temporaire

        # Mettre à jour les propriétés
        obj.DrillPositions = positions
        
        # Si tous les perçages ont le même diamètre, le définir
        if len(diameters) == 1:
            obj.DrillDiameter = list(diameters)[0]
        
        # Si tous les perçages ont la même profondeur, la définir
        if len(depths) == 1:
            obj.DrillDepth = list(depths)[0]

    def execute(self, obj):
        """Ne rien faire lors de la reconstruction"""
        pass

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderDrillGeometry:
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        vobj.Proxy = self
        self.Object = vobj.Object
        
    def getIcon(self):
        """Retourne l'icône"""
        return os.path.join(App.getHomePath(), "Mod", "Bapt", "resources", "icons", "Tree_Drilling.svg")
        
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))
        return True

    def updateData(self, obj, prop):
        """Appelé quand une propriété de l'objet est modifiée"""
        pass

    def onChanged(self, vobj, prop):
        """Appelé quand une propriété du ViewProvider est modifiée"""
        pass

    def doubleClicked(self, vobj):
        """Gérer le double-clic"""
        self.setEdit(vobj)
        return True

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
        panel = BaptDrillTaskPanel.DrillGeometryTaskPanel(vobj.Object)
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
        return None
