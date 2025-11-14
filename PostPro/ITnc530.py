Name = "ITnc530"

def blockForm(stock):
    bb = stock.Shape.BoundBox
    blk = f"BLK FORM 01 X{bb.XMin:.3f} Y{bb.YMin:.3f} Z{bb.ZMin:.3f}\n"
    blk += f"BLK FORM 02 X{bb.XMax:.3f} Y{bb.YMax:.3f} Z{bb.ZMax:.3f}\n"
    return blk