# https://forum.freecad.org/viewtopic.php?t=100312&sid=a77831c5cae7ee6feb8cf340f0e19dc6
from collections import deque
import math
import sys
from BaptUtilities import find_cam_project
import FreeCAD as App
import FreeCADGui


from pivy import coin
from enum import Enum 
from PySide import QtGui,QtCore
import Mesh,MeshPart


"""
Gcode  | Heidenhain | Description
-------|------------|----------------------------------------------
G0     | L    FMAX  | Rapid positioning
G1     | L          | Linear interpolation (feed)
G2     | C          | Circular interpolation, cw
G3     | CC         | Circular interpolation, ccw
G17    | PLANE XY   | Select XY plane for circular interpolation
G18    | PLANE XZ   | Select XZ plane for circular interpolation
G19    | PLANE YZ   | Select YZ plane for circular interpolation
G40    | R0         | Cutter compensation off 
G41    | RL         | Cutter compensation left
G42    | RR         | Cutter compensation right
G90    |            | Absolute programming
G91    | I          | Incremental programming


CHF    |CHF         | Chanfrein
RND    |RND         | Rounding
LABEL  |LBL         | Label declaration
REPEAT |CALL        | Repeat block
"""

class comp(Enum):
    G40 = 0
    G41 = 1
    G42 = 2

class absinc(Enum):
    G90 = 0
    G91 = 1


        
class memory():
    def __init__(self):
        #labels tableau de string et int
        self.labels = {}
        self.queue = deque()
        self.variables = {}
        self.current_cycle = None
        self.absincMode = absinc.G90

    def addLabel(self, key, value):
        self.labels[key]= value

class GcodeEditorTaskPanel:
    def __init__(self, obj):
        self.obj = obj
        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Gcode Editor")
        layout = QtGui.QVBoxLayout(self.form)

        self.textEdit = QtGui.QPlainTextEdit()
        self.textEdit.setPlainText(self.obj.Gcode)
        layout.addWidget(self.textEdit)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept(self):
        self.obj.Gcode = self.textEdit.toPlainText()
        FreeCADGui.Control.closeDialog()

    def reject(self):
        FreeCADGui.Control.closeDialog()

    def getStandardButtons(self):
        """Définir les boutons standard"""
        return (QtGui.QDialogButtonBox.Ok |
                   QtGui.QDialogButtonBox.Apply |
                  QtGui.QDialogButtonBox.Cancel)
    

    
