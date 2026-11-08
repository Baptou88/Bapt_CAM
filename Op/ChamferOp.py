import math

import FreeCAD as App
import FreeCADGui as Gui

import BaptPreferences
import BaptUtilities
from Op.OpContournage import ContournageCycle, ViewProviderContournageCycle
from Op.Gui.ChamferTaskPanel import ChamferTaskPanel


class ChamferProfileOperation(ContournageCycle):
    """Opération de chamfrein sur profil basée sur le pipeline de contournage."""

    Type = "ChamferProfileOperation"

    def __init__(self, obj):
        self._internal_update = False
        super().__init__(obj)
        self.Type = "ChamferProfileOperation"

        # L'opération calcule un diamètre effectif selon l'angle/diamètre de pointe.
        try:
            obj.setExpression("ToolDiameter", None)
        except Exception:
            pass

        if not hasattr(obj, "UseChamferWidth"):
            obj.addProperty("App::PropertyBool", "UseChamferWidth", "Chamfer", "Piloter le chamfrein par largeur")
            obj.UseChamferWidth = True

        if not hasattr(obj, "ChamferWidth"):
            obj.addProperty("App::PropertyLength", "ChamferWidth", "Chamfer", "Largeur du chanfrein")
            obj.ChamferWidth = 0.5

        if not hasattr(obj, "ChamferDepth"):
            obj.addProperty("App::PropertyLength", "ChamferDepth", "Chamfer", "Profondeur verticale du chanfrein")
            obj.ChamferDepth = 0.5

        if not hasattr(obj, "ToolStartDepth"):
            obj.addProperty("App::PropertyLength", "ToolStartDepth", "Chamfer", "Position outil sous Zref (relative)")
            obj.ToolStartDepth = 0.0

        if not hasattr(obj, "UseToolConicalGeometry"):
            obj.addProperty("App::PropertyBool", "UseToolConicalGeometry", "Chamfer", "Utiliser angle et pointe depuis l'outil")
            obj.UseToolConicalGeometry = True

        if not hasattr(obj, "ConeAngle"):
            obj.addProperty("App::PropertyFloat", "ConeAngle", "Chamfer", "Angle inclus de la fraise conique (degrés)")
            obj.ConeAngle = 90.0

        if not hasattr(obj, "TipDiameter"):
            obj.addProperty("App::PropertyLength", "TipDiameter", "Chamfer", "Diamètre de pointe de la fraise conique")
            obj.TipDiameter = 0.0

        if not hasattr(obj, "ComputedChamferDepth"):
            obj.addProperty("App::PropertyLength", "ComputedChamferDepth", "Chamfer", "Profondeur utilisée après calcul")
            obj.ComputedChamferDepth = 0.5
            obj.setEditorMode("ComputedChamferDepth", 1)

        if not hasattr(obj, "EffectiveToolDiameter"):
            obj.addProperty("App::PropertyLength", "EffectiveToolDiameter", "Chamfer", "Diamètre effectif à la profondeur de chamfrein")
            obj.EffectiveToolDiameter = 1.0
            obj.setEditorMode("EffectiveToolDiameter", 1)

        obj.Proxy = self

    def onChanged(self, obj, prop):
        if self._internal_update:
            return

        trigger_props = [
            "Tool", "StepDown", "Direction", "ContourGeometry",
            "ApproachType", "RetractType", "ApproachRetractLength",
            "Compensation", "SurepAxiale", "SurepRadiale",
            "UseChamferWidth", "ChamferWidth", "ChamferDepth",
            "UseToolConicalGeometry", "ConeAngle", "TipDiameter",
            "ToolStartDepth"
        ]
        if prop in trigger_props:
            self.execute(obj)

    def _get_start_z(self, obj, geom):
        zref, _ = geom.Proxy.getDepths()
        start_depth = self._float_value(obj.ToolStartDepth)
        if start_depth < 0.0:
            raise ValueError("ToolStartDepth doit être >= 0 (valeur relative à Zref)")
        return zref - start_depth

    def _float_value(self, value):
        if hasattr(value, "Value"):
            return float(value.Value)
        return float(value)

    def _get_conical_params(self, obj):
        angle = float(obj.ConeAngle)
        tip_diam = self._float_value(obj.TipDiameter)

        if getattr(obj, "UseToolConicalGeometry", True) and getattr(obj, "Tool", None) is not None:
            tool = obj.Tool
            tool_type = getattr(tool, "ToolType", "")
            if tool_type == "Fraise conique":
                angle = float(getattr(tool, "ConeAngle", angle))
                tip_diam = self._float_value(getattr(tool, "TipDiameter", tip_diam))

        if angle <= 0.0 or angle >= 179.0:
            raise ValueError("L'angle de la fraise conique doit être compris entre 0 et 179 degrés")
        if tip_diam < 0.0:
            raise ValueError("Le diamètre de pointe ne peut pas être négatif")

        return angle, tip_diam

    def _compute_depth(self, obj, angle_deg):
        if getattr(obj, "UseChamferWidth", True):
            width = max(0.0, self._float_value(obj.ChamferWidth))
            half_angle = math.radians(angle_deg / 2.0)
            tan_half = math.tan(half_angle)
            if abs(tan_half) < 1e-6:
                raise ValueError("Angle de cône invalide pour calculer la profondeur")
            return width / tan_half
        return max(0.0, self._float_value(obj.ChamferDepth))

    def _compute_effective_diameter(self, angle_deg, tip_diam, depth):
        half_angle = math.radians(angle_deg / 2.0)
        return tip_diam + 2.0 * depth * math.tan(half_angle)

    def _update_computed_properties(self, obj):
        angle_deg, tip_diam = self._get_conical_params(obj)
        depth = self._compute_depth(obj, angle_deg)
        chamfer_diam = self._compute_effective_diameter(angle_deg, tip_diam, depth)

        if chamfer_diam <= 0.0:
            raise ValueError("Le diamètre effectif calculé est nul ou négatif")

        # La position relative sous Zref règle le diamètre actif au niveau du profil.
        # Ce diamètre pilote le décalage XY de trajectoire.
        start_depth = self._float_value(obj.ToolStartDepth)
        if start_depth < 0.0:
            raise ValueError("ToolStartDepth doit être >= 0")

        half_angle = math.radians(angle_deg / 2.0)
        # Le décalage XY part du diamètre de contact à la hauteur ToolStartDepth,
        # puis applique la valeur de chanfrein vers la géométrie.
        # Donc on REDUIT la valeur absolue de l'offset (sens correct du chanfrein).
        contact_diameter = tip_diam + 2.0 * start_depth * math.tan(half_angle)
        radial_engagement = depth * math.tan(half_angle)
        path_diameter = contact_diameter - 2.0 * radial_engagement
        if path_diameter <= 0.0:
            raise ValueError("Diamètre de trajectoire <= 0. Vérifier ToolStartDepth, angle et valeur de chanfrein")

        self._internal_update = True
        try:
            obj.ComputedChamferDepth = depth
            # Affiche le diamètre effectivement utilisé pour l'offset XY.
            obj.EffectiveToolDiameter = path_diameter
            obj.CutDepth = depth
            obj.ToolDiameter = path_diameter
        finally:
            self._internal_update = False

        return depth

    def calculatePasse(self, obj, passeEquilibre=True):
        geom = self.getContourGeometry(obj)
        if not geom:
            return []

        # Pour le chamfrein, la hauteur de trajectoire est imposée directement
        # par ToolStartDepth (relative à Zref), sans plongée additionnelle.
        z_traj = self._get_start_z(obj, geom)
        return [z_traj]

    def execute(self, obj):
        if App.ActiveDocument.Restoring:
            return

        try:
            self._update_computed_properties(obj)
        except Exception as e:
            App.Console.PrintError(f"[Chamfer] Paramètres invalides: {str(e)}\n")
            return

        return super().execute(obj)


