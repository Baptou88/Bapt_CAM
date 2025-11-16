Name = "Siemens828D"

Ext = "MPF"

def blockForm(stock):
    bb = stock.Shape.BoundBox
    
    return f"(Stock dimensions: X{bb.XLength} Y{bb.YLength} Z{bb.ZLength})\n"

def toolChange(tool, cam_project):
    tool_id = getattr(tool, 'Id', None)
    tool_name = getattr(tool, 'Name', None)
    spindle = getattr(tool, 'SpindleSpeed', None)
    return f"T=\"{tool_name}\" D1\nM6\nS{spindle} M3\n"