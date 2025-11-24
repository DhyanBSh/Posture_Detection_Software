import sys
import os

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import cv2
import numpy as np
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSlider, QCheckBox, QTabWidget, QGroupBox, 
    QMessageBox, QLineEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPalette, QColor

# Plotting
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Custom Modules
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, ICON_PATH, STYLES, COLORS, 
    SIDEBAR_WIDTH, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
)
from database import DataManager
from user_profile import UserProfile
from camera import WebcamInterface
from pose import MediaPipePoseDetector
from analyzer import PostureAnalyzer
from feedback import FeedbackManager

# ------------------- VIDEO THREAD -------------------
class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray, dict)

    def __init__(self, camera, pose_detector, posture_analyzer):
        super().__init__()
        self.camera = camera
        self.pose_detector = pose_detector
        self.posture_analyzer = posture_analyzer
        self.running = True

    def run(self):
        while self.running:
            frame, timestamp = self.camera.get_frame()
            if frame is not None:
                try:
                    # --- CRITICAL FIX ---
                    # Uses the new single 'detect' method from pose.py
                    key_points = self.pose_detector.detect(frame)
                    
                    # Analyze Posture
                    posture_data = self.posture_analyzer.analyze_posture(key_points)
                    
                    # Emit Result
                    self.change_pixmap_signal.emit(frame, posture_data)
                    
                except Exception as e:
                    # Print error only once to avoid spamming if needed
                    pass
            
            self.msleep(30) # ~30 FPS Cap

    def stop(self):
        self.running = False
        self.wait()

