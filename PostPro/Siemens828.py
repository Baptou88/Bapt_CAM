Name = "Siemens828D"

Ext = "MPF"

def blockForm(stock):
    bb = stock.Shape.BoundBox
    
    return f"(Stock dimensions: X{bb.XLength} Y{bb.YLength} Z{bb.ZLength})\n"