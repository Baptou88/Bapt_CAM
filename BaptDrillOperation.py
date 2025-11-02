from BaptPath import baseOp,baseOpViewProviderProxy
from BaptTools import ToolDatabase
import FreeCAD as App
import FreeCADGui as Gui
import Part
import os
import math
from PySide import QtCore, QtGui
import BaptUtilities


cycleType = ["Simple", "Peck", "Tapping", "Boring", "Reaming", "Contournage"]

class DrillOperation(baseOp):
    """Classe représentant une opération d'usinage de perçage"""
    
    def __init__(self, obj):
        """Ajoute les propriétés"""
        super().__init__(obj)
        obj.Proxy = self
        self.Type = "DrillOperation"
        
        # Référence à la géométrie de perçage (utiliser le nom au lieu d'un lien direct)
        if not hasattr(obj, "DrillGeometryName"):
            obj.addProperty("App::PropertyString", "DrillGeometryName", "Base", "Name of drill geometry to machine")
        
        # Outil sélectionné
        if not hasattr(obj, "ToolId"):
            obj.addProperty("App::PropertyInteger", "ToolId", "Tool", "Selected tool ID")
            obj.ToolId = -1  # Valeur par défaut (aucun outil sélectionné)
        
        # Nom de l'outil (affiché en lecture seule)
        if not hasattr(obj, "ToolName"):
            obj.addProperty("App::PropertyString", "ToolName", "Tool", "Selected tool name")
            obj.setEditorMode("ToolName", 1)  # en lecture seule
        
        # Type de cycle
        if not hasattr(obj, "CycleType"):
            obj.addProperty("App::PropertyEnumeration", "CycleType", "Cycle", "Type of drilling cycle")
            obj.CycleType = cycleType
            obj.CycleType = "Simple"  # Valeur par défaut
        
        # Paramètres communs à tous les cycles
        if not hasattr(obj, "FeedRate"):
            obj.addProperty("App::PropertySpeed", "FeedRate", "Feeds", "Feed rate for drilling")
            obj.FeedRate = 100.0  # mm/min par défaut
        
        if not hasattr(obj, "SpindleSpeed"):
            obj.addProperty("App::PropertySpeed", "SpindleSpeed", "Feeds", "Spindle speed")
            obj.SpindleSpeed = 1000.0  # tr/min par défaut
        
        if not hasattr(obj, "CoolantMode"):
            obj.addProperty("App::PropertyEnumeration", "CoolantMode", "Coolant", "Coolant mode")
            obj.CoolantMode = ["Off", "Flood", "Mist"]
            obj.CoolantMode = "Flood"  # Valeur par défaut
            
        
        # Paramètres spécifiques au cycle de perçage profond (Peck)
        if not hasattr(obj, "PeckDepth"):
            obj.addProperty("App::PropertyLength", "PeckDepth", "Peck", "Depth of each peck")
            obj.PeckDepth = 2.0  # 2mm par défaut
        
        if not hasattr(obj, "Retract"):
            obj.addProperty("App::PropertyLength", "Retract", "Peck", "Retract distance after each peck")
            obj.Retract = 1.0  # 1mm par défaut
        
        # Paramètres spécifiques au cycle de taraudage
        if not hasattr(obj, "ThreadPitch"):
            obj.addProperty("App::PropertyLength", "ThreadPitch", "Tapping", "Thread pitch")
            obj.ThreadPitch = 1.0  # 1mm par défaut
        
        # Paramètres spécifiques au cycle d'alésage
        if not hasattr(obj, "DwellTime"):
            obj.addProperty("App::PropertyFloat", "DwellTime", "Boring", "Dwell time at bottom in seconds")
            obj.DwellTime = 0.5  # 0.5s par défaut
        
        # Paramètres de sécurité
        if not hasattr(obj, "SafeHeight"):
            obj.addProperty("App::PropertyLength", "SafeHeight", "Safety", "Safe height for rapid moves")
            obj.SafeHeight = 2  # 10mm par défaut
        
        # Paramètres de profondeur
        if not hasattr(obj, "FinalDepth"):
            obj.addProperty("App::PropertyLength", "FinalDepth", "Depth", "Final depth of drilling")
            obj.FinalDepth = 10.0  # 10mm par défaut
        
        # Mode de profondeur (absolu ou relatif)
        if not hasattr(obj, "DepthMode"):
            obj.addProperty("App::PropertyString", "DepthMode", "Depth", "Depth mode (Absolute or Relative)")
            obj.DepthMode = "Absolute"  # Valeur par défaut
        
        # Référence Z pour le mode relatif
        if not hasattr(obj, "ZReference"):
            obj.addProperty("App::PropertyLength", "ZReference", "Depth", "Z reference for relative depth mode")
            obj.ZReference = 0.0  # 0mm par défaut

        if not hasattr(obj,"Diam"):
            obj.addProperty("App::PropertyFloat", "Diam","Contournage","Diametre")
            obj.Diam = 20
        if not hasattr(obj,"Ap"):
            obj.addProperty("App::PropertyFloat", "Ap","Contournage","Prise de Passe Max")
            obj.Ap = 0.5

        if not hasattr(obj,"Tool"):
            obj.addProperty("App::PropertyLink", "Tool", "Op", "Tool")

    def onChanged(self, obj, prop):
        """Appelé quand une propriété est modifiée"""
        if prop == "ToolId" and obj.ToolId >= 0:
            self.updateToolInfo(obj)
        if prop == "Tool" and obj.Tool:
            self.updateToolInfo(obj)
        elif prop == "CycleType":
            self.updateVisibleProperties(obj)
        elif prop == "DrillGeometryName" and obj.DrillGeometryName:
            self.updateFromGeometry(obj)
        elif prop == "Diam":
            self.execute()

    

    def updateVisibleProperties(self, obj):
        """Met à jour la visibilité des propriétés en fonction du type de cycle"""
        # Cacher toutes les propriétés spécifiques
        obj.setEditorMode("PeckDepth", 2)  # caché
        obj.setEditorMode("Retract", 2)  # caché
        obj.setEditorMode("ThreadPitch", 2)  # caché
        obj.setEditorMode("DwellTime", 2)  # caché
        obj.setEditorMode("Diam",2)
        
        # Afficher les propriétés spécifiques au cycle sélectionné
        if obj.CycleType == "Peck":
            obj.setEditorMode("PeckDepth", 0)  # visible
            obj.setEditorMode("Retract", 0)  # visible
        elif obj.CycleType == "Tapping":
            obj.setEditorMode("ThreadPitch", 0)  # visible
        elif obj.CycleType == "Boring":
            obj.setEditorMode("DwellTime", 0)  # visible
        elif obj.CycleType == "Contournage":
            obj.setEditorMode("Diam",0)

    def updateFromGeometry(self, obj):
        """Met à jour les paramètres en fonction de la géométrie sélectionnée"""
        if not obj.DrillGeometryName:
            return
        
        # Récupérer le diamètre et la profondeur depuis la géométrie
        for geom in App.ActiveDocument.Objects:
            if geom.Name == obj.DrillGeometryName:
                if hasattr(geom, "DrillDiameter"):
                    # Mettre à jour le message dans la console
                    App.Console.PrintMessage(f"Diamètre détecté: {geom.DrillDiameter.Value}mm\n")
        
                if hasattr(geom, "DrillDepth"):
                    # Utiliser la profondeur détectée comme profondeur finale
                    obj.FinalDepth = geom.DrillDepth.Value
                    App.Console.PrintMessage(f"Profondeur détectée: {obj.FinalDepth}mm\n")

    def execute(self, obj):
        """Mettre à jour la représentation visuelle"""
        if not obj.DrillGeometryName or not hasattr(App.ActiveDocument.getObject(obj.DrillGeometryName), "DrillPositions"):
            obj.Shape = Part.Shape()  # Shape vide
            return
        
        # Obtenir les positions de perçage
        drill_geometry = App.ActiveDocument.getObject(obj.DrillGeometryName)
        positions = drill_geometry.DrillPositions
        
        if not positions:
            obj.Shape = Part.Shape()  # Shape vide
            return
        
        # Créer une représentation d'outil pour chaque position
        tool_shapes = []
        
        # Récupérer les informations sur l'outil sélectionné
        tool_info = self.getToolInfo(obj)
        if tool_info is None:
            # Aucun outil sélectionné, utiliser une représentation par défaut
            for pos in positions:
                # Créer un cylindre simple comme représentation par défaut
                cylinder = Part.makeCylinder(2.0, pos.z - obj.FinalDepth.Value, pos, App.Vector(0, 0, -1))
                tool_shapes.append(cylinder)
        else:
            # Créer une représentation réaliste de l'outil pour chaque position
            for pos in positions:
                tool_shape = self.createToolShape(pos, tool_info, obj)
                tool_shapes.append(tool_shape)
        
        obj.Gcode = ""
        if len(positions)>0:

            obj.Gcode += f"G0 X{positions[0].x} Y{positions[0].y} Z{positions[0].z + obj.SafeHeight.Value} \n"
            if obj.CycleType == "Simple":
                obj.Gcode += f"G81 Z{obj.FinalDepth.Value} R{obj.SafeHeight.Value + positions[0].z}\n"  #FIXME
            
            elif obj.CycleType == "Peck":
                obj.Gcode += f"G83 Z{obj.FinalDepth.Value} R{obj.SafeHeight.Value + positions[0].z} Q{obj.PeckDepth.Value}\n"  #FIXME
            
            elif obj.CycleType == "Contournage":
                d = obj.Diam - tool_info.diameter
                r = d /2
                profTotale = 0
                if obj.DepthMode == "Absolute":
                    profTotale = -(obj.FinalDepth.Value - (positions[0].z + obj.SafeHeight.Value)) 
                else:
                    profTotale = (positions[0].z + obj.SafeHeight.Value) + obj.FinalDepth.Value

                
                nbTour = math.ceil(profTotale / obj.Ap)
                
                prisePasse = (profTotale / nbTour) / 2
                

                obj.Gcode += f"LABEL1:\n"
                obj.Gcode += f"G91\n"
                obj.Gcode += f"G1 X{r}\n"
                for _ in range(nbTour):
                    obj.Gcode += f"G3 X{-d} Z-{prisePasse} I{-r} J{0}\n"
                    obj.Gcode += f"G3 X{d} Z-{prisePasse} I{r} J{0}\n"

                obj.Gcode += f"G3 X{-d} I{-r} J{0}\n"
                obj.Gcode += f"G3 X{d} I{r} J{0}\n"
                obj.Gcode += f"G1 X{-r}\n"
                obj.Gcode += f"G1 Z{profTotale}\n"
                obj.Gcode += f"G90\n"
                obj.Gcode += f"LABEL2:\n"
            else:
                raise Exception(f"Unsupported Cycle Type : {obj.CycleType}")
            
            for i in range(1,len(positions)):
                    
                obj.Gcode += f"G0 X{positions[i].x} Y{positions[i].y} Z{positions[i].z + obj.SafeHeight.Value} \n"
                if obj.CycleType == "Contournage":
                    obj.Gcode += "REPEAT LABEL1 LABEL2 P=1\n"
                    # obj.Gcode += f"G91\n"
                    # obj.Gcode += f"G1 X{r}\n"
                    # obj.Gcode += f"G3 X{-d} Z-0.5 I{-r} J{0}\n"
                    # obj.Gcode += f"G3 X{d} Z-0.5 I{r} J{0}\n"
                    # obj.Gcode += f"G3 X{-d} Z-0.5 I{-r} J{0}\n"
                    # obj.Gcode += f"G3 X{d} Z-0.5 I{r} J{0}\n"
                    # obj.Gcode += f"G1 X{-r}\n"
                    # obj.Gcode += f"G1 Z{2}\n"
                    # obj.Gcode += f"G90\n"
            obj.Gcode += "G80\n"

        # # Créer un fil qui relie tous les trous
        # wires = []
        # if obj.ShowPathLine and len(positions) > 1:
        #     points = []
        #     for pos in positions:
        #         # Ajouter un point au-dessus de chaque trou avec la hauteur supplémentaire
        #         elevated_pos = App.Vector(pos.x, pos.y, pos.z + obj.SafeHeight.Value)
        #         points.append(elevated_pos)
            
        #     # Créer une polyligne avec tous les points
        #     polyline = Part.makePolygon(points)
        #     wires.append(polyline)
        
        # Fusionner les formes d'outils et le fil
        shapes = tool_shapes #+ wires
        if shapes:
            compound = Part.makeCompound(shapes)
            obj.Shape = compound
    
    def getToolInfo(self, obj):
        """Récupère les informations sur l'outil sélectionné"""
        if obj.Tool is None:
            return None
        if obj.Tool.Id < 0:
            return None
            
        

            
        # Récupérer l'outil depuis la base de données
        db = ToolDatabase()
        tool = db.get_tool_by_id(obj.Tool.Id)
        return tool

    
    def createToolShape(self, position, tool, obj):
        """Crée une représentation visuelle de l'outil en fonction de son type"""
        # Calculer la profondeur finale en fonction du mode (absolu ou relatif)
        if obj.DepthMode == "Absolute":
            final_depth = obj.FinalDepth.Value
        else:  # Relatif
            final_depth = obj.ZReference.Value + obj.FinalDepth.Value
        
        # Position du fond du trou
        bottom_pos = App.Vector(position.x, position.y, position.z - final_depth)
        
        # Diamètre de l'outil
        diameter = tool.diameter
        
        # Longueur de l'outil (utiliser une valeur par défaut si non définie)
        tool_length = tool.length if tool.length > 0 else 50.0
        
        # Créer une forme différente selon le type d'outil
        if tool.type.lower() == "foret":
            # Créer un foret avec une pointe conique
            return self.createDrillBit(position, bottom_pos, diameter, tool_length, tool.point_angle)
        elif tool.type.lower() == "taraud":
            # Créer un taraud
            return self.createTapBit(position, bottom_pos, diameter, tool_length, tool.thread_pitch)
        elif tool.type.lower() == "fraise" or tool.type.lower() == "fraise torique":
            # Créer une fraise
            return self.createEndMill(position, bottom_pos, diameter, tool_length, tool.torus_radius)
        else:
            # Type d'outil inconnu, créer un cylindre simple
            return self.createSimpleTool(position, bottom_pos, diameter, tool_length)
    
    def createDrillBit(self, top_pos, bottom_pos, diameter, length, point_angle):
        """Crée une représentation d'un foret avec une pointe conique"""
        # Calculer la hauteur de la pointe conique
        point_height = diameter / (2 * math.tan(math.radians(point_angle / 2)))
        
        # profondeur du percage
        depth = top_pos.z - bottom_pos.z
        if depth <= point_height:
            #- calcul du rayon
            radius = math.tan(math.radians(point_angle / 2)) * depth
            # Créer la pointe du foret (cône)
            drill_bit = Part.makeCone(radius, 0, depth, top_pos, App.Vector(0, 0, -1))            
            
        else:
            # Créer le corps du foret (cylindre)
            body_length = top_pos.z - bottom_pos.z - point_height
            body = Part.makeCylinder(diameter / 2, body_length, top_pos, App.Vector(0, 0, -1))
            
            # Créer la pointe du foret (cône)
            tip = Part.makeCone(diameter / 2, 0, point_height, bottom_pos + App.Vector(0, 0, point_height), App.Vector(0, 0, -1))
            
            # Fusionner le corps et la pointe
            drill_bit = body.fuse(tip)
        return drill_bit
    
    def createTapBit(self, top_pos, bottom_pos, diameter, length, thread_pitch):
        """Crée une représentation d'un taraud"""
        # Créer le corps du taraud (cylindre)
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))
        
        # Ajouter des rainures pour représenter les filets
        # (Simplifié pour la visualisation)
        tap_bit = body
        
        # Nombre de filets à représenter
        num_threads = min(10, int(length / thread_pitch))
        
        # Créer des anneaux pour représenter les filets
        for i in range(num_threads):
            z_pos = bottom_pos.z + i * thread_pitch
            ring_pos = App.Vector(top_pos.x, top_pos.y, z_pos)
            ring = Part.makeTorus(diameter / 2, diameter / 10, ring_pos, App.Vector(0, 0, 1))
            tap_bit = tap_bit.fuse(ring)
        
        return tap_bit
    
    def createEndMill(self, top_pos, bottom_pos, diameter, length, torus_radius = 0):
        """Crée une représentation d'une fraise"""
        # Créer le corps de la fraise (cylindre)
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))
        
        # Si c'est une fraise torique, ajouter un arrondi au bout
        if torus_radius > 0:
            torus_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z + torus_radius)
            torus = Part.makeTorus(diameter / 2 - torus_radius, torus_radius, torus_pos, App.Vector(0, 0, 1))
            end_mill = body.fuse(torus)
        else:
            # Fraise droite, ajouter un disque plat au bout
            disk_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
            disk = Part.makeCylinder(diameter / 2, 0.1, disk_pos, App.Vector(0, 0, 1))
            end_mill = body.fuse(disk)
        
        return end_mill
    
    def createSimpleTool(self, top_pos, bottom_pos, diameter, length):
        """Crée une représentation simple d'un outil (cylindre)"""
        body_pos = App.Vector(top_pos.x, top_pos.y, bottom_pos.z)
        body = Part.makeCylinder(diameter / 2, length, body_pos, App.Vector(0, 0, 1))
        return body

    def onChanged(self, obj, prop):
        """Appelé quand une propriété change"""
        if prop == "DrillGeometryName":
            self.updateFromGeometry(obj)
        elif prop in ["ShowPathLine", "SafeHeight", "FinalDepth"]:
            self.execute(obj)

    def onDocumentRestored(self, obj):
        """Appelé lors de la restauration du document"""
        self.__init__(obj)
        self.updateVisibleProperties(obj)

    def __getstate__(self):
        """Sérialisation"""
        return None

    def __setstate__(self, state):
        """Désérialisation"""
        return None


