import os

# --- Application Core Settings ---
APP_NAME = "Posture Monitoring System"
APP_VERSION = "1.2.0"
DEFAULT_FPS = 30
MIN_FPS = 10
PROCESSING_LATENCY_MS = 100

# Logic Thresholds
BAD_POSTURE_THRESHOLD_SECONDS = 15
ALERT_REPEAT_INTERVAL_SECONDS = 60

# --- Database ---
DB_NAME = "posture_monitor.db"
DB_ENCRYPTION_KEY = "posture_monitor_key"

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.png")
ALERT_SOUND_PATH = os.path.join(ASSETS_DIR, "alert.wav")

# ==========================================
#               UI DESIGN SYSTEM
# ==========================================

# 1. Layout Dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 280  # Slightly wider for better profile spacing

# 2. Color Palette (Modern Dark Theme - UNCHANGED)
COLORS = {
    "background": "#1e1e2e",       # Deep dark blue/grey
    "surface": "#252b42",          # Slightly lighter for cards/sidebar
    "primary": "#7aa2f7",          # Soft Blue for main actions
    "secondary": "#a9b1d6",        # Muted text
    "success": "#9ece6a",          # Green for Good Posture
    "warning": "#e0af68",          # Orange for slight slouch
    "danger": "#f7768e",           # Red for Bad Posture
    "text_main": "#c0caf5",        # Bright text
    "text_dim": "#565f89",         # Dimmed text
    "border": "#414868"            # Borders
}

# 3. Typography
FONTS = {
    "header": "Segoe UI, Roboto, Helvetica, sans-serif",
    "body": "Segoe UI, Arial, sans-serif",
    "h1": "24px",
    "h2": "18px",
    "p": "14px",
    "small": "12px"
}

# 4. PyQt5 Stylesheets
STYLES = {
    # Main Window
    "main_window": f"""
        QMainWindow {{
            background-color: {COLORS['background']};
        }}
        QTabWidget::pane {{
            border: 1px solid {COLORS['border']};
            background-color: {COLORS['background']};
            border-radius: 6px;
        }}
        QTabBar::tab {{
            background: {COLORS['surface']};
            color: {COLORS['text_dim']};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {COLORS['primary']};
            color: #1a1b26; /* Dark text on active tab */
            font-weight: bold;
        }}
    """,
    
    # Sidebar Container
    "sidebar": f"""
        QFrame {{
            background-color: {COLORS['surface']};
            border-right: 1px solid {COLORS['border']};
        }}
        QLabel {{
            color: {COLORS['text_main']};
            font-family: {FONTS['header']};
        }}
        /* GroupBox Styling inside Sidebar */
        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 20px;
            font-weight: bold;
            color: {COLORS['primary']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px;
            background-color: {COLORS['surface']}; 
        }}
    """,

    # --- NEW: Profile Dropdown Style ---
    # Makes the dropdown look like a distinct input field
    "user_combo": f"""
        QComboBox {{
            background-color: {COLORS['background']}; /* Darker than sidebar */
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px 12px;
            color: {COLORS['text_main']};
            font-size: 14px;
        }}
        QComboBox:hover {{
            border: 1px solid {COLORS['primary']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
    """,

    # --- NEW: Profile Action Buttons (+ / -) ---
    # Makes them look like tools/icons rather than text buttons
    "icon_btn": f"""
        QPushButton {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            color: {COLORS['primary']};
            font-weight: bold;
            font-size: 16px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['primary']};
            color: #1a1b26;
            border: 1px solid {COLORS['primary']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['secondary']};
        }}
    """,
    
    # Status Cards
    "status_card_good": f"""
        QFrame {{
            background-color: rgba(158, 206, 106, 0.1); /* Transparent Success Green */
            border: 1px solid {COLORS['success']};
            border-radius: 12px;
        }}
        QLabel {{ color: {COLORS['success']}; font-weight: bold; font-size: 16px; }}
    """,
    
    "status_card_bad": f"""
        QFrame {{
            background-color: rgba(247, 118, 142, 0.1); /* Transparent Danger Red */
            border: 1px solid {COLORS['danger']};
            border-radius: 12px;
        }}
        QLabel {{ color: {COLORS['danger']}; font-weight: bold; font-size: 16px; }}
    """,

    # Main Action Button (Start/Stop)
    "btn_primary": f"""
        QPushButton {{
            background-color: {COLORS['primary']};
            color: #1a1b26;
            border-radius: 8px;
            padding: 12px;
            font-weight: bold;
            font-size: 14px;
            letter-spacing: 1px;
        }}
        QPushButton:hover {{
            background-color: #89b4fa;
            margin-top: -2px; /* Slight lift effect */
        }}
        QPushButton:pressed {{
            background-color: #6e91df;
            margin-top: 0px;
        }}
    """,
    
    # Secondary Buttons (Settings/Refresh)
    "btn_secondary": f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid {COLORS['border']};
            color: {COLORS['secondary']};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            border: 1px solid {COLORS['primary']};
            color: {COLORS['primary']};
            background-color: {COLORS['surface']};
        }}
    """,

    # Progress Bar
    "progress_bar": f"""
        QProgressBar {{
            border: none;
            border-radius: 4px;
            background-color: {COLORS['background']};
            text-align: center;
            color: {COLORS['text_main']};
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['danger']};
            border-radius: 4px;
        }}
    """
}

# Pose Detection specific settings
POSE_DETECTION_CONFIDENCE = 0.6
POSE_TRACKING_CONFIDENCE = 0.6