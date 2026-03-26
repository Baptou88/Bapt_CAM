

class Tool:
    """Classe représentant un outil d'usinage"""

    # Coolant: 0=off, 1=flood, 2=mist
    COOLANT_OFF = 0
    COOLANT_FLOOD = 1
    COOLANT_MIST = 2

    def __init__(self, id=None, name="", type="", diameter=0.0, length=0.0, flutes=0, material="", comment="",
                 point_angle=118.0, torus_radius=0.0, thread_pitch=0.0, speed=0.0, feed=0.0, coolant=0):
        self.id = id
        self.name = name
        self.type = type
        self.diameter = diameter
        self.length = length
        self.flutes = flutes
        self.material = material
        self.comment = comment

        # Paramètres spécifiques aux types d'outils
        self.point_angle = point_angle  # Angle de pointe pour les forets (en degrés)
        self.torus_radius = torus_radius  # Rayon du tore pour les fraises toriques (en mm)
        self.thread_pitch = thread_pitch  # Pas pour les tarauds (en mm)

        self.speed = speed  # Vitesse de coupe (en rpm)
        self.feed = feed    # Avance (en mm/min)
        self.coolant = coolant  # Arrosage: 0=off, 1=flood, 2=mist

    def to_dict(self):
        """Convertit l'outil en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'diameter': self.diameter,
            'length': self.length,
            'flutes': self.flutes,
            'material': self.material,
            'comment': self.comment,
            'point_angle': self.point_angle,
            'torus_radius': self.torus_radius,
            'thread_pitch': self.thread_pitch,
            'speed': self.speed,
            'feed': self.feed,
            'coolant': self.coolant
        }

    @classmethod
    def from_dict(cls, data):
        """Crée un outil à partir d'un dictionnaire"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ""),
            type=data.get('type', ""),
            diameter=data.get('diameter', 0.0),
            length=data.get('length', 0.0),
            flutes=data.get('flutes', 0),
            material=data.get('material', ""),
            comment=data.get('comment', ""),
            point_angle=data.get('point_angle', 118.0),
            torus_radius=data.get('torus_radius', 0.0),
            thread_pitch=data.get('thread_pitch', 0.0),
            speed=data.get('speed', 0.0),
            feed=data.get('feed', 0.0),
            coolant=data.get('coolant', 0)
        )