# ------------------- MAIN UI -------------------
class PostureMonitoringUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Managers
        self.data_manager = DataManager()
        self.camera = WebcamInterface()
        self.pose_detector = MediaPipePoseDetector()
        self.posture_analyzer = PostureAnalyzer()
        self.feedback_manager = FeedbackManager()

        # State
        self.current_user = None
        self.users = {}
        self.monitoring = False
        self.video_thread = None
        self.session_start_time = None

        self.setup_window()
        self.init_ui()
        
        # Load users immediately
        self.load_users()

        # Timer for Session Duration
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_session_timer)
        self.stats_timer.start(1000)

    def setup_window(self):
        self.setWindowTitle("Posture AI Monitor")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setStyleSheet(STYLES["main_window"])

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setStyleSheet(STYLES["sidebar"])
        self.setup_sidebar_content()
        main_layout.addWidget(self.sidebar)

        # 2. Content Area
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(STYLES["main_window"])
        
        self.monitor_tab = QWidget()
        self.setup_monitor_tab()
        self.reports_tab = QWidget()
        self.setup_reports_tab()
        self.settings_tab = QWidget()
        self.setup_settings_tab()

        self.tabs.addTab(self.monitor_tab, "Live Monitor")
        self.tabs.addTab(self.reports_tab, "Reports")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        content_layout.addWidget(self.tabs)
        main_layout.addWidget(self.content_area)

    # ------------------- SIDEBAR -------------------
    def setup_sidebar_content(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Posture AI")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['primary']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # User Selection
        user_group = QGroupBox("User Profile")
        user_group.setStyleSheet("border: none;")
        user_layout = QVBoxLayout(user_group)
        self.user_combo = QComboBox()
        self.user_combo.setStyleSheet(f"padding: 8px; background: {COLORS['background']}; color: white;")
        self.user_combo.currentIndexChanged.connect(self.change_user)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 30)
        add_btn.setStyleSheet(STYLES['btn_secondary'])
        add_btn.clicked.connect(self.add_user)
        
        del_btn = QPushButton("-")
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet(STYLES['btn_secondary'])
        del_btn.clicked.connect(self.delete_user)
        
        btn_layout.addWidget(self.user_combo)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        user_layout.addLayout(btn_layout)
        layout.addWidget(user_group)

        # Status Card
        self.status_card = QFrame()
        self.status_card.setStyleSheet(STYLES["status_card_good"])
        card_layout = QVBoxLayout(self.status_card)
        
        self.status_icon = QLabel("✓")
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setStyleSheet("font-size: 48px; border: none;")
        
        self.status_text = QLabel("Good Posture")
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        
        self.feedback_subtext = QLabel("Keep it up!")
        self.feedback_subtext.setAlignment(Qt.AlignCenter)
        self.feedback_subtext.setWordWrap(True)
        self.feedback_subtext.setStyleSheet("font-size: 12px; color: #ccc; border: none;")

        card_layout.addWidget(self.status_icon)
        card_layout.addWidget(self.status_text)
        card_layout.addWidget(self.feedback_subtext)
        layout.addWidget(self.status_card)

        # Timer
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-family: monospace; font-size: 20px; color: #fff;")
        layout.addWidget(self.timer_label)

        # Start Button
        layout.addStretch()
        self.start_btn = QPushButton("START MONITORING")
        self.start_btn.setStyleSheet(STYLES["btn_primary"])
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self.toggle_monitoring)
        layout.addWidget(self.start_btn)

    # ------------------- TABS -------------------
    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.monitor_tab)
        
        self.video_frame = QLabel("Camera Feed Offline")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 10px;")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_frame)

        metrics_layout = QHBoxLayout()
        self.neck_val = self.create_metric_label("Neck Angle")
        self.shoulders_val = self.create_metric_label("Shoulders")
        self.spine_val = self.create_metric_label("Spine")
        metrics_layout.addWidget(self.neck_val)
        metrics_layout.addWidget(self.shoulders_val)
        metrics_layout.addWidget(self.spine_val)
        layout.addLayout(metrics_layout)

    def create_metric_label(self, title):
        frame = QFrame()
        frame.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 6px; padding: 10px;")
        l = QVBoxLayout(frame)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #888; font-size: 12px;")
        val_lbl = QLabel("--")
        val_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        val_lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(title_lbl)
        l.addWidget(val_lbl, 0, Qt.AlignCenter)
        return frame

    def setup_reports_tab(self):
        layout = QVBoxLayout(self.reports_tab)
        controls = QHBoxLayout()
        self.days_combo = QComboBox()
        self.days_combo.addItems(["Last 7 Days", "Last 30 Days"])
        refresh = QPushButton("Refresh")
        refresh.setStyleSheet(STYLES["btn_secondary"])
        refresh.clicked.connect(self.update_reports)
        controls.addWidget(QLabel("Range:"))
        controls.addWidget(self.days_combo)
        controls.addWidget(refresh)
        controls.addStretch()
        layout.addLayout(controls)

        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor=COLORS['background'])
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setAlignment(Qt.AlignTop)

        grp = QGroupBox("Notifications")
        grp.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLORS['border']}; margin-top: 10px; }}")
        l = QVBoxLayout(grp)
        self.vis_alert_chk = QCheckBox("Visual Popups")
        self.aud_alert_chk = QCheckBox("Audio Alert")
        self.vis_alert_chk.setChecked(True)
        self.aud_alert_chk.setChecked(True)
        l.addWidget(self.vis_alert_chk)
        l.addWidget(self.aud_alert_chk)
        layout.addWidget(grp)

        layout.addWidget(self.create_slider_setting("Neck Threshold", 10, 60, 30, "neck_slider"))
        layout.addWidget(self.create_slider_setting("Shoulder Threshold", 5, 30, 10, "shoulder_slider"))
        layout.addWidget(self.create_slider_setting("Spine Threshold", 5, 45, 15, "spine_slider"))
        
        btn = QPushButton("Save Settings")
        btn.setStyleSheet(STYLES["btn_primary"])
        btn.clicked.connect(self.save_settings)
        layout.addWidget(btn)

    def create_slider_setting(self, label, min_val, max_val, default, attr_name):
        w = QWidget()
        l = QVBoxLayout(w)
        lbl = QLabel(f"{label}: {default}")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.valueChanged.connect(lambda v: lbl.setText(f"{label}: {v}"))
        setattr(self, attr_name, slider)
        l.addWidget(lbl)
        l.addWidget(slider)
        return w

    # ------------------- LOGIC -------------------
    def toggle_monitoring(self):
        if not self.monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        if not self.current_user:
            QMessageBox.warning(self, "Error", "Please select a user.")
            return

        try:
            self.camera.initialize()
            self.camera.start()
            
            self.video_thread = VideoThread(self.camera, self.pose_detector, self.posture_analyzer)
            self.video_thread.change_pixmap_signal.connect(self.update_frame)
            self.video_thread.start()
            
            self.monitoring = True
            self.session_start_time = datetime.now()
            self.start_btn.setText("STOP MONITORING")
            self.start_btn.setStyleSheet("background-color: #f7768e; color: white; font-weight: bold; border-radius: 6px;")
            
            # Start Session
            sid = self.data_manager.start_session(self.current_user.user_id)
            self.current_user.set_current_session(sid)
            self.posture_analyzer.reset_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", str(e))

    def stop_monitoring(self):
        if self.video_thread:
            self.video_thread.stop()
        self.camera.stop()
        
        if self.current_user and self.current_user.get_current_session():
            stats = self.posture_analyzer.get_posture_stats()
            self.data_manager.end_session(
                self.current_user.get_current_session(),
                stats.get('good_posture_seconds', 0),
                stats.get('bad_posture_seconds', 0)
            )
        
        self.monitoring = False
        self.start_btn.setText("START MONITORING")
        self.start_btn.setStyleSheet(STYLES["btn_primary"])
        self.video_frame.setText("Monitoring Paused")
        self.video_frame.setPixmap(QPixmap())

    def update_frame(self, frame, data):
        # Update Video
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.video_frame.setPixmap(QPixmap.fromImage(qt_img).scaled(
                self.video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        except: pass

        # Update UI Stats
        status = data.get('status', 'Undetected')
        is_good = data.get('is_good_posture', False)
        msgs = data.get('feedback_messages', [])
        
        # Check Alerts logic here (UI Thread is safe for simple checks)
        if status == 'Active':
            if self.posture_analyzer.should_trigger_alert():
                self.feedback_manager.trigger_alert(msgs)
                self.posture_analyzer.reset_bad_posture_timer()

        # Update Cards
        if status == 'Undetected':
            self.status_card.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 10px;")
            self.status_icon.setText("?")
            self.status_text.setText("No User")
            self.feedback_subtext.setText("Waiting...")
        elif is_good:
            self.status_card.setStyleSheet(STYLES["status_card_good"])
            self.status_icon.setText("✓")
            self.status_text.setText("Good Posture")
            self.feedback_subtext.setText("Great job!")
        else:
            self.status_card.setStyleSheet(STYLES["status_card_bad"])
            self.status_icon.setText("!")
            self.status_text.setText("Poor Posture")
            self.feedback_subtext.setText("\n".join(msgs) if msgs else "Fix posture")

        # Update Metrics
        def set_val(w, v):
            try: w.layout().itemAt(1).widget().setText(f"{int(v)}°" if v else "--")
            except: pass
            
        set_val(self.neck_val, data.get('neck_angle'))
        set_val(self.shoulders_val, data.get('shoulder_alignment'))
        set_val(self.spine_val, data.get('spine_curvature'))

    def update_posture_status(self, message, duration):
        """Slot to receive short status updates from external controller.

        `message` is a short string (e.g., 'Good Posture', 'No User Detected',
        'Fix: chin up'), and `duration` is seconds of bad posture (float).
        """
        try:
            # Update the main status text
            if message:
                self.status_text.setText(message)

            # If duration is relevant, show a short message in the subtext
            if duration is not None and duration > 0:
                # Show seconds of bad posture briefly
                self.feedback_subtext.setText(f"Bad posture for {int(duration)}s")
            else:
                # Leave existing feedback if no duration
                pass
        except Exception:
            pass

    # ------------------- HELPERS -------------------
    def update_session_timer(self):
        if self.monitoring and self.session_start_time:
            delta = datetime.now() - self.session_start_time
            s = int(delta.total_seconds())
            h, r = divmod(s, 3600)
            m, s = divmod(r, 60)
            self.timer_label.setText(f"{h:02}:{m:02}:{s:02}")

    def load_users(self):
        # FIX FOR KEYERROR: Block signals while populating
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        try:
            users = self.data_manager.get_users()
            self.users = {}
            for uid, name in users:
                self.users[uid] = UserProfile(uid, name, {})
                self.user_combo.addItem(name, uid)
            
            self.user_combo.blockSignals(False)
            if users:
                self.user_combo.setCurrentIndex(0)
                self.change_user(0)
        except Exception as e:
            print(f"User Load Error: {e}")
            self.user_combo.blockSignals(False)

    def change_user(self, idx):
        if idx < 0: return
        uid = self.user_combo.itemData(idx)
        if uid in self.users:
            self.current_user = self.users[uid]
            settings = self.data_manager.get_user_settings(uid)
            if settings:
                self.current_user.settings = settings
                self.neck_slider.setValue(settings.get("neck_angle_threshold", 30))
                self.shoulder_slider.setValue(settings.get("shoulder_alignment_threshold", 10))
                self.spine_slider.setValue(settings.get("spine_curvature_threshold", 15))
                self.vis_alert_chk.setChecked(settings.get("visual_alerts", True))
                self.aud_alert_chk.setChecked(settings.get("audio_alerts", True))
                
                # Apply immediately
                self.posture_analyzer.neck_angle_threshold = settings.get("neck_angle_threshold", 30)
                self.posture_analyzer.shoulder_alignment_threshold = settings.get("shoulder_alignment_threshold", 10)
                self.posture_analyzer.spine_curvature_threshold = settings.get("spine_curvature_threshold", 15)

    def add_user(self):
        name, ok = QLineEdit.getText(self, "New User", "Enter Name:")
        if ok and name:
            self.data_manager.create_user(name)
            self.load_users()

    def delete_user(self):
        if self.current_user:
            self.data_manager.delete_user_data(self.current_user.user_id)
            self.load_users()

    def save_settings(self):
        if not self.current_user: return
        s = {
            "neck_angle_threshold": self.neck_slider.value(),
            "shoulder_alignment_threshold": self.shoulder_slider.value(),
            "spine_curvature_threshold": self.spine_slider.value(),
            "visual_alerts": self.vis_alert_chk.isChecked(),
            "audio_alerts": self.aud_alert_chk.isChecked(),
        }
        self.data_manager.update_user_settings(self.current_user.user_id, s)
        self.change_user(self.user_combo.currentIndex()) # Re-apply
        QMessageBox.information(self, "Success", "Settings Saved")

    def update_reports(self):
        if not self.current_user: return
        days = 30 if "30" in self.days_combo.currentText() else 7
        stats = self.data_manager.get_daily_stats(self.current_user.user_id, days)
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if stats:
            dates = [x[0] for x in stats]
            good = [x[1]/60 for x in stats]
            bad = [x[2]/60 for x in stats]
            x = np.arange(len(dates))
            ax.bar(x, good, 0.4, label='Good', color=COLORS['success'])
            ax.bar(x, bad, 0.4, bottom=good, label='Bad', color=COLORS['danger'])
            ax.set_xticks(x)
            ax.set_xticklabels(dates, rotation=45, color='white')
            ax.legend()
        
        ax.set_facecolor(COLORS['background'])
        self.figure.patch.set_facecolor(COLORS['background'])
        ax.tick_params(colors='white')
        self.canvas.draw()

def apply_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS['background']))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(COLORS['surface']))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS['surface']))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(COLORS['surface']))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(COLORS['primary']))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = PostureMonitoringUI()
    window.show()
    sys.exit(app.exec_())