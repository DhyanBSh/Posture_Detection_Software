import os
import platform
import time
import threading
from config import ALERT_SOUND_PATH, ALERT_REPEAT_INTERVAL_SECONDS

class FeedbackManager:
    def __init__(self):
        self.last_alert_time = 0
        self.alert_thread = None
        self.visual_alerts_enabled = True
        self.audio_alerts_enabled = True
        self.alert_repeat_interval = ALERT_REPEAT_INTERVAL_SECONDS
    
    def set_settings(self, visual_alerts=True, audio_alerts=True, repeat_interval=60):
        self.visual_alerts_enabled = visual_alerts
        self.audio_alerts_enabled = audio_alerts
        self.alert_repeat_interval = repeat_interval
    
    def trigger_alert(self, messages):
        """
        Accepts a string OR a list of strings.
        Example input: ["Keep head straight", "Straighten your back"]
        """
        current_time = time.time()
        
        if current_time - self.last_alert_time < self.alert_repeat_interval:
            return
            
        self.last_alert_time = current_time
        
        # Format the message
        if isinstance(messages, list) and messages:
            # Joins messages: "Keep head straight & Straighten your back"
            final_message = " & ".join(messages)
        elif isinstance(messages, str):
            final_message = messages
        else:
            final_message = "Please correct your posture"
        
        self.alert_thread = threading.Thread(
            target=self._send_alerts,
            args=(final_message,)
        )
        self.alert_thread.daemon = True
        self.alert_thread.start()
    
    def _send_alerts(self, message):
        if self.visual_alerts_enabled:
            self._send_visual_alert(message)
        
        if self.audio_alerts_enabled:
            self._play_alert_sound()
            
    # ... (Keep _send_visual_alert and _play_alert_sound exactly as they were) ...
    def _send_visual_alert(self, message):
        system = platform.system()
        try:
            if system == "Windows":
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast("Posture Alert", message, icon_path=None, duration=5)
            elif system == "Darwin":  # macOS
                os.system(f'osascript -e \'display notification "{message}" with title "Posture Alert"\'')
            elif system == "Linux":
                try:
                    import dbus
                    bus = dbus.SessionBus()
                    notify = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
                    notify_interface = dbus.Interface(notify, 'org.freedesktop.Notifications')
                    notify_interface.Notify('Posture Alert', 0, '', 'Posture Alert', message, [], {}, 5000)
                except:
                    os.system(f'notify-send "Posture Alert" "{message}"')
        except Exception as e:
            print(f"Error sending visual alert: {e}")

    def _play_alert_sound(self):
        try:
            if os.path.exists(ALERT_SOUND_PATH):
                if platform.system() == "Windows":
                    import winsound
                    winsound.PlaySound(ALERT_SOUND_PATH, winsound.SND_FILENAME)
                else:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(ALERT_SOUND_PATH)
                    pygame.mixer.music.play()
            else:
                if platform.system() == "Windows":
                    import winsound
                    winsound.Beep(1000, 500)
                else:
                    print('\a')
        except Exception as e:
            print(f"Error playing alert sound: {e}")