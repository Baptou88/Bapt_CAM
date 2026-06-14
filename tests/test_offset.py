import FreeCAD as App
import FreeCADGui as Gui
import Part
import unittest
from Op import offset


class TestOffset(unittest.TestCase):
    def test01(self):
        """
        test orient Wrire function
        le wire est bien orienté
        :param self:
        """
        edges = [
            Part.makeLine(App.Vector(0, 0, 0), App.Vector(10, 0, 0)),
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(10, 10, 0)),
            Part.makeLine(App.Vector(10, 10, 0), App.Vector(0, 10, 0)),
            Part.makeLine(App.Vector(0, 10, 0), App.Vector(0, 0, 0)),
        ]
        wire = Part.Wire(edges)
        oriented_wire = offset.orientwire(wire, forward=True)
        self.assertEqual(oriented_wire.Edges[0].Vertexes[0].Point, App.Vector(0, 0, 0))
        self.assertEqual(oriented_wire.Edges[0].Vertexes[1].Point, App.Vector(10, 0, 0))

    def test02(self):
        """
        test orient Wrire function
        le premier edge est mal orienté
        :param self:
        """
        edges = [
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(0, 0, 0)),
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(10, 10, 0)),
            Part.makeLine(App.Vector(10, 10, 0), App.Vector(0, 10, 0)),
            Part.makeLine(App.Vector(0, 10, 0), App.Vector(0, 0, 0)),
        ]
        wire = Part.Wire(edges)
        oriented_wire = offset.orientwire(wire, forward=True)
        self.assertEqual(oriented_wire.Edges[0].Vertexes[0].Point, App.Vector(0, 0, 0))
        self.assertEqual(oriented_wire.Edges[0].Vertexes[1].Point, App.Vector(10, 0, 0))

    def test03(self):
        """
        test orient Wrire function
        le wire est orienté dans le sens inverse du parcours d'usinage
        :param self:
        """
        edges = [
            Part.makeLine(App.Vector(0, 0, 0), App.Vector(10, 0, 0)),
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(10, 10, 0)),
            Part.makeLine(App.Vector(10, 10, 0), App.Vector(0, 10, 0)),
            Part.makeLine(App.Vector(0, 10, 0), App.Vector(0, 0, 0)),
        ]
        wire = Part.Wire(edges)
        oriented_wire = offset.orientwire(wire, forward=False)
        self.assertEqual(oriented_wire.Edges[0].Vertexes[0].Point, App.Vector(0, 0, 0))
        self.assertEqual(oriented_wire.Edges[0].Vertexes[1].Point, App.Vector(0, 10, 0))

    def test04(self):
        """
        test offset function
        """
        edges = [
            Part.makeLine(App.Vector(0, 0, 0), App.Vector(10, 0, 0)),
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(10, 10, 0)),
            Part.makeLine(App.Vector(10, 10, 0), App.Vector(0, 10, 0)),

        ]
        wire = Part.Wire(edges)
        offset_wire = offset.offsetWire(wire, distance=1.0, forward=True, side=offset.Side.RIGHT)
        self.assertEqual(offset_wire.Edges[0].Vertexes[0].Point, App.Vector(0, -1, 0))
        self.assertEqual(offset_wire.Edges[0].Vertexes[1].Point, App.Vector(10, -1, 0))

    def test05(self):
        """
        test offset function
        """
        edges = [
            Part.makeLine(App.Vector(0, 0, 0), App.Vector(10, 0, 0)),
            Part.makeLine(App.Vector(10, 0, 0), App.Vector(10, 10, 0)),
            Part.makeLine(App.Vector(10, 10, 0), App.Vector(0, 10, 0)),

        ]
        wire = Part.Wire(edges)
        offset_wire = offset.offsetWire(wire, distance=1.0, forward=False, side=offset.Side.RIGHT)
        self.assertEqual(offset_wire.Edges[0].Vertexes[0].Point, App.Vector(0, 11, 0))