class ViewProviderChamferProfileOperation(ViewProviderContournageCycle):
    """ViewProvider pour l'opération de chamfrein."""

    def getIcon(self):
        if not self.Object.Active:
            return BaptUtilities.getIconPath("operation_disabled.svg")
        return BaptUtilities.getIconPath("Contournage.svg")

    def setEdit(self, vobj, mode=0):
        if mode == 0:
            self.panel = ChamferTaskPanel(self.Object, self.deleteObjectOnReject)
            Gui.Control.showDialog(self.panel)
            self.deleteOnReject = False
            return True
        return False


def createChamferOperation(contour=None):
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "ChamferOperation")

    ChamferProfileOperation(obj)

    if contour is not None:
        obj.ContourGeometry = contour

    pref = BaptPreferences.BaptPreferences()
    modeAjout = pref.getModeAjout()

    # 0 = ajouter à la géométrie comme enfant et au groupe opérations du projet CAM comme lien
    # 1 = ajouter à la géométrie comme enfant (pas conseillé)
    # 2 = ajouter au groupe opérations du projet CAM

    if contour is not None and (modeAjout == 1 or modeAjout == 0):
        contour.addObject(obj)
        contour.Group.append(obj)

    if contour is not None and (modeAjout == 2 or modeAjout == 0):
        camProject = BaptUtilities.find_cam_project(contour)
        if camProject:
            operations_group = camProject.Proxy.getOperationsGroup(camProject)
            if modeAjout == 2:
                operations_group.addObject(obj)
                operations_group.Group.append(obj)
            elif modeAjout == 0:
                link = doc.addObject('App::Link', f'Link_{obj.Label}')
                link.setLink(obj)
                operations_group.addObject(link)
                operations_group.Group.append(link)

    if App.GuiUp and obj.ViewObject:
        ViewProviderChamferProfileOperation(obj.ViewObject)

    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.Proxy.setEdit(obj.ViewObject)

    return obj
