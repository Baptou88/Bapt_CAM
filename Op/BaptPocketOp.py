import FreeCAD as App, FreeCADGui as Gui
import Part
from PySide import QtGui, QtCore
import sys
import traceback
import BaptUtilities
from utils import BQuantitySpinBox

pocketFillMode = ["offset","zigzag","spirale"]

class PocketOperation:
    """
    Opération d'usinage de poche basée sur ContourGeometry.
    Génère un chemin d'usinage à partir du centre avec un facteur de recouvrement.
    """
    def __init__(self, obj):
        self.Type = "PocketOperation"
        self.initProperties(obj)
        obj.Proxy = self

    def initProperties(self, obj):
        obj.addProperty("App::PropertyLink", "Contour", "Pocket", "ContourGeometry de la poche")
        obj.addProperty("App::PropertyFloat", "Overlap", "Pocket", "Facteur de recouvrement (0.1-0.9)").Overlap = 0.5
        obj.addProperty("App::PropertyFloat", "ToolDiameter", "Pocket", "Diamètre outil (mm)").ToolDiameter = 6.0
        obj.addProperty("App::PropertyFloat", "StepDown", "Pocket", "Profondeur de passe (mm)").StepDown = 2.0
        obj.addProperty("App::PropertyFloat", "FinalDepth", "Pocket", "Profondeur finale (mm)").FinalDepth = -10.0
        
        obj.addProperty("App::PropertyEnumeration", "FillMode", "Pocket", "Mode de remplissage").FillMode = pocketFillMode
        obj.FillMode = pocketFillMode[0]

        obj.addProperty("Part::PropertyPartShape", "Path", "Pocket", "Chemin d'usinage généré")

        obj.addProperty("App::PropertyInteger", "maxGeneration", "Pocket", "Nombre maximum de générations d'offset").maxGeneration = 2

        if not hasattr(obj, "desactivated"):
            obj.addProperty("App::PropertyBool", "desactivated", "General", "Désactiver le cycle")
            obj.desactivated = False

    def onChanged(self, vobj, prop):
        if prop in ["Overlap", "ToolDiameter", "StepDown", "FinalDepth", "FillMode", "Contour", "maxGeneration"]:
            self.execute(vobj)

    def is_shape_valid(self, shape):
        # Vérifie que la shape est utilisable pour le pocketing
        if not shape:
            return False
        if not hasattr(shape, 'BoundBox') or not shape.BoundBox:
            App.Console.PrintError("PocketOperation: pas de boundBox.\n")
            return False
        if hasattr(shape, 'Wires') and shape.Wires:
            for wire in shape.Wires:
                if wire.isClosed():
                    return True
            return False
        return False

    def collectEdges(self,obj):
        # Collecter toutes les arêtes sélectionnées
        edges = []
        for sub in obj.Edges:
            obj_ref = sub[0]  # L'objet référencé
            sub_names = sub[1]  # Les noms des sous-éléments (arêtes)
            
            for sub_name in sub_names:
                if "Edge" in sub_name:
                    try:
                        edge = obj_ref.Shape.getElement(sub_name)
                        edges.append(edge)
                        #App.Console.PrintMessage(f"Arête ajoutée: {sub_name} de {obj_ref.Name}\n")
                    except Exception as e:
                        App.Console.PrintError(f"Execute : Erreur lors de la récupération de l'arête {sub_name}: {str(e)}\n")
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
        App.Console.PrintMessage(f'nb collecté {len(edges)}\n')
        return edges
            
    def execute(self, obj):
        # Chercher le parent ContourGeometry dans l'arborescence
        try:
            # parent = None
            # for p in obj.InList:
            #     if hasattr(p, "Proxy") and getattr(p.Proxy, "Type", "") == "ContourGeometry":
            #         parent = p
            #         break
                
            # if not parent or not hasattr(parent, "Shape"):
            #     App.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
            #     obj.Path = None
            #     return
            
            # shape = parent.Shape

            shape = obj.Contour.Shape if obj.Contour and hasattr(obj.Contour, "Shape") else None
            
            if not shape:
                App.Console.PrintError("PocketOperation: Aucun parent ContourGeometry valide trouvé.\n")
                obj.Shape = None
                return
            
            if not self.is_shape_valid(shape):
                App.Console.PrintError("PocketOperation: Shape du parent ContourGeometry invalide ou non fermée.\n")
                obj.Path = None
                return
            
            tool_diam = obj.ToolDiameter
            overlap = obj.Overlap

            # spheres pour marquer le debut du contour
            spheres  = []
            
            # Génération du chemin selon le mode choisi
            if hasattr(obj, 'FillMode') and obj.FillMode == "zigzag":
                path = self.generate_zigzag_path(shape, tool_diam, overlap)
            
            elif hasattr(obj, 'FillMode') and obj.FillMode == "offset":
                edges = self.collectEdges(obj.Contour)

                path = self.generate_offset_path(edges, tool_diam, overlap, obj.maxGeneration)

                

                
                for i in range(len(path)):
                    edge = path[i].Wires[0].Edges[0]
                    #recupere le premier point
                    start_point = edge.Vertexes[0].Point
                    end_point = edge.Vertexes[-1].Point
                    u1,v1 = edge.ParameterRange
                    mid_param = (u1 + v1)/2
                    mid_point = edge.valueAt(mid_param)
                    #ajoute une sphere au millieu
                    App.Console.PrintMessage(f"start {start_point}, end {end_point} mid {mid_point}\n")
                    sphere = Part.makeSphere(tool_diam/4, mid_point)
                    spheres.append(sphere)
            else:
                path = self.generate_spiral_path(shape, tool_diam, overlap)
            # obj.Path = path if path else None

            if path is None:
                App.Console.PrintError("PocketOperation: Échec de la génération du chemin d'usinage.\n")
                obj.Shape = Part.Shape()
                return
            a = path
            for s in spheres:
                a.append(s)
            compound = Part.makeCompound(a)
            #Part.show(compound)
            obj.Shape = compound
        except Exception as e:
            App.Console.PrintError(f"Erreur offset: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            

    def generate_zigzag_path(self, shape, tool_diam, overlap):
        # On suppose une poche plane, contour fermé
        if not shape or not shape.BoundBox:
            return None
        bbox = shape.BoundBox
        xmin, xmax = bbox.XMin, bbox.XMax
        ymin, ymax = bbox.YMin, bbox.YMax
        pas = tool_diam * (1 - overlap)
        lines = []
        y = ymin + tool_diam/2
        direction = 1
        while y <= ymax - tool_diam/2:
            # Cherche intersections entre la ligne y et la poche
            section = shape.slice(App.Vector(0, 0, 1), y)
            if section and hasattr(section, 'Edges'):
                for edge in section.Edges:
                    p1, p2 = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
                    if direction == 1:
                        lines.append(Part.makeLine(p1, p2))
                    else:
                        lines.append(Part.makeLine(p2, p1))
            y += pas
            direction *= -1
        if lines:
            return Part.Wire(lines)
        return None

    def generate_offset_path(self,shape, tool_diam, overlap, maxGen):
        # Génère un offset intérieur de la forme
        path_edges = []
        try:
            
            current = Part.Wire(shape)

            offset_dist = tool_diam * (1 - overlap)
            generation = 0
            while True:
                generation += 1
                offset = current.makeOffset2D(-offset_dist, join=0, fill=False, openResult=False)

                current = offset

                # on arrete si l'offset n'est plus fermé ou trop petit
                if offset is None:
                    App.Console.PrintMessage("Offset nul, fin de génération.\n")
                    break

                if not offset or not hasattr(offset, 'Wires') or not offset.Wires:
                    App.Console.Warning("PocketOperation: Offset invalide ou vide.\n")
                    break
                    return None

                path_edges.append(offset)
                
                if generation >= maxGen: break
                
            App.Console.PrintMessage(f"Offset généré: nb {len(path_edges)}\n")
            return  path_edges

        except Exception as e:
            # import json
            # j = json.loads(e)
            # if  j['sErrMsg'] == "makeOffset2D: offset result has no wires.":
            #     App.Console.PrintMessage(f"Erreur offset gen: {generation}: {e.sErrMsg}\n")
            #     return path_edges
            App.Console.PrintError(f"Erreur offset gen: {generation}: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return path_edges
        
    def generate_spiral_path(self, shape, tool_diam, overlap):
        # Génère une série d'offsets intérieurs, connecte chaque boucle à la suivante par le point le plus proche
        try:
            offset_dist = tool_diam * (1 - overlap)
            loops = []
            current = shape
            while True:
                #offset = current.makeOffset2D(-offset_dist, fill=False, join=0, openResult=True)

                face = Part.Face(current)
                offset = face.makeOffset(-offset_dist)

                # On arrête si l'offset n'est plus fermé ou trop petit
                if not offset or not hasattr(offset, 'Wires') or not offset.Wires:
                    break
                # Prend la plus grande wire (pour éviter les artefacts)
                main_wire = max(offset.Wires, key=lambda w: w.Length)
                if main_wire.Length < tool_diam:
                    break
                loops.append(main_wire)
                current = main_wire
            # On connecte les boucles entre elles
            if not loops:
                return None
            path_edges = []
            prev_wire = shape.Wires[0] if hasattr(shape, 'Wires') and shape.Wires else shape
            for wire in loops:
                # Trouver le point le plus proche entre la fin du wire précédent et le wire courant
                p_start = prev_wire.Vertexes[-1].Point
                min_dist = None
                min_vert = None
                for v in wire.Vertexes:
                    dist = (p_start - v.Point).Length
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        min_vert = v.Point
                # Décale le wire courant pour commencer à ce point
                reordered = wire.copy()
                reordered.rotate(reordered.CenterOfMass, App.Vector(0,0,1), 0)  # dummy to force copy
                reordered = reordered
                # Ajoute une liaison
                path_edges.append(Part.makeLine(p_start, min_vert))
                # Ajoute le wire courant
                path_edges.extend(reordered.Edges)
                prev_wire = wire
            # Retourne un wire unique
            return Part.Wire(path_edges)
        except Exception as e:
            App.Console.PrintError(f"Erreur spirale: {e}\n")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno
            App.Console.PrintError(f"Erreur à la ligne {line_number}\n")
            return None

class PocketOperationTaskPanel():
    def __init__(self, obj):

        self.obj = obj
        self.form = Gui.PySideUic.loadUi(BaptUtilities.getPanel("PocketOp.ui"))

        self.overlapSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="Overlap", widget=self.form.overlapSpin)
        self.toolSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="ToolDiameter", widget=self.form.toolSpin)
        self.depthSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="FinalDepth", widget=self.form.depthSpin)
        self.nbGenSpin = BQuantitySpinBox.BQuantitySpinBox(obj=obj, prop="maxGeneration", widget=self.form.nbGenSpin)

        
        for i,mode in enumerate(pocketFillMode):
            self.form.modeCombo.addItem(mode)

        self.form.modeCombo.setCurrentText(obj.FillMode if hasattr(obj, 'FillMode') else "spirale")

        self.form.modeCombo.currentTextChanged.connect(self.updateObj)

    def updateObj(self):

        self.obj.FillMode = self.form.modeCombo.currentText()
        self.obj.touch()
        App.ActiveDocument.recompute()

