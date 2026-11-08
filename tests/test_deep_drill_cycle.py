import unittest

from utils.deep_drill_cycle import generate_deep_hole_cycle


class TestDeepDrillCycle(unittest.TestCase):
    def test_generate_deep_hole_cycle(self):
        lines = generate_deep_hole_cycle(
            start_z=5.0,
            final_depth=-35.0,
            tool_diameter=6.0,
            max_peck=8.0,
            retract=2.0,
            safe_height=2.0,
            spindle_rpm=100,
            feed=1000.0,
            dwell_time=0.5,
        )

        self.assertTrue(any(line.startswith("G0 X10.000 Y20.000 Z2.000") for line in lines))
        self.assertIn("S100 M3", lines)
        self.assertIn("G1 Z-4.000 F1000.0", lines)
        self.assertIn("M8", lines)
        self.assertIn("G4 P0.500", lines)
        self.assertTrue(any("G1 Z-12.000 F1000.0" == line for line in lines))
        self.assertTrue(any("G1 Z-10.000 F1000.0" == line for line in lines))


if __name__ == "__main__":
    unittest.main()