class ViewProviderDrillOperation(baseOpViewProviderProxy):
    def __init__(self, vobj):
        """Initialise le ViewProvider"""
        super().__init__(vobj)
        vobj.Proxy = self
        self.Object = vobj.Object
        
    def attach(self, vobj):
        """Appelé lors de l'attachement du ViewProvider"""
        self.Object = vobj.Object
        return super().attach(vobj)

    def getIcon(self):
        """Retourne l'icône"""
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Tree_Drilling.svg")
        
    # def setupContextMenu(self, vobj, menu):
    #     """Configuration du menu contextuel"""
    #     super().setupContextMenu()
    #     action = menu.addAction("Edit")
    #     action.triggered.connect(lambda: self.setEdit(vobj))
    #     return True

    # def updateData(self, obj, prop):
    #     """Appelé quand une propriété de l'objet est modifiée"""
    #     pass

    # def onChanged(self, vobj, prop):
    #     """Appelé quand une propriété du ViewProvider est modifiée"""
    #     pass

    # def doubleClicked(self, vobj):
    #     """Gérer le double-clic"""
    #     self.setEdit(vobj)
    #     return True

    def setEdit(self, vobj, mode=0):
        """Ouvrir l'éditeur"""
        from BaptDrillOperationTaskPanel import DrillOperationTaskPanel
        panel = DrillOperationTaskPanel(vobj.Object)
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