class ViewProviderPocketOperation:
    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        """Retourne l'icône"""

        if self.Object.desactivated:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Pocket.svg")   
     
    def attach(self, vobj):
        self.Object = vobj.Object

        pass

    def setupContextMenu(self, vobj, menu):
        """Configuration du menu contextuel"""
        action = menu.addAction("Edit")
        action.triggered.connect(lambda: self.setEdit(vobj))

        action2 = menu.addAction("Activate" if vobj.Object.desactivated else "Desactivate")
        action2.triggered.connect(lambda: self.setDesactivate(vobj))
        return True
    
    def setDesactivate(self, vobj):
        """Désactive l'objet"""
        vobj.Object.desactivated = not vobj.Object.desactivated
        if vobj.Object.desactivated:
            vobj.Object.ViewObject.Visibility = False
        else:
            vobj.Object.ViewObject.Visibility = True


    def updateData(self, fp, prop):
        pass

    def getDisplayModes(self, vobj):
        return ["Flat Lines", "Shaded", "Wireframe"]
    
    def getDefaultDisplayMode(self):
        return "FlatLines"
    
    def setDisplayMode(self, vobj, mode=None):
        if mode is None:
            return self.getDefaultDisplayMode()
        return mode
    
    def onDelete(self, vobj, subelements):
        return True
    
    def __getstate__(self):
        return None
    
    def __setstate__(self, state):
        return None
    
    def setEdit(self, vobj, mode=0):
        """Ouvre le panneau de tâches pour l'opération de poche"""
        Gui.Control.showDialog(PocketOperationTaskPanel(vobj.Object))
        return True

    def doubleClicked(self, vobj):
        """Gère le double-clic pour ouvrir le panneau de tâches"""
        self.setEdit(vobj)
        return True

def createPocketOperation(contour=None):
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "PocketOperation")

    PocketOperation(obj)
    ViewProviderPocketOperation(obj.ViewObject)

    if contour:
        obj.Contour = contour
        # Ajoute PocketOperation comme enfant de ContourGeometry dans l'arborescence
        if hasattr(contour, "addObject"):
            contour.addObject(obj)
        if hasattr(contour, "Group") and obj not in contour.Group:
            contour.Group.append(obj)
    
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.Proxy.setEdit(obj.ViewObject)
    return obj
