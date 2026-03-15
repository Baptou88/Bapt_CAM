import traceback
import os

from BaptPreferences import BaptPreferences


class GcodeWriter:
    current_position = {'X': None, 'Y': None, 'Z': None}
    current_feed = None

    def __init__(self):
        self.lines = []
        self.current_position = {'X': None, 'Y': None, 'Z': None}
        self.current_feed = None
        prefs = BaptPreferences()
        self.DEBUG = prefs.debugGcode

        """in seconds, estimated machining time"""
        self.time_estimate = 0.0

    def _caller():
        """internal function to determine the calling module."""
        filename, line, func, text = traceback.extract_stack(limit=3)[0]
        return os.path.splitext(os.path.basename(filename))[0], line, func

    def setPosition(self, x, y, z):
        self.current_position = {'X': x, 'Y': y, 'Z': z}

    def linearMove(self, arg, feed: float = None, rapid=False, force=False):
        line = 'G0' if rapid else 'G1'

        if 'comp' in arg:
            line += f" {arg['comp']}"

        distance = {'X': 0, 'Y': 0, 'Z': 0}
        for axis in ['X', 'Y', 'Z']:
            if axis in arg:
                if force or self.current_position[axis] is None or arg[axis] != self.current_position[axis]:
                    line += f" {axis}{arg[axis]:.3f}"
                    distance[axis] = abs(arg[axis] - (self.current_position[axis] or 0))
                self.current_position[axis] = arg[axis]

        if feed is not None and feed != self.current_feed:
            line += f" F{feed:.1f}"
            self.current_feed = feed

        if rapid == False and self.current_feed is not None:
            # Estimation du temps pour ce déplacement
            feed_mm_per_sec = self.current_feed / 60.0  # Convertir de mm/min à mm/s
            d = (distance['X'] ** 2 + distance['Y'] ** 2 + distance['Z'] ** 2) ** 0.5
            if feed_mm_per_sec > 0:
                move_time = d / feed_mm_per_sec
                self.time_estimate += move_time

        if self.DEBUG:
            module, line_num, func = GcodeWriter._caller()
            line += f" ; (at {module}:{line_num} in {func})"

        self.lines.append(line)

    def arcMove(self, arg, feed: float = None):
        cmd = 'G3' if arg.get('CCW', False) else 'G2'
        line = cmd
        for axis in ['X', 'Y', 'Z']:
            if axis in arg:
                if True:  # arg[axis] != self.current_position[axis]:
                    line += f" {axis}{arg[axis]:.3f}"
                self.current_position[axis] = arg[axis]
        if 'I' in arg and 'J' in arg:
            line += f" I{arg['I']:.3f} J{arg['J']:.3f}"
        elif 'R' in arg:
            line += f" R{arg['R']:.3f}"
        else:
            raise ValueError("Arc move requires either I/J or R parameters.")

        if feed is not None and feed != self.current_feed:
            line += f" F{feed:.1f}"
            self.current_feed = feed

        if self.DEBUG:
            module, line_num, func = GcodeWriter._caller()
            line += f" ; (at {module}:{line_num} in {func})"
        self.lines.append(line)

    def comment(self, text):
        self.lines.append(f"; {text}")
        if self.DEBUG:
            module, line_num, func = GcodeWriter._caller()
            self.lines[-1] += f" (at {module}:{line_num} in {func})"
