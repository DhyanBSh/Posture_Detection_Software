# camera.py
import cv2
import time
import threading
from queue import Queue

class WebcamInterface:
    def __init__(self, camera_id=0, fps=15):
        self.camera_id = camera_id
        self.fps = fps
        self.cap = None
        self.frame_queue = Queue(maxsize=2)
        self.running = False
        self.thread = None
        self.last_frame_time = 0
        self.frame_interval = 1.0 / fps
    
    def initialize(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise Exception(f"Could not open camera with ID {self.camera_id}")
        
        # Set resolution to at least 720p
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        return True
    
    def start(self):
        if not self.cap:
            self.initialize()
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
    
    def _capture_loop(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.1)  # Don't burn CPU if camera is not available
                continue
                
            current_time = time.time()
            if current_time - self.last_frame_time < self.frame_interval:
                continue
                
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame.copy())  # Make a copy to ensure thread safety
                    else:
                        # Replace the oldest frame
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put(frame.copy())
                        except:
                            pass
                    
                    self.last_frame_time = current_time
            except Exception as e:
                print(f"Error capturing frame: {e}")
                time.sleep(0.1)  # Wait a bit before trying again
    
    def get_frame(self):
        try:
            frame = self.frame_queue.get_nowait()
            return frame, time.time()
        except:
            return None, None
    
    def is_available(self):
        if not self.cap:
            return False
        return self.cap.isOpened()
        
    def release(self):
        """Alias for stop() for compatibility"""
        self.stop()