import FreeCAD as App
from Tool.BaptTools import Tool
from Tool.ToolRepository import ToolRepository
from utils import Log


import os
import re
import sys


class TlsToolRepository(ToolRepository):
    """Dépôt d'outils basé sur le format .tls (e-NC)"""

    # Mapping (Family, type) -> Tool.type
    _TYPE_MAP = {
        (0, 1): "Foret",
        (0, 5): "Taraud",
        (1, 0): "Fraise",
        (1, 1): "Fraise",
        (1, 2): "Fraise",        # hémisphérique
        (1, 3): "Fraise torique",
        (1, 4): "Fraise",        # conique
        (1, 5): "Fraise",        # 3 tailles
        (1, 6): "Fraise",        # à fileter
    }

    # Reverse mapping Tool.type -> (Family, type) par défaut
    _REVERSE_TYPE_MAP = {
        "Foret": (0, 1),
        "Taraud": (0, 5),
        "Fraise": (1, 0),
        "Fraise torique": (1, 3),
        "Autre": (1, 0),
    }

    def __init__(self, filepath):
        self.filepath = filepath
        self._tools = []
        self._next_id = 1
        if os.path.isfile(filepath):
            self._load()

    # ---- lecture ----

    def _parse_attrs(self, line):
        """Extrait les attributs clé=valeur d'une ligne pseudo-XML."""
        attrs = {}
        for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', line):
            attrs[m.group(1)] = m.group(2)
        return attrs

    def _load(self):
        """Charge le fichier .tls et peuple self._tools."""
        self._tools = []
        with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Découper sur chaque bloc <Tool> ... </Tool>
        blocks = re.split(r'<Tool>', content)
        for idx, block in enumerate(blocks):
            if '<tool_params_1' not in block:
                continue

            tool = Tool()
            tool.id = self._next_id
            self._next_id += 1

            # tool_params_1
            m = re.search(r'<tool_params_1.*', block)
            if m:
                a = self._parse_attrs(m.group())
                family = int(a.get('Family', -1))
                ttype = int(a.get('type', -1))
                tool.name = a.get('description', '')
                tool.type = self._TYPE_MAP.get((family, ttype), 'Autre')

            try:
                # tool_params_2
                m = re.search(r'<tool_params_2.*', block)
                if m:
                    a = self._parse_attrs(m.group())
                    tool.diameter = float(a.get('diameter', 0))
                    tool.length = float(a.get('length', 0))
                    tool.torus_radius = float(a.get('end_length', 0))

                # tool_params_3
                m = re.search(r'<tool_params_3.*', block)
                if m:
                    a = self._parse_attrs(m.group())
                    tool.flutes = int(a.get('teeth_nb', 0))
                    tool.point_angle = float(a.get('end_angle', 0))

                # tool_cut_conditions
                m = re.search(r'<tool_cut_conditions.*', block)
                if m:
                    a = self._parse_attrs(m.group())
                    tool.speed = float(a.get('spindle', 0))
                    tool.feed = float(a.get('feed_calc', 0))
                    tool.coolant = int(a.get('coolant', 0))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                App.Console.PrintError(f"Tool {tool.name} {str(e)} L{exc_tb.tb_lineno}\n")
                Log.baptError(f"Tool {tool.name} {str(e)}")

            self._tools.append(tool)

    # ---- interface ToolRepository ----

    def get_all_tools(self):
        return list(self._tools)

    def get_tool_by_id(self, tool_id):
        for t in self._tools:
            if t.id == tool_id:
                return t
        return None

    def add_tool(self, tool):
        tool.id = self._next_id
        self._next_id += 1
        self._tools.append(tool)
        self._save()
        return tool

    def update_tool(self, tool):
        for i, t in enumerate(self._tools):
            if t.id == tool.id:
                self._tools[i] = tool
                break
        self._save()
        return tool

    def delete_tool(self, tool_id):
        self._tools = [t for t in self._tools if t.id != tool_id]
        self._save()

    # ---- écriture ----

    def _save(self):
        """Écrit la liste d'outils dans le fichier .tls."""
        lines = []
        lines.append('<Tool Database e-NC Version=4.0>')
        lines.append('<tool_list>')
        lines.append('<version = "1.0"/>')
        lines.append('')

        for tool in self._tools:
            family, ttype = self._REVERSE_TYPE_MAP.get(tool.type, (1, 0))
            lines.append('<Tool>')
            lines.append('<version = 1.1 />')
            lines.append('<params>')
            lines.append('<version = 1.8 />')
            lines.append(f'<tool_params_1, Family="{family}", type="{ttype}", description="{tool.name}"/>')
            lines.append(f'<tool_params_2, diameter="{tool.diameter}", length="{tool.length}", cut_length="0", end_length="{tool.torus_radius}", poc_num="0", support=""/>')
            lines.append(f'<tool_params_3, end_angle="{tool.point_angle}", orient_angle="0", retract_value="0", orient_type="-1", teeth_nb="{tool.flutes}"/>')
            lines.append('<tool_correctors, radius="0", length="0", radius2="0", br_fixe="0"/>')
            lines.append('</params>')
            lines.append('<cut_conditions>')
            lines.append('<version = 6.3 />')
            lines.append(f'<tool_cut_conditions, coolant="{tool.coolant}", spindle="{tool.speed}", sens="1", cut_speed="0", speed_calc="0", toothfeed="0", feed_calc="{tool.feed}", DSD="1", DLD="50%", units="0", z_angle="20"/>')
            for n in range(10):
                speed_val = "0" if n in (0, 5) else ("auto" if n == 1 else "100%")
                lines.append(f'<tool_feedrates_{n}, speed="{speed_val}"/>')
            lines.append('</cut_conditions>')
            lines.append('</Tool>')

        lines.append('</tool_list>')
        lines.append('</Tool Database e-NC>')

        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines) + '\n')