class GcodeAnimator:
    """
    Simule le parcours d'usinage en déplaçant un marqueur (sphere) le long des segments
    feed (optionnellement rapid). Utilise QTimer (PySide) pour l'animation.
    Usage:
      anim = GcodeAnimator(view_provider)
      anim.load_paths(include_rapid=False)   # lit les listes du view provider
      anim.start(speed_mm_s=20.0)
      anim.pause()
      anim.stop()
      anim.step()                            # avance d'un pas de timer
    """
    def __init__(self, view_provider):
        from PySide import QtCore
        self.vp = view_provider
        self.timer = QtCore.QTimer()
        self.timer.setInterval(30)  # ms, ~33 FPS default
        self.timer.timeout.connect(self._on_timer)
        self.speed = 20.0  # mm / sec
        self.include_rapid = False

        self.tool = None
        self.toolMesh = None
        self.stock = None

        self.stockMesh = None
        
        # Récupérer le projet CAM actif
        project = find_cam_project(self.vp.Object)
        if project:
            self.stock = project.Proxy.getStock(project)
            self.stockMesh = App.activeDocument().addObject("Mesh::Feature", "stockMesh")
            self.stockMesh.Mesh = MeshPart.meshFromShape(Shape=self.stock.Shape, MaxLength=5)
            if hasattr(self.vp.Object, "Tool") and self.vp.Object.Tool is not None:
                self.tool = self.vp.Object.Tool
                self.toolMesh = App.activeDocument().addObject("Mesh::Feature", "toolMesh")
                self.toolMesh.Mesh = MeshPart.meshFromShape(Shape=self.tool.Shape, MaxLength=5)

        
            
        self.frequence_cut = 20
        self.indice_frequence_cut = 0

        # animation state
        self.segments = []      # list of (p0,p1) tuples
        self.seg_index = 0
        self.seg_pos = 0.0      # distance along current segment
        self.seg_len = 0.0
        self.running = False

        # create a marker in the scene (small sphere)
        self._create_marker()

    def _create_marker(self):
        # marker group: switch to show/hide
        self.marker_switch = coin.SoSwitch()
        self.marker_switch.whichChild = coin.SO_SWITCH_NONE

        self.marker_sep = coin.SoSeparator()
        self.marker_trans = coin.SoTranslation()
        self.marker_color = coin.SoBaseColor()
        self.marker_sphere = coin.SoSphere()
        self.marker_sphere.radius = 1.0

        # default color yellow
        self.marker_color.rgb.setValues(0,1,[(1.0,1.0,0.0)])

        self.marker_sep.addChild(self.marker_trans)
        self.marker_sep.addChild(self.marker_color)
        self.marker_sep.addChild(self.marker_sphere)
        self.marker_switch.addChild(self.marker_sep)

        # attach to view provider display group if available
        try:
            self.vp.my_displaymode.addChild(self.marker_switch)
        except Exception:
            pass

    def load_paths(self, include_rapid=False):
        """
        Construit la liste de segments à partir des feed_coords (et éventuellement rapid_coords)
        en respectant l'ordre d'origine du programme si disponible (self.vp.ordered_segments).
        """
        self.include_rapid = include_rapid
        segs = []
        vp = self.vp
        # prefer ordered_segments if provided by the view provider (keeps original program order)
        if hasattr(vp, "ordered_segments") and vp.ordered_segments:
            for typ, a, b in vp.ordered_segments:
                if typ == "rapid" and not include_rapid:
                    continue
                segs.append((a, b))
        else:
            # fallback: keep previous behavior (rapid then feed)
            if include_rapid and hasattr(vp, "rapid_coords"):
                rc = getattr(vp, "rapid_coords") or []
                for i in range(0, len(rc), 2):
                    if i+1 < len(rc):
                        segs.append((rc[i], rc[i+1]))
            if hasattr(vp, "feed_coords"):
                fc = getattr(vp, "feed_coords") or []
                for i in range(0, len(fc), 2):
                    if i+1 < len(fc):
                        segs.append((fc[i], fc[i+1]))
        self.segments = segs
        self.stop()  # reset indices

    def start(self, speed_mm_s=20.0):
        self.speed = float(speed_mm_s)
        if not self.segments:
            self.load_paths(self.include_rapid)
        if not self.segments:
            return
        self.running = True
        # initialize first segment
        self.seg_index = 0
        self._prepare_segment(0)
        self.marker_switch.whichChild = 0  # show marker
        self.timer.start()

    def pause(self):
        self.running = False
        self.timer.stop()

    def stop(self):
        self.pause()
        self.seg_index = 0
        self.seg_pos = 0.0
        self.seg_len = 0.0
        # hide marker
        try:
            self.marker_switch.whichChild = coin.SO_SWITCH_NONE
        except Exception:
            pass

    def step(self):
        """Avance d'un tick (utile pour debug ou pas-à-pas)."""
        if not self.segments:
            return
        self._on_timer()

    def set_speed(self, speed_mm_s):
        self.speed = float(speed_mm_s)

    def _prepare_segment(self, idx):
        if idx < 0 or idx >= len(self.segments):
            self.seg_len = 0.0
            return
        p0, p1 = self.segments[idx]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dz = p1[2] - p0[2]
        self.seg_len = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.seg_pos = 0.0
        self._set_marker_position(p0)

    def _set_marker_position(self, point):
        # set translation to point (x,y,z)
        try:
            self.marker_trans.translation.setValue(point[0], point[1], point[2])
            if self.tool is not None:
                self.tool.Placement = App.Placement(App.Vector(point[0], point[1], point[2]), App.Rotation(0,0,0,1))
            if self.toolMesh is not None:
                self.toolMesh.Placement = App.Placement(App.Vector(point[0], point[1], point[2]), App.Rotation(0,0,0,1))
            self.tool.recompute()
            self.indice_frequence_cut += 1
            if self.frequence_cut != 0 and self.indice_frequence_cut % self.frequence_cut == 0:
                self.stock.Shape = self.stock.Shape.cut(self.tool.Shape)
            #☺self.updateMesh(App.Vector(point[0],point[1],point[2]))
        except Exception as e:
            App.Console.PrintError(f" {str(e)}\n")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            App.Console.PrintMessage(f'{exc_tb.tb_lineno}\n')
            pass

    def updateMesh(self, outil_pos):
        tolerance = 0.01
        m = self.stockMesh.Mesh
        new_facets = []
        # for f in m.Facets:
        #     d = sum([(App.Vector(p) - outil_pos).Length for p in f.Points]) / 3
        #     if d > self.tool.Radius:
        #         new_facets.append(f)
        for f in m.Facets:
            inside_count = 0
            for p in f.Points:
                global_p = App.Vector(p)
                if self.toolMesh.isInside(global_p,tolerance,True):
                    inside_count += 1
                    if inside_count < 2 :
                        new_facets.append(f)

        newMesh = Mesh.Mesh(new_facets)
        self.stockMesh.Mesh = newMesh

    def _on_timer(self):
        # single step of animation based on timer interval and speed
        if not self.running or not self.segments or self.seg_index >= len(self.segments):
            self.stop()
            return

        interval_s = max(0.001, self.timer.interval() / 1000.0)
        distance = self.speed * interval_s

        # ensure current segment prepared
        if self.seg_len <= 0.0:
            self._prepare_segment(self.seg_index)

        while distance > 0 and self.seg_index < len(self.segments):
            p0, p1 = self.segments[self.seg_index]
            if self.seg_len <= 1e-12:
                # zero-length segment -> advance
                self.seg_index += 1
                if self.seg_index < len(self.segments):
                    self._prepare_segment(self.seg_index)
                continue

            remaining = self.seg_len - self.seg_pos
            if distance < remaining:
                # advance within current segment
                t = (self.seg_pos + distance) / self.seg_len
                x = p0[0] + (p1[0]-p0[0]) * t
                y = p0[1] + (p1[1]-p0[1]) * t
                z = p0[2] + (p1[2]-p0[2]) * t
                self.seg_pos += distance
                self._set_marker_position((x,y,z))
                distance = 0
            else:
                # jump to end of segment
                self._set_marker_position(p1)
                distance -= remaining
                self.seg_index += 1
                if self.seg_index < len(self.segments):
                    self._prepare_segment(self.seg_index)
                else:
                    # finished all segments
                    self.stop()
                    return

    def is_running(self):
        return self.running

