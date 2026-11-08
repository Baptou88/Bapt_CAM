import FreeCAD as App
import FreeCADGui as Gui
from Lib.re import template
from Op import BaseOp


def generate_report(cam_project):
    """Génère un rapport de programmation pour le projet CAM donné."""
    doc = App.activeDocument()

    sheet = doc.addObject('Spreadsheet::Sheet', 'Spreadsheet_Rapport')
    sheet.set("A1", str("Tool Id"))
    sheet.set("B1", "Tool Name")
    sheet.set("C1", "ops")
    sheet.set("D1", "Time Estimate (s)")

    row = 2
    for i, tool in enumerate(cam_project.Proxy.getToolsGroup().Group):
        sheet.set(f"A{row}", str(tool.Id))
        sheet.set(f"B{row}", str(tool.Label))
        for j, op in enumerate(tool.InList):
            if isinstance(op.Proxy, BaseOp.baseOp):
                sheet.set(f"C{row}", str(op.Name))
                sheet.set(f"D{row}", str(op.TimeEstimate.Value if hasattr(op, 'TimeEstimate') else "N/A"))
                row = row + 1

    td = doc.addObject('TechDraw::DrawViewSpreadsheet', 'RapportView')
    td.Source = sheet
    td.CellEnd = "D" + str(row - 1)
    td.ScaleType = u"Automatic"
    template_file = App.getResourceDir() + "/Mod/TechDraw/Templates/ISO/A4_Landscape_TD.svg"

    page = doc.addObject("TechDraw::DrawPage", "Page")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template.Template = template_file
    page.Template = template
    page.addView(td)
