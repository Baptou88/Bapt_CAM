from BaptPreferences import BaptPreferences
from Tool.BaptTools import Tool


import sqlite3

from Tool.ToolRepository import ToolRepository


class SqliteToolRepository(ToolRepository):
    """Dépôt d'outils basé sur SQLite"""

    def __init__(self):
        # Récupérer le chemin depuis les préférences
        prefs = BaptPreferences()
        self.db_path = prefs.getToolsDbPath()

        # Initialiser la base de données
        self.init_database()

    def init_database(self):
        """Initialise la base de données si elle n'existe pas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Vérifier si la table existe déjà
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tools'")
        table_exists = cursor.fetchone()

        if not table_exists:
            # Créer la table des outils si elle n'existe pas
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                diameter REAL,
                length REAL,
                flutes INTEGER,
                material TEXT,
                comment TEXT,
                point_angle REAL DEFAULT 118.0,
                torus_radius REAL DEFAULT 0.0,
                thread_pitch REAL DEFAULT 0.0,
                speed REAL DEFAULT 0.0,
                feed REAL DEFAULT 0.0,
                coolant INTEGER DEFAULT 0
            )
            ''')
        else:
            # Vérifier si les nouvelles colonnes existent, sinon les ajouter
            try:
                cursor.execute("SELECT point_angle FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN point_angle REAL DEFAULT 118.0")

            try:
                cursor.execute("SELECT torus_radius FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN torus_radius REAL DEFAULT 0.0")

            try:
                cursor.execute("SELECT thread_pitch FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN thread_pitch REAL DEFAULT 0.0")

            try:
                cursor.execute("SELECT speed FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN speed REAL DEFAULT 0.0")

            try:
                cursor.execute("SELECT feed FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN feed REAL DEFAULT 0.0")

            try:
                cursor.execute("SELECT coolant FROM tools LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tools ADD COLUMN coolant INTEGER DEFAULT 0")

        conn.commit()
        conn.close()

    def get_all_tools(self):
        """Récupère tous les outils de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, type, diameter, length, flutes, material, comment, point_angle, torus_radius, thread_pitch, speed, feed, coolant FROM tools")
        rows = cursor.fetchall()

        tools = []
        for row in rows:
            tool = Tool(
                id=row[0],
                name=row[1],
                type=row[2],
                diameter=row[3],
                length=row[4],
                flutes=row[5],
                material=row[6],
                comment=row[7],
                point_angle=row[8],
                torus_radius=row[9],
                thread_pitch=row[10],
                speed=row[11],
                feed=row[12],
                coolant=row[13] or 0
            )
            tools.append(tool)

        conn.close()
        return tools

    def get_tool_by_id(self, tool_id):
        """Récupère un outil par son ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, type, diameter, length, flutes, material, comment, point_angle, torus_radius, thread_pitch, speed, feed, coolant FROM tools WHERE id=?", (tool_id,))
        row = cursor.fetchone()

        if row:
            tool = Tool(
                id=row[0],
                name=row[1],
                type=row[2],
                diameter=row[3],
                length=row[4],
                flutes=row[5],
                material=row[6],
                comment=row[7],
                point_angle=row[8],
                torus_radius=row[9],
                thread_pitch=row[10],
                speed=row[11],
                feed=row[12],
                coolant=row[13] or 0
            )
            conn.close()
            return tool
        else:
            conn.close()
            return None

    def add_tool(self, tool):
        """Ajoute un outil à la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO tools (name, type, diameter, length, flutes, material, comment, point_angle, torus_radius, thread_pitch, speed, feed, coolant)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tool.name, tool.type, tool.diameter, tool.length, tool.flutes, tool.material, tool.comment,
              tool.point_angle, tool.torus_radius, tool.thread_pitch, tool.speed, tool.feed, tool.coolant))

        # Récupérer l'ID généré
        tool.id = cursor.lastrowid

        conn.commit()
        conn.close()
        return tool

    def update_tool(self, tool):
        """Met à jour un outil dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE tools
        SET name=?, type=?, diameter=?, length=?, flutes=?, material=?, comment=?, point_angle=?, torus_radius=?, thread_pitch=?, speed=?, feed=?, coolant=?
        WHERE id=?
        ''', (tool.name, tool.type, tool.diameter, tool.length, tool.flutes, tool.material, tool.comment,
              tool.point_angle, tool.torus_radius, tool.thread_pitch, tool.speed, tool.feed, tool.coolant, tool.id))

        conn.commit()
        conn.close()
        return tool

    def delete_tool(self, tool_id):
        """Supprime un outil de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tools WHERE id=?", (tool_id,))

        conn.commit()
        conn.close()