class GcodeAnimationControl():
    """Interface graphique pour contrôler GcodeAnimator"""
    def __init__(self, animator, parent=None):
        #super(GcodeAnimationControl, self).__init__(parent)
        self.animator = animator

        self.ui1 = QtGui.QWidget()
        self.ui1.setWindowTitle("Animation Control")

        self.ui2 = QtGui.QWidget()
        self.ui2.setWindowTitle("Tool Position")
        
        self.form = [self.ui1,self.ui2]

        # Layout principal vertical
        layout = QtGui.QVBoxLayout(self.ui1)
        
        # Boutons de contrôle dans un layout horizontal
        btnLayout = QtGui.QHBoxLayout()
        
        # Bouton Play
        self.playBtn = QtGui.QPushButton()
        self.playBtn.setIcon(QtGui.QIcon(":/icons/media-playback-start.svg"))
        self.playBtn.setToolTip("Play")
        self.playBtn.clicked.connect(self.play)
        
        # Bouton Pause
        self.pauseBtn = QtGui.QPushButton()
        self.pauseBtn.setIcon(QtGui.QIcon(":/icons/media-playback-pause.svg"))
        self.pauseBtn.setToolTip("Pause")
        self.pauseBtn.clicked.connect(self.pause)
        
        # Bouton Stop
        self.stopBtn = QtGui.QPushButton()
        self.stopBtn.setIcon(QtGui.QIcon(":/icons/media-playback-stop.svg"))
        self.stopBtn.setToolTip("Stop")
        self.stopBtn.clicked.connect(self.stop)
        
        # Bouton Step
        self.stepBtn = QtGui.QPushButton()
        self.stepBtn.setIcon(QtGui.QIcon(":/icons/media-skip-forward.svg"))
        self.stepBtn.setToolTip("Single Step")
        self.stepBtn.clicked.connect(self.step)
        
        # Contrôle de vitesse
        speedLayout = QtGui.QHBoxLayout()
        speedLayout.addWidget(QtGui.QLabel("Speed:"))
        self.speedSpinBox = QtGui.QDoubleSpinBox()
        self.speedSpinBox.setRange(0.1, 1000.0)
        self.speedSpinBox.setValue(self.animator.speed)
        self.speedSpinBox.setSuffix(" mm/s")
        self.speedSpinBox.valueChanged.connect(self.speedChanged)
        speedLayout.addWidget(self.speedSpinBox)
        
        # Contrôle de frequence
        frequenceLayout = QtGui.QHBoxLayout()
        frequenceLayout.addWidget(QtGui.QLabel("Frequence:"))
        self.frequenceSpinBox = QtGui.QDoubleSpinBox()
        self.frequenceSpinBox.setRange(0., 1000.0)
        self.frequenceSpinBox.setValue(self.animator.frequence_cut)
        self.frequenceSpinBox.valueChanged.connect(self.frequenceChanged)
        frequenceLayout.addWidget(self.frequenceSpinBox)
        
        # Include Rapid moves checkbox
        self.rapidCheckBox = QtGui.QCheckBox("Include Rapid Moves")
        self.rapidCheckBox.setChecked(self.animator.include_rapid)
        self.rapidCheckBox.stateChanged.connect(self.rapidChanged)
        
        # Ajouter les widgets aux layouts
        btnLayout.addWidget(self.playBtn)
        btnLayout.addWidget(self.pauseBtn)
        btnLayout.addWidget(self.stopBtn)
        btnLayout.addWidget(self.stepBtn)
        
        layout.addLayout(btnLayout)
        layout.addLayout(speedLayout)
        layout.addLayout(frequenceLayout)
        layout.addWidget(self.rapidCheckBox)

        layoutToolPos = QtGui.QVBoxLayout(self.ui2)
        self.toolPosXLabel = QtGui.QLabel("X: 0.0")
        self.toolPosYLabel = QtGui.QLabel("Y: 0.0")
        self.toolPosZLabel = QtGui.QLabel("Z: 0.0")

        layoutToolPos.addWidget(self.toolPosXLabel)
        layoutToolPos.addWidget(self.toolPosYLabel)
        layoutToolPos.addWidget(self.toolPosZLabel)
        
        # Timer pour mettre à jour l'état des boutons
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.updateButtons)
        self.updateTimer.start(100)  # 10 Hz
        
        self.updateButtons()

        if self.animator.tool is not None:
            self.animator.tool.Visibility = True
    
    def play(self):
        """Démarre ou reprend l'animation"""
        if not self.animator.is_running():
            self.animator.start(self.speedSpinBox.value())
        self.updateButtons()
    
    def pause(self):
        """Met en pause l'animation"""
        self.animator.pause()
        self.updateButtons()
    
    def stop(self):
        """Arrête l'animation"""
        self.animator.stop()
        self.updateButtons()
    
    def step(self):
        """Avance d'un pas"""
        self.animator.step()
        self.updateButtons()
    
    def speedChanged(self, value):
        """Appelé quand la vitesse change"""
        self.animator.set_speed(value)
    
    def frequenceChanged(self,value):
        self.animator.frequence_cut = value

    def rapidChanged(self, state):
        """Appelé quand la case Include Rapid change"""
        include_rapid = (state == QtCore.Qt.Checked)
        self.animator.include_rapid = include_rapid
        self.animator.load_paths(include_rapid)
        
    def updateButtons(self):
        """Met à jour l'état des boutons selon l'état de l'animation"""
        running = self.animator.is_running()
        self.playBtn.setEnabled(not running)
        self.pauseBtn.setEnabled(running)
        self.stopBtn.setEnabled(running)
        self.stepBtn.setEnabled(not running)

        if running:
            self.toolPosXLabel.setText(f"X: {self.animator.marker_trans.translation.getValue()[0]:.3f}")
            self.toolPosYLabel.setText(f"Y: {self.animator.marker_trans.translation.getValue()[1]:.3f}")
            self.toolPosZLabel.setText(f"Z: {self.animator.marker_trans.translation.getValue()[2]:.3f}")
    
    def closeEvent(self, event):
        """Arrête l'animation quand on ferme la fenêtre"""
        self.animator.stop()
        self.updateTimer.stop()
        if self.animator.tool is not None:
            self.animator.tool.Visibility = False
        if self.animator.stockMesh is not None:
            App.activeDocument().removeObject(self.animator.stockMesh.Name)
            self.animator.stockMesh = None
        if self.animator.toolMesh is not None:
            App.activeDocument().removeObject(self.animator.toolMesh.Name)
            self.animator.toolMesh = None
        #super(GcodeAnimationControl, self).closeEvent(event)

    def accept(self):
        self.stop()
        self.closeEvent(None)
        FreeCADGui.Control.closeDialog()
        return True
    
    def reject(self):
        self.stop()
        self.closeEvent(None)
        FreeCADGui.Control.closeDialog()
        return False
    


