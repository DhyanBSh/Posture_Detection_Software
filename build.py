import os
import sys
import subprocess
import shutil

def build_executable():
    """Build the executable using PyInstaller"""
    
    # 1. Check/Install PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 2. Define Assets to Include
    # We need to ensure assets like the icon and sound file are tracked
    icon_path = 'icon.ico' if os.path.exists('icon.ico') else 'None'
    
    # 3. Create the Spec File content
    # UPDATED: Added 'win10toast' and 'pygame' to hiddenimports
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'cv2', 
        'mediapipe', 
        'PyQt5', 
        'cryptography', 
        'matplotlib', 
        'numpy', 
        'playsound',
        'win10toast',  # Added for Windows Notifications
        'pygame',      # Added for Audio fallback
        'pkg_resources.py2_warn' # Helper for some windows dists
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PostureMonitoringSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to True if you want to see error messages during testing
    icon={repr(icon_path) if icon_path != 'None' else 'None'}
)
"""
    
    print("Generating Spec file...")
    with open("PostureMonitoringSystem.spec", "w") as f:
        f.write(spec_content)
    
    # 4. Run PyInstaller
    print("Building executable... This may take a few minutes.")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "PostureMonitoringSystem.spec", "--clean"])
    
    # 5. Create Distribution Directory
    dist_dir = "PostureMonitoringSystem_Dist"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # 6. Copy Executable
    exe_name = "PostureMonitoringSystem.exe" if os.name == "nt" else "PostureMonitoringSystem"
    src_exe = os.path.join("dist", exe_name)
    dst_exe = os.path.join(dist_dir, exe_name)
    
    if os.path.exists(src_exe):
        shutil.copy(src_exe, dst_exe)
        print(f"Moved executable to {dist_dir}")
    else:
        print(f"ERROR: Could not find built executable at {src_exe}")
        return

    # 7. Copy External Assets (Crucial for sounds/icons to work)
    # If you have an alert sound defined in config.py, we should copy it here
    assets_to_copy = ["alert_sound.wav", "icon.ico", "config.py"]
    
    for asset in assets_to_copy:
        if os.path.exists(asset):
            shutil.copy(asset, dist_dir)
            print(f"Copied asset: {asset}")
    
    # 8. Create README
    readme_content = """
# Posture Monitoring System

## Quick Start
1. Double-click 'PostureMonitoringSystem.exe' to start.
2. Ensure you have a webcam connected.

## Troubleshooting
- If the app closes immediately, try running it from a command prompt (CMD) to see any error messages.
- Ensure 'alert_sound.wav' is in this folder if you want audio alerts.

## Privacy
All processing happens locally on your machine.
"""
    
    with open(os.path.join(dist_dir, "README.txt"), "w") as f:
        f.write(readme_content)
    
    print("-" * 50)
    print(f"Build SUCCESS! Open the folder '{dist_dir}' to run your app.")
    print("-" * 50)

if __name__ == "__main__":
    build_executable()