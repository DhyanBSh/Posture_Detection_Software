import sys
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

# Import your modules
from ui import PostureMonitoringUI
from camera import WebcamInterface
from pose import MediaPipePoseDetector
from analyzer import PostureAnalyzer
from feedback import FeedbackManager
from database import DataManager

class PostureMonitoringSystem(QObject):
    # Signals for UI updates
    # str: Status text, float: Bad posture duration (for progress bar/timer)
    # Emit a frame and a dict of analysis results so it matches UI slot signature
    frame_ready = pyqtSignal(object, dict)
    posture_status = pyqtSignal(str, float)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.current_user = None
        
        # Initialize components
        self.camera = WebcamInterface()
        self.pose_detector = MediaPipePoseDetector()
        
        # NEW: Uses the updated Analyzer with smoothing
        self.analyzer = PostureAnalyzer()
        
        # NEW: Uses the updated Feedback manager that accepts lists of messages
        self.feedback_manager = FeedbackManager()
        
        self.data_manager = DataManager()
        
        # Setup UI
        self.app = QApplication(sys.argv)
        self.main_window = PostureMonitoringUI()
        
        # Connect signals
        self.frame_ready.connect(self.main_window.update_frame)
        self.posture_status.connect(self.main_window.update_posture_status)
        
        # Setup processing timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        
    def start_monitoring(self, user_id):
        """Start the posture monitoring for the specified user"""
        if not self.camera.initialize():
            QMessageBox.critical(self.main_window, "Error", "Failed to initialize camera")
            return False
            
        self.current_user = user_id
        self.is_running = True
        
        # Reset analyzer stats when starting a new session
        self.analyzer.reset_stats()
        
        # Start processing timer (10 FPS is sufficient for posture)
        self.timer.start(100)
        return True
        
    def stop_monitoring(self):
        """Stop the posture monitoring"""
        self.is_running = False
        self.timer.stop()
        self.camera.release()
        
    def process_frame(self):
        """Process a single frame from the camera"""
        if not self.is_running:
            return
            
        # 1. Get frame
        frame, timestamp = self.camera.get_frame()
        if frame is None:
            return
            
        try:
            # 2. Detect pose landmarks
            # Assumes pose_detector returns a dict: {'nose': {'x':0, 'y':0}, ...}
            key_points = self.pose_detector.detect(frame)
            
            # 3. Analyze Posture (Using new Analyzer logic)
            analysis_result = self.analyzer.analyze_posture(key_points)
            
            status = analysis_result['status'] # 'Active', 'Undetected', etc.
            is_good = analysis_result['is_good_posture']
            duration = analysis_result['bad_posture_duration']
            feedback_msgs = analysis_result.get('feedback_messages', [])
            
            # 4. Handle Feedback / Alerts
            if status == 'Active':
                # Check if we need to trigger an alert based on duration
                if self.analyzer.should_trigger_alert():
                    # Pass the specific messages (e.g., ["Keep head straight"])
                    self.feedback_manager.trigger_alert(feedback_msgs)
                    
                    # Reset the internal timer so we don't spam alerts immediately
                    self.analyzer.reset_bad_posture_timer()
            
            # 5. Update UI Text
            if status == 'Undetected':
                ui_message = "No User Detected"
            elif is_good:
                ui_message = "Good Posture"
            else:
                # If bad posture, show the specific reason in the UI
                if feedback_msgs:
                    ui_message = f"Fix: {', '.join(feedback_msgs)}"
                else:
                    ui_message = "Poor Posture"

            # Emit signals to UI (frame + analysis dict for the main UI updater)
            self.frame_ready.emit(frame, analysis_result)
            self.posture_status.emit(ui_message, duration)
            
            # 6. Database Logging (Throttled)
            # Log only if active and every ~10 seconds
            current_time = time.time()
            if status == 'Active' and int(current_time) % 10 == 0:
                self.data_manager.log_posture_event(
                    self.current_user, 
                    timestamp, 
                    analysis_result, 
                    not is_good # log 'is_poor'
                )

        except Exception as e:
            print(f"Error in process_frame: {e}")
            # Even if analysis fails, try to keep showing the camera feed
            self.frame_ready.emit(frame)

    def run(self):
        """Run the application"""
        self.main_window.show()
        return self.app.exec_()
        
    def shutdown(self):
        """Clean shutdown of the application"""
        self.stop_monitoring()
        self.data_manager.close()

if __name__ == "__main__":
    app = PostureMonitoringSystem()
    return_code = app.run()
    app.shutdown()
    sys.exit(return_code)